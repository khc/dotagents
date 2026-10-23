import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "dot"
sys.path.insert(0, str(PLUGIN / "src"))

from agents.workflows.review import aggregate_verdict, read_review_context, validate_review_context  # noqa: E402


def finding(finding_id="F1", severity="high", blocking=True, status="open", **extra):
    return {
        "finding_id": finding_id,
        "category": "Bugs",
        "location": "src/a.ts:10",
        "description": "d",
        "severity": severity,
        "confidence": "confirmed",
        "fix_direction": "f",
        "blocking": blocking,
        "status": status,
        "evidence_refs": [{"source": "direct", "location": "src/a.ts:10"}],
        **extra,
    }


def gap(material=True):
    return {"description": "no plan supplied", "material": material, "effect": "requirements unchecked"}


def context(findings=(), gaps=(), verdict=None, **extra):
    findings, gaps = list(findings), list(gaps)
    return {
        "schema_version": 2,
        "target": "src/a.ts",
        "review_mode": "path",
        "source_workflow": "standalone",
        "findings": findings,
        "verification_gaps": gaps,
        "summary": "s",
        "reasoning": "r",
        "verdict": verdict or aggregate_verdict(findings, gaps),
        **extra,
    }


class VerdictTests(unittest.TestCase):
    def test_aggregation_table(self):
        cases = {
            "no findings": ((), (), "ready"),
            "material gap beats clean findings": ((), (gap(),), "not-ready"),
            "non-material gap is ignored": ((), (gap(False),), "ready"),
            "open blocking high": ((finding(),), (), "not-ready"),
            "open blocking critical": ((finding(severity="critical"),), (), "not-ready"),
            "medium only": ((finding(severity="medium"),), (), "ready-with-fixes"),
            "low only (non-blocking)": ((finding(severity="low", blocking=False),), (), "ready"),
            "mixed": ((finding(severity="low", blocking=False), finding("F2", "medium")), (), "ready-with-fixes"),
            "addressed high": ((finding(status="addressed"),), (), "ready"),
            "deferred high": ((finding(status="deferred"),), (), "ready"),
        }
        for name, (findings, gaps, expected) in cases.items():
            with self.subTest(name):
                self.assertEqual(aggregate_verdict(list(findings), list(gaps)), expected)


class ValidationTests(unittest.TestCase):
    def reject(self, ctx, fragment):
        with self.assertRaises(ValueError) as caught:
            validate_review_context(ctx)
        self.assertIn(fragment, str(caught.exception))

    def test_legacy_context_passes_unchanged(self):
        for legacy in ({"summary": "legacy review"}, {"findings": [], "verdict": "ready"}, []):
            with self.subTest(legacy=legacy):
                self.assertIs(validate_review_context(legacy), legacy)

    def test_valid_v2(self):
        ctx = context([finding(), finding("F2", "low", blocking=False)], [gap(False)])
        self.assertIs(validate_review_context(ctx), ctx)

    def test_invalid_enums(self):
        for key, value in (("severity", "urgent"), ("confidence", "sure"), ("status", "closed"), ("category", "Style")):
            with self.subTest(key=key):
                self.reject(context([finding(**{key: value})], verdict="not-ready"), f".{key} must be one of")
        self.reject(context(review_mode="repo"), "review_mode")
        self.reject(context(source_workflow="chat"), "source_workflow")
        self.reject(context(schema_version=3), "schema_version")

    def test_missing_required_fields(self):
        for key in ("finding_id", "blocking", "status", "evidence_refs", "location", "description", "fix_direction"):
            with self.subTest(key=key):
                broken = finding()
                del broken[key]
                with self.assertRaises(ValueError):
                    validate_review_context(context([broken], verdict="not-ready"))
        for key in ("target", "summary", "reasoning", "findings", "verification_gaps"):
            with self.subTest(key=key):
                ctx = context()
                del ctx[key]
                with self.assertRaises(ValueError):
                    validate_review_context(ctx)

    def test_duplicate_finding_id(self):
        self.reject(context([finding("F1"), finding("F1")], verdict="not-ready"), "unique")

    def test_finding_id_format(self):
        self.reject(context([finding("one")], verdict="not-ready"), "F<n>")

    def test_verdict_mismatch(self):
        self.reject(context([finding()], verdict="ready"), "disagrees")
        self.reject(context([], [gap()], verdict="ready"), "disagrees")
        self.reject(context([finding(severity="medium")], verdict="ready"), "disagrees")

    def test_non_blocking_high_needs_disposition(self):
        bare = finding(blocking=False)
        self.reject(context([bare], verdict="ready"), "disposition")
        ok = finding(blocking=False, disposition={"authority": "user", "rationale": "accepted risk"})
        validate_review_context(context([ok], verdict="ready"))

    def test_research_evidence_needs_url_and_quote(self):
        ref = {"source": "research", "location": "docs"}
        self.reject(context([finding(evidence_refs=[ref])], verdict="not-ready"), "url and quote")
        ref.update(url="https://example.com", quote="exact")
        validate_review_context(context([finding(evidence_refs=[ref])], verdict="not-ready"))

    def test_gap_shape(self):
        self.reject(context(gaps=[{"description": "x", "material": "yes", "effect": "y"}], verdict="ready"), "material")


class LegacyReadTests(unittest.TestCase):
    def test_v1_gets_explicit_unavailable_fields(self):
        v1 = json.loads((PLUGIN / "evals/review/files/legacy-v1/context.json").read_text())
        read = read_review_context(copy.deepcopy(v1))
        self.assertEqual(read["verdict"], v1["verdict"])
        self.assertEqual(read["schema_version"], 1)
        self.assertEqual(read["verification_gaps"], "unavailable")
        self.assertEqual(read["subject"], "unavailable")
        for original, adapted in zip(v1["findings"], read["findings"]):
            self.assertEqual(adapted["finding_id"], "unavailable")
            self.assertEqual(adapted["blocking"], "unavailable")
            self.assertEqual(adapted["evidence_refs"], "unavailable")
            self.assertEqual(adapted["fix_direction"], original["fix_direction"])

    def test_v2_is_untouched(self):
        ctx = context([finding()])
        self.assertIs(read_review_context(ctx), ctx)

    def test_minimal_legacy_context_still_reads(self):
        self.assertEqual(read_review_context({"summary": "legacy review"})["summary"], "legacy review")


class HandoffAlignmentTests(unittest.TestCase):
    def test_finding_id_maps_to_handoff_id(self):
        schema = json.loads((PLUGIN / "skills/workflow/schemas/review-handoff.schema.json").read_text())
        item = schema["properties"]["findings"]["items"]
        handoff = {**finding(), "id": finding()["finding_id"]}
        self.assertTrue(set(item["required"]) <= set(handoff))
        for key in ("blocking", "status", "evidence_refs", "lens", "disposition"):
            self.assertIn(key, item["properties"])
        self.assertIn("verification_gaps", schema["properties"])


class HelperCliTests(unittest.TestCase):
    def run_review(self, project, payload):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        return subprocess.run(
            [sys.executable, "-B", str(PLUGIN / "scripts/review_workflow.py"), "--agent", "codex",
             "--scope", str(project), "--context", json.dumps(payload)],
            cwd=project, env=env, text=True, capture_output=True,
        )

    def test_roundtrip_and_rejection(self):
        with tempfile.TemporaryDirectory(prefix="review contract ") as directory:
            project = Path(directory)
            subprocess.run(["git", "init", "--quiet", str(project)], check=True)
            saved = self.run_review(project, context([finding()]))
            self.assertEqual(saved.returncode, 0, saved.stderr)
            row = sqlite3.connect(project / ".sidecar/sidecar.db").execute(
                "SELECT context FROM sidecar WHERE uuid = ?", (saved.stdout.strip(),)
            ).fetchone()
            self.assertEqual(json.loads(row[0])["findings"][0]["finding_id"], "F1")
            rejected = self.run_review(project, context([finding()], verdict="ready"))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("disagrees", rejected.stderr)
            count = sqlite3.connect(project / ".sidecar/sidecar.db").execute("SELECT COUNT(*) FROM sidecar").fetchone()
            self.assertEqual(count[0], 1)

    def test_invalid_context_leaves_no_sidecar(self):
        with tempfile.TemporaryDirectory(prefix="review contract ") as directory:
            project = Path(directory)
            subprocess.run(["git", "init", "--quiet", str(project)], check=True)
            self.assertNotEqual(self.run_review(project, context([finding("bad")])).returncode, 0)
            self.assertFalse((project / ".sidecar").exists())


if __name__ == "__main__":
    unittest.main()

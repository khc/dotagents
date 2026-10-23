import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "dot"
sys.path.insert(0, str(PLUGIN / "src"))

from agents.workflows.review_subject import Args, capture_subject  # noqa: E402

EXECUTION = {
    "strategy": "single", "override": "none", "reason": "thresholds unset and no risk-sensitive content",
    "signals": {"mode": "path"}, "lenses": [], "research": "not_needed", "research_excerpt_authorized": False,
}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def finding(finding_id, severity, status="open", **extra):
    return {
        "finding_id": finding_id, "category": "Bugs", "location": "src/a.ts:1", "description": "d",
        "severity": severity, "confidence": "confirmed", "fix_direction": "f", "blocking": True, "status": status,
        "evidence_refs": [{"source": "direct", "location": "src/a.ts:1", "quote": "q"}], **extra,
    }


class ReviewFixReviewFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="review flow ")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "--quiet")
        (self.repo / "src").mkdir()
        (self.repo / "src/a.ts").write_text("v1\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "--quiet", "-m", "base")

    def helper(self, name, *args):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        done = subprocess.run([sys.executable, "-B", str(PLUGIN / f"scripts/{name}_workflow.py"), *args],
                              cwd=self.repo, env=env, text=True, capture_output=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def subject(self):
        return capture_subject(Args(kind="working_tree", review_mode="path", target="src", start_path=str(self.repo)))

    def review(self, findings, verdict, subject, **extra):
        ctx = {
            "schema_version": 2, "target": "src", "review_mode": "path", "source_workflow": "standalone",
            "subject": subject, "execution": EXECUTION, "findings": findings, "verification_gaps": [],
            "summary": "s", "reasoning": "r", "verdict": verdict, **extra,
        }
        return self.helper("review", "--agent", "codex", "--scope", str(self.repo), "--context", json.dumps(ctx))

    def read(self, uuid):
        return json.loads(self.helper("fix", "get_review", "--review_uuid", uuid))["context"]

    def test_stable_ids_subject_metadata_and_verdicts_through_fix_and_re_review(self):
        first_subject = self.subject()
        first = self.review([finding("F1", "high"), finding("F2", "medium")], "not-ready", first_subject)
        saved = self.read(first)
        self.assertEqual([f["finding_id"] for f in saved["findings"]], ["F1", "F2"])
        self.assertEqual(saved["subject"], first_subject)

        self.helper("fix", "save_fix", "--agent", "codex", "--scope", str(self.repo), "--review_uuid", first,
                    "--context", json.dumps({"findings_fixed": [{"finding_id": "F1", "location": "src/a.ts:1", "description": "d"}],
                                             "summary": "fixed F1", "verification": "t"}))
        (self.repo / "src/a.ts").write_text("v2 with a line moved\n\n")  # the fix edits the file
        second_subject = self.subject()
        self.assertNotEqual(second_subject["diff_sha256"], first_subject["diff_sha256"])
        self.assertNotEqual(second_subject["content_hashes"], first_subject["content_hashes"])

        re_review = self.review(
            [finding("F2", "medium", location="src/a.ts:9"),  # still open, line moved, same identity
             finding("F1", "high", status="addressed"),  # reviewer-inspected evidence closes it
             finding("F3", "low", blocking=False)],  # a defect the fix introduced
            "ready-with-fixes", second_subject, prior_review_uuid=first)
        again = self.read(re_review)
        self.assertEqual(sorted(f["finding_id"] for f in again["findings"]), ["F1", "F2", "F3"])
        self.assertEqual({f["finding_id"]: f["status"] for f in again["findings"]}["F1"], "addressed")
        self.assertEqual(again["subject"], second_subject)
        self.assertEqual(again["verdict"], "ready-with-fixes")  # an open blocking medium finding: not acceptance
        self.assertEqual(again["prior_review_uuid"], first)

    def test_workflow_never_treats_an_unfavorable_verdict_as_acceptance(self):
        workflow = runpy.run_path(str(PLUGIN / "skills/workflow/bin/workflow.py"))

        def status(**fields):
            body = {"stage": "review", "status": "findings", "summary": "s", "review_mode": "path", **fields}
            return workflow["parse_result"](f"<ORCHESTRATION_RESULT>\n{json.dumps(body)}\n</ORCHESTRATION_RESULT>", "review")

        self.assertEqual(status(verdict="ready", findings_count=0, status="ready")["status"], "ready")
        for verdict in ("ready-with-fixes", "not-ready"):
            with self.subTest(verdict=verdict):
                self.assertEqual(status(verdict=verdict, findings_count=2)["status"], "findings")
                self.assertEqual(status(verdict=verdict, findings_count=1, status="ready")["status"], "findings")
                inconsistent = status(verdict=verdict, findings_count=0, status="findings")
                self.assertEqual(inconsistent["status"], "blocked")
        gap = status(verdict="not-ready", findings_count=0, blocker="no ticket supplied; requirements unchecked")
        self.assertEqual((gap["status"], gap["blocker"]), ("blocked", "no ticket supplied; requirements unchecked"))

    def test_re_review_that_drops_an_open_finding_is_rejected(self):
        first = self.review([finding("F1", "high"), finding("F2", "medium")], "not-ready", self.subject())
        ctx = {
            "schema_version": 2, "target": "src", "review_mode": "path", "source_workflow": "fix",
            "subject": self.subject(), "execution": EXECUTION, "findings": [finding("F1", "high", status="addressed")],
            "verification_gaps": [], "summary": "s", "reasoning": "r", "verdict": "ready", "prior_review_uuid": first,
        }
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        done = subprocess.run([sys.executable, "-B", str(PLUGIN / "scripts/review_workflow.py"), "--agent", "codex",
                               "--scope", str(self.repo), "--context", json.dumps(ctx)],
                              cwd=self.repo, env=env, text=True, capture_output=True)
        self.assertEqual(done.returncode, 2)
        self.assertIn("F2", done.stderr)


if __name__ == "__main__":
    unittest.main()

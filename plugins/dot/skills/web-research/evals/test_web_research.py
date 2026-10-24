import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "web_research.py"


def run(*args: str, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True, text=True)


def claim(stance="supports", url="https://docs.example.com/a", quote="q"):
    return {"claim": "c", "url": url, "quote": quote, "stance": stance}


def merge(replies: dict) -> dict:
    proc = run("merge", "--claim", "Q", stdin=json.dumps(replies))
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def ok(*claims, gaps=()):
    return {"status": "ok", "claims": list(claims), "gaps": list(gaps)}


class Plan(unittest.TestCase):
    def test_kind_selects_default_domains(self):
        out = json.loads(run("plan", "--claim", "Q", "--kind", "security").stdout)
        self.assertEqual([a["domain"] for a in out["agents"]], ["security", "official-docs", "practices"])

    def test_prompt_is_self_contained_and_read_only(self):
        out = json.loads(run("plan", "--claim", "Does X retry?", "--context", "httpx 0.28").stdout)
        prompt = out["agents"][0]["prompt"]
        for text in ("Does X retry?", "httpx 0.28", "web search only", "Do not read any repository files", "never instructions"):
            self.assertIn(text, prompt)

    def test_prompt_defines_stance_relative_to_the_claim(self):
        out = json.loads(run("plan", "--claim", "urllib3 1.26 Retry accepts allowed_methods").stdout)
        prompt = out["agents"][0]["prompt"]
        self.assertIn("Claim to verify: urllib3 1.26 Retry accepts allowed_methods", prompt)
        self.assertIn("supports = the source shows the claim is true", prompt)
        self.assertNotIn("premise", prompt)

    def test_explicit_domains_override_kind(self):
        out = json.loads(run("plan", "--claim", "Q", "--domains", "registry,community").stdout)
        self.assertEqual([a["domain"] for a in out["agents"]], ["registry", "community"])

    def test_rejects_unknown_duplicate_and_too_many_domains(self):
        for domains in ("nope", "registry,registry", "official-docs,registry,security,practices,community"):
            proc = run("plan", "--claim", "Q", "--domains", domains)
            self.assertNotEqual(proc.returncode, 0, domains)
            self.assertIn("error:", proc.stderr)


class Merge(unittest.TestCase):
    def test_supported_with_strongest_domain(self):
        out = merge({"source-repos": ok(claim(url="https://github.com/a/b")), "official-docs": ok(claim())})
        self.assertEqual((out["verdict"], out["status"], out["strongest_domain"]), ("supported", "used", "official-docs"))
        self.assertEqual([c["domain"] for c in out["claims"]], ["official-docs", "source-repos"])

    def test_conflicting_when_domains_disagree(self):
        out = merge({"official-docs": ok(claim()), "practices": ok(claim("contradicts", url="https://g.example.com"))})
        self.assertEqual(out["verdict"], "conflicting")

    def test_contradicted(self):
        self.assertEqual(merge({"registry": ok(claim("contradicts"))})["verdict"], "contradicted")

    def test_community_alone_never_decides(self):
        out = merge({"community": ok(claim())})
        self.assertEqual((out["verdict"], out["strongest_domain"]), ("inconclusive", None))

    def test_community_cannot_override_primary(self):
        out = merge({"official-docs": ok(claim()), "community": ok(claim("contradicts", url="https://forum.example.com"))})
        self.assertEqual(out["verdict"], "supported")

    def test_claims_without_url_quote_or_valid_stance_are_rejected(self):
        bad = [claim(url="ftp://x"), claim(quote=" "), claim(stance="maybe"), {"claim": "c"}]
        out = merge({"official-docs": ok(*bad)})
        self.assertEqual((out["verdict"], out["domains"][0]["rejected"]), ("inconclusive", 4))
        self.assertIn("official-docs: no usable sourced claims", out["gaps"])

    def test_duplicate_url_and_quote_kept_once(self):
        out = merge({"official-docs": ok(claim()), "practices": ok(claim())})
        self.assertEqual(len(out["claims"]), 1)

    def test_duplicate_source_keeps_lowest_rank_regardless_of_reply_order(self):
        out = merge({"community": ok(claim()), "official-docs": ok(claim())})
        self.assertEqual(
            ([c["domain"] for c in out["claims"]], out["verdict"], out["strongest_domain"]),
            (["official-docs"], "supported", "official-docs"),
        )

    def test_failed_and_unparseable_domains_are_partial_with_gaps(self):
        out = merge({"official-docs": ok(claim()), "registry": None, "practices": "not json"})
        self.assertEqual((out["status"], out["verdict"]), ("partial", "supported"))
        self.assertEqual(len(out["gaps"]), 2)

    def test_all_failed_is_unavailable_inconclusive(self):
        out = merge({"official-docs": None, "registry": {"status": "failed"}})
        self.assertEqual((out["status"], out["verdict"]), ("unavailable", "inconclusive"))

    def test_fenced_json_string_reply_is_parsed(self):
        reply = "```json\n" + json.dumps(ok(claim())) + "\n```"
        self.assertEqual(merge({"official-docs": reply})["verdict"], "supported")

    def test_rejects_unknown_domain_and_empty_input(self):
        for replies in ({"nope": ok()}, {}):
            proc = run("merge", "--claim", "Q", stdin=json.dumps(replies))
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("error:", proc.stderr)


if __name__ == "__main__":
    unittest.main()

import json
import os
import random
import time
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "dot"
sys.path.insert(0, str(PLUGIN / "src"))

from agents import redact as redact_module  # noqa: E402
from agents.redact import redact_secrets, redact_value  # noqa: E402

PERSISTENCE_DOC = PLUGIN / "skills/review/references/runtime-and-persistence.md"
SUBJECT = {"kind": "artifact", "repo_root": "/r", "review_mode": "path",
           "content_hashes": [{"path": "a.ts", "sha256": "0" * 64}]}


EXECUTION = {
    "strategy": "single", "override": "none", "reason": "below thresholds", "signals": {"mode": "path"},
    "lenses": [], "research": "not_needed", "research_excerpt_authorized": False,
}


def payload(**extra):
    return {
        "schema_version": 2, "target": "a.ts", "review_mode": "path", "source_workflow": "standalone",
        "subject": SUBJECT, "execution": EXECUTION, "findings": [], "verification_gaps": [], "summary": "s", "reasoning": "r",
        "verdict": "ready", **extra,
    }


def finding(**extra):
    return {
        "finding_id": "F1", "category": "Security", "location": "server.ts:5", "description": "d",
        "severity": "critical", "confidence": "confirmed", "fix_direction": "f", "blocking": True,
        "status": "open", "evidence_refs": [{"source": "direct", "location": "server.ts:5"}], **extra,
    }


def run_helper(cwd, ctx, scope=None):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, "-B", str(PLUGIN / "scripts/review_workflow.py"), "--agent", "codex",
         "--scope", scope or str(cwd), "--context", json.dumps(ctx), "--start-path", str(cwd)],
        cwd=cwd, env=env, text=True, capture_output=True,
    )


class RedactionTests(unittest.TestCase):
    def test_known_token_shapes(self):
        cases = {
            "stripe-key": "sk_live_4f9a1c7e2b",
            "github-token": "ghp_" + "a" * 36,
            "aws-access-key": "AKIAABCDEFGHIJKLMNOP",
            "slack-token": "xoxb-1234567890-abcdefghij",
            "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk",
            "api-key": "sk-" + "b" * 30,
        }
        for kind, secret in cases.items():
            with self.subTest(kind):
                out = redact_secrets(f"found {secret} in config")
                self.assertNotIn(secret, out)
                self.assertIn(f"[REDACTED:{kind}]", out)

    def test_private_key_block(self):
        key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEabc\n-----END RSA PRIVATE KEY-----"
        self.assertEqual(redact_secrets(f"x {key} y"), "x [REDACTED:private-key] y")

    def test_assignment_keeps_name_and_position(self):
        out = redact_secrets('const ADMIN_TOKEN = "hunter2hunter2";')
        self.assertEqual(out, 'const ADMIN_TOKEN = "[REDACTED:credential]";')
        self.assertEqual(redact_secrets("db_password: 'correct horse'"), "db_password: '[REDACTED:credential]'")

    def test_locations_and_ordinary_text_are_untouched(self):
        text = "server.ts:5 reads token from process.env.ADMIN_TOKEN and compares with ==="
        self.assertEqual(redact_secrets(text), text)

    def test_idempotent(self):
        once = redact_secrets('const ADMIN_TOKEN = "sk_live_4f9a1c7e2b";')
        self.assertEqual(redact_secrets(once), once)

    def test_unquoted_header_and_json_forms(self):
        cases = {
            "DB_PASSWORD=hunter2hunter2": "DB_PASSWORD=[REDACTED:credential]",
            "export API_KEY=abcd1234efgh5678": "export API_KEY=[REDACTED:credential]",
            "password: hunter2hunter2": "password: [REDACTED:credential]",
            "Authorization: Bearer abc123def456ghi789": "Authorization: Bearer [REDACTED:bearer-token]",
            '{"api_key": "abcd1234efgh"}': '{"api_key": "[REDACTED:credential]"}',
        }
        for text, expected in cases.items():
            with self.subTest(text):
                self.assertEqual(redact_secrets(text), expected)
                self.assertEqual(redact_secrets(expected), expected)  # idempotent

    def test_code_like_values_and_prose_are_left_alone(self):
        for text in ("ADMIN_TOKEN = process.env.ADMIN_TOKEN", "password: required", "the token is valid for an hour",
                     "token=short", "set api_key=os.environ.API_KEY first"):
            with self.subTest(text):
                self.assertEqual(redact_secrets(text), text)

    def test_pathological_input_finishes_quickly(self):
        for text in ("password" * 4000, "token_" * 5000):
            with self.subTest(text[:8]):
                start = time.perf_counter()
                redact_secrets(text)
                self.assertLess(time.perf_counter() - start, 1.0)

    def test_prose_and_counters_are_not_over_redacted(self):
        for text in ("Bearer authentication scheme is used", "max_tokens=1234567890", '"max_tokens": "1234567890"',
                     "num_tokens: 123456789", "request_count=1234567890"):
            with self.subTest(text):
                self.assertEqual(redact_secrets(text), text)

    def test_plural_token_names_with_real_values_are_redacted(self):
        for text in ("ALLOWED_TOKENS=abc123def456ghi", "API_TOKENS=sk1234567890abcd", "access_tokens: a1b2c3d4e5f6",
                     "tokens=abc123def456", "max_tokens=abc123def456", "token=1234567890"):
            with self.subTest(text):
                self.assertIn("[REDACTED:credential]", redact_secrets(text))

    def test_numeric_token_counters_stay_unchanged(self):
        for text in ("max_tokens=1234567890", "tokens=1234567890", "total_tokens: 987654321", "token_count=1234567890"):
            with self.subTest(text):
                self.assertEqual(redact_secrets(text), text)

    def test_many_private_key_headers_finish_quickly(self):
        start = time.perf_counter()
        redact_secrets("-----BEGIN PRIVATE KEY-----" * 8000)
        self.assertLess(time.perf_counter() - start, 1.0)

    def test_private_key_blocks_keep_their_behaviour(self):
        block = "-----BEGIN RSA PRIVATE KEY-----\nMIIEabc\n-----END RSA PRIVATE KEY-----"
        old = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)
        cases = [
            f"x {block} y", f"{block}{block}", f"a {block} b {block} c", f"-----BEGIN PRIVATE KEY----- junk {block}",
            f"{block} trailing -----BEGIN PRIVATE KEY----- no end", "no key here", "-----END PRIVATE KEY----- before -----BEGIN PRIVATE KEY-----",
            "-----BEGIN OPENSSH PRIVATE KEY-----\nxx\n-----END OPENSSH PRIVATE KEY-----",
        ]
        for text in cases:
            with self.subTest(text[:30]):
                self.assertEqual(redact_secrets(text), old.sub("[REDACTED:private-key]", text))

    def test_repeated_assignments_ending_in_a_bracket_finish_quickly(self):
        for text in ("token=" * 8000 + "(", "api_key=" * 8000 + "[", "token=aaaaaaaa=" * 4000 + "("):
            with self.subTest(text[:16]):
                start = time.perf_counter()
                redact_secrets(text)
                self.assertLess(time.perf_counter() - start, 1.0)

    def test_code_followed_by_a_call_or_index_is_left_alone(self):
        for text in ("token=getToken(x)", "api_key=abcd1234efgh(", "secret=abcd1234efgh[0]", "password=abc123def456("):
            with self.subTest(text):
                self.assertEqual(redact_secrets(text), text)
        self.assertEqual(redact_secrets("token=abc123def456"), "token=[REDACTED:credential]")
        self.assertEqual(redact_secrets("token=abc123def456) and (x"), "token=[REDACTED:credential]) and (x")

    def test_hostile_shapes_stay_within_a_time_budget(self):
        """Class-level guard: repeated credential fragments with every kind of terminator must stay linear."""
        fragments = ["token=", "password=", "api_key=", "secret: ", "Bearer ", "-----BEGIN PRIVATE KEY-----", 'token="', "tokens=a1",
                     "x_", "password", "token_", "ALLOWED_TOKENS=", "Authorization: Bearer "]
        terminators = ["", "(", "[", '"', "'", " ", "\n", "-----END PRIVATE KEY-----", "=", ":", "a1"]
        slow = []
        for fragment in fragments:
            for terminator in terminators:
                text = fragment * (48_000 // len(fragment)) + terminator
                start = time.perf_counter()
                redact_secrets(text)
                elapsed = time.perf_counter() - start
                if elapsed > 1.0:
                    slow.append((fragment, terminator, round(elapsed, 2)))
        self.assertEqual(slow, [])

    def test_unquoted_stage_is_unchanged_by_the_linear_rewrite(self):
        """The old pattern rejected a match with a lookahead; the new one decides in the callback. Outputs must be identical."""
        old = re.compile(
            rf"(?P<name>{redact_module.NAME})(?P<sep>\s*[:=]\s*)(?!\[REDACTED:)(?P<value>[A-Za-z0-9_\-+/=.~]{{8,}})(?![A-Za-z0-9_\-+/=.~(\[])",
            re.I,
        )
        pieces = ["token", "password", "api_key", "secret", "Tokens", "=", ":", " ", "(", "[", "]", ")", "abc123def456", "a1", "xxxxxxxx",
                  "max_", "[REDACTED:credential]", "1234567890", ".", "-", "\n", "x"]
        rng = random.Random(20261023)
        for _ in range(4000):
            text = "".join(rng.choice(pieces) for _ in range(rng.randint(1, 14)))
            expected = old.sub(redact_module._unquoted, text)
            self.assertEqual(redact_module.UNQUOTED.sub(redact_module._unquoted, text), expected, text)

    def test_long_credential_names_are_still_redacted(self):
        text = "MY_SERVICE_INTEGRATION_PRODUCTION_DB_PASSWORD=hunter2hunter2"
        self.assertEqual(redact_secrets(text), "MY_SERVICE_INTEGRATION_PRODUCTION_DB_PASSWORD=[REDACTED:credential]")
        self.assertEqual(redact_secrets("my_service_integration_production_max_tokens=1234567890"),
                         "my_service_integration_production_max_tokens=1234567890")

    def test_names_that_merely_start_like_a_counter_are_still_redacted(self):
        for text in ("numeric_password=hunter2hunter2", "minimal_secret=a1b2c3d4e5f6", "counter_token=abc123def456",
                     "total_api_key=abc123def456"):
            with self.subTest(text):
                self.assertIn("[REDACTED:credential]", redact_secrets(text))

    def test_numeric_passwords_and_real_tokens_are_still_redacted(self):
        cases = {
            "password=12345678": "password=[REDACTED:credential]",
            "access_token=abc123def456": "access_token=[REDACTED:credential]",
            "Bearer abc123def456ghi": "Bearer [REDACTED:bearer-token]",
            "DB_PASSWORD=hunter2hunter2": "DB_PASSWORD=[REDACTED:credential]",
        }
        for text, expected in cases.items():
            with self.subTest(text):
                self.assertEqual(redact_secrets(text), expected)

    def test_nested_values_but_not_subject(self):
        ctx = {"findings": [{"description": "key sk_live_4f9a1c7e2b leaked",
                             "evidence_refs": [{"quote": 'TOKEN = "sk_live_4f9a1c7e2b"'}]}],
               "subject": {"content_hashes": [{"sha256": "sk_live_4f9a1c7e2b"}]}}
        out = redact_value(ctx)
        self.assertNotIn("sk_live", json.dumps(out["findings"]))
        self.assertEqual(out["subject"], ctx["subject"])


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="review exec ")
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        subprocess.run(["git", "init", "--quiet", str(self.project)], check=True)

    def test_credentials_are_not_stored(self):
        secret = "sk_live_4f9a1c7e2b"
        ctx = payload(
            findings=[finding(description=f"hard-coded {secret}", evidence_refs=[
                {"source": "direct", "location": "server.ts:5", "quote": f'const ADMIN_TOKEN = "{secret}";'}])],
            verdict="not-ready", reasoning=f"token {secret} is live",
        )
        done = run_helper(self.project, ctx)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn(secret, done.stdout + done.stderr)
        stored = sqlite3.connect(self.project / ".sidecar/sidecar.db").execute("SELECT context FROM sidecar").fetchone()[0]
        self.assertNotIn(secret, stored)
        saved = json.loads(stored)
        self.assertEqual(saved["findings"][0]["location"], "server.ts:5")  # location kept
        self.assertIn("[REDACTED:stripe-key]", saved["findings"][0]["description"])
        self.assertEqual(saved["verdict"], "not-ready")

    def test_unquoted_credentials_are_not_stored(self):
        ctx = payload(
            findings=[finding(description="found DB_PASSWORD=hunter2hunter2 in .env",
                              evidence_refs=[{"source": "direct", "location": ".env:3", "quote": "Authorization: Bearer abc123def456ghi789"}])],
            verdict="not-ready",
        )
        self.assertEqual(run_helper(self.project, ctx).returncode, 0)
        stored = sqlite3.connect(self.project / ".sidecar/sidecar.db").execute("SELECT context FROM sidecar").fetchone()[0]
        for secret in ("hunter2hunter2", "abc123def456ghi789"):
            self.assertNotIn(secret, stored)
        self.assertIn(".env:3", stored)

    def test_clean_context_is_stored_as_written(self):
        ctx = payload()
        self.assertEqual(run_helper(self.project, ctx).returncode, 0)
        stored = sqlite3.connect(self.project / ".sidecar/sidecar.db").execute("SELECT context FROM sidecar").fetchone()[0]
        self.assertEqual(stored, json.dumps(ctx))

    def test_rejected_payload_exit_code_and_message(self):
        done = run_helper(self.project, payload(verdict="not-ready"))
        self.assertEqual(done.returncode, 2)
        self.assertIn("review rejected (nothing saved)", done.stderr)
        self.assertNotIn("Traceback", done.stderr)

    @unittest.skipIf(os.geteuid() == 0, "permissions are not enforced for root")
    def test_denied_persistence_reports_storage_failure(self):
        sidecar = self.project / ".sidecar"
        sidecar.mkdir()
        sidecar.chmod(stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(sidecar.chmod, stat.S_IRWXU)
        done = run_helper(self.project, payload())
        self.assertEqual(done.returncode, 3)
        self.assertIn("review NOT saved (storage failed)", done.stderr)
        self.assertNotIn("Traceback", done.stderr)

    def test_hostile_scope_characters_are_stored_verbatim(self):
        hostile = "/tmp/x'; $(touch /tmp/pwned-review-test) `id` \"q\""
        done = run_helper(self.project, payload(), scope=hostile)
        self.assertEqual(done.returncode, 0, done.stderr)
        row = sqlite3.connect(self.project / ".sidecar/sidecar.db").execute("SELECT scope FROM sidecar").fetchone()
        self.assertEqual(row[0], hostile)
        self.assertFalse(Path("/tmp/pwned-review-test").exists())


class PreflightTests(unittest.TestCase):
    def snippet(self):
        text = PERSISTENCE_DOC.read_text()
        section = text.split("## Preflight", 1)[1]
        return re.search(r"```bash\n(.*?)```", section, re.S).group(1)

    def run_snippet(self, root, path):
        return subprocess.run(
            ["/bin/sh", "-c", self.snippet()], capture_output=True, text=True,
            env={"PATH": path, "dot_plugin_root": str(root)},
        )

    def fake_root(self, parent, helpers=("review_workflow.py", "review_subject.py", "context_workflow.py")):
        root = Path(parent) / "plugin"
        (root / "scripts").mkdir(parents=True)
        for name in helpers:
            (root / "scripts" / name).write_text("")
        return root

    def fake_uv(self, parent):
        bin_dir = Path(parent) / "bin"
        bin_dir.mkdir()
        uv = bin_dir / "uv"
        uv.write_text("#!/bin/sh\n")
        uv.chmod(0o755)
        return str(bin_dir)

    def test_ready_environment_passes(self):
        with tempfile.TemporaryDirectory() as parent:
            done = self.run_snippet(self.fake_root(parent), self.fake_uv(parent))
            self.assertEqual((done.returncode, done.stdout), (0, ""))

    def test_missing_runtime_is_named(self):
        with tempfile.TemporaryDirectory() as parent:
            done = self.run_snippet(self.fake_root(parent), "")
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("missing dependency: uv", done.stdout)

    def test_missing_helper_is_named(self):
        with tempfile.TemporaryDirectory() as parent:
            root = self.fake_root(parent, helpers=("review_workflow.py",))
            done = self.run_snippet(root, self.fake_uv(parent))
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("missing helper: " + str(root / "scripts/review_subject.py"), done.stdout)
            self.assertIn("missing helper: " + str(root / "scripts/context_workflow.py"), done.stdout)


if __name__ == "__main__":
    unittest.main()

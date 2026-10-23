import json
import os
import random
import re
import time
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "dot"
sys.path.insert(0, str(PLUGIN / "src"))

from agents.workflows.review_strategy import (  # noqa: E402
    LENSES,
    RISK_CONTENT,
    THRESHOLDS,
    Choose,
    applicable_lenses,
    choose_strategy,
    compute_signals,
    parse_override,
)

SMALL = {"mode": "path", "files": 3, "lines": 120, "areas": 1, "criteria": 0, "risky": []}
BIG = {"mode": "change", "files": 40, "lines": 2500, "areas": 4, "criteria": 6, "risky": []}
RISKY = {**SMALL, "risky": ["path:app/auth/token.ts"]}
LIMITS = {"files": 10, "lines": 800, "areas": 3, "criteria": 8}
UNSET = {k: None for k in LIMITS}


def names(result):
    return [lens["name"] for lens in result["lenses"]]


class RiskContentTests(unittest.TestCase):
    def test_long_single_line_with_many_select_words_finishes_quickly(self):
        for text in ("SELECT x " * 32000, "select x " * 32000, "SELECT " * 40000 + "{"):
            with self.subTest(text[:12]):
                start = time.perf_counter()
                RISK_CONTENT.search(text)
                self.assertLess(time.perf_counter() - start, 1.0)

    def test_sql_templates_are_still_risky(self):
        for text in ("`SELECT * FROM t WHERE id = ${id}`", "db.query(`SELECT a FROM b WHERE c = '${c}'`)", "exec(cmd)", "child_process"):
            with self.subTest(text):
                self.assertIsNotNone(RISK_CONTENT.search(text))
        self.assertIsNone(RISK_CONTENT.search("SELECT a FROM b WHERE id = 1"))

    def test_bounded_pattern_matches_the_old_one_on_short_lines(self):
        old = re.compile(r"(\bexec\(|\beval\(|child_process|private key|password|secret|api[_-]?key|\bSELECT\b.+\$\{|createCipher)", re.I)
        pieces = ["SELECT", "select", " ", "x", "${", "$", "{", "}", "\n", "exec(", "eval(", "password", "a", "FROM", "t", "`", "createCipher"]
        rng = random.Random(20261023)
        for _ in range(4000):
            text = "".join(rng.choice(pieces) for _ in range(rng.randint(1, 30)))
            self.assertEqual(bool(RISK_CONTENT.search(text)), bool(old.search(text)), text)


class OverrideParsingTests(unittest.TestCase):
    def test_leading_token_with_a_target(self):
        self.assertEqual(parse_override(["single", "src/x.ts"]), ("single", ["src/x.ts"]))
        self.assertEqual(parse_override(["agents", "src/x.ts", "extra"]), ("agents", ["src/x.ts", "extra"]))

    def test_token_without_a_target_is_the_target(self):
        self.assertEqual(parse_override(["single"]), ("none", ["single"]))
        self.assertEqual(parse_override(["agents"]), ("none", ["agents"]))

    def test_real_path_with_the_same_name_after_another_arg(self):
        self.assertEqual(parse_override(["src/x.ts", "single"]), ("none", ["src/x.ts", "single"]))

    def test_flag_forms(self):
        self.assertEqual(parse_override(["--single", "src/x.ts"]), ("single", ["src/x.ts"]))
        self.assertEqual(parse_override(["src/x.ts", "--agents"]), ("agents", ["src/x.ts"]))

    def test_conflicting_flags(self):
        with self.assertRaises(ValueError):
            parse_override(["--single", "--agents", "x"])

    def test_no_override(self):
        self.assertEqual(parse_override(["src/x.ts"]), ("none", ["src/x.ts"]))
        self.assertEqual(parse_override([]), ("none", []))


class DecisionTableTests(unittest.TestCase):
    def test_table(self):
        sec = ["security"]
        full = list(LENSES)
        cases = [
            ("small path, thresholds set", SMALL, LIMITS, "none", True, "single", []),
            ("large change over thresholds", BIG, LIMITS, "none", True, "agents", full),
            ("risk-sensitive small path", RISKY, LIMITS, "none", True, "agents", sec),
            ("risk-sensitive with thresholds unset", RISKY, UNSET, "none", True, "agents", sec),
            ("symbol review is single", {**SMALL, "mode": "symbol"}, LIMITS, "none", True, "single", []),
            ("symbol review even when risky", {**RISKY, "mode": "symbol"}, LIMITS, "none", True, "single", []),
            ("big change with thresholds unset", BIG, UNSET, "none", True, "single", []),
            ("override single beats size", BIG, LIMITS, "single", True, "single", []),
            ("override single beats risk", RISKY, LIMITS, "single", True, "single", []),
            ("override agents on a symbol review", {**SMALL, "mode": "symbol"}, LIMITS, "agents", True, "agents", full),
            ("override agents on a small path", SMALL, LIMITS, "agents", True, "agents", full),
            ("no sub-agent support", BIG, LIMITS, "none", False, "single", []),
            ("override agents, no sub-agent support", BIG, LIMITS, "agents", False, "single", []),
        ]
        for name, signals, limits, override, subagents, strategy, lenses in cases:
            with self.subTest(name):
                result = choose_strategy(signals, limits, override, subagents)
                self.assertEqual(result["strategy"], strategy)
                self.assertEqual(sorted(names(result)), sorted(lenses))
                self.assertEqual(result["override"], override)
                self.assertTrue(result["reason"])

    def test_fallback_is_reported(self):
        result = choose_strategy(BIG, LIMITS, "agents", False)
        self.assertEqual(result["fallback"], "sub-agents unavailable in this runtime")
        self.assertIn("override: agents", result["reason"])
        self.assertNotIn("fallback", choose_strategy(BIG, LIMITS, "agents", True))

    def test_each_threshold_alone_triggers_delegation(self):
        for key in ("files", "lines", "areas", "criteria"):
            with self.subTest(key):
                over = {**SMALL, key: LIMITS[key] + 1}
                result = choose_strategy(over, LIMITS, "none", True)
                self.assertEqual(result["strategy"], "agents")
                self.assertIn(key, result["reason"])
                at_limit = {**SMALL, key: LIMITS[key]}
                self.assertEqual(choose_strategy(at_limit, LIMITS, "none", True)["strategy"], "single")

    def test_unset_thresholds_are_reported_and_shipped_unset(self):
        result = choose_strategy(SMALL, UNSET, "none", True)
        self.assertEqual(result["thresholds_unset"], ["areas", "criteria", "files", "lines"])
        self.assertIn("thresholds unset", result["reason"])
        self.assertEqual(set(THRESHOLDS), set(LIMITS))
        self.assertTrue(all(v is None for v in THRESHOLDS.values()), "thresholds must be calibrated before being set")

    def test_deterministic(self):
        first = choose_strategy(BIG, LIMITS, "none", True)
        self.assertEqual(first, choose_strategy(dict(BIG), dict(LIMITS), "none", True))


class LensTests(unittest.TestCase):
    def test_every_category_belongs_to_exactly_one_lens(self):
        categories = [c for cats in LENSES.values() for c in cats]
        self.assertEqual(len(categories), len(set(categories)))
        self.assertEqual(set(categories), {
            "Security", "Bugs", "Design", "Performance", "Maintainability", "Observability", "Testing",
            "Requirements / Plan", "Production Readiness", "Documentation", "Library / Reuse"})

    def test_requirements_category_needs_criteria(self):
        without = {lens["name"]: lens["categories"] for lens in applicable_lenses(0)}
        with_reqs = {lens["name"]: lens["categories"] for lens in applicable_lenses(3)}
        self.assertEqual(without["correctness"], ["Bugs"])
        self.assertEqual(with_reqs["correctness"], ["Bugs", "Requirements / Plan"])

    def test_override_never_adds_lenses_beyond_the_applicable_set(self):
        result = choose_strategy({**SMALL, "criteria": 0}, LIMITS, "agents", True)
        flat = [c for lens in result["lenses"] for c in lens["categories"]]
        self.assertNotIn("Requirements / Plan", flat)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


class SignalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="review strategy ")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "--quiet")
        (self.repo / "src").mkdir()
        (self.repo / "src/a.ts").write_text("one\ntwo\n")
        (self.repo / "docs").mkdir()
        (self.repo / "docs/readme.md").write_text("doc\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "--quiet", "-m", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")

    def signals(self, mode, target=".", start_path=None, **kw):
        return compute_signals(Choose(mode=mode, target=target, start_path=start_path or str(self.repo), **kw))

    def test_path_review_counts_files_lines_and_areas(self):
        s = self.signals("path")
        self.assertEqual((s["files"], s["lines"], s["areas"], s["risky"]), (2, 3, 2, []))

    def test_change_review_counts_the_diff(self):
        (self.repo / "src/a.ts").write_text("one\ntwo\nthree\n")
        (self.repo / "src/new.ts").write_text("x\n")
        s = self.signals("change", base=self.base)
        self.assertEqual((s["files"], s["lines"]), (2, 1))  # a.ts +1; untracked new.ts not in the numstat

    def test_risky_path_and_content_are_detected(self):
        (self.repo / "src/auth").mkdir()
        (self.repo / "src/auth/token.ts").write_text("export const x = 1;\n")
        (self.repo / "src/run.ts").write_text("import { exec } from 'child_process';\nexec(cmd);\n")
        s = self.signals("path")
        joined = " ".join(s["risky"])
        self.assertIn("path:src/auth/token.ts", joined)
        self.assertIn("content:src/run.ts", joined)

    def test_relative_target_resolves_from_start_path_not_the_repo_root(self):
        s = self.signals("path", target="a.ts", start_path=str(self.repo / "src"))
        self.assertEqual((s["files"], s["lines"]), (1, 2))
        outside = self.signals("path", target="src/a.ts", start_path=str(self.repo))
        self.assertEqual(outside["files"], 1)

    def test_target_outside_the_repository_is_an_error(self):
        with self.assertRaises(ValueError):
            self.signals("path", target="../elsewhere")

    def test_names_with_spaces_and_non_ascii_are_counted_once(self):
        (self.repo / "src/my file.ts").write_text("a\nb\n")
        (self.repo / "src/é.ts").write_text("c\n")
        s = self.signals("path")
        self.assertEqual(s["files"], 4)  # a.ts, my file.ts, é.ts and docs/readme.md
        git(self.repo, "add", ".")
        git(self.repo, "commit", "--quiet", "-m", "names")
        (self.repo / "src/my file.ts").write_text("a\nb\nc\n")
        (self.repo / "src/é.ts").write_text("c\nd\n")
        change = self.signals("change", base="HEAD")
        self.assertEqual((change["files"], change["lines"]), (2, 2))

    def test_risk_ignores_prose_and_lookalike_paths(self):
        (self.repo / "docs/notes.md").write_text("Never commit a secret or a password.\n")
        (self.repo / "src/author").mkdir()
        (self.repo / "src/author/bio.ts").write_text("export const bio = 1;\n")
        (self.repo / "docs/data.json").write_text('{"password": "x"}\n')
        self.assertEqual(self.signals("path")["risky"], [])

    def test_risk_still_detects_code_and_real_auth_paths(self):
        (self.repo / "src/run.ts").write_text("exec(cmd);\n")
        (self.repo / "src/auth").mkdir()
        (self.repo / "src/auth/session.ts").write_text("export {};\n")
        (self.repo / "src/migrations").mkdir()
        (self.repo / "src/migrations/001.sql").write_text("select 1;\n")
        risky = " ".join(self.signals("path")["risky"])
        for expected in ("content:src/run.ts", "path:src/auth/session.ts", "path:src/migrations/001.sql"):
            self.assertIn(expected, risky)

    def test_criteria_and_symbol_mode_pass_through(self):
        s = self.signals("symbol", target="src/a.ts", criteria=4)
        self.assertEqual((s["mode"], s["criteria"], s["files"]), ("symbol", 4, 1))


class CliErrorTests(unittest.TestCase):
    def run_cli(self, *args, cwd):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        return subprocess.run([sys.executable, "-B", str(PLUGIN / "scripts/review_strategy.py"), *args],
                              cwd=cwd, env=env, text=True, capture_output=True)

    def assert_one_line_rejection(self, done, fragment):
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        self.assertEqual(len(done.stderr.strip().splitlines()), 1, done.stderr)
        self.assertIn("review_strategy rejected", done.stderr)
        self.assertIn(fragment, done.stderr)

    def test_unbalanced_quote_in_the_request(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assert_one_line_rejection(self.run_cli("parse", "--request", "single 'unterminated", cwd=directory), "No closing quotation")

    def test_not_a_git_repository(self):
        with tempfile.TemporaryDirectory(prefix="not a repo ") as directory:
            done = self.run_cli("choose", "--mode", "path", "--target", ".", "--start-path", directory, cwd=directory)
        self.assert_one_line_rejection(done, "not a git repository")

    def test_target_outside_the_repository(self):
        with tempfile.TemporaryDirectory(prefix="review strategy ") as directory:
            repo = Path(directory)
            git(repo, "init", "--quiet")
            done = self.run_cli("choose", "--mode", "path", "--target", "../elsewhere", "--start-path", str(repo), cwd=repo)
        self.assert_one_line_rejection(done, "outside the repository")


class CliTests(unittest.TestCase):
    def run_cli(self, *args, cwd=None):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        return subprocess.run([sys.executable, "-B", str(PLUGIN / "scripts/review_strategy.py"), *args],
                              cwd=cwd, env=env, text=True, capture_output=True)

    def test_parse_subcommand(self):
        out = self.run_cli("parse", "--request", "agents src/x.ts --foo")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), {"override": "agents", "arguments": "src/x.ts --foo"})
        out = self.run_cli("parse", "--request", "'path with space/a.ts'")
        self.assertEqual(json.loads(out.stdout), {"override": "none", "arguments": "'path with space/a.ts'"})

    def test_choose_subcommand_on_a_real_repo(self):
        with tempfile.TemporaryDirectory(prefix="review strategy ") as tmp:
            repo = Path(tmp)
            git(repo, "init", "--quiet")
            (repo / "a.ts").write_text("x\n")
            git(repo, "add", ".")
            git(repo, "commit", "--quiet", "-m", "base")
            out = self.run_cli("choose", "--mode", "path", "--target", ".", "--start-path", str(repo), cwd=repo)
            self.assertEqual(out.returncode, 0, out.stderr)
            result = json.loads(out.stdout)
            self.assertEqual((result["strategy"], result["override"]), ("single", "none"))
            self.assertEqual(result["signals"]["files"], 1)
            forced = json.loads(self.run_cli("choose", "--mode", "path", "--target", ".", "--override", "agents",
                                             "--start-path", str(repo), cwd=repo).stdout)
            self.assertEqual(forced["strategy"], "agents")
            self.assertEqual(len(forced["lenses"]), 5)
            nosub = json.loads(self.run_cli("choose", "--mode", "path", "--target", ".", "--override", "agents",
                                            "--subagents", "no", "--start-path", str(repo), cwd=repo).stdout)
            self.assertEqual((nosub["strategy"], nosub["fallback"]), ("single", "sub-agents unavailable in this runtime"))


if __name__ == "__main__":
    unittest.main()

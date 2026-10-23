import hashlib
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

from agents.workflows.review import aggregate_verdict, validate_review_context  # noqa: E402
from agents.workflows.review_subject import Args, capture_subject, is_stale  # noqa: E402


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


EXECUTION = {
    "strategy": "single", "override": "none", "reason": "below thresholds", "signals": {"mode": "path"},
    "lenses": [], "research": "not_needed", "research_excerpt_authorized": False,
}


def review_context(subject, **extra):
    mode = subject.get("review_mode", "path") if isinstance(subject, dict) else "path"
    return {
        "schema_version": 2, "target": "src", "review_mode": mode, "source_workflow": "standalone",
        "findings": [], "verification_gaps": [], "summary": "s", "reasoning": "r", "verdict": "ready",
        "subject": subject, "execution": EXECUTION, **extra,
    }


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="review subject ")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "--quiet")
        (self.repo / "src").mkdir()
        (self.repo / "src/a.ts").write_text("one\n")
        (self.repo / "src/b.ts").write_text("b\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "--quiet", "-m", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")

    def subject(self, kind, **kw):
        review_mode = kw.pop("review_mode", "change")
        kw.setdefault("base_justification", "test base")
        return capture_subject(Args(kind=kind, review_mode=review_mode, target="src", start_path=str(self.repo), **kw))

    def paths(self, subject):
        return [h["path"] for h in subject["content_hashes"]]

    def layers(self):
        """committed change to a.ts, staged b.ts, unstaged a.ts, untracked c.ts"""
        (self.repo / "src/a.ts").write_text("two\n")
        git(self.repo, "commit", "--quiet", "-am", "committed")
        (self.repo / "src/b.ts").write_text("staged\n")
        git(self.repo, "add", "src/b.ts")
        (self.repo / "src/a.ts").write_text("three\n")
        (self.repo / "src/c.ts").write_text("untracked\n")


class LayerTests(RepoCase):
    def test_layer_inclusion_and_exclusion(self):
        self.layers()
        committed = self.subject("commit_range", base=self.base)
        index = self.subject("index")
        tree = self.subject("working_tree")
        tree_from_base = self.subject("working_tree", base=self.base)
        self.assertEqual(self.paths(committed), ["src/a.ts"])  # the committed change only
        self.assertEqual(self.paths(index), ["src/b.ts"])  # staged only
        self.assertEqual(self.paths(tree), ["src/a.ts", "src/b.ts", "src/c.ts"])  # staged + unstaged + untracked vs HEAD
        self.assertEqual(self.paths(tree_from_base), ["src/a.ts", "src/b.ts", "src/c.ts"])
        self.assertNotIn("src/c.ts", self.paths(index))  # untracked appears only in working_tree
        self.assertNotIn("src/c.ts", self.paths(committed))

    def test_hashes_identify_content(self):
        self.layers()
        by_path = {h["path"]: h["sha256"] for h in self.subject("working_tree")["content_hashes"]}
        self.assertEqual(by_path["src/a.ts"], hashlib.sha256(b"three\n").hexdigest())
        self.assertEqual(self.subject("index")["content_hashes"][0]["sha256"], hashlib.sha256(b"staged\n").hexdigest())

    def test_capture_is_reproducible(self):
        self.layers()
        self.assertEqual(self.subject("working_tree"), self.subject("working_tree"))

    def test_diff_hash_differs_by_layer(self):
        self.layers()
        hashes = {k: self.subject(k, **({"base": self.base} if k == "commit_range" else {}))["diff_sha256"]
                  for k in ("commit_range", "index", "working_tree")}
        self.assertEqual(len(set(hashes.values())), 3)

    def test_commit_range_needs_base(self):
        with self.assertRaises(ValueError):
            self.subject("commit_range")


class PathModeTests(RepoCase):
    def test_path_review_hashes_every_file_under_the_target(self):
        subject = self.subject("working_tree", review_mode="path")  # clean tree: no diff, but the reviewed files are still identified
        self.assertEqual(self.paths(subject), ["src/a.ts", "src/b.ts"])
        validate_review_context(review_context(subject))

    def test_symbol_review_with_adjacent_context_included(self):
        (self.repo / "lib").mkdir()
        (self.repo / "lib/dep.ts").write_text("dep\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "--quiet", "-m", "dep")
        subject = capture_subject(Args(
            kind="working_tree", review_mode="symbol", target="src/a.ts", include=["lib/dep.ts"], start_path=str(self.repo),
        ))
        self.assertEqual(self.paths(subject), ["lib/dep.ts", "src/a.ts"])
        self.assertFalse(is_stale(subject))
        (self.repo / "lib/dep.ts").write_text("changed\n")
        self.assertTrue(is_stale(subject))

    def test_edit_to_a_reviewed_file_makes_a_path_review_stale(self):
        subject = self.subject("working_tree", review_mode="path")
        self.assertFalse(is_stale(subject))
        (self.repo / "src/b.ts").write_text("edited\n")
        self.assertTrue(is_stale(subject))


class RelativeTargetTests(RepoCase):
    def test_relative_target_resolves_from_start_path(self):
        subject = capture_subject(Args(kind="working_tree", review_mode="path", target="a.ts", start_path=str(self.repo / "src")))
        self.assertEqual(subject["target"], "src/a.ts")
        self.assertEqual(self.paths(subject), ["src/a.ts"])

    def test_target_outside_the_repository_is_an_error(self):
        with self.assertRaises(ValueError):
            capture_subject(Args(kind="working_tree", review_mode="path", target="../elsewhere", start_path=str(self.repo)))


class UnusualNameTests(RepoCase):
    NAMES = ("é.ts", "my file.ts")

    def write_names(self):
        for name in self.NAMES:
            (self.repo / "src" / name).write_text(f"content of {name}\n")

    def test_working_tree_hashes_non_ascii_and_spaced_names(self):
        self.write_names()
        subject = self.subject("working_tree")
        by_path = {h["path"]: h["sha256"] for h in subject["content_hashes"]}
        for name in self.NAMES:
            self.assertEqual(by_path[f"src/{name}"], hashlib.sha256(f"content of {name}\n".encode()).hexdigest())
        self.assertNotIn("missing", by_path.values())

    def test_committed_and_staged_layers_hash_them_too(self):
        self.write_names()
        git(self.repo, "add", ".")
        staged = {h["path"]: h["sha256"] for h in self.subject("index")["content_hashes"]}
        git(self.repo, "commit", "--quiet", "-m", "names")
        committed = self.subject("commit_range", base=self.base)
        for name in self.NAMES:
            digest = hashlib.sha256(f"content of {name}\n".encode()).hexdigest()
            self.assertEqual(staged[f"src/{name}"], digest)
            self.assertIn({"path": f"src/{name}", "sha256": digest}, committed["content_hashes"])

    def test_editing_an_untracked_unusual_name_makes_the_subject_stale(self):
        self.write_names()
        subject = self.subject("working_tree")
        self.assertFalse(is_stale(subject))
        (self.repo / "src/é.ts").write_text("edited\n")
        self.assertTrue(is_stale(subject))

    def test_path_review_lists_them(self):
        self.write_names()
        self.assertEqual(self.paths(self.subject("working_tree", review_mode="path")),
                         ["src/a.ts", "src/b.ts", "src/my file.ts", "src/é.ts"])


class GitFailureTests(RepoCase):
    def test_is_stale_reports_a_git_failure_as_a_value_error(self):
        subject = {**self.subject("working_tree"), "repo_root": str(self.repo / "gone")}
        with self.assertRaises(ValueError) as caught:
            is_stale(subject)
        self.assertIn("git", str(caught.exception))
        self.assertNotIn("Traceback", str(caught.exception))


class StaleTests(RepoCase):
    def test_edit_after_capture_makes_working_tree_stale(self):
        self.layers()
        tree = self.subject("working_tree")
        self.assertFalse(is_stale(tree))
        (self.repo / "src/a.ts").write_text("four\n")
        self.assertTrue(is_stale(tree))

    def test_new_untracked_file_makes_working_tree_stale(self):
        tree = self.subject("working_tree")
        (self.repo / "src/new.ts").write_text("x\n")
        self.assertTrue(is_stale(tree))

    def test_restaging_makes_index_stale(self):
        self.layers()
        index = self.subject("index")
        (self.repo / "src/b.ts").write_text("restaged\n")
        git(self.repo, "add", "src/b.ts")
        self.assertTrue(is_stale(index))

    def test_commit_range_and_artifact_are_never_stale(self):
        self.layers()
        self.assertFalse(is_stale(self.subject("commit_range", base=self.base)))
        self.assertFalse(is_stale({"kind": "artifact"}))


class SubjectValidationTests(RepoCase):
    def reject(self, ctx, fragment):
        with self.assertRaises(ValueError) as caught:
            validate_review_context(ctx)
        self.assertIn(fragment, str(caught.exception))

    def test_captured_subjects_validate(self):
        self.layers()
        for kind, kw in (("commit_range", {"base": self.base}), ("index", {}), ("working_tree", {})):
            with self.subTest(kind):
                validate_review_context(review_context(self.subject(kind, **kw)))

    def test_head_alone_does_not_represent_a_dirty_tree(self):
        self.layers()
        head_only = {"kind": "working_tree", "repo_root": str(self.repo), "review_mode": "path",
                     "head": self.base, "content_hashes": []}
        self.reject(review_context(head_only), "diff_sha256")
        self.reject(review_context({"head": self.base}), "subject.kind")

    def test_missing_subject_is_rejected(self):
        ctx = review_context(None)
        del ctx["subject"]
        self.reject(ctx, "subject must be an object")

    def test_change_review_needs_base_justification(self):
        self.layers()
        subject = self.subject("commit_range", base=self.base, base_justification=None)
        self.reject(review_context(subject), "base_justification")
        subject["base_justification"] = "task branched from this commit"
        validate_review_context(review_context(subject))

    def test_subject_mode_must_match(self):
        self.layers()
        self.reject(review_context(self.subject("index", review_mode="symbol"), review_mode="path"), "subject.review_mode")

    def test_artifact_needs_a_hash(self):
        self.reject(review_context({"kind": "artifact", "repo_root": "/r", "review_mode": "path", "content_hashes": []}), "content hash")

    def test_stale_review_cannot_be_ready(self):
        self.layers()
        subject = self.subject("working_tree")
        self.assertEqual(aggregate_verdict([], [], stale=True), "not-ready")
        self.reject(review_context(subject, stale=True), "disagrees")
        validate_review_context(review_context(subject, stale=True, verdict="not-ready"))


class SaveTimeStalenessTests(RepoCase):
    def save(self, ctx):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        return subprocess.run(
            [sys.executable, "-B", str(PLUGIN / "scripts/review_workflow.py"), "--agent", "codex",
             "--scope", str(self.repo), "--context", json.dumps(ctx), "--start-path", str(self.repo)],
            cwd=self.repo, env=env, text=True, capture_output=True,
        )

    def test_fresh_saves_stale_is_rejected_unless_marked(self):
        self.layers()
        subject = self.subject("working_tree")
        fresh = self.save(review_context(subject))
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        (self.repo / "src/a.ts").write_text("changed during review\n")
        rejected = self.save(review_context(subject))
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("changed since the subject was captured", rejected.stderr)
        marked = self.save(review_context(subject, stale=True, verdict="not-ready"))
        self.assertEqual(marked.returncode, 0, marked.stderr)
        count = sqlite3.connect(self.repo / ".sidecar/sidecar.db").execute("SELECT COUNT(*) FROM sidecar").fetchone()
        self.assertEqual(count[0], 2)


class SaveTimeGitFailureTests(RepoCase):
    def test_missing_repo_is_a_one_line_rejection_not_a_traceback(self):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        subject = {**self.subject("working_tree"), "repo_root": str(self.repo / "gone")}
        done = subprocess.run(
            [sys.executable, "-B", str(PLUGIN / "scripts/review_workflow.py"), "--agent", "codex", "--scope", str(self.repo),
             "--context", json.dumps(review_context(subject)), "--start-path", str(self.repo)],
            cwd=self.repo, env=env, text=True, capture_output=True,
        )
        self.assertEqual(done.returncode, 2)
        self.assertIn("review rejected (nothing saved)", done.stderr)
        self.assertNotIn("Traceback", done.stderr)


class CliErrorTests(RepoCase):
    def run_cli(self, *args, cwd=None):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        return subprocess.run([sys.executable, "-B", str(PLUGIN / "scripts/review_subject.py"), *args],
                              cwd=cwd or self.repo, env=env, text=True, capture_output=True)

    def assert_one_line_rejection(self, done, fragment):
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        self.assertEqual(len(done.stderr.strip().splitlines()), 1, done.stderr)
        self.assertIn("review_subject rejected", done.stderr)
        self.assertIn(fragment, done.stderr)

    def test_not_a_git_repository(self):
        with tempfile.TemporaryDirectory(prefix="not a repo ") as directory:
            done = self.run_cli("--kind", "working_tree", "--review-mode", "path", "--target", ".", "--start-path", directory, cwd=directory)
        self.assert_one_line_rejection(done, "not a git repository")

    def test_target_outside_the_repository(self):
        done = self.run_cli("--kind", "working_tree", "--review-mode", "path", "--target", "../elsewhere", "--start-path", str(self.repo))
        self.assert_one_line_rejection(done, "outside the repository")

    def test_commit_range_without_base(self):
        done = self.run_cli("--kind", "commit_range", "--review-mode", "change", "--target", "src", "--start-path", str(self.repo))
        self.assert_one_line_rejection(done, "--base")

    def test_unknown_revision(self):
        done = self.run_cli("--kind", "working_tree", "--review-mode", "path", "--target", "src", "--head", "nosuchrev", "--start-path", str(self.repo))
        self.assert_one_line_rejection(done, "bad revision")


class CliTests(RepoCase):
    def test_cli_prints_the_subject(self):
        self.layers()
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        out = subprocess.run(
            [sys.executable, "-B", str(PLUGIN / "scripts/review_subject.py"), "--kind", "working_tree",
             "--review-mode", "change", "--base-justification", "test base", "--target", "src",
             "--start-path", str(self.repo)],
            cwd=self.repo, env=env, text=True, capture_output=True, check=True,
        ).stdout
        self.assertEqual(json.loads(out), self.subject("working_tree"))


if __name__ == "__main__":
    unittest.main()

import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOT = ROOT / "plugins" / "dot"
PLUGIN = ROOT / "plugins" / "cross-review"
SKILL = PLUGIN / "skills" / "cross-review"


class CrossReviewPluginTests(unittest.TestCase):
    def test_manifest(self):
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["name"], "cross-review")
        self.assertRegex(manifest["version"], r"^\d+\.\d+\.\d+$")

    def test_skill_inventory(self):
        self.assertEqual({p.name for p in (PLUGIN / "skills").iterdir()}, {"cross-review"})
        frontmatter = (SKILL / "SKILL.md").read_text().split("---", 2)[1]
        self.assertEqual(yaml.safe_load(frontmatter)["name"], "cross-review")

    def test_eval_links(self):
        evals_file = SKILL / "evals" / "evals.json"
        data = json.loads(evals_file.read_text())
        self.assertEqual(data["skill_name"], "cross-review")
        self.assertEqual(len(data["evals"]), 4)
        for case in data["evals"]:
            self.assertTrue((evals_file.parent / case["yaml"]).resolve().is_file(), case["yaml"])
            for fixture in case["files"]:
                self.assertTrue((ROOT / fixture).is_file(), fixture)
        scenarios = sorted((PLUGIN / "evals").glob("*.yaml"))
        self.assertEqual(len(scenarios), 4)
        for file in scenarios:
            scenario = yaml.safe_load(file.read_text())
            self.assertEqual(scenario["skill"], "cross-review:cross-review", file)
            self.assertTrue((SKILL / scenario["fixture"]).is_dir(), file)

    def test_skill_text_names_the_runner_and_both_roots(self):
        text = (SKILL / "SKILL.md").read_text() + (SKILL / "references" / "fanout.md").read_text()
        for needle in ("review_fanout.py", "cross_review_root", "dot_plugin_root", "DOT_PLUGIN_ROOT"):
            self.assertIn(needle, text)
        self.assertIsNone(re.search(r"workflow\.py[\"'\s]+review-fanout", text), "the old dot runner command is gone")

    def test_smoke_check(self):
        env = {**os.environ, "DOT_PLUGIN_ROOT": str(DOT)}
        proc = subprocess.run(
            [sys.executable, "-B", str(PLUGIN / "scripts" / "smoke_check.py")],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS", proc.stdout)


if __name__ == "__main__":
    unittest.main()

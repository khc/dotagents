import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import runpy
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "dot"
SKILLS = {
    "bug", "feature", "find-skills", "fix", "implement", "nlm-skill",
    "plan", "refactor", "research", "review", "scope", "skill-wrapper", "workflow",
}


class DotPluginTests(unittest.TestCase):
    def test_package_inventory(self):
        portable = json.loads((PLUGIN / "plugin.json").read_text())
        claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
        for key in ("name", "version", "author"):
            self.assertEqual(portable[key], claude[key])
        self.assertEqual(portable["name"], "dot")
        self.assertEqual({p.name for p in (PLUGIN / "skills").iterdir()}, SKILLS)
        for name in SKILLS:
            frontmatter = (PLUGIN / "skills" / name / "SKILL.md").read_text().split("---", 2)[1]
            self.assertEqual(yaml.safe_load(frontmatter)["name"], name)
            alias = ROOT / "skills" / name
            self.assertTrue(alias.is_symlink(), name)
            self.assertEqual(alias.resolve(), PLUGIN / "skills" / name)
        for name in ("context", "review", "fix", "sidecar"):
            script = (PLUGIN / "scripts" / f"{name}_workflow.py").read_text()
            self.assertIn('# requires-python = ">=3.14"', script)
            self.assertIn('# dependencies = ', script)
        self.assertTrue((PLUGIN / "src/schemas/sidecar.schema.sql").is_file())

    def relocated(self):
        cache = ROOT / ".task-cache"
        cache.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix="dot plugin test ", dir=cache)
        self.addCleanup(temp.cleanup)
        directory = Path(temp.name)
        plugin = directory / "installed dot"
        shutil.copytree(PLUGIN, plugin, ignore=shutil.ignore_patterns("__pycache__", ".venv"))
        project = directory / "target project"
        project.mkdir()
        subprocess.run(["git", "init", "--quiet", str(project)], check=True)
        child = project / "app"
        child.mkdir()
        return plugin, project, child

    def run_helper(self, plugin, cwd, name, *args, check=True):
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTHONPATH", None)
        return subprocess.run(
            [sys.executable, "-B", str(plugin / "scripts" / f"{name}_workflow.py"), *args],
            cwd=cwd, env=env, text=True, capture_output=True, check=check,
        )

    def test_relocated_scope(self):
        plugin, project, child = self.relocated()
        file = child / "target.py"
        file.write_text("pass\n")
        for target, allowed in ((".", f"{child}/**"), ("target.py", str(file))):
            with self.subTest(target=target):
                result = json.loads(self.run_helper(plugin, child, "context", target).stdout)
                self.assertEqual(result["repo_root"], str(project))
                self.assertEqual(result["scope_boundaries"]["allowed"], allowed)
        missing = self.run_helper(plugin, child, "context", "missing.py", check=False)
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("does not exist", missing.stderr)

    def test_relocated_sidecar_roundtrip(self):
        plugin, project, child = self.relocated()
        review_id = self.run_helper(
            plugin, child, "review", "--agent", "codex", "--scope", str(child),
            "--context", '{"summary":"legacy review"}',
        ).stdout.strip()
        review = json.loads(self.run_helper(plugin, child, "fix", "get_review").stdout)
        self.assertEqual(review["uuid"], review_id)
        self.assertEqual(review["skill"], "review")
        self.assertEqual(review["context"]["summary"], "legacy review")
        fix_id = self.run_helper(
            plugin, child, "fix", "save_fix", "--agent", "codex", "--scope", str(child),
            "--review_uuid", review_id, "--context", '{"summary":"fixed"}',
        ).stdout.strip()
        db = project / ".sidecar/sidecar.db"
        with sqlite3.connect(db) as connection:
            self.assertEqual(connection.execute(
                "SELECT skill, parent_uuid, relation, status FROM sidecar WHERE uuid = ?", (fix_id,),
            ).fetchone(), ("fix", review_id, "fix", "done"))
            self.assertEqual(connection.execute(
                "SELECT status FROM sidecar WHERE uuid = ?", (review_id,),
            ).fetchone(), ("done",))
        self.assertFalse((plugin / ".sidecar").exists())
        self.assertFalse((child / ".sidecar").exists())

    def test_qualified_stage_prompts(self):
        plugin, project, child = self.relocated()
        workflow = runpy.run_path(str(plugin / "skills/workflow/bin/workflow.py"))
        stages = ("feature", "refactor", "bug", "plan", "implement", "review", "fix")
        for stage in stages:
            with self.subTest(stage=stage):
                prompt = workflow["stage_prompt"](
                    "planned", stage, child, project / "request.md", project, 0,
                )
                self.assertIn(f"$dot:{stage}", prompt)
                self.assertIn("$dot:scope", prompt)
                self.assertIn(f'"stage": "{stage}"', prompt)
        prompt = workflow["stage_prompt"](
            "planned", "plan", child, project / "request.md", project, 0,
            active_plan={"path": ".plans/plan_1.md", "plan_id": "plan_1", "revision": 2, "status": "draft"},
            plan_reason="amendment", amendment="Keep the same plan",
        )
        self.assertIn(str(plugin / "skills/plan/SKILL.md"), prompt)
        self.assertIn(".plans/plan_1.md", prompt)
        self.assertIn("Keep the same plan", prompt)
        for name in ("feature", "planned"):
            self.assertEqual(workflow["TRANSITIONS"][name][("plan", "success")], "AWAITING_PLAN_APPROVAL")
            self.assertEqual(workflow["TRANSITIONS"][name][("implement", "replan")], "plan")

    def test_eval_links(self):
        for name in ("scope", "review", "fix"):
            file = PLUGIN / "skills" / name / "evals/evals.json"
            data = json.loads(file.read_text())
            self.assertEqual(data["skill_name"], name)
            for scenario in data["evals"]:
                self.assertTrue((file.parent / scenario["yaml"]).is_file(), scenario["yaml"])
                for fixture in scenario["files"]:
                    self.assertTrue((ROOT / fixture).is_file(), fixture)
        for file in (PLUGIN / "evals").glob("*/*.yaml"):
            scenario = yaml.safe_load(file.read_text())
            self.assertIn(scenario["skill"], {"dot:scope", "dot:review", "dot:fix"})
            if "fixture" in scenario:
                name = scenario["skill"].split(":")[-1]
                self.assertTrue((PLUGIN / "skills" / name / scenario["fixture"]).is_dir(), file)

    def test_ide_local_discovery(self):
        for name in SKILLS:
            file = ROOT / "skills" / name / "SKILL.md"
            self.assertTrue(file.is_file(), name)
            text = file.read_text()
            self.assertEqual(yaml.safe_load(text.split("---", 2)[1])["name"], name)
            self.assertIn("## Local skill compatibility", text)
            self.assertIn("unqualified skill name", text)
            self.assertEqual(file.resolve().parents[2], PLUGIN)
        policy = (ROOT / "AGENTS.md").read_text()
        self.assertIn("$scope when plugin skills are unavailable", policy)

    def test_claude_stage_loads_plugin(self):
        plugin, project, child = self.relocated()
        workflow = runpy.run_path(str(plugin / "skills/workflow/bin/workflow.py"))
        with mock.patch.dict(os.environ, {}, clear=True):
            command = workflow["cli_command"]("claude", "stage prompt", child)
        self.assertEqual(command, ["claude", "-p", "--plugin-dir", str(plugin), "stage prompt"])
        with mock.patch.dict(os.environ, {
            "CLAUDE_CMD": "custom-claude", "CLAUDE_ARGS": '-p --model example --plugin-dir "other plugin"',
        }, clear=True):
            command = workflow["cli_command"]("claude", "stage prompt", child)
        self.assertEqual(command, ["custom-claude", "-p", "--model", "example", "--plugin-dir",
                                   "other plugin", "--plugin-dir", str(plugin), "stage prompt"])

    def test_portable_skill_instructions(self):
        for name in ("scope", "feature", "review", "fix"):
            text = (PLUGIN / "skills" / name / "SKILL.md").read_text()
            self.assertIn("dot_plugin_root", text)
            self.assertIn("uv run --no-project", text)
            self.assertNotIn("~/.agents/scripts/", text)
            self.assertIn("parents[2]", text)

    def test_report_uses_plugin_skill_path(self):
        with mock.patch.object(sys, "path", [str(ROOT / "src"), str(PLUGIN / "src"), *sys.path]):
            import skill_report
        stub = skill_report.ToolReport("validator", [], 0, "pass", "valid", [], "", "")
        validators = {
            name: mock.Mock(return_value=stub) for name in (
                "_run_skillcheck", "_run_skills_validate", "_run_skill_validator",
                "_run_cclint", "_run_markdownlint",
            )
        }
        with mock.patch.multiple(skill_report, **validators):
            report = json.loads(skill_report.generate_report(skill_report.ReportArgs(
                skill="scope", start_path=str(ROOT),
            )))
        path = PLUGIN / "skills/scope/SKILL.md"
        self.assertEqual(report["skill_path"], str(path))
        self.assertEqual(report["skill"], "scope")
        self.assertEqual(report["overall_status"], "pass")
        self.assertEqual(set(report), {"skill", "skill_path", "overall_status", "summary", "tools"})
        validators["_run_skillcheck"].assert_called_once_with(ROOT, path)

    def test_marketplace_sources(self):
        for file in (ROOT / ".agents/plugins/marketplace.json", ROOT / ".claude-plugin/marketplace.json"):
            marketplace = json.loads(file.read_text())
            self.assertEqual(marketplace["name"], "dot-local")
            self.assertEqual(len(marketplace["plugins"]), 1)
            entry = marketplace["plugins"][0]
            self.assertEqual(entry["name"], "dot")
            source = entry["source"]
            path = source["path"] if isinstance(source, dict) else source
            self.assertEqual((ROOT / path).resolve(), PLUGIN)


if __name__ == "__main__":
    unittest.main()

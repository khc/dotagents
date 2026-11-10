#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import json
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
required = [
    "SKILL.md",
    "bin/workflow.py",
    "workflows/feature.md",
    "workflows/refactor.md",
    "workflows/bug.md",
    "workflows/planned.md",
    "workflows/review.md",
    "schemas/plan-handoff.schema.json",
    "schemas/implementation-handoff.schema.json",
    "schemas/review-handoff.schema.json",
    "schemas/fix-handoff.schema.json",
    "runtime/claude/README.md",
    "runtime/codex/README.md",
    "runtime/agy/README.md",
    "fixtures/review-dry-run.txt",
]
missing = [p for p in required if not (root/p).exists()]
for p in (root/"schemas").glob("*.json"):
    json.loads(p.read_text())

cli_checks = [
    [],
    ["start"],
    ["resume"],
    ["approve"],
    ["cancel"],
]
for extra_args in cli_checks:
    proc = subprocess.run(
        [sys.executable, str(root/"bin/workflow.py"), *extra_args, "--help"],
        capture_output=True,
    )
    if proc.returncode != 0:
        print("failing subcommand:", " ".join(extra_args) or "(root)")
        raise SystemExit(1)

if missing:
    print("missing:", *missing, sep="\n- ")
    raise SystemExit(1)


def fail(message: str) -> None:
    print("failing check:", message)
    raise SystemExit(1)


def normalize(text: str, scope: Path) -> str:
    text = text.replace(str(scope), "<scope>")
    return re.sub(r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}", "<uuid>", text)


def dry_run(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "bin/workflow.py"), "start", "review",
         "--runtime", "claude", "--scope", str(root), "--request", "x",
         "--dry-run", *extra],
        capture_output=True,
        text=True,
    )


spec = importlib.util.spec_from_file_location("workflow", root / "bin/workflow.py")
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)

# agy runtime
agy_cmd = wf.cli_command("agy", "x", Path("."))
if agy_cmd[:2] != ["agy", "-p"] or agy_cmd[-1] != "x":
    fail(f"agy cli_command shape: {agy_cmd}")

# R5: dry-run output is unchanged
proc = dry_run()
baseline = (root / "fixtures/review-dry-run.txt").read_text()
if proc.returncode != 0 or normalize(proc.stdout, root) != baseline:
    fail("review dry-run output differs from fixtures/review-dry-run.txt")

# run_process timeout
original_run = wf.subprocess.run


def raise_timeout(*args, **kwargs):
    raise subprocess.TimeoutExpired(cmd="x", timeout=kwargs.get("timeout"))


wf.subprocess.run = raise_timeout
try:
    wf.run_process("claude", "p", Path("."), timeout=1)
    fail("run_process did not raise on timeout")
except RuntimeError as exc:
    if "timed out" not in str(exc):
        fail(f"run_process timeout message: {exc}")
finally:
    wf.subprocess.run = original_run

if wf.run_process.__defaults__ != (None,):
    fail("run_process timeout must default to None")

# single-file scope: run_process starts reviewers in the file's directory, and start needs a directory scope
with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / "a.ts"
    target.write_text("export const a = 1;\n")

    calls = []

    class Done:
        stdout, returncode = "ok", 0

    original_run = wf.subprocess.run
    wf.subprocess.run = lambda cmd, **kwargs: (calls.append((cmd, kwargs)), Done())[1]
    try:
        wf.run_process("claude", "p", target)
        wf.run_process("codex", "p", target)
    finally:
        wf.subprocess.run = original_run
    parent = str(target.parent)
    if [kwargs["cwd"] for _, kwargs in calls] != [parent, parent] or parent not in calls[1][0]:
        fail(f"file scope must run reviewers in the file's directory: {calls}")

    proc = subprocess.run(
        [sys.executable, str(root / "bin/workflow.py"), "start", "review", "--runtime", "claude",
         "--scope", str(target), "--request", "x", "--dry-run"],
        capture_output=True, text=True,
    )
    if proc.returncode == 0 or "directory scope" not in proc.stderr:
        fail("start with a file scope must fail with a directory-scope message")

# stage_prompt caller overrides replace only the review stage input and the runner-files lines
with tempfile.TemporaryDirectory() as tmp:
    scope = Path(tmp)
    args = ("review", "review", scope, scope / "request.md", scope / "artifacts", 0)
    plain = wf.stage_prompt(*args)
    custom = wf.stage_prompt(*args, stage_input="CUSTOM STAGE INPUT", runner_files="CUSTOM RUNNER FILES")
    if "CUSTOM" in plain:
        fail("stage_prompt without overrides must not contain override text")
    if (
        "CUSTOM STAGE INPUT" not in custom
        or "CUSTOM RUNNER FILES" not in custom
        or "Original request file" in custom
        or "Perform an independent review" in custom
        or wf.REREVIEW_NOTE not in custom
        or "<ORCHESTRATION_RESULT>" not in custom
        or "Available prior stage artifacts:\n- none" not in custom
    ):
        fail("stage_prompt overrides must replace only the review stage input and the runner-files lines")

print("orchestration package smoke check: PASS")

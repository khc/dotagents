#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys

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
print("orchestration package smoke check: PASS")

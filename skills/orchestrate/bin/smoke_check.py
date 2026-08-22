#!/usr/bin/env python3
from pathlib import Path
import json, sys

root = Path(__file__).resolve().parents[1]
required = [
    "SKILL.md",
    "bin/workflow.py",
    "workflows/feature.md",
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
if missing:
    print("missing:", *missing, sep="\n- ")
    raise SystemExit(1)
print("orchestration package smoke check: PASS")

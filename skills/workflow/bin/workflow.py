#!/usr/bin/env python3
"""
Portable serial workflow runner for Claude Code and Codex CLI.

Each lifecycle stage is a fresh CLI process. The stage must append a machine
result between ORCHESTRATION_RESULT markers. The runner stores only stage
artifacts/final output, never conversation history.

Agy uses its native invoke_subagent runtime; see runtime/agy/.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

RESULT_RE = re.compile(
    r"<ORCHESTRATION_RESULT>\s*(\{.*?\})\s*</ORCHESTRATION_RESULT>",
    re.S,
)

TRANSITIONS = {
    "feature": {
        ("feature", "success"): "review",
        ("feature", "needs_plan"): "plan",
        ("feature", "blocked"): "STOP",
        ("plan", "success"): "implement",
        ("plan", "blocked"): "STOP",
        ("implement", "success"): "review",
        ("implement", "replan"): "plan",
        ("implement", "blocked"): "STOP",
        ("review", "ready"): "DONE",
        ("review", "findings"): "fix",
        ("review", "blocked"): "STOP",
        ("fix", "success"): "review",
        ("fix", "diagnosis_mismatch"): "review",
        ("fix", "blocked"): "STOP",
    },
    "planned": {
        ("plan", "success"): "implement",
        ("plan", "blocked"): "STOP",
        ("implement", "success"): "review",
        ("implement", "replan"): "plan",
        ("implement", "blocked"): "STOP",
        ("review", "ready"): "DONE",
        ("review", "findings"): "fix",
        ("review", "blocked"): "STOP",
        ("fix", "success"): "review",
        ("fix", "diagnosis_mismatch"): "review",
        ("fix", "blocked"): "STOP",
    },
    "review": {
        ("review", "ready"): "DONE",
        ("review", "findings"): "fix",
        ("review", "blocked"): "STOP",
        ("fix", "success"): "review",
        ("fix", "diagnosis_mismatch"): "review",
        ("fix", "blocked"): "STOP",
    },
}

VALID_STATUS = {
    "feature": {"success", "needs_plan", "blocked"},
    "plan": {"success", "blocked"},
    "implement": {"success", "replan", "blocked"},
    "review": {"ready", "findings", "blocked"},
    "fix": {"success", "diagnosis_mismatch", "blocked"},
}

ROLE = {
    "feature": "builder",
    "plan": "planner",
    "implement": "builder",
    "review": "reviewer",
    "fix": "fixer",
}

def initial_stage(workflow: str) -> str:
    return {"feature": "feature", "planned": "plan", "review": "review"}[workflow]

def cli_command(runtime: str, prompt: str, cwd: Path) -> list[str]:
    if runtime == "claude":
        base = shlex.split(os.environ.get("CLAUDE_CMD", "claude"))
        extra = shlex.split(os.environ.get("CLAUDE_ARGS", "-p"))
        return base + extra + [prompt]
    if runtime == "codex":
        base = shlex.split(os.environ.get("CODEX_CMD", "codex"))
        extra = shlex.split(os.environ.get("CODEX_ARGS", "exec"))
        # --cd is supported by current Codex exec builds; override CODEX_ARGS
        # if a local version uses a different cwd mechanism.
        if "--cd" not in extra and "-C" not in extra:
            extra += ["--cd", str(cwd)]
        return base + extra + [prompt]
    raise ValueError(f"unsupported runtime: {runtime}")

def stage_prompt(
    workflow: str,
    stage: str,
    scope: Path,
    request_file: Path,
    artifacts_dir: Path,
    cycle: int,
) -> str:
    prior = sorted(artifacts_dir.glob("*.json"))
    prior_lines = "\n".join(f"- {p}" for p in prior) or "- none"
    allowed = " | ".join(sorted(VALID_STATUS[stage]))

    stage_input = {
        "feature": "Use the original request. Invoke `$feature`.",
        "plan": "Use the original request and any explicit prior blocker artifact. Invoke `$plan`.",
        "implement": "Read the latest plan artifact and invoke `$implement` against that exact plan.",
        "review": (
            "Perform an independent review in a fresh context. Read only the "
            "relevant plan/implementation/prior-review/fix artifacts. Invoke `$review`."
        ),
        "fix": "Read the latest review artifact and invoke `$fix` for its findings.",
    }[stage]

    return f"""You are the {ROLE[stage]} stage of workflow `{workflow}`.

This is a fresh isolated lifecycle-stage invocation. Do not execute any later
workflow stage yourself. Return control to the orchestrator when this stage is done.

Active repo scope: {scope}
Original request file: {request_file}
Workflow artifact directory: {artifacts_dir}
Review/fix cycle: {cycle}

Before repo work, activate `$context` on exactly `{scope}` if this fresh runtime
does not already have that scope active. Do not broaden scope.

{stage_input}

Available prior stage artifacts:
{prior_lines}

IMPORTANT HANDOFF RULES
- Read stage artifacts, not previous-agent conversation history.
- Do not seek or reconstruct another agent's private reasoning.
- Preserve the lifecycle ownership rules of the invoked skill.
- Reviewer must treat producer claims as context, not evidence.
- Do not invoke the next lifecycle skill.

After completing the normal skill response, append EXACTLY one machine result:
<ORCHESTRATION_RESULT>
{{
  "stage": "{stage}",
  "status": "<one of: {allowed}>",
  "summary": "<brief factual stage result>",
  "verdict": "<ready|ready-with-fixes|not-ready|null>",
  "findings_count": <integer-or-0>,
  "review_mode": "<change|path|symbol|null>",
  "target": "<review target or null>",
  "target_symbol": "<symbol or null>",
  "source_uuid": "<sidecar/stage UUID or null>",
  "blocker": "<blocker or null>"
}}
</ORCHESTRATION_RESULT>

Use valid JSON: double quotes, no comments, no trailing commas.
Do not claim success/ready unless the invoked skill's evidence requirements are met.
"""

def run_process(runtime: str, prompt: str, cwd: Path) -> str:
    cmd = cli_command(runtime, prompt, cwd)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = proc.stdout or ""
    if proc.returncode != 0:
        raise RuntimeError(
            f"{runtime} stage process failed ({proc.returncode})\n{output}"
        )
    return output

def parse_result(output: str, stage: str) -> dict[str, Any]:
    matches = RESULT_RE.findall(output)
    if not matches:
        raise RuntimeError(
            f"stage {stage} did not emit <ORCHESTRATION_RESULT> JSON"
        )
    result = json.loads(matches[-1])
    if result.get("stage") != stage:
        raise RuntimeError(
            f"stage mismatch: expected {stage}, got {result.get('stage')}"
        )
    status = result.get("status")
    if status not in VALID_STATUS[stage]:
        raise RuntimeError(
            f"invalid {stage} status {status!r}; expected {sorted(VALID_STATUS[stage])}"
        )

    if stage == "review":
        verdict = result.get("verdict")
        findings_count = int(result.get("findings_count") or 0)

        # Normalize conservatively from the actual review contract.
        if findings_count > 0:
            normalized = "findings"
        elif status == "blocked":
            normalized = "blocked"
        elif verdict == "ready":
            normalized = "ready"
        elif verdict in {"ready-with-fixes", "not-ready"}:
            # A non-ready verdict without serialized findings is inconsistent;
            # do not terminate the workflow.
            normalized = "blocked"
            result["blocker"] = result.get("blocker") or (
                f"inconsistent review result: verdict={verdict} but findings_count=0"
            )
        else:
            normalized = status

        result["status"] = normalized

    return result

def save_artifact(
    artifacts: Path,
    seq: int,
    stage: str,
    result: dict[str, Any],
    output: str,
) -> Path:
    obj = {
        "sequence": seq,
        "stage": stage,
        "result": result,
        "final_output": output,
    }
    path = artifacts / f"{seq:03d}-{stage}.json"
    path.write_text(json.dumps(obj, indent=2))
    return path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("workflow", choices=["feature", "planned", "review"])
    ap.add_argument("--runtime", required=True, choices=["claude", "codex"])
    ap.add_argument("--scope", required=True)
    req = ap.add_mutually_exclusive_group(required=True)
    req.add_argument("--request")
    req.add_argument("--request-file")
    ap.add_argument("--state-dir")
    ap.add_argument("--max-review-fix-cycles", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    scope = Path(args.scope).resolve()
    if not scope.exists():
        raise SystemExit(f"scope does not exist: {scope}")

    workflow_id = str(uuid.uuid4())
    state_root = (
        Path(args.state_dir).resolve()
        if args.state_dir
        else scope / ".workflow" / workflow_id
    )
    artifacts = state_root / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    request_file = state_root / "request.md"
    if args.request_file:
        request_file.write_text(Path(args.request_file).read_text())
    else:
        request_file.write_text(args.request)

    state = {
        "workflow_id": workflow_id,
        "workflow": args.workflow,
        "runtime": args.runtime,
        "scope": str(scope),
        "stage": initial_stage(args.workflow),
        "status": "running",
        "review_fix_cycle": 0,
        "sequence": 0,
    }

    stage = state["stage"]
    while stage not in {"DONE", "STOP"}:
        state["sequence"] += 1
        if stage == "review":
            # First review is cycle 0. Increment only after a fix has run.
            pass

        prompt = stage_prompt(
            args.workflow,
            stage,
            scope,
            request_file,
            artifacts,
            state["review_fix_cycle"],
        )

        if args.dry_run:
            print(f"\n=== {stage.upper()} ===\n{prompt}")
            return 0

        output = run_process(args.runtime, prompt, scope)
        result = parse_result(output, stage)
        artifact_path = save_artifact(
            artifacts, state["sequence"], stage, result, output
        )

        transition = TRANSITIONS[args.workflow].get((stage, result["status"]))
        if transition is None:
            raise RuntimeError(
                f"no transition for {args.workflow}: {stage}/{result['status']}"
            )

        if stage == "fix" and result["status"] in {"success", "diagnosis_mismatch"}:
            state["review_fix_cycle"] += 1
            if state["review_fix_cycle"] > args.max_review_fix_cycles:
                transition = "STOP"
                result["blocker"] = (
                    f"review/fix loop exceeded {args.max_review_fix_cycles} cycles"
                )

        state["last_artifact"] = str(artifact_path)
        state["last_result"] = result
        state["stage"] = transition
        (state_root / "state.json").write_text(json.dumps(state, indent=2))
        print(
            f"[{state['sequence']}] {stage}: {result['status']} -> {transition}"
        )
        stage = transition

    state["status"] = "done" if stage == "DONE" else "blocked"
    state["stage"] = stage
    (state_root / "state.json").write_text(json.dumps(state, indent=2))
    print(json.dumps(state, indent=2))
    return 0 if stage == "DONE" else 2

if __name__ == "__main__":
    raise SystemExit(main())

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
from datetime import datetime, timezone
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
        ("plan", "success"): "AWAITING_PLAN_APPROVAL",
        ("plan", "blocked"): "STOP",
        # The three AWAITING_PLAN_APPROVAL entries below document the full
        # state diagram only; run_stage_loop's while-loop guard excludes
        # AWAITING_PLAN_APPROVAL, so they are never looked up. The actual
        # transitions are hardcoded in cmd_resume/cmd_approve/cmd_cancel.
        ("AWAITING_PLAN_APPROVAL", "user_approves"): "implement",
        ("AWAITING_PLAN_APPROVAL", "user_amends"): "plan",
        ("AWAITING_PLAN_APPROVAL", "user_cancels"): "STOP",
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
    "refactor": {
        ("refactor", "success"): "review",
        ("refactor", "blocked"): "STOP",
        ("review", "ready"): "DONE",
        ("review", "findings"): "fix",
        ("review", "blocked"): "STOP",
        ("fix", "success"): "review",
        ("fix", "diagnosis_mismatch"): "review",
        ("fix", "blocked"): "STOP",
    },
    "bug": {
        ("bug", "success"): "review",
        ("bug", "blocked"): "STOP",
        ("review", "ready"): "DONE",
        ("review", "findings"): "fix",
        ("review", "blocked"): "STOP",
        ("fix", "success"): "review",
        ("fix", "diagnosis_mismatch"): "review",
        ("fix", "blocked"): "STOP",
    },
    "planned": {
        ("plan", "success"): "AWAITING_PLAN_APPROVAL",
        ("plan", "blocked"): "STOP",
        # Documents the full state diagram only; not consulted by
        # run_stage_loop (see the "feature" dict above for why). Actual
        # transitions are hardcoded in cmd_resume/cmd_approve/cmd_cancel.
        ("AWAITING_PLAN_APPROVAL", "user_approves"): "implement",
        ("AWAITING_PLAN_APPROVAL", "user_amends"): "plan",
        ("AWAITING_PLAN_APPROVAL", "user_cancels"): "STOP",
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

DEFAULT_MAX_REVIEW_FIX_CYCLES = 5

VALID_STATUS = {
    "feature": {"success", "needs_plan", "blocked"},
    "refactor": {"success", "blocked"},
    "bug": {"success", "blocked"},
    "plan": {"success", "blocked"},
    "implement": {"success", "replan", "blocked"},
    "review": {"ready", "findings", "blocked"},
    "fix": {"success", "diagnosis_mismatch", "blocked"},
}

ROLE = {
    "feature": "builder",
    "refactor": "builder",
    "bug": "builder",
    "plan": "planner",
    "implement": "builder",
    "review": "reviewer",
    "fix": "fixer",
}

# Stage-specific handoff identifier field, matching SKILL.md's Persistence
# section and schemas/*.schema.json (plan_id, implementation_id, review_uuid,
# fix_uuid).
STAGE_ID_FIELD = {
    "feature": "implementation_id",
    "refactor": "implementation_id",
    "bug": "implementation_id",
    "plan": "plan_id",
    "implement": "implementation_id",
    "review": "review_uuid",
    "fix": "fix_uuid",
}

def initial_stage(workflow: str) -> str:
    return {
        "feature": "feature",
        "refactor": "refactor",
        "bug": "bug",
        "planned": "plan",
        "review": "review",
    }[workflow]

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
    active_plan: dict | None = None,
    plan_reason: str | None = None,
    amendment: str | None = None,
) -> str:
    prior = sorted(artifacts_dir.glob("*.json"))
    prior_lines = "\n".join(f"- {p}" for p in prior) or "- none"
    allowed = " | ".join(sorted(VALID_STATUS[stage]))
    id_field = STAGE_ID_FIELD[stage]

    def plan_stage_input() -> str:
        if active_plan is None:
            return "Use the original request. Invoke `$plan`."
        reopen = (
            f"Reopen the existing plan artifact at `{active_plan['path']}` "
            f"(plan_id `{active_plan['plan_id']}`, currently revision "
            f"{active_plan['revision']}, status `{active_plan['status']}`). "
            "Follow `skills/plan/SKILL.md`'s Plan Revision rules: increment "
            "`revision`, keep `status: draft`, and reuse the same `plan_id` "
            "-- do not create a new plan file."
        )
        if plan_reason == "amendment":
            reopen += f"\n\nReason: conversational amendment.\nAmendment: {amendment}"
        elif plan_reason == "implement_replan":
            reopen += (
                "\n\nReason: implement returned status=replan. Read the latest "
                "`implement` artifact's `blocker` field for the re-plan evidence."
            )
        return reopen

    stage_input = {
        "feature": "Use the original request. Invoke `$feature`.",
        "refactor": "Use the original request. Invoke `$refactor`.",
        "bug": "Use the original request. Invoke `$bug`.",
        "plan": plan_stage_input() if stage == "plan" else "",
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

Before repo work, activate `$scope` on exactly `{scope}` if this fresh runtime
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
  "{id_field}": "<sidecar/stage UUID or null>",
  "plan_path": "<path to plan_<timestamp>.md or null>",
  "plan_revision": <integer-or-null>,
  "plan_status": "<draft|approved|null>",
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

    if stage == "plan" and status == "success":
        plan_path = result.get("plan_path")
        plan_revision = result.get("plan_revision")
        plan_status = result.get("plan_status")
        if not plan_path:
            raise RuntimeError("plan stage success missing plan_path")
        if not isinstance(plan_revision, int):
            raise RuntimeError(
                f"plan stage success has invalid plan_revision {plan_revision!r}; expected int"
            )
        if plan_status != "draft":
            raise RuntimeError(
                f"plan stage success has invalid plan_status {plan_status!r}; expected 'draft'"
            )

    return result

def save_artifact(
    artifacts: Path,
    seq: int,
    stage: str,
    result: dict[str, Any],
    output: str,
    workflow_id: str,
    scope: Path,
) -> Path:
    obj = {
        "sequence": seq,
        "stage": stage,
        "workflow_id": workflow_id,
        "scope": str(scope),
        "result": result,
        "final_output": output,
    }
    path = artifacts / f"{seq:03d}-{stage}.json"
    path.write_text(json.dumps(obj, indent=2))
    return path

def run_stage_loop(
    workflow: str,
    runtime: str,
    scope: Path,
    request_file: Path,
    artifacts: Path,
    state: dict,
    max_cycles: int,
    dry_run: bool,
    plan_reason: str = "initial",
    amendment: str | None = None,
) -> int:
    state_root = artifacts.parent
    stage = state["stage"]
    prev_stage: str | None = None
    prev_status: str | None = None

    while stage not in {"DONE", "STOP", "AWAITING_PLAN_APPROVAL"}:
        state["sequence"] += 1

        if stage == "plan":
            effective_plan_reason = (
                "implement_replan"
                if prev_stage == "implement" and prev_status == "replan"
                else plan_reason
            )
            prompt = stage_prompt(
                workflow,
                stage,
                scope,
                request_file,
                artifacts,
                state["review_fix_cycle"],
                active_plan=state.get("active_plan"),
                plan_reason=effective_plan_reason,
                amendment=amendment if effective_plan_reason == "amendment" else None,
            )
        else:
            prompt = stage_prompt(
                workflow,
                stage,
                scope,
                request_file,
                artifacts,
                state["review_fix_cycle"],
            )

        if dry_run:
            print(f"\n=== {stage.upper()} ===\n{prompt}")
            return 0

        output = run_process(runtime, prompt, scope)
        result = parse_result(output, stage)
        artifact_path = save_artifact(
            artifacts, state["sequence"], stage, result, output,
            state["workflow_id"], scope,
        )

        transition = TRANSITIONS[workflow].get((stage, result["status"]))
        if transition is None:
            raise RuntimeError(
                f"no transition for {workflow}: {stage}/{result['status']}"
            )

        if stage == "fix" and result["status"] in {"success", "diagnosis_mismatch"}:
            state["review_fix_cycle"] += 1
            if state["review_fix_cycle"] > max_cycles:
                transition = "STOP"
                result["blocker"] = (
                    f"review/fix loop exceeded {max_cycles} cycles"
                )

        if stage == "plan" and transition == "AWAITING_PLAN_APPROVAL":
            state["active_plan"] = {
                "path": result.get("plan_path"),
                "plan_id": result.get("plan_id"),
                "revision": result.get("plan_revision"),
                "status": result.get("plan_status"),
            }

        state["last_artifact"] = str(artifact_path)
        state["last_result"] = result
        state["stage"] = transition
        (state_root / "state.json").write_text(json.dumps(state, indent=2))
        print(
            f"[{state['sequence']}] {stage}: {result['status']} -> {transition}"
        )
        prev_stage, prev_status = stage, result["status"]
        stage = transition

    state["status"] = {
        "DONE": "done",
        "AWAITING_PLAN_APPROVAL": "awaiting_plan_approval",
    }.get(stage, "blocked")
    state["stage"] = stage
    (state_root / "state.json").write_text(json.dumps(state, indent=2))
    print(json.dumps(state, indent=2))
    return {"DONE": 0, "STOP": 2, "AWAITING_PLAN_APPROVAL": 3}[stage]

def resolve_state_root(scope: str | None, state_dir: str | None, workflow_id: str) -> Path:
    if state_dir:
        return Path(state_dir).resolve()
    if scope:
        return Path(scope).resolve() / ".workflow" / workflow_id
    raise SystemExit("either --scope or --state-dir is required")

def load_state(state_root: Path, workflow_id: str) -> dict:
    state_path = state_root / "state.json"
    if not state_path.exists():
        raise SystemExit(f"unknown workflow_id: {workflow_id} (no state.json at {state_path})")
    return json.loads(state_path.read_text())

def write_state(state_root: Path, state: dict) -> None:
    (state_root / "state.json").write_text(json.dumps(state, indent=2))

def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    subparsers = ap.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="start a fresh workflow run")
    start.add_argument("workflow", choices=["feature", "refactor", "bug", "planned", "review"])
    start.add_argument("--runtime", required=True, choices=["claude", "codex"])
    start.add_argument("--scope", required=True)
    req = start.add_mutually_exclusive_group(required=True)
    req.add_argument("--request")
    req.add_argument("--request-file")
    start.add_argument("--state-dir")
    start.add_argument("--max-review-fix-cycles", type=int, default=DEFAULT_MAX_REVIEW_FIX_CYCLES)
    start.add_argument("--dry-run", action="store_true")

    resume = subparsers.add_parser("resume", help="reopen an AWAITING_PLAN_APPROVAL plan with an amendment")
    resume.add_argument("workflow_id")
    resume.add_argument("--message", required=True)
    resume.add_argument("--scope")
    resume.add_argument("--state-dir")
    resume.add_argument("--runtime", choices=["claude", "codex"])
    resume.add_argument("--dry-run", action="store_true")

    approve = subparsers.add_parser("approve", help="approve an AWAITING_PLAN_APPROVAL plan and dispatch $implement")
    approve.add_argument("workflow_id")
    approve.add_argument("--scope")
    approve.add_argument("--state-dir")
    approve.add_argument("--dry-run", action="store_true")

    cancel = subparsers.add_parser("cancel", help="cancel an AWAITING_PLAN_APPROVAL workflow")
    cancel.add_argument("workflow_id")
    cancel.add_argument("--scope")
    cancel.add_argument("--state-dir")
    cancel.add_argument("--reason")

    return ap

def cmd_start(args: argparse.Namespace) -> int:
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
    request_file = state_root / "request.md"
    if not args.dry_run:
        artifacts.mkdir(parents=True, exist_ok=True)
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
        "max_review_fix_cycles": args.max_review_fix_cycles,
    }

    return run_stage_loop(
        args.workflow,
        args.runtime,
        scope,
        request_file,
        artifacts,
        state,
        args.max_review_fix_cycles,
        args.dry_run,
        plan_reason="initial",
    )

def cmd_resume(args: argparse.Namespace) -> int:
    state_root = resolve_state_root(args.scope, args.state_dir, args.workflow_id)
    state = load_state(state_root, args.workflow_id)
    if state["stage"] != "AWAITING_PLAN_APPROVAL":
        raise SystemExit(
            f"cannot resume: workflow is not awaiting plan approval (state={state['stage']!r})"
        )

    amendment_path = state_root / f"amendment-{state['sequence'] + 1:03d}.md"
    if not args.dry_run:
        amendment_path.write_text(args.message)

    runtime = args.runtime or state["runtime"]
    scope = Path(state["scope"])
    artifacts = state_root / "artifacts"
    request_file = state_root / "request.md"
    state["stage"] = "plan"

    return run_stage_loop(
        state["workflow"],
        runtime,
        scope,
        request_file,
        artifacts,
        state,
        state.get("max_review_fix_cycles", DEFAULT_MAX_REVIEW_FIX_CYCLES),
        args.dry_run,
        plan_reason="amendment",
        amendment=args.message,
    )

def cmd_approve(args: argparse.Namespace) -> int:
    state_root = resolve_state_root(args.scope, args.state_dir, args.workflow_id)
    state = load_state(state_root, args.workflow_id)
    active_plan = state.get("active_plan")
    if state["stage"] != "AWAITING_PLAN_APPROVAL" or not active_plan:
        raise SystemExit(
            "cannot approve: workflow is not awaiting plan approval with an active plan "
            f"(state={state['stage']!r}, active_plan={active_plan!r})"
        )

    scope = Path(state["scope"])
    plan_path = Path(active_plan["path"])
    if not plan_path.is_absolute():
        plan_path = scope / plan_path
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    artifacts = state_root / "artifacts"
    request_file = state_root / "request.md"

    if args.dry_run:
        print(
            f"=== APPROVE (dry-run) ===\n"
            f"Would patch {plan_path}:\n"
            f"  status: draft -> approved\n"
            f"  updated_at: {timestamp}"
        )
        prompt = stage_prompt(
            state["workflow"], "implement", scope, request_file, artifacts,
            state["review_fix_cycle"],
        )
        print(f"\n=== IMPLEMENT ===\n{prompt}")
        return 0

    text = plan_path.read_text()
    patched, n = re.subn(r"(?m)^status:\s*draft\s*$", "status: approved", text, count=1)
    if n == 0:
        raise RuntimeError(f"approve: no 'status: draft' line found in {plan_path}")
    patched, _ = re.subn(r"(?m)^updated_at:.*$", f"updated_at: {timestamp}", patched, count=1)
    plan_path.write_text(patched)

    active_plan["status"] = "approved"
    state["stage"] = "implement"
    # Persist state.json before dispatching the implement stage so it never
    # disagrees with the already-patched plan file if the subprocess raises.
    write_state(state_root, state)

    return run_stage_loop(
        state["workflow"],
        state["runtime"],
        scope,
        request_file,
        artifacts,
        state,
        state.get("max_review_fix_cycles", DEFAULT_MAX_REVIEW_FIX_CYCLES),
        False,
    )

def cmd_cancel(args: argparse.Namespace) -> int:
    state_root = resolve_state_root(args.scope, args.state_dir, args.workflow_id)
    state = load_state(state_root, args.workflow_id)
    if state["stage"] != "AWAITING_PLAN_APPROVAL":
        raise SystemExit(
            f"cannot cancel: workflow is not awaiting plan approval (state={state['stage']!r})"
        )
    state["stage"] = "STOP"
    state["status"] = "blocked"
    if args.reason:
        state["cancel_reason"] = args.reason
    write_state(state_root, state)
    print(json.dumps(state, indent=2))
    return 2

def main() -> int:
    ap = build_arg_parser()
    args = ap.parse_args()
    return {
        "start": cmd_start,
        "resume": cmd_resume,
        "approve": cmd_approve,
        "cancel": cmd_cancel,
    }[args.command](args)

if __name__ == "__main__":
    raise SystemExit(main())

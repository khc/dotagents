#!/usr/bin/env python3
"""
Portable serial workflow runner for Claude Code, Codex CLI, and Agy (`agy -p`).

Each lifecycle stage is a fresh CLI process. The stage must append a machine
result between ORCHESTRATION_RESULT markers. The runner stores only stage
artifacts/final output, never conversation history.

Agy also has a native invoke_subagent runtime; see runtime/agy/.
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
from concurrent.futures import ThreadPoolExecutor
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

RUNTIMES = ["claude", "codex", "agy"]
WORKFLOWS = ["feature", "refactor", "bug", "planned", "review"]
DEFAULT_REVIEW_TIMEOUT = 900
# Prompts travel as one command-line argument; Linux caps a single argument near 128 KB.
MAX_PROMPT_BYTES = 100_000

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
        return base + extra + ["--plugin-dir", str(Path(__file__).resolve().parents[3]), prompt]
    if runtime == "codex":
        base = shlex.split(os.environ.get("CODEX_CMD", "codex"))
        extra = shlex.split(os.environ.get("CODEX_ARGS", "exec"))
        # --cd is supported by current Codex exec builds; override CODEX_ARGS
        # if a local version uses a different cwd mechanism.
        if "--cd" not in extra and "-C" not in extra:
            extra += ["--cd", str(cwd)]
        return base + extra + [prompt]
    if runtime == "agy":
        base = shlex.split(os.environ.get("AGY_CMD", "agy"))
        extra = shlex.split(os.environ.get("AGY_ARGS", "-p"))
        return base + extra + [prompt]
    raise ValueError(f"unsupported runtime: {runtime}")

def scope_dir(scope: Path) -> Path:
    """Directory to run in for a scope that may be a single file."""
    return scope if scope.is_dir() else scope.parent

def read_text_exact(path: Path) -> str:
    """Read text without newline translation, so typed requests stay verbatim."""
    return path.read_bytes().decode("utf-8")

def write_text_exact(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))

def ensure_prompt_fits(prompt: str) -> None:
    size = len(prompt.encode("utf-8"))
    if size > MAX_PROMPT_BYTES:
        raise SystemExit(
            "request text is too large to pass verbatim as a command-line argument "
            f"({size} bytes of prompt; limit {MAX_PROMPT_BYTES}). Shorten it, or put the "
            "details in a file inside the scope and refer to the path."
        )

def arguments_block(text: str, label: str) -> str:
    """Embed user text unchanged; a random token keeps it from closing the block."""
    if not text:
        return "No arguments were supplied."
    token = uuid.uuid4().hex[:8]
    return f"{label}\n<ARGUMENTS token={token}>\n{text}\n</ARGUMENTS token={token}>"

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
    review_phase: str | None = None,
    review_runtimes: list[str] | None = None,
    review_timeout: int | None = None,
    request_text: str | None = None,
) -> str:
    prior = sorted(artifacts_dir.glob("*.json"))
    prior_lines = "\n".join(f"- {p}" for p in prior) or "- none"
    runner_files = (
        f"Original request file: {request_file}\n"
        f"Workflow artifact directory: {artifacts_dir}"
    )
    if request_text is not None and scope.is_file():
        # Runner files live outside a single-file scope; never point reviewers at them.
        runner_files = "Workflow artifacts: none (file scope: runner files are outside the active scope)"
        prior_lines = "- none"
    allowed = " | ".join(sorted(VALID_STATUS[stage]))
    id_field = STAGE_ID_FIELD[stage]

    def plan_stage_input() -> str:
        if active_plan is None:
            return "Use the original request. Invoke `$dot:plan`."
        reopen = (
            f"Reopen the existing plan artifact at `{active_plan['path']}` "
            f"(plan_id `{active_plan['plan_id']}`, currently revision "
            f"{active_plan['revision']}, status `{active_plan['status']}`). "
            f"Follow `{Path(__file__).resolve().parents[2] / 'plan' / 'SKILL.md'}`'s Plan Revision rules: increment "
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

    def review_stage_input() -> str:
        base = (
            "Perform an independent review in a fresh context. Read only the "
            "relevant plan/implementation/prior-review/fix artifacts. Invoke `$dot:review`."
        )
        if review_phase == "independent":
            if request_text is not None:
                base = (
                    "Perform an independent review in a fresh context. Read only the "
                    "relevant plan/implementation/prior-review/fix artifacts. "
                    + (
                        "Invoke `$dot:review` with exactly the text inside the ARGUMENTS "
                        "block below, as if the user had typed it after `/dot:review`. "
                        "Do not rephrase, summarize, or add to it.\n\n"
                        + arguments_block(request_text, "Arguments (verbatim):")
                        if request_text
                        else "Invoke `$dot:review` on the active scope path. "
                        "No arguments were supplied."
                    )
                )
            return (
                f"{base}\n\nOther reviewers are working in parallel. Do not read "
                "`.sidecar/` and do not run `sidecar_workflow.py read`; read only "
                "the stage artifacts listed below."
            )
        if review_phase == "cross":
            return (
                "Invoke `$dot:cross-review`. Run the independent reviewers with:\n\n"
                f"uv run --no-project {shlex.quote(str(Path(__file__).resolve()))} review-fanout "
                f"--state-dir {shlex.quote(str(artifacts_dir.parent))} "
                f"--workflow {shlex.quote(workflow)} --scope {shlex.quote(str(scope))} "
                f"--runtimes {shlex.quote(','.join(review_runtimes or []))} "
                f"--cycle {cycle} --review-timeout {review_timeout}\n\n"
                "Then follow the skill to synthesize and save the final review."
                + (
                    "\n\n"
                    + arguments_block(
                        request_text,
                        "Arguments the user gave to `$dot:cross-review` (verbatim):",
                    )
                    if request_text is not None
                    else ""
                )
            )
        return base

    stage_input = {
        "feature": "Use the original request. Invoke `$dot:feature`.",
        "refactor": "Use the original request. Invoke `$dot:refactor`.",
        "bug": "Use the original request. Invoke `$dot:bug`.",
        "plan": plan_stage_input() if stage == "plan" else "",
        "implement": "Read the latest plan artifact and invoke `$dot:implement` against that exact plan.",
        "review": review_stage_input(),
        "fix": "Read the latest review artifact and invoke `$dot:fix` for its findings.",
    }[stage]

    return f"""You are the {ROLE[stage]} stage of workflow `{workflow}`.

This is a fresh isolated lifecycle-stage invocation. Do not execute any later
workflow stage yourself. Return control to the orchestrator when this stage is done.

Active repo scope: {scope}
{runner_files}
Review/fix cycle: {cycle}

Before repo work, activate `$dot:scope` on exactly `{scope}` if this fresh runtime
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
  "plan_path": "<repo-root-relative path to .plans/plan_<timestamp>.md, or null>",
  "plan_revision": <integer-or-null>,
  "plan_status": "<draft|approved|null>",
  "blocker": "<blocker or null>"
}}
</ORCHESTRATION_RESULT>

Use valid JSON: double quotes, no comments, no trailing commas.
Do not claim success/ready unless the invoked skill's evidence requirements are met.
"""

def run_process(
    runtime: str, prompt: str, cwd: Path, timeout: float | None = None
) -> str:
    cwd = scope_dir(cwd)
    cmd = cli_command(runtime, prompt, cwd)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"{runtime} stage process timed out after {timeout}s"
        ) from None
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

REVIEWER_ATTEMPTS = 2

def run_reviewer(
    runtime: str, prompt: str, scope: Path, timeout: float | None
) -> tuple[dict[str, Any], str]:
    """Run one independent reviewer; retry once only on envelope problems.

    Process failures and timeouts propagate immediately. A non-blocked result
    must carry `review_uuid`, otherwise the review was never saved to the sidecar.
    """
    for attempt in range(REVIEWER_ATTEMPTS):
        output = run_process(runtime, prompt, scope, timeout)
        try:
            result = parse_result(output, "review")
            if result["status"] != "blocked" and not result.get("review_uuid"):
                raise RuntimeError(
                    f"{runtime} review result missing review_uuid (not saved to sidecar)"
                )
        except (RuntimeError, ValueError):
            if attempt == REVIEWER_ATTEMPTS - 1:
                raise
            continue
        return result, output
    raise AssertionError("unreachable")

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
    request_text: str | None = None,
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
            review_kwargs = {}
            if stage == "review" and state.get("review_runtimes"):
                review_kwargs = {
                    "review_phase": "cross",
                    "review_runtimes": state["review_runtimes"],
                    "review_timeout": state.get("review_timeout", DEFAULT_REVIEW_TIMEOUT),
                    "request_text": (
                        request_text
                        if request_text is not None
                        else read_text_exact(request_file) if request_file.exists() else None
                    ),
                }
            prompt = stage_prompt(
                workflow,
                stage,
                scope,
                request_file,
                artifacts,
                state["review_fix_cycle"],
                **review_kwargs,
            )

        ensure_prompt_fits(prompt)
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

def repo_root(scope: Path) -> Path:
    """Resolve the repo root for a scope dir, matching scripts/context_workflow.py."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(scope),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).resolve()
    except OSError:
        pass
    return scope.resolve()

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

def runtime_list(value: str) -> list[str]:
    runtimes = list(dict.fromkeys(v.strip() for v in value.split(",") if v.strip()))
    unknown = [r for r in runtimes if r not in RUNTIMES]
    if unknown or len(runtimes) < 2:
        raise argparse.ArgumentTypeError(
            f"expected at least 2 runtimes from {RUNTIMES}, got {value!r}"
        )
    return runtimes

def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    subparsers = ap.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="start a fresh workflow run")
    start.add_argument("workflow", choices=WORKFLOWS)
    start.add_argument("--runtime", required=True, choices=RUNTIMES)
    start.add_argument("--scope", required=True)
    req = start.add_mutually_exclusive_group(required=True)
    req.add_argument("--request")
    req.add_argument("--request-file")
    start.add_argument("--state-dir")
    start.add_argument("--max-review-fix-cycles", type=int, default=DEFAULT_MAX_REVIEW_FIX_CYCLES)
    start.add_argument(
        "--review-runtimes",
        type=runtime_list,
        help="comma-separated runtimes for cross-review (at least 2)",
    )
    start.add_argument("--review-timeout", type=int, default=DEFAULT_REVIEW_TIMEOUT)
    start.add_argument("--dry-run", action="store_true")

    resume = subparsers.add_parser("resume", help="reopen an AWAITING_PLAN_APPROVAL plan with an amendment")
    resume.add_argument("workflow_id")
    resume.add_argument("--message", required=True)
    resume.add_argument("--scope")
    resume.add_argument("--state-dir")
    resume.add_argument("--runtime", choices=RUNTIMES)
    resume.add_argument("--dry-run", action="store_true")

    approve = subparsers.add_parser("approve", help="approve an AWAITING_PLAN_APPROVAL plan and dispatch $dot:implement")
    approve.add_argument("workflow_id")
    approve.add_argument("--scope")
    approve.add_argument("--state-dir")
    approve.add_argument("--dry-run", action="store_true")

    cancel = subparsers.add_parser("cancel", help="cancel an AWAITING_PLAN_APPROVAL workflow")
    cancel.add_argument("workflow_id")
    cancel.add_argument("--scope")
    cancel.add_argument("--state-dir")
    cancel.add_argument("--reason")

    fanout = subparsers.add_parser(
        "review-fanout",
        help="run independent reviewers on several runtimes and report their sidecar UUIDs",
    )
    fanout.add_argument("--scope", required=True)
    fanout.add_argument("--runtimes", required=True, type=runtime_list)
    fanout.add_argument("--workflow", choices=WORKFLOWS, default="review")
    fanout.add_argument("--cycle", type=int, default=0)
    fanout.add_argument("--review-timeout", type=int, default=DEFAULT_REVIEW_TIMEOUT)
    fanout.add_argument("--state-dir", help="existing workflow state root to reuse")
    fanout.add_argument("--request")
    fanout.add_argument("--request-file")
    fanout.add_argument("--dry-run", action="store_true")

    return ap

def cmd_start(args: argparse.Namespace) -> int:
    scope = Path(args.scope).resolve()
    if not scope.exists():
        raise SystemExit(f"scope does not exist: {scope}")
    if scope.is_file():
        raise SystemExit(
            "start requires a directory scope: workflow artifacts must live inside the "
            "scope. Use a directory scope, or review-fanout for a single-file review."
        )

    workflow_id = str(uuid.uuid4())
    state_root = (
        Path(args.state_dir).resolve()
        if args.state_dir
        else scope / ".workflow" / workflow_id
    )
    artifacts = state_root / "artifacts"
    request_file = state_root / "request.md"
    request_text = (
        read_text_exact(Path(args.request_file)) if args.request_file else args.request
    )
    if not args.dry_run:
        artifacts.mkdir(parents=True, exist_ok=True)
        write_text_exact(request_file, request_text)

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
    if args.review_runtimes:
        state["review_runtimes"] = args.review_runtimes
        state["review_timeout"] = args.review_timeout

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
        request_text=request_text,
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
        # plan paths are relative to the repo root (dot:plan's SKILL.md's
        # Plan Artifact section), never to the workflow's scope dir.
        plan_path = repo_root(scope) / plan_path
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

def reviewer_entry(runtime: str, future: Any) -> dict[str, Any]:
    try:
        result, _ = future.result()
    except Exception as exc:  # any reviewer failure blocks the ensemble
        return {
            "runtime": runtime,
            "status": "blocked",
            "verdict": None,
            "findings_count": 0,
            "review_uuid": None,
            "blocker": str(exc)[:500],
        }
    return {
        "runtime": runtime,
        "status": result["status"],
        "verdict": result.get("verdict"),
        "findings_count": int(result.get("findings_count") or 0),
        "review_uuid": result.get("review_uuid"),
        "blocker": result.get("blocker"),
    }

def cmd_review_fanout(args: argparse.Namespace) -> int:
    scope = Path(args.scope).resolve()
    if not scope.exists():
        raise SystemExit(f"scope does not exist: {scope}")

    state_root = (
        Path(args.state_dir).resolve()
        if args.state_dir
        else scope_dir(scope) / ".workflow" / str(uuid.uuid4())
    )
    artifacts = state_root / "artifacts"
    request_file = state_root / "request.md"
    if request_file.exists():
        request = read_text_exact(request_file)
    elif args.request_file:
        request = read_text_exact(Path(args.request_file))
    elif args.request is not None:
        request = args.request
    elif args.dry_run:
        request = "<request text>"
    else:
        raise SystemExit("--request or --request-file is required without an existing --state-dir")
    if not args.dry_run:
        artifacts.mkdir(parents=True, exist_ok=True)
        if not request_file.exists():
            write_text_exact(request_file, request)

    prompt = stage_prompt(
        args.workflow, "review", scope, request_file, artifacts, args.cycle,
        review_phase="independent", request_text=request,
    )
    ensure_prompt_fits(prompt)
    if args.dry_run:
        for runtime in args.runtimes:
            print(f"=== REVIEW ({runtime}) ===\n{prompt}")
        return 0

    # Re-review cycles reuse the state dir, so every run gets its own result file.
    run_id = str(uuid.uuid4())
    result_file = state_root / f"fanout-{run_id}.json"
    print(f"FANOUT_RESULT={result_file}", flush=True)
    with ThreadPoolExecutor(max_workers=len(args.runtimes)) as pool:
        futures = {
            runtime: pool.submit(run_reviewer, runtime, prompt, scope, args.review_timeout)
            for runtime in args.runtimes
        }
    reviewers = [reviewer_entry(runtime, future) for runtime, future in futures.items()]
    ok = all(r["status"] != "blocked" and r["review_uuid"] for r in reviewers)
    report = {
        "run_id": run_id,
        "state_dir": str(state_root),
        "ok": ok,
        "reviewers": reviewers,
    }

    tmp = result_file.with_name(result_file.name + ".tmp")
    tmp.write_text(json.dumps(report, indent=2))
    os.replace(tmp, result_file)
    print(json.dumps(report, indent=2))
    return 0 if ok else 2

def main() -> int:
    ap = build_arg_parser()
    args = ap.parse_args()
    return {
        "start": cmd_start,
        "resume": cmd_resume,
        "approve": cmd_approve,
        "cancel": cmd_cancel,
        "review-fanout": cmd_review_fanout,
    }[args.command](args)

if __name__ == "__main__":
    raise SystemExit(main())

# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///
"""Run independent reviewers on several runtimes and report their sidecar UUIDs.

Moved from the dot plugin's workflow.py (`review-fanout`). It needs the dot plugin: the reviewers run `$dot:review`
in child processes started with the helpers of dot's `skills/workflow/bin/workflow.py`, which is loaded from the dot
plugin root (`--dot-plugin-root`, else the DOT_PLUGIN_ROOT environment variable, else the sibling `../dot`).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

DEFAULT_REVIEW_TIMEOUT = 900
REVIEWER_ATTEMPTS = 2
WORKFLOW_PATH = Path("skills/workflow/bin/workflow.py")
FILE_SCOPE_RUNNER_FILES = "Workflow artifacts: none (file scope: runner files are outside the active scope)"

wf: Any = None  # dot's workflow module, set by load_workflow()


def find_dot_plugin_root(explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit)
    elif os.environ.get("DOT_PLUGIN_ROOT"):
        candidate = Path(os.environ["DOT_PLUGIN_ROOT"])
    else:
        candidate = Path(__file__).resolve().parents[2] / "dot"
    root = candidate.expanduser().resolve()
    if not (root / WORKFLOW_PATH).is_file():
        raise SystemExit(f"Error: the dot plugin was not found (looked in {root}); set DOT_PLUGIN_ROOT.")
    return root


def load_workflow(dot_plugin_root: str | None) -> Any:
    path = find_dot_plugin_root(dot_plugin_root) / WORKFLOW_PATH
    spec = importlib.util.spec_from_file_location("workflow", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime_list(value: str) -> list[str]:
    return list(dict.fromkeys(v.strip() for v in value.split(",") if v.strip()))


def validate_choices(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Check the values that depend on dot's workflow module, once it is loaded."""
    unknown = [r for r in args.runtimes if r not in wf.RUNTIMES]
    if unknown or len(args.runtimes) < 2:
        parser.error(
            f"argument --runtimes: expected at least 2 runtimes from {wf.RUNTIMES}, "
            f"got {','.join(args.runtimes)!r}"
        )
    if args.workflow not in wf.WORKFLOWS:
        parser.error(f"argument --workflow: invalid choice: {args.workflow!r} (choose from {wf.WORKFLOWS})")


def run_reviewer(
    runtime: str, prompt: str, scope: Path, timeout: float | None
) -> tuple[dict[str, Any], str]:
    """Run one independent reviewer; retry once only on envelope problems.

    Process failures and timeouts propagate immediately. A non-blocked result
    must carry `review_uuid`, otherwise the review was never saved to the sidecar.
    """
    for attempt in range(REVIEWER_ATTEMPTS):
        output = wf.run_process(runtime, prompt, scope, timeout)
        try:
            result = wf.parse_result(output, "review")
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


def independent_stage_input(request_text: str) -> str:
    base = (
        "Perform an independent review in a fresh context. Read only the "
        "relevant plan/implementation/prior-review/fix artifacts. "
        + (
            "Invoke `$dot:review` with exactly the text inside the ARGUMENTS "
            "block below, as if the user had typed it after `/dot:review`. "
            "Do not rephrase, summarize, or add to it.\n\n"
            + wf.arguments_block(request_text, "Arguments (verbatim):")
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


def build_prompt(
    workflow: str, scope: Path, request_file: Path, artifacts: Path, cycle: int, request_text: str
) -> str:
    # Runner files live outside a single-file scope; never point reviewers at them.
    runner_files = FILE_SCOPE_RUNNER_FILES if scope.is_file() else None
    return wf.stage_prompt(
        workflow, "review", scope, request_file, artifacts, cycle,
        stage_input=independent_stage_input(request_text), runner_files=runner_files,
    )


def cmd_review_fanout(args: argparse.Namespace) -> int:
    scope = Path(args.scope).resolve()
    if not scope.exists():
        raise SystemExit(f"scope does not exist: {scope}")

    state_root = (
        Path(args.state_dir).resolve()
        if args.state_dir
        else wf.scope_dir(scope) / ".workflow" / str(uuid.uuid4())
    )
    artifacts = state_root / "artifacts"
    request_file = state_root / "request.md"
    if request_file.exists():
        request = wf.read_text_exact(request_file)
    elif args.request_file:
        request = wf.read_text_exact(Path(args.request_file))
    elif args.request is not None:
        request = args.request
    elif args.dry_run:
        request = "<request text>"
    else:
        raise SystemExit("--request or --request-file is required without an existing --state-dir")
    if not args.dry_run:
        artifacts.mkdir(parents=True, exist_ok=True)
        if not request_file.exists():
            wf.write_text_exact(request_file, request)

    prompt = build_prompt(args.workflow, scope, request_file, artifacts, args.cycle, request)
    wf.ensure_prompt_fits(prompt)
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


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Run independent reviewers on several runtimes and report their sidecar UUIDs."
    )
    ap.add_argument("--dot-plugin-root", help="root of the dot plugin (default: $DOT_PLUGIN_ROOT, else ../dot)")
    ap.add_argument("--scope", required=True)
    ap.add_argument("--runtimes", required=True, type=runtime_list)
    ap.add_argument("--workflow", default="review")
    ap.add_argument("--cycle", type=int, default=0)
    ap.add_argument("--review-timeout", type=int, default=DEFAULT_REVIEW_TIMEOUT)
    ap.add_argument("--state-dir", help="existing workflow state root to reuse")
    ap.add_argument("--request")
    ap.add_argument("--request-file")
    ap.add_argument("--dry-run", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    global wf
    parser = build_arg_parser()
    args = parser.parse_args(argv)  # parse everything first: nothing is imported from the dot plugin before this succeeds
    wf = load_workflow(args.dot_plugin_root)
    validate_choices(parser, args)
    return cmd_review_fanout(args)


if __name__ == "__main__":
    raise SystemExit(main())

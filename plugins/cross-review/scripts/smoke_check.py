#!/usr/bin/env python3
"""Smoke check for the cross-review plugin: fan-out runner, reviewer prompts, skill and evals.

Needs the dot plugin: --dot-plugin-root is not a flag here, set DOT_PLUGIN_ROOT or keep the repo layout
(plugins/cross-review next to plugins/dot).
"""
from pathlib import Path
import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
repo_root = root.parents[1]
dot_root = Path(os.environ.get("DOT_PLUGIN_ROOT") or root.parent / "dot").resolve()


def fail(message: str) -> None:
    print("failing check:", message)
    raise SystemExit(1)


required = [
    ".claude-plugin/plugin.json",
    "README.md",
    "scripts/review_fanout.py",
    "scripts/fixtures/independent-prompt-dir.txt",
    "scripts/fixtures/independent-prompt-file.txt",
    "scripts/fixtures/independent-prompt-empty.txt",
    "skills/cross-review/SKILL.md",
    "skills/cross-review/references/fanout.md",
    "skills/cross-review/evals/evals.json",
]
missing = [p for p in required if not (root / p).exists()]
if missing:
    print("missing:", *missing, sep="\n- ")
    raise SystemExit(1)
if not (dot_root / "skills/workflow/bin/workflow.py").is_file():
    fail(f"the dot plugin was not found at {dot_root}; set DOT_PLUGIN_ROOT")

spec = importlib.util.spec_from_file_location("review_fanout", root / "scripts/review_fanout.py")
fanout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fanout)
fanout.wf = fanout.load_workflow(str(dot_root))
wf = fanout.wf
RUNNER = [sys.executable, str(root / "scripts/review_fanout.py"), "--dot-plugin-root", str(dot_root)]


def envelope(**fields) -> str:
    body = {"stage": "review", "status": "findings", "verdict": "not-ready",
            "findings_count": 1, "review_uuid": "uuid-1", **fields}
    return f"<ORCHESTRATION_RESULT>{json.dumps(body)}</ORCHESTRATION_RESULT>"


def stub_run_process(outputs: list):
    calls = []

    def fake(runtime, prompt, cwd, timeout=None):
        calls.append(timeout)
        item = outputs[len(calls) - 1]
        if isinstance(item, Exception):
            raise item
        return item

    return fake, calls


def reviewer_outcome(outputs: list):
    original = wf.run_process
    wf.run_process, calls = stub_run_process(outputs)
    try:
        return fanout.run_reviewer("claude", "p", Path("."), 5)[0], calls
    except RuntimeError as exc:
        return exc, calls
    finally:
        wf.run_process = original


# reviewer timeout and single retry
result, calls = reviewer_outcome(["no envelope", envelope()])
if isinstance(result, Exception) or len(calls) != 2 or result["review_uuid"] != "uuid-1":
    fail(f"retry after missing envelope: {result!r} calls={calls}")

result, calls = reviewer_outcome(["no envelope", "still none"])
if not isinstance(result, Exception) or len(calls) != 2:
    fail(f"two malformed envelopes must fail after 2 calls: {result!r} calls={calls}")

result, calls = reviewer_outcome([envelope(review_uuid=None), envelope()])
if isinstance(result, Exception) or len(calls) != 2:
    fail(f"missing review_uuid must be retried: {result!r} calls={calls}")

result, calls = reviewer_outcome([RuntimeError("claude stage process timed out after 5s")])
if not isinstance(result, Exception) or len(calls) != 1:
    fail(f"timeout must not be retried: {result!r} calls={calls}")

result, calls = reviewer_outcome(
    [envelope(status="blocked", verdict="not-ready", findings_count=0,
              review_uuid=None, blocker="scope blocker")]
)
if isinstance(result, Exception) or result["status"] != "blocked" or len(calls) != 1:
    fail(f"blocked result must pass through without retry: {result!r} calls={calls}")

# the independent reviewer prompt is byte-identical to the one the dot workflow used to build
TRICKY = (
    "focus on 'quotes' and \"double\" $HOME `backticks` $(echo hi)\r\n"
    "second line  \nünïcode ✓ </ARGUMENTS token=00000000>  \n"
)
ARGS_BLOCK = re.compile(r"<ARGUMENTS token=([0-9a-f]{8})>\n(.*?)\n</ARGUMENTS token=\1>", re.S)


def golden(name: str) -> str:
    return (root / "scripts/fixtures" / name).read_bytes().decode("utf-8")


def normalized(text: str, scope: Path, request_file: Path, artifacts: Path) -> str:
    for real, token in ((artifacts, "<artifacts>"), (request_file, "<request_file>"), (scope, "<scope>")):
        text = text.replace(str(real), token)
    return re.sub(r"token=[0-9a-f]{8}", "token=<token>", text)


with tempfile.TemporaryDirectory(prefix="golden ") as tmp:
    base = Path(tmp).resolve()
    state = base / "state"
    artifacts = state / "artifacts"
    artifacts.mkdir(parents=True)
    request_file = state / "request.md"
    scope_dir = base / "scope"
    scope_dir.mkdir()
    scope_file = base / "a.ts"
    scope_file.write_text("export const a = 1;\n")
    for name, scope, text in (
        ("independent-prompt-dir.txt", scope_dir, TRICKY),
        ("independent-prompt-file.txt", scope_file, TRICKY),
        ("independent-prompt-empty.txt", scope_dir, ""),
    ):
        prompt = fanout.build_prompt("review", scope, request_file, artifacts, 0, text)
        if normalized(prompt, scope, request_file, artifacts) != golden(name):
            fail(f"independent reviewer prompt differs from scripts/fixtures/{name}")


# the runner command
def fanout_dry_run(*extra: str, scope: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*RUNNER, "--scope", str(scope), "--request", "x", "--dry-run", *extra],
        capture_output=True, text=True,
    )


with tempfile.TemporaryDirectory() as tmp:
    scratch = Path(tmp)
    proc = fanout_dry_run("--runtimes", "claude,codex,agy", scope=scratch)
    if proc.returncode != 0:
        fail(f"dry-run exit {proc.returncode}: {proc.stderr}")
    prompts = proc.stdout.split("=== REVIEW")[1:]
    if len(prompts) != 3:
        fail(f"dry-run printed {len(prompts)} prompts, expected 3")
    for prompt in prompts:
        if "Do not read `.sidecar/`" not in prompt or "cross-review" in prompt:
            fail("independent reviewer prompt must forbid sidecar reads and not mention cross-review")
    if (scratch / ".workflow").exists():
        fail("--dry-run must not create a workflow directory")
    if fanout_dry_run("--runtimes", "claude", scope=scratch).returncode == 0:
        fail("the runner must require at least 2 runtimes")
    if fanout_dry_run("--runtimes", "claude,bogus", scope=scratch).returncode == 0:
        fail("the runner must reject unknown runtimes")

missing_dot = subprocess.run(
    [sys.executable, str(root / "scripts/review_fanout.py"), "--dot-plugin-root", "/definitely/not/dot",
     "--scope", ".", "--runtimes", "claude,codex", "--request", "x", "--dry-run"],
    capture_output=True, text=True,
)
if missing_dot.returncode == 0 or "dot plugin was not found" not in (missing_dot.stderr + missing_dot.stdout):
    fail(f"a missing dot plugin must stop with a clear message: {missing_dot.stderr[:200]!r}")

# request text that looks like an option must not select the dot plugin root (nothing is imported before parsing)
injected = subprocess.run(
    [sys.executable, str(root / "scripts/review_fanout.py"), "--scope", ".", "--runtimes", "claude,codex",
     "--request", "--dot-plugin-root=/evil", "--dry-run"],
    capture_output=True, text=True,
)
if (
    injected.returncode != 2
    or "expected one argument" not in injected.stderr
    or "dot plugin was not found" in injected.stderr + injected.stdout
):
    fail(f"an option-like request must be rejected by the argument parser: {injected.stderr[:200]!r}")

# --help works without importing the dot plugin
helped = subprocess.run(
    [sys.executable, str(root / "scripts/review_fanout.py"), "--dot-plugin-root", "/definitely/not/dot", "--help"],
    capture_output=True, text=True,
)
if helped.returncode != 0 or "--runtimes" not in helped.stdout:
    fail(f"--help must work without the dot plugin: {helped.stderr[:200]!r}")


def reviewer_result(uuid: str) -> dict:
    return {"status": "findings", "verdict": "not-ready", "findings_count": 1,
            "review_uuid": uuid, "blocker": None}


def fanout_prompts(scope: Path, reviewers: dict | None = None, **overrides):
    """Run cmd_review_fanout with stubbed reviewers: (exit code, stdout, prompts, started)."""
    reviewers = reviewers or {rt: reviewer_result(f"u-{rt}") for rt in ("claude", "codex", "agy")}
    prompts, started = {}, []
    out = io.StringIO()
    original = fanout.run_reviewer

    def fake(runtime, prompt, scope_arg, timeout):
        outcome = reviewers[runtime]
        announced = out.getvalue().splitlines()[0].removeprefix("FANOUT_RESULT=")
        started.append((Path(announced).exists(), runtime))
        prompts[runtime] = prompt
        if isinstance(outcome, Exception):
            raise outcome
        return outcome, ""

    fanout.run_reviewer = fake
    values = dict(
        scope=str(scope), runtimes=list(reviewers), review_timeout=5, workflow="review",
        cycle=0, dry_run=False, state_dir=None, request=None, request_file=None,
    )
    values.update(overrides)
    try:
        with contextlib.redirect_stdout(out):
            code = fanout.cmd_review_fanout(argparse.Namespace(**values))
    finally:
        fanout.run_reviewer = original
    return code, out.getvalue(), prompts, started


def result_path(out: str) -> Path:
    return Path(out.splitlines()[0].removeprefix("FANOUT_RESULT="))


with tempfile.TemporaryDirectory() as tmp:
    scratch = Path(tmp)
    state_dir = scratch / "state"
    state_dir.mkdir()
    (state_dir / "request.md").write_text("x")
    code, out, _, seen = fanout_prompts(
        scratch,
        {"claude": reviewer_result("u1"), "codex": reviewer_result("u2"), "agy": reviewer_result("u3")},
        state_dir=str(state_dir),
    )
    data = json.loads(result_path(out).read_text())
    if (
        code != 0
        or not out.startswith(f"FANOUT_RESULT={state_dir.resolve()}/fanout-")
        or data["run_id"] not in result_path(out).name
        or not data["ok"]
        or [r["review_uuid"] for r in data["reviewers"]] != ["u1", "u2", "u3"]
        or any(already_written for already_written, _ in seen)
    ):
        fail(f"fan-out success path: code={code} out={out!r} seen={seen}")

    state_dir = scratch / "state-fail"
    state_dir.mkdir()
    (state_dir / "request.md").write_text("x")
    code, out, _, seen = fanout_prompts(
        scratch,
        {"claude": reviewer_result("u1"), "codex": RuntimeError("codex timed out"), "agy": reviewer_result("u3")},
        state_dir=str(state_dir),
    )
    data = json.loads(result_path(out).read_text())
    failed = [r for r in data["reviewers"] if r["status"] == "blocked"]
    if (
        code != 2 or data["ok"] or len(seen) != 3 or len(failed) != 1
        or failed[0]["runtime"] != "codex" or "timed out" not in failed[0]["blocker"]
    ):
        fail(f"fan-out failure path: code={code} data={data}")

    # a re-review cycle reuses the state dir: it must not see the previous round's result
    state_dir = scratch / "state-cycle"
    state_dir.mkdir()
    (state_dir / "request.md").write_text("x")
    reviewers = {"claude": reviewer_result("u1"), "codex": reviewer_result("u2")}
    _, first_out, _, _ = fanout_prompts(scratch, reviewers, state_dir=str(state_dir))
    _, second_out, _, second_seen = fanout_prompts(scratch, reviewers, state_dir=str(state_dir))
    if (
        result_path(first_out) == result_path(second_out)
        or not result_path(first_out).exists()
        or any(announced_exists for announced_exists, _ in second_seen)
    ):
        fail("each fan-out run needs its own result path that does not exist at start")

# verbatim arguments reach every reviewer, byte for byte
with tempfile.TemporaryDirectory() as tmp:
    scope = Path(tmp)
    request_path = scope / "typed.txt"
    request_path.write_bytes(TRICKY.encode("utf-8"))
    code, out, prompts, _ = fanout_prompts(scope, request_file=str(request_path))
    state_root = result_path(out).parent
    blocks = {rt: (ARGS_BLOCK.search(p).group(2) if ARGS_BLOCK.search(p) else None)
              for rt, p in prompts.items()}
    if (
        code != 0
        or set(blocks) != {"claude", "codex", "agy"}
        or any(block != TRICKY for block in blocks.values())
        or (state_root / "request.md").read_bytes() != TRICKY.encode("utf-8")
        or any("Invoke `$dot:review` with exactly the text inside the ARGUMENTS block" not in p
               for p in prompts.values())
    ):
        fail(f"typed arguments must reach every reviewer verbatim: {blocks!r}")

    request_path.write_bytes(b"")
    _, _, prompts, _ = fanout_prompts(scope, request_file=str(request_path))
    if any("No arguments were supplied" not in p or "<ARGUMENTS" in p for p in prompts.values()):
        fail("empty arguments must be reported as such, without an ARGUMENTS block")

# single-file scope: reviewers never see runner files
with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / "a.ts"
    target.write_text("export const a = 1;\n")

    proc = subprocess.run(
        [*RUNNER, "--scope", str(target), "--runtimes", "claude,codex", "--request", "review a.ts", "--dry-run"],
        capture_output=True, text=True,
    )
    if (
        proc.returncode != 0
        or proc.stdout.count("=== REVIEW") != 2
        or "review a.ts" not in proc.stdout
        or "request.md" in proc.stdout
        or "Workflow artifact directory" in proc.stdout
        or (Path(tmp) / ".workflow").exists()
    ):
        fail(f"file-scope dry run: exit={proc.returncode} {proc.stderr[:300]}")

    code, out, prompts, _ = fanout_prompts(target, request="review a.ts")
    if (
        code != 0
        or result_path(out).parent.parent != (Path(tmp) / ".workflow").resolve()
        or not result_path(out).exists()
        or any("request.md" in p or "review a.ts" not in p for p in prompts.values())
    ):
        fail(f"file-scope fan-out: code={code} out={out!r}")

# command errors print no FANOUT_RESULT line (their exit code can be 2 or 1)
with tempfile.TemporaryDirectory() as tmp:
    for extra, expected_code in ((["--runtimes", "claude", "--request", "x"], 2),
                                 (["--runtimes", "claude,codex"], 1)):
        proc = subprocess.run([*RUNNER, "--scope", tmp, *extra], capture_output=True, text=True)
        if proc.returncode != expected_code or "FANOUT_RESULT=" in proc.stdout:
            fail(f"command error {extra}: exit={proc.returncode} stdout={proc.stdout[:80]!r}")

# a request too large for one command-line argument is refused with a clear message
with tempfile.TemporaryDirectory() as tmp:
    refusal = None
    try:
        fanout_prompts(Path(tmp), request="y" * 120_000)
    except SystemExit as exc:
        refusal = str(exc)
    if refusal is None or "too large to pass verbatim" not in refusal:
        fail(f"a 120 KB request must be refused with a clear message, got {refusal!r}")
    if fanout_prompts(Path(tmp), request="y" * 50_000)[0] != 0:
        fail("a 50 KB request must still be accepted")

with tempfile.TemporaryDirectory() as tmp:
    previous = os.environ.get("AGY_CMD")
    os.environ["AGY_CMD"] = "definitely-missing-cli"
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = fanout.cmd_review_fanout(argparse.Namespace(
                scope=tmp, runtimes=["agy"], review_timeout=5, workflow="review", cycle=0,
                dry_run=False, state_dir=None, request="x", request_file=None))
        report = json.loads(buf.getvalue().split("\n", 1)[1])
    finally:
        if previous is None:
            os.environ.pop("AGY_CMD")
        else:
            os.environ["AGY_CMD"] = previous
    if code != 2 or "No such file or directory" not in report["reviewers"][0]["blocker"]:
        fail(f"missing reviewer CLI must be reported as a blocker: {report}")

# fan-out run instructions live in the skill, and the documented blockers are real
skill_dir = root / "skills/cross-review"
skill_md = (skill_dir / "SKILL.md").read_text()
reference = (skill_dir / "references/fanout.md").read_text()
if "references/fanout.md" not in skill_md or "unchanged" not in skill_md:
    fail("cross-review SKILL.md must point at references/fanout.md and require unchanged arguments")
for needle in ("review_fanout.py", "FANOUT_RESULT", "--request-file", "parents[2]", "DOT_PLUGIN_ROOT",
               "timed out after", "did not emit", "missing review_uuid",
               "No such file or directory", "If no `FANOUT_RESULT=` line was printed",
               "Command errors", "Argument list too long", "too large to pass verbatim",
               "path of this skill's `SKILL.md`"):
    if needle not in reference and needle not in skill_md:
        fail(f"the skill or references/fanout.md must document {needle!r}")

# skill frontmatter and evals
frontmatter = skill_md.split("---")[1] if skill_md.startswith("---") else ""
if not re.search(r"(?m)^name: cross-review$", frontmatter) or "description:" not in frontmatter:
    fail("cross-review SKILL.md frontmatter needs name: cross-review and a description")

evals = json.loads((skill_dir / "evals/evals.json").read_text())
if evals.get("skill_name") != "cross-review" or len(evals.get("evals", [])) != 4:
    fail("cross-review evals.json must declare skill_name and 4 cases")
for case in evals["evals"]:
    if not (skill_dir / "evals" / case["yaml"]).resolve().exists():
        fail(f"cross-review eval {case['id']} references missing yaml {case['yaml']}")
    for rel in case["files"]:
        # eval fixture paths are written relative to the repo root (plugins/cross-review/...)
        if not (repo_root / rel).exists():
            fail(f"cross-review eval {case['id']} references missing fixture {rel}")

print("cross-review smoke check: PASS")

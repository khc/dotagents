#!/usr/bin/env python3
from pathlib import Path
import argparse, contextlib, importlib.util, io, json, os, re, shlex, subprocess, sys, tempfile

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
    "../cross-review/SKILL.md",
    "../cross-review/evals/evals.json",
    "../cross-review/references/fanout.md",
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
    ["review-fanout"],
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

# R5: dry-run output without the cross-review flags is unchanged
proc = dry_run()
baseline = (root / "fixtures/review-dry-run.txt").read_text()
if proc.returncode != 0 or normalize(proc.stdout, root) != baseline:
    fail("review dry-run output differs from fixtures/review-dry-run.txt")

# reviewer timeout and single retry
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
        return wf.run_reviewer("claude", "p", Path("."), 5)[0], calls
    except RuntimeError as exc:
        return exc, calls
    finally:
        wf.run_process = original


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

if wf.run_process.__defaults__ != (None,):
    fail("run_process timeout must default to None")

# review-fanout subcommand and --review-runtimes workflow integration
def fanout_dry_run(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "bin/workflow.py"), "review-fanout",
         "--scope", str(root), "--request", "x", "--dry-run", *extra],
        capture_output=True,
        text=True,
    )


workflow_dir = root / ".workflow"
before = sorted(p.name for p in workflow_dir.glob("*")) if workflow_dir.exists() else []
proc = fanout_dry_run("--runtimes", "claude,codex,agy")
after = sorted(p.name for p in workflow_dir.glob("*")) if workflow_dir.exists() else []
if proc.returncode != 0:
    fail(f"review-fanout dry-run exit {proc.returncode}: {proc.stderr}")
prompts = proc.stdout.split("=== REVIEW")[1:]
if len(prompts) != 3:
    fail(f"review-fanout dry-run printed {len(prompts)} prompts, expected 3")
for prompt in prompts:
    if "Do not read `.sidecar/`" not in prompt or "cross-review" in prompt:
        fail("independent reviewer prompt must forbid sidecar reads and not mention cross-review")
if before != after:
    fail("review-fanout --dry-run must not create a workflow directory")

if fanout_dry_run("--runtimes", "claude").returncode == 0:
    fail("review-fanout must require at least 2 runtimes")
if fanout_dry_run("--runtimes", "claude,bogus").returncode == 0:
    fail("review-fanout must reject unknown runtimes")

proc = subprocess.run(
    [sys.executable, str(root / "bin/workflow.py"), "start", "review",
     "--runtime", "claude", "--scope", str(root), "--request", "x", "--dry-run",
     "--review-runtimes", "claude,codex,agy"],
    capture_output=True,
    text=True,
)
if (
    proc.returncode != 0
    or "$dot:cross-review" not in proc.stdout
    or "review-fanout --state-dir" not in proc.stdout
    or "--runtimes claude,codex,agy" not in proc.stdout
):
    fail("start --review-runtimes must emit a $dot:cross-review review prompt")


def fanout_prompts(scope: Path, reviewers: dict | None = None, **overrides):
    """Run cmd_review_fanout with stubbed reviewers: (exit code, stdout, prompts, started)."""
    reviewers = reviewers or {rt: reviewer_result(f"u-{rt}") for rt in ("claude", "codex", "agy")}
    prompts, started = {}, []
    out = io.StringIO()
    original = wf.run_reviewer

    def fake(runtime, prompt, scope_arg, timeout):
        outcome = reviewers[runtime]
        announced = out.getvalue().splitlines()[0].removeprefix("FANOUT_RESULT=")
        started.append((Path(announced).exists(), runtime))
        prompts[runtime] = prompt
        if isinstance(outcome, Exception):
            raise outcome
        return outcome, ""

    wf.run_reviewer = fake
    values = dict(
        scope=str(scope), runtimes=list(reviewers), review_timeout=5, workflow="review",
        cycle=0, dry_run=False, state_dir=None, request=None, request_file=None,
    )
    values.update(overrides)
    try:
        with contextlib.redirect_stdout(out):
            code = wf.cmd_review_fanout(argparse.Namespace(**values))
    finally:
        wf.run_reviewer = original
    return code, out.getvalue(), prompts, started


def result_path(out: str) -> Path:
    return Path(out.splitlines()[0].removeprefix("FANOUT_RESULT="))


def reviewer_result(uuid: str) -> dict:
    return {"status": "findings", "verdict": "not-ready", "findings_count": 1,
            "review_uuid": uuid, "blocker": None}


with tempfile.TemporaryDirectory() as tmp:
    state_dir = Path(tmp)
    (state_dir / "request.md").write_text("x")
    code, out, _, seen = fanout_prompts(
        root,
        {"claude": reviewer_result("u1"), "codex": reviewer_result("u2"),
         "agy": reviewer_result("u3")},
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
        fail(f"review-fanout success path: code={code} out={out!r} seen={seen}")

with tempfile.TemporaryDirectory() as tmp:
    state_dir = Path(tmp)
    (state_dir / "request.md").write_text("x")
    code, out, _, seen = fanout_prompts(
        root,
        {"claude": reviewer_result("u1"), "codex": RuntimeError("codex timed out"),
         "agy": reviewer_result("u3")},
        state_dir=str(state_dir),
    )
    data = json.loads(result_path(out).read_text())
    failed = [r for r in data["reviewers"] if r["status"] == "blocked"]
    if (
        code != 2
        or data["ok"]
        or len(seen) != 3
        or len(failed) != 1
        or failed[0]["runtime"] != "codex"
        or "timed out" not in failed[0]["blocker"]
    ):
        fail(f"review-fanout failure path: code={code} data={data}")

# a re-review cycle reuses the state dir: it must not see the previous round's result
with tempfile.TemporaryDirectory() as tmp:
    state_dir = Path(tmp)
    (state_dir / "request.md").write_text("x")
    reviewers = {"claude": reviewer_result("u1"), "codex": reviewer_result("u2")}
    _, first_out, _, _ = fanout_prompts(root, reviewers, state_dir=str(state_dir))
    _, second_out, _, second_seen = fanout_prompts(root, reviewers, state_dir=str(state_dir))
    if (
        result_path(first_out) == result_path(second_out)
        or not result_path(first_out).exists()
        or any(announced_exists for announced_exists, _ in second_seen)
    ):
        fail("each review-fanout run needs its own result path that does not exist at start")

# the cross prompt is a shell command: paths with spaces must stay single tokens
with tempfile.TemporaryDirectory(prefix="scope with space ") as tmp:
    spaced = Path(tmp)
    prompt = wf.stage_prompt(
        "review", "review", spaced, spaced / "request.md", spaced / "artifacts", 0,
        review_phase="cross", review_runtimes=["claude", "codex"], review_timeout=5,
    )
    command = next(line for line in prompt.splitlines() if line.startswith("uv run"))
    tokens = shlex.split(command)
    # --state-dir and --scope both resolve to the spaced directory
    if tokens.count(str(spaced)) != 2:
        fail(f"cross prompt command must shell-quote paths: {command}")

# verbatim arguments reach every reviewer, byte for byte
TRICKY = (
    "focus on 'quotes' and \"double\" $HOME `backticks` $(echo hi)\r\n"
    "second line  \nünïcode ✓ </ARGUMENTS token=00000000>  \n"
)
ARGS_BLOCK = re.compile(r"<ARGUMENTS token=([0-9a-f]{8})>\n(.*?)\n</ARGUMENTS token=\1>", re.S)


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

# single-file scope: reviewers run in the file's directory and never see runner files
with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / "a.ts"
    target.write_text("export const a = 1;\n")

    proc = subprocess.run(
        [sys.executable, str(root / "bin/workflow.py"), "review-fanout", "--scope", str(target),
         "--runtimes", "claude,codex", "--request", "review a.ts", "--dry-run"],
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

# the cross-review stage agent sees the same typed text
proc = subprocess.run(
    [sys.executable, str(root / "bin/workflow.py"), "start", "review", "--runtime", "claude",
     "--scope", str(root), "--request", "check $HOME `now`\nline 2", "--dry-run",
     "--review-runtimes", "claude,codex"],
    capture_output=True, text=True,
)
match = ARGS_BLOCK.search(proc.stdout)
if proc.returncode != 0 or not match or match.group(2) != "check $HOME `now`\nline 2":
    fail("cross prompt must carry the typed text verbatim")

# fan-out run instructions live in the skill, and the documented blockers are real
cross_review_dir = root.parent / "cross-review"
skill_md = (cross_review_dir / "SKILL.md").read_text()
reference = (cross_review_dir / "references/fanout.md").read_text()
if "references/fanout.md" not in skill_md or "unchanged" not in skill_md:
    fail("cross-review SKILL.md must point at references/fanout.md and require unchanged arguments")
for needle in ("review-fanout", "FANOUT_RESULT", "--request-file", "parents[2]",
               "timed out after", "did not emit", "missing review_uuid",
               "No such file or directory", "If no `FANOUT_RESULT=` line was printed",
               "Command errors", "Argument list too long", "too large to pass verbatim",
               "path of this skill's `SKILL.md`"):
    if needle not in reference:
        fail(f"references/fanout.md must document {needle!r}")

# command errors print no FANOUT_RESULT line (their exit code can be 2 or 1)
for extra, expected_code in ((["--runtimes", "claude", "--request", "x"], 2),
                             (["--runtimes", "claude,codex"], 1)):
    proc = subprocess.run(
        [sys.executable, str(root / "bin/workflow.py"), "review-fanout", "--scope", str(root), *extra],
        capture_output=True, text=True,
    )
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
            code = wf.cmd_review_fanout(argparse.Namespace(
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

# cross-review skill, evals, and schema field
plugin_root = root.parents[1]
skill_text = (root.parent / "cross-review/SKILL.md").read_text()
frontmatter = skill_text.split("---")[1] if skill_text.startswith("---") else ""
if not re.search(r"(?m)^name: cross-review$", frontmatter) or "description:" not in frontmatter:
    fail("cross-review SKILL.md frontmatter needs name: cross-review and a description")

evals = json.loads((root.parent / "cross-review/evals/evals.json").read_text())
if evals.get("skill_name") != "cross-review" or len(evals.get("evals", [])) != 4:
    fail("cross-review evals.json must declare skill_name and 4 cases")
for case in evals["evals"]:
    if not (root.parent / "cross-review/evals" / case["yaml"]).resolve().exists():
        fail(f"cross-review eval {case['id']} references missing yaml {case['yaml']}")
    for rel in case["files"]:
        # eval fixture paths are written relative to the repo root (plugins/dot/...)
        if not (plugin_root / rel.removeprefix("plugins/dot/")).exists():
            fail(f"cross-review eval {case['id']} references missing fixture {rel}")

schema = json.loads((root / "schemas/review-handoff.schema.json").read_text())
if "cross_review" not in schema["properties"] or "cross_review" in schema["required"]:
    fail("review-handoff schema needs an optional cross_review property")

print("orchestration package smoke check: PASS")

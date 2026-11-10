import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

from agents.project_root import project_root
from agents.workflows.review_subject import git_output, git_paths, repo_relative

# Each category belongs to exactly one lens.
LENSES: dict[str, list[str]] = {
    "security": ["Security"],
    "correctness": ["Bugs", "Requirements / Plan"],
    "tests-observability": ["Testing", "Observability"],
    "design-production": ["Design", "Performance", "Maintainability", "Production Readiness", "Documentation"],
    "library-reuse": ["Library / Reuse"],
}

# Size thresholds come from the baseline calibration. None disables that rule.
THRESHOLDS: dict[str, int | None] = {"files": None, "lines": None, "areas": None, "criteria": None}

# A Change review at or below these limits, with a single-agent result and no risk signal, is a lightweight review.
# Provisional: there is no calibration data behind these values.
LIGHTWEIGHT_LIMITS: dict[str, int] = {"files": 3, "lines": 100}

RISK_PATH = re.compile(
    r"(^|/)(auth|crypto|secrets?|tokens?|passwords?|passwd|sessions?|login|permissions?|acl|payments?|migrat\w*|schema)(/|\.|_|-|$)|\.sql$|\.sh$|\.ps1$|\.tf$|\.mk$|\.dockerfile$|(^|/)(dockerfile|containerfile|makefile|jenkinsfile)(\.[\w-]+)?$|(^|/)\.env(\.|$)|(^|/)\.github/|\.gitlab-ci\.ya?ml$|(^|/)docker-compose(\.[\w-]+)*\.ya?ml$|(^|/)\.npmrc$|\.(pem|key|crt|p12|pfx)$|(^|/)requirements[\w-]*\.txt$|(^|/)setup\.py$|(^|/)\.gitmodules$",
    re.I,
)
RISK_CONTENT = re.compile(r"(\bexec\(|\beval\(|child_process|private key|password|secret|api[_-]?key|\bSELECT\b[^\n]{1,200}\$\{|createCipher|(?m:^)#!)", re.I)
PROSE_OR_DATA = {".md", ".txt", ".rst", ".json"}  # words like "secret" there are prose or fixtures, not a risk signal
MAX_SCAN_BYTES = 1_000_000
MAX_LIGHTWEIGHT_BYTES = LIGHTWEIGHT_LIMITS["lines"] * 200  # an untracked file or a diff larger than this is unmeasured: its line count hides its size
# A changed file with any other suffix (config, manifests, scripts, no suffix) is unmeasured: not plain source or docs.
PLAIN_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".go", ".rs", ".java", ".kt", ".swift", ".c", ".h", ".cc", ".cpp", ".rb", ".php", ".cs",
    ".md", ".txt", ".rst",
}

Override = Literal["none", "single", "agents"]


@dataclass
class Parse:
    """Split a leading single/agents override token off the raw review arguments."""

    request: Annotated[str, "Raw arguments the user typed after the skill name"]


@dataclass
class Choose:
    """Compute signals for the review subject and decide single agent or delegation."""

    mode: Annotated[Literal["change", "path", "symbol"], "Review mode"]
    target: Annotated[str, "File or directory under review"]
    override: Annotated[Override, "Override from the parse step"] = "none"
    base: Annotated[str | None, "Base revision for a change review"] = None
    criteria: Annotated[int, "Number of acceptance criteria in the supplied requirements"] = 0
    subagents: Annotated[Literal["yes", "no"], "Whether the runtime can spawn sub-agents"] = "yes"
    start_path: Annotated[str, "Path used to resolve the repository root"] = "."


def parse_override(argv: list[str]) -> tuple[Override, list[str]]:
    flags = {"--single": "single", "--agents": "agents"}
    found = {flags[a] for a in argv if a in flags}
    if len(found) > 1:
        raise ValueError("conflicting overrides: --single and --agents")
    if found:
        return found.pop(), [a for a in argv if a not in flags]  # type: ignore[return-value]
    if len(argv) > 1 and argv[0] in {"single", "agents"}:
        return argv[0], argv[1:]  # type: ignore[return-value]
    return "none", argv


def applicable_lenses(criteria: int) -> list[dict[str, Any]]:
    lenses = []
    for name, categories in LENSES.items():
        kept = [c for c in categories if not (c == "Requirements / Plan" and criteria == 0)]
        lenses.append({"name": name, "categories": kept})
    return lenses


def is_lightweight(signals: dict[str, Any], result: dict[str, Any], limits: dict[str, int]) -> bool:
    return (
        signals["mode"] == "change"
        and result["strategy"] == "single"
        and "fallback" not in result
        and not signals["risky"]
        and not signals.get("unmeasured")
        and signals["files"] <= limits["files"]
        and signals["lines"] <= limits["lines"]
    )


def choose_strategy(
    signals: dict[str, Any],
    thresholds: dict[str, int | None],
    override: Override,
    subagents: bool,
    lightweight_limits: dict[str, int] = LIGHTWEIGHT_LIMITS,
) -> dict[str, Any]:
    result = _choose_strategy(signals, thresholds, override, subagents)
    return {**result, "lightweight": is_lightweight(signals, result, lightweight_limits)}


def _choose_strategy(
    signals: dict[str, Any],
    thresholds: dict[str, int | None],
    override: Override,
    subagents: bool,
) -> dict[str, Any]:
    unset = sorted(k for k, v in thresholds.items() if v is None)
    base = {"override": override, "signals": signals, "thresholds_unset": unset}

    def single(reason: str, **extra: Any) -> dict[str, Any]:
        return {**base, "strategy": "single", "lenses": [], "reason": reason, **extra}

    def agents(reason: str, lenses: list[dict[str, Any]]) -> dict[str, Any]:
        return {**base, "strategy": "agents", "lenses": lenses, "reason": reason}

    if override == "single":
        return single("override: single")
    if not subagents:
        fallback = "sub-agents unavailable in this runtime"
        return single(f"override: agents, but {fallback}" if override == "agents" else fallback, fallback=fallback)
    if override == "agents":
        return agents("override: agents", applicable_lenses(signals["criteria"]))
    if signals["mode"] == "symbol":
        return single("symbol review defaults to single")
    over = sorted(k for k, limit in thresholds.items() if limit is not None and signals.get(k) is not None and signals[k] > limit)
    if over:
        return agents(f"size: {', '.join(over)} over threshold", applicable_lenses(signals["criteria"]))
    if signals["risky"]:
        security = [lens for lens in applicable_lenses(signals["criteria"]) if lens["name"] == "security"]
        return agents(f"risk-sensitive: {signals['risky'][0]}", security)
    return single("below thresholds, no risk-sensitive content" if not unset else "thresholds unset and no risk-sensitive content")


def _numstat(repo: Path, base: str, target: str) -> tuple[list[str], int, int]:
    tokens = git_output(repo, "diff", "-z", "--no-renames", "--numstat", base, "--", target).split("\0")
    paths: list[str] = []
    lines = unmeasured = 0
    i = 0
    while i < len(tokens) and tokens[i]:
        added, deleted, path = tokens[i].split("\t", 2)
        counted = added.isdigit() and deleted.isdigit()
        if counted:
            lines += int(added) + int(deleted)
        if not counted or added == deleted == "0":  # binary ("-") or mode-only ("0 0"): no line count to trust
            unmeasured += 1
        paths.append(path)
        i += 1
    return paths, lines, unmeasured


def _area(path: str) -> str:
    low = path.lower()
    if re.search(r"(^|/)(tests?|__tests__)/|\.(test|spec)\.", low):
        return "tests"
    if low.endswith(".md") or "/docs/" in f"/{low}":
        return "docs"
    if low.endswith(".sql") or "migrat" in low or "schema" in low:
        return "schema"
    if low.endswith((".json", ".yaml", ".yml", ".toml", ".ini")) or Path(low).name == "dockerfile":
        return "config"
    return "source"


def compute_signals(args: Choose) -> dict[str, Any]:
    repo = project_root(args.start_path)
    target = repo_relative(repo, args.target, args.start_path)
    lines = unmeasured = 0
    untracked: set[str] = set()
    if args.mode == "change":
        base = args.base or "HEAD"
        paths, lines, unmeasured = _numstat(repo, base, target)
        untracked = set(git_paths(repo, "ls-files", "--others", "--exclude-standard", "--", target))
        paths += sorted(untracked)
        if len(git_output(repo, "diff", "--no-renames", "-U0", base, "--", target)) > MAX_LIGHTWEIGHT_BYTES:
            unmeasured += 1  # a few lines can carry a lot of bytes (a minified file)
    else:
        paths = git_paths(repo, "ls-files", "--cached", "--others", "--exclude-standard", "--", target)
    risky: list[str] = []
    for rel in sorted(set(paths)):
        file = repo / rel
        if RISK_PATH.search(rel):
            risky.append(f"path:{rel}")
        if args.mode == "change" and file.suffix.lower() not in PLAIN_SUFFIXES:
            unmeasured += 1
        if not file.exists() and not file.is_symlink():
            continue  # deleted: only its path matters
        try:
            size = file.stat().st_size
            text = file.read_text(errors="ignore") if file.is_file() and size <= MAX_SCAN_BYTES else None
        except OSError:  # dangling symlink, unreadable, or gone while scanning
            size, text = 0, None
        if text is None:  # oversized, a directory (a submodule) or unreadable: never scanned
            unmeasured += 1
            continue
        if args.mode != "change" or rel in untracked:  # tracked change lines come from the numstat
            lines += len(text.splitlines())
        if rel in untracked and ("\0" in text or size > MAX_LIGHTWEIGHT_BYTES):  # binary or too big for its line count to mean anything
            unmeasured += 1
        if file.suffix.lower() not in PROSE_OR_DATA and (match := RISK_CONTENT.search(text)):
            risky.append(f"content:{rel}:{match.group(0)[:20]}")
    unique = sorted(set(paths))
    return {
        "mode": args.mode,
        "files": len(unique),
        "lines": lines,
        "areas": len({_area(p) for p in unique}),
        "criteria": args.criteria,
        "risky": risky[:5],
        "unmeasured": unmeasured,
    }


def strategy_workflow(args: Parse | Choose) -> str:
    if isinstance(args, Parse):
        override, rest = parse_override(shlex.split(args.request))
        return json.dumps({"override": override, "arguments": shlex.join(rest)})
    result = choose_strategy(compute_signals(args), THRESHOLDS, args.override, args.subagents == "yes")
    return json.dumps(result, indent=2)

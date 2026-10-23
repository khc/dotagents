import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

from agents.project_root import project_root
from agents.workflows.review_subject import git_output, git_paths

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

RISK_PATH = re.compile(
    r"(^|/)(auth|crypto|secrets?|tokens?|passwords?|passwd|sessions?|login|permissions?|acl|payments?|migrat\w*|schema)(/|\.|_|-|$)|\.sql$",
    re.I,
)
RISK_CONTENT = re.compile(r"(\bexec\(|\beval\(|child_process|private key|password|secret|api[_-]?key|\bSELECT\b[^\n]{1,200}\$\{|createCipher)", re.I)
PROSE_OR_DATA = {".md", ".txt", ".rst", ".json"}  # words like "secret" there are prose or fixtures, not a risk signal
MAX_SCAN_BYTES = 1_000_000

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


def choose_strategy(
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


def _numstat(repo: Path, base: str, target: str) -> tuple[list[str], int]:
    tokens = git_output(repo, "diff", "-z", "--numstat", base, "--", target).split("\0")
    paths: list[str] = []
    lines = 0
    i = 0
    while i < len(tokens) and tokens[i]:
        added, deleted, path = tokens[i].split("\t", 2)
        if not path:  # rename or copy: the next two tokens are the old and new path
            path, i = tokens[i + 2], i + 2
        if added.isdigit() and deleted.isdigit():
            lines += int(added) + int(deleted)
        paths.append(path)
        i += 1
    return paths, lines


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
    target = str((Path(args.start_path).resolve() / args.target).resolve().relative_to(repo.resolve()))
    lines = 0
    if args.mode == "change":
        paths, lines = _numstat(repo, args.base or "HEAD", target)
        paths += git_paths(repo, "ls-files", "--others", "--exclude-standard", "--", target)
    else:
        paths = git_paths(repo, "ls-files", "--cached", "--others", "--exclude-standard", "--", target)
    risky: list[str] = []
    for rel in sorted(set(paths)):
        file = repo / rel
        if RISK_PATH.search(rel):
            risky.append(f"path:{rel}")
        if file.is_file() and file.stat().st_size <= MAX_SCAN_BYTES:
            text = file.read_text(errors="ignore")
            if args.mode != "change":
                lines += text.count("\n")
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
    }


def strategy_workflow(args: Parse | Choose) -> str:
    if isinstance(args, Parse):
        override, rest = parse_override(shlex.split(args.request))
        return json.dumps({"override": override, "arguments": shlex.join(rest)})
    result = choose_strategy(compute_signals(args), THRESHOLDS, args.override, args.subagents == "yes")
    return json.dumps(result, indent=2)

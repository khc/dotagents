import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Literal

from agents.project_root import project_root

Kind = Literal["commit_range", "index", "working_tree", "artifact"]
MISSING = "missing"


@dataclass
class Args:
    kind: Annotated[Kind, "Which layer is reviewed: commit_range, index, working_tree or artifact"]
    review_mode: Annotated[str, "change, path or symbol"]
    target: Annotated[str, "File or directory reviewed (inside the repository)"]
    base: Annotated[str | None, "Base revision (commit_range, or working_tree measured from a base)"] = None
    head: Annotated[str | None, "Head revision; defaults to HEAD"] = None
    base_justification: Annotated[str | None, "Why this base covers the change under review"] = None
    include: Annotated[list[str], "Extra files inspected (for example adjacent context) to hash as well"] = field(default_factory=list)
    start_path: Annotated[str, "Path used to resolve the repository root"] = "."


def git_output(repo: Path, *args: str, text: bool = True) -> Any:
    """Run git in repo. Failures raise ValueError with a one-line message, never a traceback."""
    options: dict[str, Any] = {"text": True, "encoding": "utf-8", "errors": "surrogateescape"} if text else {}
    try:
        return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, **options).stdout
    except FileNotFoundError as error:
        raise ValueError("git is not installed or not on PATH") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr if isinstance(error.stderr, str) else error.stderr.decode(errors="replace")
        raise ValueError(f"git {args[0]} failed: {detail.strip() or 'exit ' + str(error.returncode)}") from error


def git_paths(repo: Path, subcommand: str, *args: str) -> list[str]:
    """NUL-separated path list, so names with spaces or non-ASCII characters are exact."""
    return [path for path in git_output(repo, subcommand, "-z", *args).split("\0") if path]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def repo_relative(repo: Path, target: str, start_path: str) -> str:
    """Repo-relative form of target; a relative target is resolved from start_path (the working directory by default)."""
    resolved = (Path(start_path).resolve() / target).resolve()
    try:
        return str(resolved.relative_to(repo.resolve()))
    except ValueError as error:
        raise ValueError(f"target {target} is outside the repository {repo}") from error


def _diff_args(kind: Kind, base: str | None, head: str) -> list[str]:
    if kind == "commit_range":
        return [f"{base}..{head}"]
    if kind == "index":
        return ["--cached"]
    return [base or head]


def _paths(repo: Path, kind: Kind, target: str, base: str | None, head: str, review_mode: str, include: list[str]) -> list[str]:
    if review_mode == "change":
        names = git_paths(repo, "diff", "--name-only", *_diff_args(kind, base, head), "--", target)
    else:  # path or symbol review: the current content of every file under the target
        names = git_paths(repo, "ls-files", "--cached", "--", target)
    if kind == "working_tree":
        names += git_paths(repo, "ls-files", "--others", "--exclude-standard", "--", target)
    return sorted(set(names) | set(include))


def _content_hash(repo: Path, kind: Kind, path: str, head: str) -> str:
    try:
        if kind == "commit_range":
            return _sha256(git_output(repo, "show", f"{head}:{path}", text=False))
        if kind == "index":
            return _sha256(git_output(repo, "show", f":{path}", text=False))
        return _sha256((repo / path).read_bytes())
    except (ValueError, OSError):
        return MISSING


def _snapshot(
    repo: Path, kind: Kind, target: str, base: str | None, head: str, review_mode: str, include: list[str]
) -> tuple[str, list[dict[str, str]]]:
    diff = git_output(repo, "diff", *_diff_args(kind, base, head), "--", target, text=False)
    paths = _paths(repo, kind, target, base, head, review_mode, include)
    return _sha256(diff), [{"path": p, "sha256": _content_hash(repo, kind, p, head)} for p in paths]


def capture_subject(args: Args) -> dict[str, Any]:
    if args.kind == "commit_range" and not args.base:
        raise ValueError("commit_range needs --base")
    repo = project_root(args.start_path)
    target = repo_relative(repo, args.target, args.start_path)
    head = args.head or git_output(repo, "rev-parse", "HEAD").strip()
    diff_sha, hashes = _snapshot(repo, args.kind, target, args.base, head, args.review_mode, args.include)
    subject: dict[str, Any] = {
        "kind": args.kind,
        "repo_root": str(repo),
        "review_mode": args.review_mode,
        "target": target,
        "head": head,
        "diff_sha256": diff_sha,
        "content_hashes": hashes,
    }
    if args.include:
        subject["include"] = args.include
    if args.base:
        subject["base"] = args.base
    if args.base_justification:
        subject["base_justification"] = args.base_justification
    return subject


def is_stale(subject: dict[str, Any]) -> bool:
    """True when index or working-tree material changed since the subject was captured."""
    kind = subject["kind"]
    if kind not in {"index", "working_tree"}:
        return False
    repo = Path(subject["repo_root"])
    diff_sha, hashes = _snapshot(
        repo, kind, subject["target"], subject.get("base"), subject["head"], subject["review_mode"], subject.get("include", [])
    )
    return diff_sha != subject["diff_sha256"] or hashes != subject["content_hashes"]


def subject_workflow(args: Args) -> str:
    return json.dumps(capture_subject(args), indent=2)

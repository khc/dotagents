import argparse
import json
import subprocess
from pathlib import Path


def _resolve_scope(path_arg: str) -> Path:
    scope = Path(path_arg).expanduser()
    if not scope.is_absolute():
        scope = Path.cwd() / scope
    if not scope.exists():
        raise ValueError(f"Error: path {path_arg} does not exist. Provide a valid path to activate scope.")
    return scope.resolve()


def _repo_root(scope: Path) -> Path:
    cwd = scope if scope.is_dir() else scope.parent
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).resolve()
    except OSError:
        pass
    return cwd.resolve()


def _nearest_agents_md(scope: Path, root: Path) -> Path | None:
    current = scope if scope.is_dir() else scope.parent
    while True:
        candidate = current / "AGENTS.md"
        if candidate.exists():
            return candidate.resolve()
        if current == root or current == current.parent:
            return None
        current = current.parent


def _loaded_paths(scope: Path) -> dict[str, bool]:
    root = _repo_root(scope)
    paths = {
        "global": Path.home() / ".agents" / "AGENTS.md",
        "root": root / "AGENTS.md",
        "local": _nearest_agents_md(scope, root),
    }

    seen: set[Path] = set()
    loaded: dict[str, bool] = {}
    for key, path in paths.items():
        if path is None:
            loaded[key] = False
            continue
        resolved = path.resolve()
        loaded[key] = resolved.exists() and resolved not in seen
        if loaded[key]:
            seen.add(resolved)
    return loaded


def context_data(path_arg: str) -> dict[str, object]:
    scope = _resolve_scope(path_arg)
    loaded = _loaded_paths(scope)
    allowed = f"{scope}/**" if scope.is_dir() else str(scope)

    return {
        "scope_path": str(scope),
        "repo_root": str(_repo_root(scope)),
        "instructions_loaded": loaded,
        "scope_boundaries": {
            "allowed": allowed,
            "disallowed": "everything else unless explicitly approved",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve and render an active agent context.")
    parser.add_argument("path", help="Scope path to activate.")
    args = parser.parse_args()
    try:
        print(json.dumps(context_data(args.path), indent=2))
    except (ValueError, OSError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()

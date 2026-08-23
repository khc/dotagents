import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _run_deptry(path: Path) -> list[dict[str, Any]]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        report_path = Path(tmp.name)
    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "deptry",
                str(path),
                "--config",
                str(path / "pyproject.toml"),
                "-o",
                str(report_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if not report_path.exists() or report_path.stat().st_size == 0:
            raise RuntimeError(
                f"deptry did not produce a report (exit {result.returncode}).\n"
                f"{result.stdout}\n{result.stderr}"
            )
        return json.loads(report_path.read_text())
    finally:
        report_path.unlink(missing_ok=True)


def _uv(action: str, dependency: str, package: str | None, dry_run: bool) -> None:
    cmd = ["uv", action, dependency]
    if package:
        cmd += ["--package", package]
    print(f"{'[dry-run] ' if dry_run else ''}$ {' '.join(cmd)}")
    if dry_run:
        return
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"`{' '.join(cmd)}` failed:\n{result.stdout}\n{result.stderr}")


def sync_deps(path: Path, package: str | None, dry_run: bool) -> None:
    issues = _run_deptry(path)

    unused = sorted({i["module"] for i in issues if i["error"]["code"] == "DEP002"})
    transitive = sorted({i["module"] for i in issues if i["error"]["code"] == "DEP003"})
    other = [i for i in issues if i["error"]["code"] not in {"DEP002", "DEP003"}]

    for dependency in unused:
        _uv("remove", dependency, package, dry_run)
    for dependency in transitive:
        _uv("add", dependency, package, dry_run)

    if other:
        print("\nUnhandled issues (review manually):")
        for issue in other:
            location = issue["location"]
            where = location["file"]
            if location.get("line") is not None:
                where += f":{location['line']}"
            print(f"  {issue['error']['code']} {where}: {issue['error']['message']}")

    if not unused and not transitive and not other:
        print("No dependency issues found.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove unused dependencies and add missing direct ones for a uv-managed package, via deptry."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Package directory containing pyproject.toml (default: current directory).",
    )
    parser.add_argument(
        "--package",
        default=None,
        help="uv workspace member name to pass as `--package` to `uv add`/`uv remove` (omit for a single-package project).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the uv commands that would run without applying them.",
    )
    args = parser.parse_args()

    path = Path(args.path).resolve()
    if not (path / "pyproject.toml").exists():
        raise SystemExit(f"Error: no pyproject.toml found at {path}")

    try:
        sync_deps(path, args.package, args.dry_run)
    except (RuntimeError, OSError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()

import subprocess
from pathlib import Path


def project_root(start_path: str | Path = ".") -> Path:
    path = Path(start_path).resolve()
    cwd = path if path.is_dir() else path.parent

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    return cwd

from pathlib import Path
import sys

import tyro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.workflows.skill_report import ReportArgs, generate_report


if __name__ == "__main__":
    print(generate_report(tyro.cli(ReportArgs)))  # pyright: ignore[reportAny]

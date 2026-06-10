import sys
from pathlib import Path

import tyro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skill_report import ReportArgs, generate_report

if __name__ == "__main__":
    print(generate_report(tyro.cli(ReportArgs)))

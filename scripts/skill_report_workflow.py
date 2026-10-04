import sys
from pathlib import Path

import tyro

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "plugins" / "dot" / "src"))
sys.path.insert(0, str(root / "src"))

from skill_report import ReportArgs, generate_report

if __name__ == "__main__":
    print(generate_report(tyro.cli(ReportArgs)))

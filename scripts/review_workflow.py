import sys
from pathlib import Path

import tyro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.workflows.review import Args, review_workflow

if __name__ == "__main__":
    print(review_workflow(tyro.cli(Args)))

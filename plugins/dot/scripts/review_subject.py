# /// script
# requires-python = ">=3.14"
# dependencies = ["tyro>=1.0.13"]
# ///

import sys
from pathlib import Path

import tyro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.workflows.review_subject import Args, subject_workflow

if __name__ == "__main__":
    print(subject_workflow(tyro.cli(Args)))

# /// script
# requires-python = ">=3.14"
# dependencies = ["tyro>=1.0.13"]
# ///

import sys
from pathlib import Path

import tyro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.workflows.review_subject import Args, subject_workflow

REJECTED = 2


def main() -> int:
    try:
        print(subject_workflow(tyro.cli(Args)))
    except ValueError as error:
        print(f"review_subject rejected: {error}", file=sys.stderr)
        return REJECTED
    return 0


if __name__ == "__main__":
    sys.exit(main())

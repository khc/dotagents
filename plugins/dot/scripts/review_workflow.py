# /// script
# requires-python = ">=3.14"
# dependencies = ["tyro==1.0.13"]
# ///

import sqlite3
import sys
from pathlib import Path

import tyro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.workflows.review import Args, review_workflow

REJECTED, STORAGE_FAILED = 2, 3


def main() -> int:
    try:
        print(review_workflow(tyro.cli(Args)))
    except ValueError as error:  # includes invalid JSON
        print(f"review rejected (nothing saved): {error}", file=sys.stderr)
        return REJECTED
    except (OSError, sqlite3.Error) as error:
        print(f"review NOT saved (storage failed): {error}", file=sys.stderr)
        return STORAGE_FAILED
    return 0


if __name__ == "__main__":
    sys.exit(main())

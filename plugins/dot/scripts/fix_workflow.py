# /// script
# requires-python = ">=3.14"
# dependencies = ["tyro>=1.0.13"]
# ///

import sys
from pathlib import Path

import tyro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.workflows.fix import GetReviewArgs, SaveFixArgs, get_review, save_fix

if __name__ == "__main__":

    def _get_review(args: GetReviewArgs) -> None:
        print(get_review(args))

    def _save_fix(args: SaveFixArgs) -> None:
        print(save_fix(args))

    tyro.extras.subcommand_cli_from_dict(
        {
            "get_review": _get_review,
            "save_fix": _save_fix,
        },
        use_underscores=True,
        config=(tyro.conf.OmitArgPrefixes,),
    )

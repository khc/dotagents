# /// script
# requires-python = ">=3.14"
# dependencies = ["tyro>=1.0.13"]
# ///

import sys
from pathlib import Path

import tyro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.workflows.sidecar import ReadArgs, SaveArgs, UpdateArgs, read, save, update

if __name__ == "__main__":

    def _save(args: SaveArgs) -> None:
        print(save(args))

    def _read(args: ReadArgs) -> None:
        print(read(args))

    def _update(args: UpdateArgs) -> None:
        print(update(args))

    tyro.extras.subcommand_cli_from_dict(
        {
            "save": _save,
            "read": _read,
            "update": _update,
        },
        use_underscores=True,
        config=(tyro.conf.OmitArgPrefixes,),
    )

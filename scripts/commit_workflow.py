#!/Users/khc/.agents/.venv/bin/python

import sys
from pathlib import Path

import tyro

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.workflows.commit import (
    ExecuteCommitArgs,
    SaveCommitArgs,
    execute_commit,
    save_commit,
)

if __name__ == "__main__":

    def _save(args: SaveCommitArgs) -> None:
        try:
            print(save_commit(args))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    def _execute(args: ExecuteCommitArgs) -> None:
        try:
            print(execute_commit(args))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    tyro.extras.subcommand_cli_from_dict(
        {
            "save": _save,
            "execute": _execute,
        },
        use_underscores=True,
        config=(tyro.conf.OmitArgPrefixes,),
    )

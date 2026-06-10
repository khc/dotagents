import sys
from pathlib import Path
from typing import Literal, assert_never

ContextInput = Literal["inline", "file", "stdin"]


def load_context(context: str, context_input: ContextInput) -> str:
    if context_input == "inline":
        return context
    if context_input == "file":
        return Path(context).read_text()
    if context_input == "stdin":
        return sys.stdin.read()
    assert_never(context_input)

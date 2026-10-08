# /// script
# requires-python = ">=3.10"
# dependencies = ["json-five"]
# ///
"""Point VS Code's Copilot commit message setting at config/*.md.

settings.json is JSONC (comments, trailing commas), so it is edited through
json-five's round-trip model, which preserves comments and formatting.

Usage: uv run scripts/install_copilot_commit_instructions.py
"""

import json
from pathlib import Path

from json5.dumper import ModelDumper, dumps
from json5.loader import ModelLoader, loads

KEY = "github.copilot.chat.commitMessageGeneration.instructions"
INSTRUCTIONS = Path(__file__).resolve().parent.parent / "config" / "github_copilot_chat_commitMessageGeneration_instructions.md"
SETTINGS = Path.home() / "Library/Application Support/Code/User/settings.json"


def parse(text: str):
    return loads(text, loader=ModelLoader())


def set_key(text: str) -> str:
    value = json.dumps([{"file": str(INSTRUCTIONS)}], indent=4).replace("\n", "\n    ")
    document = parse(text)
    settings = document.value
    new_key, new_value = parse(f'{{\n    "{KEY}": {value}\n}}').value.key_value_pairs[0]

    keys = [getattr(key, "characters", None) for key in settings.keys]
    if KEY in keys:
        old_value = settings.values[keys.index(KEY)]
        new_value.wsc_before, new_value.wsc_after = old_value.wsc_before, old_value.wsc_after
        settings.values[keys.index(KEY)] = new_value
    else:
        new_key.wsc_before = ["\n    "]
        new_value.wsc_after = settings.values[-1].wsc_after if settings.values else ["\n"]
        if settings.values:
            settings.values[-1].wsc_after = []
        settings.keys.append(new_key)
        settings.values.append(new_value)
    return dumps(document, dumper=ModelDumper())


def main() -> None:
    text = SETTINGS.read_text() if SETTINGS.exists() else "{}\n"
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(set_key(text))
    print(f"Updated {KEY} in {SETTINGS}")


if __name__ == "__main__":
    main()

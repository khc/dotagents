#!/usr/bin/env python3
"""
Simple tool to call endpoints using the openai package
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
import openai
from openai import OpenAI
import tyro


@dataclass
class Args:
    skill: Annotated[
        Path,
        tyro.conf.arg(aliases=["-s"]),
    ]
    """Path to skill MD file or skill directory."""


def main() -> None:
    args = tyro.cli(Args)

    # Use hardcoded base URL for local endpoint
    base_url = "http://localhost:1234/v1"

    api_key = os.environ.get("OPENAI_API_KEY", "test")
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )

    # Resolve and read skill file
    if args.skill.is_file():
        skill_file = args.skill
    elif (args.skill / "SKILL.md").is_file():
        skill_file = args.skill / "SKILL.md"
    else:
        print(
            f"Error: Skill path '{args.skill}' not found or does not contain SKILL.md",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        system_prompt = skill_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading skill file: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Calling client.responses.create on {base_url} with skill instructions...")
    try:
        response = client.responses.create(
            model="test",
            input=[{"role": "user", "content": "Generate example output"}],
            instructions=system_prompt,
        )

        print("Response received successfully:")
        print(response.model_dump_json(indent=2))
    except openai.APIStatusError as e:
        print(f"API Error: Status {e.status_code}", file=sys.stderr)
        print("Response Body:", file=sys.stderr)
        print(e.response.text, file=sys.stderr)
        sys.exit(1)
    except openai.APIConnectionError as e:
        print(f"Connection Error: {e}", file=sys.stderr)
        sys.exit(1)
    except openai.APIError as e:
        print(f"OpenAI API Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

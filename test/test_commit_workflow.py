from pathlib import Path

from agents.workflows.commit import get_validation_commands


def test_get_validation_commands_ignores_placeholder_commands(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        """
## Validation

- Run `uv run pytest`
- Use `$context <path>` before repo work
""".strip()
    )

    assert get_validation_commands(tmp_path) == ["uv run pytest"]

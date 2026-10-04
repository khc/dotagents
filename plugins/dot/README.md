# Dot plugin

This directory is the complete installable package. It does not require the surrounding development checkout or its virtual environment.

## Skills

Includes `bug`, `feature`, `find-skills`, `fix`, `implement`, `nlm-skill`, `plan`, `refactor`, `research`, `review`, `scope`, `skill-wrapper`, and `workflow`.

Codex examples:

```text
$dot:scope /path/to/project
$dot:plan Describe the requested change
$dot:implement .plans/plan_<timestamp>.md
```

Claude Code examples:

```text
/dot:scope /path/to/project
/dot:plan Describe the requested change
/dot:implement .plans/plan_<timestamp>.md
```

The plugin name supplies `dot:`. Each skill's frontmatter name remains unqualified.

For Codex's VS Code extension, which does not support plugins, the development checkout at `~/.agents` supplies `skills/<name>` symlinks to these same skill directories. Use plain names such as `$scope` and `$plan` in the IDE; loaded instructions translate internal `dot:<name>` references to the available local names. Keep these compatibility symlinks. Native plugin hosts retain `dot:<name>` invocations.

## Prerequisites

- Git and `uv` on PATH; `uv` manages Python 3.14.
- `tyro>=1.0.13` for review/fix/sidecar helpers, declared as inline script dependencies.
- Claude Code or Codex CLI for workflow subprocess stages, or the existing Agy adapter for native stages.
- External `superpowers:writing-skills` for `dot:skill-wrapper`.
- The existing NotebookLM CLI or MCP connection for `dot:nlm-skill`.

## Load or install

Claude Code local development:

```bash
claude --plugin-dir /absolute/path/to/dot
```

The development repository provides `dotagents` marketplaces. Register that repository and install `dot@dotagents` in Claude Code, or choose `dot` in the Codex native plugin directory. Start a fresh session to confirm `dot:*` discovery. Validation does not prove installation or activation.

The workflow runner passes this package's root with `--plugin-dir` to every fresh Claude stage, so local development also works without marketplace installation. Configured `CLAUDE_CMD` and `CLAUDE_ARGS` remain supported; other plugin paths in those arguments are retained.

## Bundled helpers

Resolve the package root from the loaded skill file: `Path(skill_file).resolve().parents[2]`. Claude Code substitutes `${CLAUDE_PLUGIN_ROOT}` in loaded Markdown. Codex exposes the actual `SKILL.md` path in its catalog. A plugin variable is not assumed to exist in an arbitrary shell.

Set `dot_plugin_root` to that resolved absolute path and keep cwd in the target project:

```bash
dot_plugin_root="/absolute/path/to/dot"
uv run --no-project "$dot_plugin_root/scripts/context_workflow.py" .
uv run --no-project "$dot_plugin_root/scripts/review_workflow.py" --help
uv run --no-project "$dot_plugin_root/scripts/fix_workflow.py" --help
uv run --no-project "$dot_plugin_root/scripts/sidecar_workflow.py" --help
```

Inline script metadata supplies Python/dependency requirements. Modules and the SQL schema live under the bundled `src/`. First execution may require network access to obtain missing dependencies; there is no reliance on `~/.agents/.venv`.

Plans stay at `<target repo>/.plans/`, sidecar data at `<target repo>/.sidecar/`, and workflow handoffs at `<active scope>/.workflow/<workflow-id>/`. Persisted skill identifiers remain `review` and `fix`; workflow stage names and approval gates also remain unchanged.

## Validation

```bash
python skills/workflow/bin/smoke_check.py
claude plugin validate /absolute/path/to/dot
```

The development repository also provides relocation tests, per-skill validation, and combined reports.

## Migration and rollback

Confirm native discovery before removing external old copies of these same skills. Synced skills and unrelated plugins stay separate; this migration deletes no external copies.

Rollback restores the former repository paths from the reviewed migration diff and removes the new package/catalog files. Target-project plans, sidecar entries, and workflow artifacts keep their locations and identifiers throughout.

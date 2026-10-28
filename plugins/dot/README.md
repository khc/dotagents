# Dot plugin

This directory is the complete installable package. It does not require the surrounding development checkout or its virtual environment.

## Skills

Includes 13 skills: `bug`, `cross-review`, `feature`, `find-skills`, `fix`, `implement`, `plan`, `refactor`, `research`, `review`, `scope`, `skill-wrapper`, and `workflow`.

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

## Prerequisites

- Git and `uv` on PATH; `uv` manages Python 3.14.
- `tyro==1.0.13` for review/fix/sidecar helpers, declared as inline script dependencies.
- Claude Code or Codex CLI for workflow subprocess stages, or the existing Agy adapter for native stages.
- External `superpowers:writing-skills` for `dot:skill-wrapper`.

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
uv run --no-project --locked "$dot_plugin_root/scripts/context_workflow.py" .
uv run --no-project --locked "$dot_plugin_root/scripts/review_workflow.py" --help
uv run --no-project --locked "$dot_plugin_root/scripts/review_subject.py" --help
uv run --no-project --locked "$dot_plugin_root/scripts/review_strategy.py" --help
uv run --no-project --locked "$dot_plugin_root/scripts/fix_workflow.py" --help
uv run --no-project --locked "$dot_plugin_root/scripts/sidecar_workflow.py" --help
```

Inline script metadata supplies Python/dependency requirements, and each script ships a `uv lock --script` lockfile (`<script>.py.lock`) so `--locked` installs exactly `tyro==1.0.13` and nothing else. Modules and the SQL schema live under the bundled `src/`. First execution may require network access to download that pinned package; there is no reliance on `~/.agents/.venv`.

Plans stay at `<target repo>/.plans/`, sidecar data at `<target repo>/.sidecar/`, and workflow handoffs at `<active scope>/.workflow/<workflow-id>/` (for a single-file scope, `<file's directory>/.workflow/<id>/`). Persisted skill identifiers remain `review` and `fix`; workflow stage names and approval gates also remain unchanged.

## What the plugin runs, sends, and fetches

- **Local commands:** `git rev-parse` and `git -C <repo>` read-only queries, `uv run --no-project --locked` for the bundled helpers, and SQLite for sidecar storage under `<target repo>/.sidecar/`.
- **Subprocess stages:** `skills/workflow/bin/workflow.py` starts fresh `claude`, `codex`, or `agy` CLI processes (overridable with `CLAUDE_CMD`, `CODEX_CMD`, `AGY_CMD`) and passes them the stage prompt and the artifacts it writes under `<active scope>/.workflow/`. Those CLIs send that content to their own providers under their own terms; the plugin sends nothing else.
- **Network from plugin code:** none. The bundled Python makes no HTTP requests. The only download is the pinned `tyro==1.0.13` package fetched by `uv` on first run of the helpers.
- **Web research:** `dot:web-research` asks an agent with web access to look up external facts. The skill passes identifiers only (library and API names, versions, error strings), never repository text unless you authorize an excerpt, and redacts credentials first.
- **Skills installer:** `dot:find-skills` runs `npx skills@1.7.4` (the Skills CLI, pinned) only when you ask it to find or install a skill.
- **Credentials:** the plugin reads no credentials from your environment and stores none. Reviews print `[REDACTED:<type>]` instead of secret values.

## Validation

```bash
python skills/workflow/bin/smoke_check.py
claude plugin validate /absolute/path/to/dot
```

The development repository also provides relocation tests, per-skill validation, and combined reports.

## Migration and rollback

Confirm native discovery before removing external old copies of these same skills. Synced skills and unrelated plugins stay separate; this migration deletes no external copies.

The package retains 13 skills and intentionally excludes NotebookLM. The development checkout uses the native plugin layout without local skill aliases.

Rollback restores the former repository paths from the reviewed migration diff and removes the new package/catalog files. Target-project plans, sidecar entries, and workflow artifacts keep their locations and identifiers throughout.

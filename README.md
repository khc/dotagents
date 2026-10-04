# Dot skills

The `dot` plugin packages 13 local skills for Codex CLI/desktop and Claude Code. Invoke `$dot:plan` in Codex or `/dot:plan` in Claude Code. The plugin supplies the namespace; frontmatter names remain unqualified. Codex's VS Code extension uses the local skill symlinks with plain names such as `$plan`.

## Included skills

| Skill | Purpose |
| --- | --- |
| `dot:scope` | Activate scope and repository instructions |
| `dot:feature` | Implement a bounded feature |
| `dot:plan` | Create and revise an implementation plan |
| `dot:implement` | Execute an approved plan |
| `dot:review` | Review changes, paths, or symbols |
| `dot:fix` | Apply review findings |
| `dot:bug` | Diagnose and fix a concrete symptom |
| `dot:refactor` | Restructure code while preserving behavior |
| `dot:research` | Find existing implementation solutions |
| `dot:workflow` | Orchestrate isolated lifecycle stages |
| `dot:find-skills` | Discover additional skills |
| `dot:nlm-skill` | Use NotebookLM CLI or MCP tools |
| `dot:skill-wrapper` | Improve skills with reusable evals |

`dot:skill-wrapper` requires the external `superpowers:writing-skills` skill. NotebookLM requires its existing CLI or MCP connection. The package does not supply those services.

## Workflows

- Bounded feature: `dot:scope → dot:feature → dot:review → [dot:fix → dot:review]*`
- Planned implementation: `dot:scope → dot:plan → approval → dot:implement → dot:review → [dot:fix → dot:review]*`
- Standalone review: `dot:scope → dot:review → [dot:fix → dot:review]*`

See [workflow documentation](plugins/dot/skills/workflow/README.md) for Claude/Codex subprocess stages and the existing Agy/Antigravity adapter.

## Layout

```text
.agents/plugins/marketplace.json
.claude-plugin/marketplace.json
plugins/dot/
├── plugin.json
├── .claude-plugin/plugin.json
├── skills/
├── scripts/
├── src/agents/
├── src/schemas/sidecar.schema.sql
└── evals/
skills/<name>/                # symlinks to plugins/dot/skills/<name>/ for IDE discovery
skills/synced/                 # independent synced collection
scripts/                      # development tools
src/skill_report.py
src/quick_validate.py
```

Only `plugins/dot/` is the installable package. Both catalogs resolve `./plugins/dot` from this repository root. Synced skills remain independent.

## Install

Bundled helpers require Git and `uv` on PATH. `uv` manages Python 3.14 and inline dependencies without a checkout-specific virtual environment.

### Codex

```bash
codex plugin marketplace add /absolute/path/to/this/repository
```

Open the native plugin selector (`/plugins` in CLI, or Plugins in the desktop app), select the `dot-local` source, and install `dot`. Start a fresh session and select `$dot:scope` or `$dot:plan`. Registration/installation change host settings; creating the package does not install it.

### Codex VS Code extension

The IDE extension [does not support plugins](https://learn.chatgpt.com/docs/plugins). When this checkout lives at `~/.agents`, the tracked `skills/<name>` symlinks expose all 13 skills through Codex's [local skill discovery](https://learn.chatgpt.com/docs/build-skills). No plugin installation is needed for these local skills. Restart Codex if the selector has not refreshed, then invoke `$scope`, `$plan`, or another unqualified skill name.

Local skill instructions translate `dot:<name>` references to the unqualified name when the namespace is absent from the catalog. The symlinks reuse the plugin's instructions, assets, and helpers; they contain no copied skill implementations. In a CLI/desktop session with `dot` installed, both local and plugin identities may appear; prefer `$dot:<name>` there. Keep these compatibility symlinks when removing unrelated duplicate installations.

### Claude Code

Load the package for local development:

```bash
claude --plugin-dir /absolute/path/to/this/repository/plugins/dot
```

Or install from the marketplace:

```bash
claude plugin marketplace add /absolute/path/to/this/repository
claude plugin install dot@dot-local
```

Start a fresh session and invoke `/dot:scope` or `/dot:plan`.

## Runtime paths

Resolve resources from the loaded skill file. Run helpers from the target project working directory, preserving:

- Plans: `<target repo>/.plans/`
- Review/fix persistence: `<target repo>/.sidecar/`
- Workflow handoffs: `<active scope>/.workflow/<workflow-id>/`

See [the package README](plugins/dot/README.md) for helper commands and dependencies.

## Validate

From the development repository with its dependencies installed:

```bash
.venv/bin/python -B -m unittest discover -s test -p test_dot_plugin.py
.venv/bin/python -B plugins/dot/skills/workflow/bin/smoke_check.py
task skills:validate skill=scope
task skillcheck skill=scope
task report:json skill=scope
claude plugin validate ./plugins/dot
claude plugin validate .
```

Taskfile validators retain their names and unqualified `skill=<name>` argument, resolving skills below `plugins/dot/skills/`. Report output fields remain unchanged.

## Migration and rollback

The 13 tracked skill trees and their shared runtime moved into `plugins/dot/`; their former local paths are compatibility symlinks for IDE discovery. After confirming native discovery, remove any separate old copies of these same skills from other host skill roots to avoid duplicates. Keep the compatibility symlinks, synced skills, and unrelated skills. External copies are not automatically removed.

Rollback restores moved paths and removes new package/catalog files using the reviewed migration diff. Target-project `.plans`, `.sidecar`, and `.workflow` locations and persisted identifiers are unchanged and need no data migration.

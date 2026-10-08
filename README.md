# Dot skills

The `dot` plugin packages 12 skills for Codex CLI/desktop and Claude Code. Invoke `$dot:plan` in Codex or `/dot:plan` in Claude Code. The plugin supplies the namespace; frontmatter names remain unqualified.

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
| `dot:skill-wrapper` | Improve skills with reusable evals |

`dot:skill-wrapper` requires the external `superpowers:writing-skills` skill.

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

Open the native plugin selector (`/plugins` in CLI, or Plugins in the desktop app), select the `dotagents` source, and install `dot`. Start a fresh session and select `$dot:scope` or `$dot:plan`. Registration/installation change host settings; creating the package does not install it.

### Codex VS Code extension

The IDE extension [does not support plugins](https://learn.chatgpt.com/docs/plugins). This checkout supplies the native plugin package without local skill aliases. Use Codex CLI/desktop or Claude Code to load it.

### Claude Code

Load the package for local development:

```bash
claude --plugin-dir /absolute/path/to/this/repository/plugins/dot
```

Or install from the marketplace:

```bash
claude plugin marketplace add /absolute/path/to/this/repository
claude plugin install dot@dotagents
```

Start a fresh session and invoke `/dot:scope` or `/dot:plan`.

## Copilot commit message instructions (VS Code)

[config/github_copilot_chat_commitMessageGeneration_instructions.md](config/github_copilot_chat_commitMessageGeneration_instructions.md) holds Conventional Commits rules for GitHub Copilot's commit message generation.

Add it to VS Code `settings.json` (Command Palette → `Preferences: Open User Settings (JSON)`):

```json
"github.copilot.chat.commitMessageGeneration.instructions": [
  { "file": "/absolute/path/to/this/repository/config/github_copilot_chat_commitMessageGeneration_instructions.md" }
]
```

Use a path relative to the workspace root (e.g. `config/...md`) in workspace settings. Then click the sparkle icon in the Source Control commit box to generate a message.

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

The 12 retained skill trees and their shared runtime live in `plugins/dot/`. The NotebookLM skill is intentionally excluded, and the former local skill aliases have been removed. After confirming native discovery, remove any separate old copies of these same skills from other host skill roots to avoid duplicates. Keep synced and unrelated skills. External copies are not automatically removed.

Rollback restores moved paths and removes new package/catalog files using the reviewed migration diff. Target-project `.plans`, `.sidecar`, and `.workflow` locations and persisted identifiers are unchanged and need no data migration.

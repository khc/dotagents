# Agent SDLC Package

Portable SDLC skill set and subagent orchestration for Claude Code, Codex CLI, and Agy/Antigravity.

## Included skills

- `context` — scope and repo-instruction ownership
- `feature` — bounded feature implementation
- `plan` — repo-grounded decomposition for larger changes
- `implement` — faithful execution of an existing plan
- `review` — change/path/symbol review and acceptance
- `fix` — remediation of review findings
- `workflow` — orchestrates the above across isolated agents (fresh-agent dispatch, artifact handoffs, review/fix loops)

## Workflows

### Bounded feature
`context → feature → review → [fix → review]*`

### Planned implementation
`context → plan → implement → review → [fix → review]*`

### Standalone review
`context → review → [fix → review]*`

## Layout

```text
skills/
├── context/SKILL.md
├── feature/SKILL.md
├── plan/SKILL.md
├── implement/SKILL.md
├── review/SKILL.md
├── fix/SKILL.md
└── workflow/
    ├── SKILL.md
    ├── bin/
    ├── workflows/
    ├── schemas/
    ├── adapters/
    └── runtime/
docs/
└── workflows/
    ├── feature.md
    ├── planned.md
    └── review.md
```

## Orchestration

The `workflow` skill is runtime-neutral in policy and runtime-specific only in stage spawning.

- Claude Code: fresh `claude -p` process per stage
- Codex CLI: fresh `codex exec` process per stage
- Agy/Antigravity: native `invoke_subagent`

Canonical handoff transport is filesystem artifacts under:

`<scope>/.workflow/<workflow-id>/`

See `skills/workflow/README.md`.

## Install

Copy `skills/*` into the skill root used by your runtime.

For Agy, also copy:

`skills/workflow/runtime/agy/agents/*.md`

to:

`.agents/agents/`

For Claude/Codex, invoke the workflow runner directly from `skills/workflow/bin/workflow.py`.

## Validate

```bash
python skills/workflow/bin/smoke_check.py
```

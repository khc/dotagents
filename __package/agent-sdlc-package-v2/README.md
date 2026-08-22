# Agent SDLC Package

Portable SDLC skill set and subagent orchestration for Claude Code, Codex CLI, and Agy/Antigravity.

## Included skills

- `context` — scope and repo-instruction ownership
- `feature` — bounded feature implementation
- `plan` — repo-grounded decomposition for larger changes
- `implement` — faithful execution of an existing plan
- `review` — change/path/symbol review and acceptance
- `fix` — remediation of review findings

## Workflows

### Bounded feature
`context → feature → review → [fix → review]*`

### Planned implementation
`context → plan → implement → review → [fix → review]*`

### Standalone review
`context → review → [fix → review]*`

## Layout

```text
agent-sdlc-package/
├── skills/
│   ├── context/SKILL.md
│   ├── feature/SKILL.md
│   ├── plan/SKILL.md
│   ├── implement/SKILL.md
│   ├── review/SKILL.md
│   └── fix/SKILL.md
├── workflows/
│   ├── feature.md
│   ├── planned.md
│   └── review.md
└── orchestration/
    ├── SKILL.md
    ├── bin/
    ├── workflows/
    ├── schemas/
    ├── adapters/
    └── runtime/
```

## Orchestration

The orchestration layer is runtime-neutral in policy and runtime-specific only in stage spawning.

- Claude Code: fresh `claude -p` process per stage
- Codex CLI: fresh `codex exec` process per stage
- Agy/Antigravity: native `invoke_subagent`

Canonical handoff transport is filesystem artifacts under:

`<scope>/.workflow/<workflow-id>/`

See `orchestration/README.md`.

## Install

Copy `skills/*` into the skill root used by your runtime.

For Agy, also copy:

`orchestration/runtime/agy/agents/*.md`

to:

`.agents/agents/`

For Claude/Codex, invoke the orchestration runner directly from `orchestration/bin/workflow.py`.

## Validate

```bash
python orchestration/bin/smoke_check.py
```


## Review loop invariant

Workflow completion requires an exact `$review` verdict of `ready` with zero findings.

- `ready-with-fixes` → fixer → re-review
- `not-ready` with findings → fixer → re-review
- only `ready` with no findings → done

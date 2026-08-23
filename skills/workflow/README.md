# Agent Workflow Orchestration

Portable orchestration for:

1. `context → feature → review → [fix → review]*`
2. `context → refactor → review → [fix → review]*`
3. `context → plan → implement → review → [fix → review]*`
4. `context → review → [fix → review]*`

## Runnable runtimes

### Claude Code

```bash
python bin/workflow.py feature --runtime claude --scope . --request "..."
```

Uses a fresh `claude -p` subprocess per lifecycle stage.

### Codex CLI

```bash
python bin/workflow.py planned --runtime codex --scope . --request-file task.md
```

Uses a fresh `codex exec` subprocess per lifecycle stage.

### Agy / Antigravity

Copy the custom stage agents:

```bash
mkdir -p .agents/agents
cp runtime/agy/agents/*.md .agents/agents/
```

Then invoke `$workflow` from the parent Agy agent and let it use native
`invoke_subagent` for every lifecycle stage.

## Design

- skills own lifecycle behavior
- orchestrator owns transitions and isolation
- filesystem artifacts are the canonical handoff transport
- fresh reviewer context is mandatory
- stage agents never invoke the next lifecycle stage
- max review/fix cycles defaults to 5

## Configuration

Claude:
- `CLAUDE_CMD`
- `CLAUDE_ARGS`

Codex:
- `CODEX_CMD`
- `CODEX_ARGS`

## Validation

```bash
python bin/smoke_check.py
python bin/workflow.py feature --runtime claude --scope . --request "..." --dry-run
python bin/workflow.py feature --runtime codex --scope . --request "..." --dry-run
```

`--dry-run` prints the exact stage prompt without invoking a model.

## Layout

- `SKILL.md` — runtime-neutral workflow policy
- `bin/workflow.py` — executable Claude/Codex state-machine runner
- `runtime/agy/agents/` — native Agy subagent definitions
- `workflows/` — workflow transitions/handoff policy
- `schemas/` — handoff schemas
- `adapters/` — runtime mapping notes

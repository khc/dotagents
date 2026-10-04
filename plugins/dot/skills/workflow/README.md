# Agent Workflow Orchestration

Portable orchestration for:

1. `scope → feature → review → [fix → review]*`
2. `scope → refactor → review → [fix → review]*`
3. `scope → bug → review → [fix → review]*`
4. `scope → plan → AWAITING_PLAN_APPROVAL → implement → review → [fix → review]*`
5. `scope → review → [fix → review]*`

## Runnable runtimes

### Claude Code

```bash
python bin/workflow.py start feature --runtime claude --scope . --request "..."
```

Uses a fresh `claude -p` subprocess per lifecycle stage.

### Codex CLI

```bash
python bin/workflow.py start planned --runtime codex --scope . --request-file task.md
python bin/workflow.py resume <workflow-id> --scope . --message "Don't use JWT; use sessions"
python bin/workflow.py approve <workflow-id> --scope .
```

`planned` (and any `feature` that escalates via `needs_plan`) pauses at `awaiting_plan_approval` after `$dot:plan` succeeds; resume with `resume`/`approve`/`cancel` using the printed `workflow-id`.

Uses a fresh `codex exec` subprocess per lifecycle stage.

### Agy / Antigravity

Copy the custom stage agents:

```bash
mkdir -p .agents/agents
cp runtime/agy/agents/*.md .agents/agents/
```

Then invoke `$dot:workflow` from the parent Agy agent and let it use native
`invoke_subagent` for every lifecycle stage.

## Design

- skills own lifecycle behavior
- orchestrator owns transitions and isolation
- filesystem artifacts are the canonical handoff transport
- fresh reviewer context is mandatory
- stage agents never invoke the next lifecycle stage
- max review/fix cycles defaults to 5
- `planned` workflows pause for explicit human plan approval (`AWAITING_PLAN_APPROVAL`) before `$dot:implement` runs

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
python bin/workflow.py start feature --runtime claude --scope . --request "..." --dry-run
python bin/workflow.py start feature --runtime codex --scope . --request "..." --dry-run
```

`--dry-run` prints the exact stage prompt without invoking a model.

## Layout

- `SKILL.md` — runtime-neutral workflow policy
- `bin/workflow.py` — executable Claude/Codex state-machine runner
- `runtime/agy/agents/` — native Agy subagent definitions
- `workflows/` — workflow transitions/handoff policy
- `schemas/` — handoff schemas
- `adapters/` — runtime mapping notes

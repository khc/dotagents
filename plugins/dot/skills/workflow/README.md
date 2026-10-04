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

### Agy subprocess

```bash
python bin/workflow.py start feature --runtime agy --scope . --request "..."
```

Uses a fresh `agy -p` subprocess per lifecycle stage.

### Cross-review

Run independent reviewers on several runtimes, then synthesize with `$dot:cross-review`:

```bash
# stage agent / skill entry point: fan out and print reviewer sidecar UUIDs
python bin/workflow.py review-fanout --scope . --runtimes claude,codex,agy --request "Review src/auth"

# workflow: the review stage invokes $dot:cross-review
python bin/workflow.py start review --runtime claude --scope . \
  --request "Review src/auth" --review-runtimes claude,codex,agy
```

`--review-timeout` (default 900 s) bounds each reviewer; a missing or malformed envelope is retried once. Any reviewer failure blocks the review. Cross-review needs `bin/workflow.py`; native Agy `invoke_subagent` stages run a single reviewer.

`review-fanout` accepts a file or a directory as `--scope` and passes the request text to every reviewer verbatim, as the arguments of `$dot:review`. For a single-file scope the reviewers run in the file's directory and see only that file; `start` requires a directory scope. See `../cross-review/references/fanout.md` for the full run instructions.

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

Agy:
- `AGY_CMD`
- `AGY_ARGS`

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

# Claude Code Runtime

Claude Code supports headless fresh invocations with `claude -p`. The portable
runner uses one new Claude process per lifecycle stage.

## Prerequisites

- `claude` on PATH and authenticated
- lifecycle skills discoverable in Claude Code
- repo permissions configured for the desired writes/commands

## Run

```bash
python bin/workflow.py start feature \
  --runtime claude \
  --scope /path/to/repo/subtree \
  --request "Add ..."
```

Refactor:

```bash
python bin/workflow.py start refactor --runtime claude --scope . \
  --request "Extract the retry logic in client.ts into a shared helper"
```

Bug:

```bash
python bin/workflow.py start bug --runtime claude --scope . \
  --request "TypeError: cannot read 'id' of undefined in checkout.ts on submit"
```

Planned:

```bash
python bin/workflow.py start planned --runtime claude --scope . --request-file task.md
python bin/workflow.py resume <workflow-id> --scope . --message "Don't use JWT; use sessions"
python bin/workflow.py approve <workflow-id> --scope .
python bin/workflow.py cancel <workflow-id> --scope .
```

`planned` (and any `feature` that escalates via `needs_plan`) pauses at `awaiting_plan_approval` after `$plan` succeeds; resume with `resume`/`approve`/`cancel` using the printed `workflow-id`.

Standalone review:

```bash
python bin/workflow.py start review --runtime claude --scope src/auth \
  --request "Review token.ts::verifyToken"
```

The default invocation is `claude -p`. Override safely if needed:

```bash
export CLAUDE_CMD=claude
export CLAUDE_ARGS='-p --max-turns 80'
```

Do not use `--continue` or `--resume`: every lifecycle stage must start fresh.

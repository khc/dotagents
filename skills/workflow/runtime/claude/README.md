# Claude Code Runtime

Claude Code supports headless fresh invocations with `claude -p`. The portable
runner uses one new Claude process per lifecycle stage.

## Prerequisites

- `claude` on PATH and authenticated
- lifecycle skills discoverable in Claude Code
- repo permissions configured for the desired writes/commands

## Run

```bash
python bin/workflow.py feature \
  --runtime claude \
  --scope /path/to/repo/subtree \
  --request "Add ..."
```

Refactor:

```bash
python bin/workflow.py refactor --runtime claude --scope . \
  --request "Extract the retry logic in client.ts into a shared helper"
```

Planned:

```bash
python bin/workflow.py planned --runtime claude --scope . --request-file task.md
```

Standalone review:

```bash
python bin/workflow.py review --runtime claude --scope src/auth \
  --request "Review token.ts::verifyToken"
```

The default invocation is `claude -p`. Override safely if needed:

```bash
export CLAUDE_CMD=claude
export CLAUDE_ARGS='-p --max-turns 80'
```

Do not use `--continue` or `--resume`: every lifecycle stage must start fresh.

# Codex Runtime

The portable runner uses a new `codex exec` process for each lifecycle stage.
This provides fresh context while keeping the same serial workspace.

## Prerequisites

- `codex` on PATH and authenticated
- lifecycle skills discoverable by Codex
- repo sandbox/approval configuration appropriate for the workflow

## Run

```bash
python bin/workflow.py feature \
  --runtime codex \
  --scope /path/to/repo/subtree \
  --request "Add ..."
```

Refactor:

```bash
python bin/workflow.py refactor --runtime codex --scope . \
  --request "Extract the retry logic in client.ts into a shared helper"
```

Planned:

```bash
python bin/workflow.py planned --runtime codex --scope . --request-file task.md
```

Standalone review:

```bash
python bin/workflow.py review --runtime codex --scope src/auth \
  --request "Review token.ts::verifyToken"
```

Defaults to `codex exec --cd <scope>`. Override the command arguments for the
installed Codex version or your sandbox policy:

```bash
export CODEX_CMD=codex
export CODEX_ARGS='exec'
```

Do not use `resume` for lifecycle stages: the workflow requires fresh context,
especially for every review/re-review.

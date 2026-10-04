# Codex Runtime

The portable runner uses a new `codex exec` process for each lifecycle stage.
This provides fresh context while keeping the same serial workspace.

## Prerequisites

- `codex` on PATH and authenticated
- lifecycle skills discoverable by Codex
- repo sandbox/approval configuration appropriate for the workflow

## Run

```bash
python bin/workflow.py start feature \
  --runtime codex \
  --scope /path/to/repo/subtree \
  --request "Add ..."
```

Refactor:

```bash
python bin/workflow.py start refactor --runtime codex --scope . \
  --request "Extract the retry logic in client.ts into a shared helper"
```

Bug:

```bash
python bin/workflow.py start bug --runtime codex --scope . \
  --request "TypeError: cannot read 'id' of undefined in checkout.ts on submit"
```

Planned:

```bash
python bin/workflow.py start planned --runtime codex --scope . --request-file task.md
python bin/workflow.py resume <workflow-id> --scope . --message "Don't use JWT; use sessions"
python bin/workflow.py approve <workflow-id> --scope .
python bin/workflow.py cancel <workflow-id> --scope .
```

`planned` (and any `feature` that escalates via `needs_plan`) pauses at `awaiting_plan_approval` after `$dot:plan` succeeds; resume with `resume`/`approve`/`cancel` using the printed `workflow-id`.

Standalone review:

```bash
python bin/workflow.py start review --runtime codex --scope src/auth \
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

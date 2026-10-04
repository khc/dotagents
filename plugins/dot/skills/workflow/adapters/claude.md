# Claude adapter

Runnable transport: `bin/workflow.py --runtime claude`.

Each stage is a fresh `claude -p` subprocess. Do not resume/continue prior
sessions. Skills are invoked by instruction inside that fresh stage.

Configuration:
- `CLAUDE_CMD` default `claude`
- `CLAUDE_ARGS` default `-p`

See `runtime/claude/README.md`.

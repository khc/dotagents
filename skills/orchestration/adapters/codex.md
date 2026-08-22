# Codex adapter

Runnable transport: `bin/workflow.py --runtime codex`.

Each stage is a fresh `codex exec` subprocess. Do not use `resume` across
lifecycle stages. Skills are invoked by instruction inside that fresh stage.

Configuration:
- `CODEX_CMD` default `codex`
- `CODEX_ARGS` default `exec`

See `runtime/codex/README.md`.

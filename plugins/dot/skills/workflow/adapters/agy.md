# Agy adapter

Runnable transport: native `invoke_subagent`.

Copy `runtime/agy/agents/*.md` to `.agents/agents/`, invoke `$dot:workflow` from
the main agent, and use one fresh custom subagent per stage.

Use workspace `inherit` for the serial workflow unless deliberate worktree
isolation is needed. Do not pass transcripts between agents.

See `runtime/agy/README.md`.

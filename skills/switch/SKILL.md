---
name: switch
description: Activate a scoped working context within a repo path, apply local AGENTS.md rules, and strictly limit all work to that subtree.
---

# Switch

Activate and lock the working context to a specific repo path.

## Activation

1. Verify the provided path exists. If it does not, stop immediately and report: `Error: path <path> does not exist. Provide a valid path to activate scope.`
2. Set the provided path as the active scope.
2. Load:
   - global `~/.agents/AGENTS.md`
   - repo-root `AGENTS.md`
   - nearest `<path>/AGENTS.md` (takes precedence over global and root)
3. Confirm:

### Active Context
- Path: <path>

### Instructions Loaded

| File | Loaded |
|------|--------|
| Global AGENTS.md | yes/no |
| Root AGENTS.md | yes/no |
| Local AGENTS.md | yes/no |

### Scope Boundaries
- Allowed: <path>/**
- Disallowed: everything else unless explicitly approved

Do not proceed until this confirmation is returned.

## Execution Rules

- Operate ONLY within the active scope.
- Reads, edits, and commands must stay inside `<path>/**`.
- If a dependency outside scope is required:
  - STOP
  - explain why (1 sentence)
  - ask for approval

## Token Control

- Do not scan entire repo
- Do not summarize unrelated files
- Do not build global context unless explicitly requested
- Load only files directly required for the task

## Guardrails

- No architecture analysis unless asked
- No dependency exploration unless required
- No proactive suggestions outside scope
- No “helpful” expansion

## Failure Mode

If the task cannot be completed within scope:
- State limitation in 1–2 sentences
- Ask for permission to expand scope

## Output

Use this shape:

````markdown
## Switch

### Active Context
- Path: `<path>`

### Instructions Loaded

| File | Loaded |
|------|--------|
| Global AGENTS.md | yes/no |
| Root AGENTS.md | yes/no |
| Local AGENTS.md | yes/no |

### Scope Boundaries
- Allowed: `<path>/**`
- Disallowed: everything else unless explicitly approved
````

## Response format

Start every response with the `## Switch` heading (plain, not in a code block). Render output directly beneath it.

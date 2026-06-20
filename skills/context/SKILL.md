---
name: context
description: Activate a scoped working context within a repo path, apply local AGENTS.md rules, and strictly limit all work to that subtree.
---

# Context

Activate and lock the working context to a specific repo path.

## Activation

1. Run the context helper:

   ```bash
   ~/.agents/.venv/bin/python ~/.agents/scripts/context_workflow.py <path>
   ```

2. Parse the JSON returned by the helper.
3. Treat `scope_path` as the active scope.
4. Render the confirmation using the Output template below.
5. Do not proceed until this confirmation is returned.

The helper resolves `<path>` relative to the current working directory, normalizes it to an absolute real path, verifies it exists, detects the repo root with `git rev-parse --show-toplevel` and falls back to the scope directory, de-duplicates repeated `AGENTS.md` paths, and reports the loaded instruction files.

## Execution Rules

- Operate ONLY within the active scope.
- Reads and edits must stay within declared allowed paths.
- Commands must target only declared allowed paths and must not trigger repo-wide scans.
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

## Helper Output

The helper returns JSON:

```json
{
  "scope_path": "/absolute/path",
  "instructions_loaded": {
    "global": true,
    "root": true,
    "local": false
  },
  "scope_boundaries": {
    "allowed": "/absolute/path/**",
    "disallowed": "everything else unless explicitly approved"
  }
}
```

## Output

Render this shape from the helper JSON:

````markdown
## Context

### Active Context
- Path: `<scope_path>`

### Instructions Loaded

| File | Loaded |
|------|--------|
| Global AGENTS.md | yes/no from `instructions_loaded.global` |
| Root AGENTS.md | yes/no from `instructions_loaded.root` |
| Local AGENTS.md | yes/no from `instructions_loaded.local` |

### Scope Boundaries
- Allowed: `<scope_boundaries.allowed>`
- Disallowed: `<scope_boundaries.disallowed>`
````

## Response format

Start every response with the `## Context` heading (plain, not in a code block). Render output directly beneath it.

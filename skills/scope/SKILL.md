---
name: scope
description: Use when starting work on a repo path, scoping tasks to a subtree, or before performing reads, edits, or commands in a repository.
compatibility: Requires python and git on PATH.
---

# Scope

Activate and lock the working scope to a specific repo path before doing repo work in it. Scoping first keeps the session cheap, predictable, and free of edits that wander outside what was actually asked.

## Activation

1. Run the scope helper:

   ```bash
   ~/.agents/.venv/bin/python ~/.agents/scripts/context_workflow.py <path>
   ```

2. If the helper errors instead of returning JSON (e.g. the path doesn't exist), stop here — see **Activation Failure** below. Do not guess at a path or proceed without a confirmed scope.
3. Otherwise, parse the JSON it returns and treat `scope_path` as the active scope.
4. Render the confirmation using the Output template below, starting the response with the `## Scope` heading.
5. Do not do any other repo work until this confirmation has been rendered.

The helper resolves `<path>` relative to the current working directory, normalizes it to an absolute real path, verifies it exists, detects the repo root with `git rev-parse --show-toplevel` and falls back to the scope directory, de-duplicates repeated `AGENTS.md` paths, and reports the loaded instruction files.

### Activation Failure

If the helper exits with an error instead of JSON, there is no active scope — don't infer one from the request or fall back to a similar-looking path. Respond with:

```markdown
## Scope

Scope activation failed: <one sentence with the helper's error and why there's no confirmed scope>.

<one sentence asking the user to confirm the correct path, or for permission to search for it>
```

Then stop and wait for the user's reply before touching any files.

## Scope Ownership

The active scope is authoritative for both the scoped path and repo instructions until `$scope` is explicitly activated again.

- Downstream skills must reuse `scope_path`, `scope_boundaries`, and the instruction state established here rather than independently widening scope.
- Treat the `AGENTS.md` files loaded by the helper as the applicable instruction set for the active scope.
- A downstream skill may read an additional `AGENTS.md` only when it is inside `scope_boundaries.allowed`, applies more specifically to a file the task legitimately needs, and was not already loaded by the helper.
- Do not leave the active scope merely to rediscover repo instructions, tooling, conventions, or dependencies.
- Workflow handoffs (`$feature`, `$plan`, `$implement`, `$review`, `$fix`) inherit this scope; a handoff does not implicitly reactivate or broaden scope.

## Working Within Scope

Once a scope is active, everything you do should stay inside `scope_boundaries.allowed` — that's the entire point of activating one:

- Reads, edits, and commands target only paths under the active scope; don't run anything that would scan or touch the rest of the repo.
- If finishing the task genuinely needs something outside scope (a dependency, a file elsewhere), stop, explain why in one sentence, and ask for approval — see Failure Mode.

## Stay Efficient and On-Task

A narrow scope is also a budget, not just a boundary — spending it on things nobody asked for defeats the reason the scope was narrowed in the first place:

- Don't scan the whole repo or summarize files unrelated to the task.
- Don't build broader/global context unless the user explicitly asks for it.
- Load only the files the task actually needs.
- Skip architecture analysis, dependency exploration, or "while I'm here" suggestions unless the user asked for them.

## Failure Mode

Whenever the task can't be completed within the active scope — not only at activation, but any time a mid-task need turns out to live outside it — state the limitation in 1-2 sentences and ask for permission to expand scope. Don't expand scope unilaterally, and don't silently route around the limitation instead of surfacing it.

Approval to expand scope must be followed by an explicit `$scope` activation on the newly approved path before repo work continues; verbal approval alone does not mutate `scope_boundaries.allowed`.

## Common Rationalizations & Red Flags

**Violating the letter of scope boundaries is violating the spirit of the rules.**

| Excuse / Rationalization | Reality |
|---|---|
| "Just running a quick read/search across the entire repo" | Whole-repo searches waste tokens and violate scope boundaries. Restrict all tools to `scope_boundaries.allowed` or ask permission. |
| "Helper failed on a typo, but the intended directory is obvious" | Inferring paths causes silent scope drift. Stop immediately, report failure, and confirm the path. |
| "Only editing 1 line in a shared utility outside scope" | Any touch outside `scope_boundaries.allowed` is a scope breach. Stop and request permission to expand scope. |
| "Urgent deploy / production emergency overrides scoping" | Urgency increases the risk of regressions. Scope discipline is strictly required at all times. |

### Red Flags - STOP and Ask
- Running search/grep across the whole workspace when scoped to a subtree.
- Guessing or falling back to a similar-looking directory when activation fails.
- Editing or reading dependencies outside scope without explicit permission.
- Bypassing scope activation because "the task is small".

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

On successful activation, render this shape from the helper JSON, starting every response with the plain `## Scope` heading (not inside a code block):

````markdown
## Scope

### Active Scope
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

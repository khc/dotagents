---
name: bug
description: Use when a visible symptom (console error, stack trace, unexpected behavior) needs to be investigated and fixed in one pass. Trigger with "fix this bug", "investigate the error", or a pasted stack trace.
---

# Bug

Investigate a symptom, identify the root cause, apply a minimal fix, and confirm it resolves the issue — in one pass.

## Workflow

If a scoped context is not active:
- STOP
- run `/context` first

1. Read `AGENTS.md` first. If absent, skip and proceed from the scoped path only.
2. Accept the symptom as input: error message, stack trace, log output, or behavior description.

## Method

- Use `Grep` to locate the error string, symbol, or call site. Do not read files speculatively.
- Use `Glob` only if the error gives no direct location hint.
- Do not read files not connected to the symptom.

## Investigation Phase

1. Locate the error origin using the symptom (file, line, symbol).
2. Read at most 2–3 files directly implicated by the symptom. Stop. Do not read further.
3. Identify the root cause in 1–3 bullets:
   - what is failing
   - why it is failing
   - what the fix must preserve

Do not implement during investigation.

## Fix Phase

Apply the minimal fix:

- Change only what is required to resolve the root cause
- Do not refactor surrounding code
- Do not fix unrelated issues
- Prefer the smallest correct change

## Verification Phase

After the fix, confirm inline by reasoning over already-read code only. Do not read additional files during verification.

- State what the fix changes and why it resolves the root cause
- Identify any obvious regression risk in directly touched code
- Do not run a full audit or re-review the module

## Output

Use this shape:

````markdown
## Bug

### Root Cause
- what is failing
- why it is failing
- what the fix must preserve

### Fix
`path/to/file:line` — diff or targeted edit

### Verification
- fix resolves root cause
- regression risk (1–2 lines max)
````

## Scope Gate

- Do not fix issues unrelated to the reported symptom
- Do not expand into refactoring or cleanup
- Do not run $review or $audit unless the user explicitly asks

## Execution Rules

- Proceed with best-effort investigation on any symptom. Ask for clarification only if no code location can be identified after exhausting `Grep` and `Glob`.
- Do not pause between investigation and fix
- Do not reread unchanged files
- Do not summarize what you did beyond the output format above

## Style

- Direct
- Symptom-driven
- Minimal fix, maximum confidence
- No scope creep

## Response format

Start every response with the `## Bug` heading (plain, not in a code block). Render output directly beneath it.

---
name: refactor
description: Use when the user explicitly asks to restructure, rename, extract, or simplify existing code without changing its behavior. Not for bug fixes or new features.
---

# Refactor

Restructure existing code to improve clarity, reduce duplication, or simplify structure — without changing observable behavior.

## Workflow

If a scoped context is not active:
- STOP
- run $context first

1. Read `AGENTS.md` first. If absent, skip and proceed from the scoped path only.
2. Identify the refactor target from the user's request text only. Do not read source files before the planning phase.

## Method

- Use `Grep` to locate all call sites, usages, or references before renaming or moving anything.
- Use `Read` only on the files directly named in the refactor target.
- Read at most 2–3 files. Do not traverse further.
- Do not read files not implicated by the stated refactor.

## Scope Gate

This skill is strictly structural. Do not:
- Fix bugs encountered during refactoring
- Add new behavior or features
- Expand cleanup beyond the stated target
- Rename or reorganize anything outside the requested scope

If a bug or missing feature is encountered:
- ignore it during refactoring
- do not fix it
- after completion, surface it as a single line: `Note: unrelated issue found in <file> — not addressed.`

## Planning Phase (MANDATORY)

Return a short plan BEFORE making changes. Do NOT write code in this phase.

### Target
- What is being restructured (1–2 bullets)

### Behavior Preservation
- How existing behavior will be confirmed unchanged (tests, call-site check, reasoning)

### Touchpoints
- Files to change

After outputting the plan, wait for user confirmation before proceeding to Implementation Phase.

## Implementation Phase

- Apply the smallest structural change that achieves the stated goal
- Prefer diffs over full file output; show only changed lines
- Do not reformat code outside the touched area
- Do not rename beyond what is requested

## Behavior Preservation

After changes, confirm inline by reasoning over already-read code:
- Existing call sites still satisfied
- No logic altered — only structure
- Check for tests only via `Grep` on the refactored symbol name in test files. Do not browse test directories.
- If tests exist, state that they should pass unchanged. If none found, flag it.
- Do not run a full audit unless explicitly asked

## Output

Use this shape:

````markdown
## Refactor

### Target
- what is being restructured

### Behavior Preservation
- how behavior will be confirmed unchanged

### Touchpoints
- files to change

---

### Changes
{diff or targeted edit — no unchanged content}

### Preservation Check
- call sites satisfied
- no logic altered
- test coverage note if missing
````

## Execution Rules

- Do not ask for confirmation once execution has started
- Do not reread unchanged files
- Do not search for additional improvements
- Do not refactor beyond what was requested
- Optimize for low LOC delta and readability

## Style

- Direct
- Structural, not behavioral
- Minimal output
- No scope creep

## Response format

Start every response with the `## Refactor` heading (plain, not in a code block). Render output directly beneath it.

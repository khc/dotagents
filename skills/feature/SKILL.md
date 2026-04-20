---
name: feature
description: Deliver a new feature or substantial behavior extension with a structured plan → implement workflow. Trigger with "add a feature", "implement X", or "build Y".
---

Deliver features in a controlled, minimal, and modular way.

## Workflow

If a scoped context is not active:
- STOP
- run $switch first

1. Read `AGENTS.md` first.
2. If missing, inspect only:
   - `pyproject.toml` or `package.json` (deps and tooling)
   - top-level directory listing (structure)
   - one representative source file (conventions)
   - Do not crawl the full repo.
3. Define minimal viable scope:
   - user-facing behavior
   - touched files/modules
   - edge cases (only if obvious)
   - tests/config/migrations if required

## Method

- Use `Glob` for repo structure exploration
- Use `Grep` for symbol, function, or dependency lookup
- Use `Read` only for files identified as direct touchpoints
- Never read full directories or accumulate broad file contents into context

## Research Gate

Before implementation, check whether the task may benefit from replacing bespoke code with:
- standard library support
- framework-native utilities
- dependencies already present in the project
- a well-established external library

Do not assume triviality without explicitly checking the criteria above.

If the library or built-in choice is non-trivial:
- STOP
- run $research
- do not proceed to Planning Phase

If the choice is trivial:
- proceed to Planning Phase

Treat the choice as non-trivial if any of the following are true:
- multiple viable approaches exist
- the task involves parsing, validation, serialization, auth, crypto, HTTP, retries, caching, concurrency, background jobs, file handling, or database access
- the current implementation would require noticeable bespoke logic
- adding a library could materially reduce LOC or risk

If the best path is obvious and already supported by the standard library or existing project utilities:
- proceed without `$research`
- confirm the utility or function exists via a targeted `Grep` or `Read` before referencing it in the plan
- state that decision briefly in the plan

## Planning Phase (MANDATORY)

Return a short plan BEFORE coding.

Do NOT write code in this phase.

After completing the plan:
- transition immediately to Implementation Phase
- do not wait for confirmation

### Scope
- What will be built (1–3 bullets)

### Touchpoints
- Files/modules to change or add

### Approach
- Standard library / existing project / external library / bespoke

### Library Decision (if relevant)
- Option A (name + 1-line reason)
- Option B (optional)
- Final choice + why

## Implementation Phase

Proceed immediately after the plan unless the user explicitly requested planning only.

Do not repeat the plan.

- Implement minimal working solution
- Reuse existing abstractions
- No overengineering
- Keep functions small and explicit
- Side effects at boundaries

## Execution Rules

- Do not ask for confirmation
- Do not pause after planning
- Do not restate the plan
- Do not reread unchanged files unless necessary
- Do not explore outside the scoped context

## Code Output Rules

- Return:
  - plan
  - followed by code or diff/patch
- Do not add explanations beyond the plan
- Prefer diffs over full file output; split large implementations across multiple edits

## Testing

- Add/update minimal tests if applicable
- Prefer existing test patterns

## Constraints

- Do not expand scope
- Do not introduce new abstractions unless necessary
- Do not add libraries unless justified in plan
- Avoid duplication

## Style

- Direct and minimal
- Idiomatic to the repo
- Optimize for readability and changeability

## Output

Use this shape:

````markdown
## Feature

### Scope
- what will be built

### Touchpoints
- files/modules to change or add

### Approach
standard library / existing project / external library / bespoke

---

{implementation — diff or edit follows}
````

## Response format

Start every response with the `## Feature` heading (plain, not in a code block). Render output directly beneath it.

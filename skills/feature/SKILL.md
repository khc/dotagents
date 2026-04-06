---
name: feature
description: Use when the user explicitly asks to add a new feature or a substantial behavior extension and wants a structured feature-delivery workflow that requires $research first when the library or built-in choice is non-trivial.
---

# Feature

Deliver features in a controlled, minimal, and modular way. Do not jump to implementation before planning is complete.

## Workflow

If a scoped context is not active:
- STOP
- run $switch first

1. Read `AGENTS.md` first.
2. If missing, inspect repo structure, conventions, and dependencies.
3. Define minimal viable scope:
   - user-facing behavior
   - touched files/modules
   - edge cases (only if obvious)
   - tests/config/migrations if required

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

If the best path is obvious and already supported by the standard library or existing project utilities, proceed without `$research`, but state that decision briefly in the plan.

## Planning Phase (MANDATORY)

Return a short plan BEFORE coding:

Do NOT write code in this phase.

After completing the plan:
- transition to Implementation Phase

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

Do NOT write code in this phase.

## Implementation Phase

Proceed to implementation immediately after the plan unless the user explicitly requested planning only.

Do not repeat the plan.

- Implement minimal working solution
- Reuse existing abstractions
- No overengineering
- Keep functions small and explicit
- Side effects at boundaries

## Code Output Rules

- Return only:
  - code OR
  - diff/patch
- No explanations
- Max ~150 lines unless required

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

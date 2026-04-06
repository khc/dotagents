## Global Agent Policy

- Only one skill may be active at a time
- Do not chain skills unless explicitly instructed
- Always activate $switch before any repo work
- Do not proceed without confirmed scope
- Follow the active skill strictly; do not mix behaviors

## Execution Discipline

- Do not explain internal reasoning
- Do not ask for confirmation when the next action is obvious from the active skill
- Do not reread unchanged files unless a write failed or new context is required
- Do not verify trivial edits with extra reads unless the user asked for validation
- Prefer direct execution over discussion when scope is already confirmed

## Coding Principles

- Prefer simple solutions (KISS)
- Avoid duplication (DRY)
- Keep functions small and focused
- Write readable, idiomatic code for the language
- Reuse existing project utilities and patterns
- Prefer existing project utilities and dependencies over adding new ones
- Avoid unnecessary abstractions
- Keep side effects at boundaries
- Prefer explicit behavior over implicit or hidden logic
- Prefer the smallest correct implementation and minimal output
- Optimize for readability first, then performance if needed

## Design Principles (Light SOLID)

- Keep functions and modules focused on a single responsibility
- Prefer extending behavior via composition rather than modifying existing code
- Ensure components can be replaced without breaking callers
- Keep interfaces and APIs small and focused
- Avoid hardcoding external dependencies; pass them explicitly

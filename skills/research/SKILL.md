---
name: research
description: Use when the user wants targeted implementation research before coding, especially to find simpler approaches, reduce LOC, improve correctness, or identify standard/library support that should replace bespoke code.
---

# Research

Use this skill to research the smallest solid way to implement a task before writing code.

## Goal

Find the leanest dependable approach with emphasis on:
- lower LOC
- less bespoke code
- existing standard/library support
- better correctness, maintainability, performance, or security

## Workflow

If a scoped context is not active:
- STOP
- run $switch first

1. Read `AGENTS.md` first. If absent, skip and proceed from the scoped path only.
2. If a scoped path is active, obey that scope and nearest applicable `AGENTS.md`.
3. Read only the minimum relevant context:
   - target files or path
   - at most 2–3 directly related files; use `Grep` to locate existing utilities rather than reading entire modules
   - dependency manifests (`pyproject.toml`, `package.json`, etc.) only when the task involves library or dependency selection
   - existing utilities/helpers already used in the same area
4. Define the concrete problem to solve in 1-3 bullets.
5. Check options in this order:
   - standard library
   - framework-native utilities
   - dependencies already in the project
   - 1-2 well-established external libraries, only if materially better
   
   **For external libraries**: if no external libraries are already known to fit, run a web search to vet candidates. First run `~/.agents/.venv/bin/python ~/.agents/skills/research/scripts/today.py` to get the current date, then include it in search queries to ensure documentation and activity data are recent. Evaluate based on: current maintenance status, documentation quality, adoption/community size, fit with current stack. Do not evaluate libraries without checking recent data.
6. Compare options using these criteria (weight them by task priority):
   - LOC reduction (higher weight if code size is a constraint)
   - fit with current stack (highest weight if integration burden is high)
   - maintenance burden (higher weight for long-lived projects)
   - correctness and edge-case coverage (highest weight for security/stability-critical tasks)
   - performance/security impact (higher weight if task involves those domains)
   When criteria conflict (e.g., LOC vs. correctness), prioritize the criterion most relevant to the stated problem.
7. Recommend one path explicitly with a confidence signal:
   - **clear winner** — one option dominates across most criteria
   - **reasonable choice** — best option within constraints, but tradeoffs exist
   - **close call** — multiple options are similar; recommendation based on tiebreaker criterion
   - built-in / existing dependency / external library / bespoke
8. Check: is research sufficient?
   - If you have evaluated 2–3 realistic options and weighed the key tradeoffs: research is sufficient, proceed to output
   - If you are uncertain or key information is missing: note it explicitly in Implementation Notes or Caveats; do not continue researching
   - Do not research beyond this point without explicit user request
9. Do not implement unless the user explicitly asks.

## Guardrails

- Research only what is needed for the stated task.
- Do not rewrite architecture.
- Do not propose new libraries without clear benefit.
- Prefer existing project support over adding dependencies.
- Prefer standard library over external packages when it is good enough.
- Avoid vague “could use a library” suggestions.
- Name the exact module, class, utility, or 1-2 libraries that fit.

## Output

Use this shape:

````markdown
## Research

### Problem
- bullet

### Current Fit
- existing support or bespoke risk

### Options
| Option | Type | Pros | Cons | LOC Impact |
|--------|------|------|------|------------|

### Recommendation
**[confidence: clear winner / reasonable choice / close call]** — chosen path and why

### Implementation Notes
- touched areas, caveats, uncertainty
````

- List at most 3 options; for each: name, type (standard / existing dependency / external / bespoke), pros (what it gains), cons (what it loses), LOC impact.
- Confidence signal required: clear winner / reasonable choice / close call.
- Omit Options table if there is only one viable path; state why directly in Recommendation.

## Style

- Direct and concise
- Recommendation-first
- No coding unless asked
- No overthinking
- No scope creep

## Response format

Start every response with the `## Research` heading (plain, not in a code block). Render output directly beneath it.

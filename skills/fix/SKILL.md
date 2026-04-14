---
name: fix
description: Use after a completed review when the user wants specific findings fixed with minimal scope, minimal code, and no re-analysis beyond what is required to implement the chosen fixes safely.
---

# Fix

Use this skill to implement fixes for existing review findings in a controlled, low-token way.

## Fast Path

If the fix touches a single file and requires ≤5 lines changed:

- skip planning
- return minimal patch directly
- do not add tests unless explicitly required
- do not include explanations

## Preconditions

- Run only after a review exists.
- Treat the review findings as the source of truth.
- Fix only the findings the user asked to address.
- Do not re-review the whole target or expand into unrelated cleanup.
- Accept explicit finding IDs or references when provided and limit fixes strictly to them.

If the user runs `/fix` immediately after a review and does not specify finding IDs:
- treat it as "fix all findings from the latest review"
- do not ask for clarification

## Workflow

If a scoped context is not active:
- STOP
- run $switch first

1. Read `AGENTS.md` first. If absent, skip and proceed from the scoped path only.
2. If a scoped path is active, obey the active scope and nearest applicable `AGENTS.md`.
3. Read only:
   - the specific files named in the review findings, not the full target tree
   - at most one directly called or imported file from the fix site if required for safety
   - existing tests for the touched area
4. Start from the review findings, not from fresh exploration.
5. For each requested fix:
   - identify the smallest safe code change
   - prefer existing project utilities and patterns
   - prefer standard library or existing dependencies before bespoke code
6. If a finding suggested replacing bespoke code with built-in or library support:
   - use existing project support first
   - otherwise use the standard library if it fits
   - only introduce a new library if the user asked for it or the review already established it as the better fit
7. Implement the narrowest fix set first, then update tests.
8. Validate only what is needed for the changed area.

## Fix Scope Gate

Do not introduce new findings.

If an issue is encountered that is not part of the provided review:
- ignore it
- do not fix it
- do not mention it unless it blocks the requested fix

## Execution Rules

- Do not ask for clarification if the intent can be reasonably inferred from the latest review or command
- Do not pause or ask questions once execution has started unless blocked
- Do not re-analyze architecture unless required for the fix
- Do not search for additional issues unless the user asks
- Do not refactor beyond what the fix requires
- Do not rename, move, or reorganize code unless necessary for correctness
- Do not re-run review or re-evaluate severity of findings
- Keep edits local and reversible
- Optimize for low LOC and clarity

## Required Output Before Coding

If NOT using Fast Path:

Return a short execution plan:

### Fix Scope
- Findings being fixed
- Files to change
- Tests to update

### Approach
- built-in / existing project utility / existing dependency / minimal bespoke

Keep this to 3–6 bullets total.
Do not include broad analysis.

## Code Output Rules

After the plan (or immediately for Fast Path):

- return:
  - plan
  - followed by code or diff/patch
- no chain-of-thought
- do not add explanations beyond the plan
- no alternative designs
- no extra improvements
- keep output as small as practical

## Testing

- Add or update minimal tests for the fixed behavior
- Prefer existing test style and helpers
- Do not add broad new test infrastructure

## Failure Mode

If a requested fix cannot be done safely within current scope:

- state the blocker in 1–2 sentences
- name the exact extra file or dependency context required
- stop there

## Style

- Direct
- Minimal
- Review-driven
- No overthinking
- No scope creep

---
name: plan
description: Use when a repo change needs planning before implementation -- multiple independently testable tasks, coordinated interfaces, material risk, migrations, or security-sensitive design. Break requirements into the smallest executable, testable tasks with exact files/interfaces/verification, then hand off to `$implement` without modifying code. For one coherent bounded change, use `$feature` instead.
---

# Plan

Use this skill to decide whether a repo change needs an implementation plan and, when it does, produce the smallest repo-grounded plan that an implementation agent can execute without rediscovering the design.

Planning is read-only. Do not modify source files, tests, configuration, generated artifacts, Git state, or branch state.

## Goal

Produce an executable implementation contract with:

- the smallest correct scope
- explicit requirements and acceptance criteria
- exact files/areas likely to change
- clear task boundaries and dependencies
- targeted test and verification strategy
- enough technical context for `$implement` to execute without broad re-analysis

Optimize for low scope, low token usage, and low rework — not for the shortest possible plan.

## Workflow Gate

If a scoped context is not active:

- STOP
- run `$context` first
- after `$context` completes, confirm the active scope path, then continue
- do not infer scope from the requested target alone

Use the repo instructions already loaded by `$context`. Read an additional nearest applicable `AGENTS.md` only if it is inside `scope_boundaries.allowed`, applies to required planning evidence, and was not already loaded. If no applicable project instructions are available, proceed using the active scoped path only.

## Route Before Planning

Classify the requested work before deep exploration.

### Direct routes

Do not create an implementation plan when the request is already one of these:

- code/file/change review → `$review`
- applying existing review findings → `$fix`
- research-only question → `$research`

Return the minimal route and stop.

### Implementation routes

Choose between:

- **Feature path** — use `$feature` for a bounded change whose implementation can be safely understood and completed as one coherent unit; successful implementation then hands off to `$review`, with `$fix → $review` only if findings exist.
- **Planned path** — use `$plan → $implement` when the change contains multiple independently testable tasks, coordinated interfaces, material contract/migration/security/architectural risk, or otherwise benefits from explicit decomposition; successful implementation then hands off to `$review`, with `$fix → $review` only if findings exist.

If the user explicitly asks for a plan, create one even if the task appears bounded.

If uncertainty about implementation risk can be resolved by a small amount of scoped inspection, inspect before choosing between Feature and Planned paths. Do not guess from filenames or task wording alone.

## Planning Exploration

For a Planned path, inspect only enough repo context to produce an executable plan.

Read, in this order:

1. user-supplied requirements, task text, spec, acceptance criteria, or issue description
2. `AGENTS.md` and scoped project guidance
3. target files/directories and their structure
4. existing tests for the affected behavior
5. directly relevant callers, callees, interfaces, schemas, or configuration
6. recent Git history for affected files only when it materially informs compatibility, intent, or avoided regressions

Stay within the active context's `scope_boundaries.allowed`.

Do not explore unrelated modules "for completeness."

If required planning evidence lies outside the active scope, stop and request the exact scope expansion before reading it.

## Planning Rules

1. **Ground the plan in inspected code.**
   - Do not invent file paths, symbols, APIs, test commands, or dependencies.
   - Mark a file as `Create` only when the plan actually requires a new file.
   - Cite existing symbols exactly as they appear.

2. **Separate requirements from implementation choices.**
   - Requirements/acceptance criteria describe what must be true.
   - The plan describes how the scoped repo should achieve it.
   - If a requirement is ambiguous enough to change implementation materially, stop and surface that ambiguity rather than silently choosing.

3. **Use the smallest independently testable task as the decomposition unit.**
   - Each task should produce a coherent change that can be implemented and verified independently.
   - Split tasks when one could reasonably be accepted/rejected without the other.
   - Fold scaffolding, small config edits, and documentation into the task that needs them instead of creating ceremony-only tasks.
   - Avoid micro-steps such as separate tasks for "open file", "edit line", or "run formatter."

4. **Preserve interfaces between tasks.**
   - When one task produces an API, type, schema, config key, or behavior consumed by another task, name that contract explicitly.
   - Keep names/signatures consistent across the entire plan.
   - Do not leave placeholders such as `TBD`, `TODO`, "appropriate validation", or "add tests."

5. **Plan tests around behavior.**
   - Identify the minimal regression/behavior tests required for each task.
   - Reuse existing test style, helpers, fixtures, and commands.
   - For changed runtime behavior, plan RED → implementation → GREEN when practical.
   - Do not invent verification commands. Use commands defined by `AGENTS.md` or already-established project tooling.

6. **Plan production-readiness work only when applicable.**
   - Include compatibility, migration, rollout/rollback, documentation, observability, or security work only when the change actually touches those contracts.
   - Do not add generic "best practice" work unrelated to the requested outcome.

7. **Do not implement during planning.**
   - No source edits.
   - No test edits.
   - No generated scaffolding.
   - No commits.
   - Read-only commands and test discovery are allowed; running tests is allowed only when needed to establish existing behavior or baseline and permitted by project guidance.

8. **Do not perform the later lifecycle stages.**
   - Do not invoke `$implement`, `$feature`, `$review`, or `$fix` from inside planning.
   - The plan ends with the next-step handoff.

## Plan Self-Review

Before returning the plan, check it yourself:

1. **Requirement coverage** — every supplied requirement or acceptance criterion maps to at least one task.
2. **Scope discipline** — every planned file/change is necessary for the requested outcome.
3. **Executability** — each task has enough repo-grounded detail for `$implement` to act without broad exploration.
4. **Testability** — each behavioral task has a concrete verification path.
5. **Interface consistency** — names, signatures, schemas, config keys, and task dependencies agree across tasks.
6. **Placeholder scan** — no vague "handle errors", "add tests", "refactor as needed", `TBD`, or equivalent placeholders.
7. **Ordering** — task dependencies are explicit and tasks are ordered so each prerequisite exists before it is consumed.

Fix plan defects inline before returning it. Do not dispatch a separate reviewer.

## Output

### Direct / Feature Route

Use this compact shape when a full plan is unnecessary:

```markdown
## Plan

### Route
`$feature → $review → [$fix → $review]*`
or
`$review`
or
`$fix`
or
`$research`

### Scope
- Target: ...
- Outcome: ...

### Reason
...

### Next Step
...
```

### Planned Route

Use this shape:

```markdown
## Plan

### Goal
...

### Requirements
- ...

### Scope
- Target: ...
- In scope: ...
- Out of scope: ...

### Approach
2–5 concise bullets describing the chosen implementation approach and important constraints.

### Tasks

#### 1. <independently testable task>
- Files:
  - Modify: `path`
  - Create: `path`       # only when required
  - Test: `path`
- Requirements: ...
- Implementation: concrete repo-grounded change, naming relevant symbols/interfaces
- Interfaces / dependencies: ...
- Verification: exact targeted test/check or established project command
- Done when: observable acceptance condition

#### 2. ...
...

### Risks / Stop Conditions
- only material risks, ambiguities, migrations, compatibility concerns, or conditions requiring re-planning

### Handoff
`$implement` — execute these tasks in order, preserving scope and acceptance criteria.
```

Omit empty optional fields rather than filling them with generic text.

## Plan Identity

When the runtime/workflow supports persistence, assign or retain a stable plan identifier so `$implement` and later `$review` can refer to the exact plan that governed the implementation.

The handoff should preserve:

- goal and requirements
- ordered tasks and task IDs
- scoped files/areas
- interfaces/dependencies
- verification and Done When conditions
- material assumptions and stop conditions

Do not require persistence for same-session execution; the complete current-session plan is sufficient when it can be passed intact.

## Handoff Contract

The plan is the implementation contract for `$implement`.

`$implement` may inspect the files named by a task and the minimal adjacent context needed to execute it, but should not redesign the plan silently.

If implementation discovers that:

- a required file/interface differs materially from the plan
- a task cannot be completed inside the planned scope
- an assumption or acceptance criterion is false
- a migration, security, compatibility, or architectural issue materially changes the approach

then implementation should stop and return the blocker for re-planning rather than silently expanding scope.

After `$implement`, acceptance belongs to `$review`, not to `$implement`.

## Style

- Direct
- Repo-grounded
- Minimal but executable
- No implementation
- No speculative file lists
- No scope creep
- No ceremony-only tasks

## Response format

Start every response with the `## Plan` heading (plain, not in a code block). Render output directly beneath it.

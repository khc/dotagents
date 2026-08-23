---
name: implement
description: Use when a completed implementation plan already exists and the user wants it executed faithfully. Implement tasks in dependency order with minimal scope, targeted tests, and fresh verification -- without redesigning the plan, reviewing independently, or absorbing unrelated work. If no plan exists, route to `$plan`; use `$feature` for bounded work needing no prior plan.
---

# Implement

Use this skill to execute an existing repo-grounded implementation plan.

`implement` is a plan executor, not a planner, feature designer, reviewer, or general bug-fixer.

## Goal

Execute the approved plan with:

- faithful requirement and task coverage
- minimal scope
- preserved interfaces between tasks
- behavior-focused tests where planned or required
- fresh verification for each completed task
- explicit stop/re-plan behavior when the plan proves materially wrong

Final acceptance belongs to `$review`, not to `$implement`.

## Preconditions

A completed implementation plan must already exist in the current workflow or be explicitly supplied by the user.

The plan must contain enough information to execute safely, including:

- goal or expected outcome
- scoped target
- one or more concrete implementation tasks
- relevant files/areas
- requirements or acceptance conditions
- task ordering/dependencies when applicable
- verification path for behavioral work

If no executable plan exists:

- STOP
- report `Error: no implementation plan found. Run $plan first.`
- do not silently convert the request into `$feature`

If the user explicitly asks to bypass planning for a bounded change, `$feature` is the appropriate skill instead.

## Workflow Gate

If an active scope is not established:

- STOP
- run `$scope` first
- after `$scope` completes, confirm the active scope path, then continue
- do not infer scope from the plan's paths alone

Use the repo instructions already loaded by `$scope`. Read an additional nearest applicable `AGENTS.md` only if it is inside `scope_boundaries.allowed`, applies to a required planned touchpoint, and was not already loaded. If no applicable project instructions are available, proceed using the active scoped path and the plan.

The active scope boundary is authoritative. A plan does not grant permission to read or modify paths outside `scope_boundaries.allowed`.

If the plan requires an out-of-scope file:

- STOP before reading or editing it
- name the exact path and why the plan requires it
- return for scope expansion / re-planning

## Plan Intake

Before editing:

1. Read the complete plan.
2. Extract:
   - goal
   - requirements / acceptance criteria
   - in-scope and out-of-scope boundaries
   - ordered tasks
   - files for each task
   - interfaces/dependencies between tasks
   - verification commands or expected checks
   - stop/re-plan conditions
3. Check the plan for execution blockers only:
   - referenced existing file or symbol is absent
   - task dependency is impossible in the stated order
   - required interface conflicts with inspected code
   - verification command is unavailable under project guidance
   - task requires leaving active scope
   - a stated assumption is materially false
4. Do not re-review design choices merely because another implementation is possible.

If a blocker materially changes scope, interfaces, acceptance criteria, security posture, migration strategy, or task decomposition:

- STOP before implementation of the affected task
- report the exact mismatch
- return to `$plan`

Do not silently redesign.

## Change Boundary

Before the first implementation edit, capture enough read-only Git state for `$review` to identify the implementation delta:

- `BASE_SHA` — current `HEAD` before implementation edits, when available
- pre-existing dirty paths within active scope
- the plan identifier/reference when one exists

Do not require a clean working tree and do not modify Git state.

At completion, preserve for review:

- plan reference / exact governing plan
- `BASE_SHA`
- current `HEAD` when available
- actual touched files
- pre-existing changes that overlap touched files
- scoped diff/change boundary
- task-level and aggregate fresh verification evidence

If pre-existing edits overlap the same lines and the implementation delta cannot be distinguished reliably, report that as a review-evidence limitation.

## Execution Model

Execute tasks in plan order unless the plan explicitly marks tasks as independent and reorderable.

For each task:

1. **Load task context**
   - read only the planned files for that task
   - read existing tests for the touched behavior
   - inspect the minimum directly relevant callers/callees/interfaces needed to implement safely
   - remain within active scope

2. **Confirm task preconditions**
   - planned symbols/interfaces still exist as expected
   - prerequisites from earlier tasks are present
   - the task's acceptance condition remains achievable without changing the plan

3. **Establish regression evidence when applicable**
   - for changed testable runtime behavior, add or update the smallest behavior/regression test before production code when practical
   - verify RED against the pre-change behavior when safe and meaningful
   - do not create destructive/out-of-scope state merely to force RED
   - if the plan explicitly says no test is needed for a non-behavioral task, do not add one gratuitously

4. **Implement the smallest safe change**
   - follow the plan's stated approach and interfaces
   - prefer existing project utilities, stdlib, framework-native support, then existing dependencies
   - do not introduce new dependencies unless the plan explicitly calls for them
   - do not refactor unrelated code
   - do not rename/move/reorganize files unless the plan requires it
   - preserve compatibility/migration constraints stated in the plan

5. **Verify the task**
   - re-read changed lines
   - run the task's targeted verification
   - run applicable test/lint/static-check commands required by `AGENTS.md`
   - inspect fresh output before claiming success
   - never infer success from test existence or a previous run

6. **Record task completion**
   - requirement/acceptance criteria satisfied
   - files changed
   - tests/checks run
   - fresh result
   - any material deviation: none, or STOP for re-planning

Continue to the next task only after the current task has fresh passing verification or is explicitly non-executable for a documented reason.

## Plan Fidelity

The plan is the implementation contract.

### Allowed implementation discretion

You may make local choices that do not materially change the plan, such as:

- exact variable names for new local variables
- equivalent idiomatic syntax
- use of an already-established local helper
- formatting required by project tooling
- minor test-fixture details
- small implementation details necessary to realize the specified interface

### Requires re-planning

STOP and return to `$plan` if execution would require any of the following:

- adding/removing a planned task
- changing a requirement or acceptance criterion
- materially changing the planned architecture or data flow
- changing a public API, schema, config contract, migration strategy, or compatibility behavior not anticipated by the plan
- touching materially different files/modules than the plan identified
- introducing a new external dependency not planned
- broadening security-sensitive scope
- replacing the planned fix/approach with a materially different one
- discovering that a core plan assumption is false

Do not use "implementation necessity" as justification for silent scope expansion.

## Task Failure / Retry

If a task implementation or verification fails:

1. inspect the failure evidence narrowly
2. determine whether the failure is:
   - a local implementation mistake within the existing plan, or
   - evidence that the plan is materially wrong/incomplete
3. for a local implementation mistake:
   - revert only the failed speculative edit when needed
   - make one evidence-driven correction within the same task and plan
   - verify again
4. if the second attempt fails, or correction requires changing the plan:
   - stop
   - preserve already-completed verified tasks
   - report the blocker
   - return to `$plan`

Never stack speculative fixes.

Do not invoke `$fix`: `$fix` is for findings produced by `$review`, not for implementation mistakes discovered while executing a plan.

## Tests and Verification

Tests are part of implementation evidence, not final review.

- Behavioral changes: prefer RED → implementation → GREEN where practical.
- Non-behavioral changes: use the smallest applicable verification; do not add tests for ceremony.
- Use existing test style, helpers, and fixtures.
- Use verification commands from the plan and the project instructions established by `$scope`.
- Do not guess alternative project commands if none are documented.
- If a required verification command cannot be run, report the gap and do not claim the affected task succeeded.
- A passing targeted test does not authorize unrelated changes.

Before declaring the implementation complete, run the plan-level verification required by the plan/`AGENTS.md` for the aggregate change when such a command exists.

A successful implementation claim requires fresh evidence from the current working tree.

## Scope Gate

Do not absorb unrelated issues encountered while implementing.

If you discover code that is:

- buggy
- insecure
- duplicated
- poorly designed
- undocumented
- otherwise improvable

but it is not required by the plan:

- do not fix it
- do not turn it into a new task
- do not expand scope
- mention it only if it blocks the planned implementation

Independent issue discovery and acceptance belong to `$review`.

## Review / Implement Ownership

Maintain a strict lifecycle boundary:

- `$plan` owns decomposition, intended approach, task scope, interfaces, and acceptance criteria
- `$implement` owns faithful execution, regression protection, and implementation verification
- `$review` owns independent correctness judgment, findings, severity/confidence, and acceptance/verdict
- `$fix` owns remediation of review findings

`$implement` must not:

- mark the overall change `ready`
- close review findings
- perform an independent production-readiness review
- re-rank or reinterpret requirements
- invoke `$review` or `$fix` internally

After implementation completes, hand off to `$review`.

## Output

Use this shape:

```markdown
## Implement

### Plan
- Goal: ...
- Tasks: N
- Scope: ...

### Completed

#### 1. <task>
- Files: ...
- Verification: `<command>` — pass/fail summary
- Acceptance: satisfied

#### 2. ...

### Change Boundary
- Plan: ...
- BASE_SHA: ...
- HEAD_SHA: ...
- Touched files: ...
- Pre-existing overlap: none / ...

### Deviations
- None
```

If execution stops for re-planning:

```markdown
## Implement

### Completed
- ...

### Blocked
- Task: ...
- Mismatch: ...
- Required re-plan: ...

### Next Step
`$plan`
```

If all planned tasks are implemented and freshly verified:

```markdown
### Handoff
`$review` — review the completed implementation against the exact governing plan and the captured change boundary, using touched files and fresh verification evidence.
```

Keep completion reporting concise. Do not repeat the full plan.

## Style

- Direct
- Plan-driven
- Minimal
- Evidence-backed
- No redesign
- No scope creep
- No unrelated cleanup
- No self-review disguised as implementation

## Response format

Start every response with the `## Implement` heading (plain, not in a code block). Render output directly beneath it.

# Feature Workflow Orchestration

## Flow

`scope → feature → review → [fix → review]*`

If feature returns needs_plan, transition to:

plan → AWAITING_PLAN_APPROVAL → implement → review → [fix → review]*

See `workflows/planned.md` for the Plan Approval Gate mechanics; a successful
plan never auto-transitions to `$dot:implement`.

## Handoffs

### scope → feature
Pass active scope + user request.

### feature → review
Pass `implementation-handoff.json` containing:
- acceptance criteria
- touched files
- base/head state
- pre-existing overlap
- scoped diff/change boundary
- fresh verification

### review → fix
Pass `review-handoff.json`.

### fix → review
Pass:
- original `review-handoff.json`
- latest `fix-handoff.json`
- same review mode/target

## Completion

Only `review.status = ready` completes the workflow.


## Review transition invariant

Only exact review verdict `ready` with zero findings may complete the workflow.
`ready-with-fixes` and `not-ready` with findings always transition to `$dot:fix`.

# Refactor Workflow Orchestration

## Flow

`context → refactor → review → [fix → review]*`

Bounded structural change only. If `$refactor` reports `blocked` because its
Complexity Gate fails, STOP and report that the change requires `$plan`; do
not auto-transition into the Planned Workflow.

## Handoffs

### context → refactor
Pass active scope + user request.

### refactor → review
Pass `implementation-handoff.json` containing:
- behavior invariants
- touchpoints
- base/head state
- pre-existing overlap
- scoped diff/change boundary
- fresh preservation verification (baseline + post-refactor)

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
`ready-with-fixes` and `not-ready` with findings always transition to `$fix`.

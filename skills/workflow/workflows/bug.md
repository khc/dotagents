# Bug Workflow Orchestration

## Flow

`context → bug → review → [fix → review]*`

Bounded symptom-driven diagnosis and fix only. If `$bug` reports `blocked`,
STOP and report the required next step; do not auto-transition into another
workflow. Possible reasons and their required next step:

- Complexity Gate fails (multi-cause, coordinated, or architecture-level
  remediation) → `$plan`
- no concrete symptom exists (this is a "find issues" request, not a bug) → `$review`
- the issue is already a structured `$review` finding with `fix_direction` → `$fix`

## Handoffs

### context → bug
Pass active scope + user-reported symptom (error, stack trace, failing test,
bad output, or reproduction steps).

### bug → review
Pass `implementation-handoff.json` containing:
- root cause (confirmed/likely, what fails, why, what must be preserved)
- touchpoints
- base/head state
- pre-existing overlap
- scoped diff/change boundary
- fresh reproduction/fix verification (RED baseline + GREEN post-fix)

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

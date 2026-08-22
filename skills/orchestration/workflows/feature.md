# Feature Workflow Orchestration

## Flow

`context → feature → review → [fix → review]*`

If feature returns `needs_plan`, transition to:

`plan → implement → review → [fix → review]*`

## Handoffs

### context → feature
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

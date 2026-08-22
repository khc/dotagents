# Standalone Review Workflow Orchestration

## Flow

`context → review → [fix → review]*`

## Review modes

- symbol
- path
- change

The original mode and target must be preserved through every fix/re-review cycle.

## Handoffs

### context → review
Pass:
- active scope
- explicit target
- optional target symbol
- requirements/change range only when explicitly available

### review → fix
Pass `review-handoff.json`.

### fix → review
Pass:
- original review mode/target
- prior review artifact
- latest fix artifact

## Completion

Only `review.status = ready` completes the workflow.

For symbol/path reviews, `ready` applies only to the reviewed scope.

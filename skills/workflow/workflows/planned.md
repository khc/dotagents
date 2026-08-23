# Planned Workflow Orchestration

## Flow

`scope → plan → implement → review → [fix → review]*`

## Handoffs

### scope → plan
Pass active scope + user requirements/specification.

### plan → implement
Pass exact `plan-handoff.json`.

### implement → review
Pass:
- exact `plan-handoff.json`
- `implementation-handoff.json`

### review → fix
Pass `review-handoff.json`.

### fix → review
Pass:
- governing `plan-handoff.json`
- prior `review-handoff.json`
- latest `fix-handoff.json`

## Re-plan

When `implement.status = replan`, start a fresh planner and provide:
- original user requirements
- active scope
- previous plan artifact
- explicit blocker from implement

Do not pass implementer reasoning.

## Completion

Only `review.status = ready` completes the workflow.


## Review transition invariant

Only exact review verdict `ready` with zero findings may complete the workflow.
`ready-with-fixes` and `not-ready` with findings always transition to `$fix`.

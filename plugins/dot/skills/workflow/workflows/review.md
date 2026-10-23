# Standalone Review Workflow Orchestration

## Flow

`scope → review → [fix → review]*`

## Review modes

- symbol
- path
- change

The original mode and target must be preserved through every fix/re-review cycle.

## Handoffs

### scope → review
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
- prior review artifact (its `review_uuid` is the re-review's `prior_review_uuid`)
- latest fix artifact

## Completion

Only `review.status = ready` completes the workflow.

For symbol/path reviews, `ready` applies only to the reviewed scope.


## Verdict to transition mapping

- `ready` + no findings → DONE
- `ready-with-fixes` + findings → FIX
- `not-ready` + findings → FIX
- blocker preventing valid review → STOP

`ready-with-fixes` is non-terminal.

## Ownership

- Coordinator: dispatches one fresh reviewer stage with the selected context (scope, target, mode, requirements or range when explicit, and on re-review the prior review artifact and latest fix artifact), applies the verdict mapping above, and runs the review/fix loop.
- Reviewer (`$dot:review`): runs the review contract, records `subject` and `execution`, may start read-only lens and research agents, merges and judges, and is the only one that saves.
- Implementer (`$dot:fix`): verifies each finding against the current code, fixes it, and reports `finding_id` values; it never closes a finding.
- Re-review: the reviewer sets `prior_review_uuid`, carries every prior `finding_id`, and closes a finding only on evidence it inspected itself.

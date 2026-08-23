# Planned Workflow Orchestration

## Flow

`scope → plan → AWAITING_PLAN_APPROVAL → implement → review → [fix → review]*`

`AWAITING_PLAN_APPROVAL` is not a stage but the gate defined in `SKILL.md`'s Plan Approval Gate.

## Handoffs

### scope → plan
Pass active scope + user requirements/specification.

### plan → AWAITING_PLAN_APPROVAL
Persist `active_plan` (see `SKILL.md`'s Plan Approval Gate). Never dispatch `$implement` from here.

### AWAITING_PLAN_APPROVAL → plan (amendment)
Any message that is not explicit approval or explicit cancellation, per `SKILL.md`'s Plan Approval Gate approval-parsing rule, routes back to `$plan` to reopen `active_plan` as an amendment.

### AWAITING_PLAN_APPROVAL → implement (approval)
Explicit approval, per `SKILL.md`'s Plan Approval Gate approval-parsing rule, flips `active_plan.status` to `approved` and dispatches `$implement` with the exact `plan-handoff.json`.

### AWAITING_PLAN_APPROVAL → STOP (cancel)
Explicit cancellation, per `SKILL.md`'s Plan Approval Gate approval-parsing rule, transitions the workflow to `STOP`. The plan artifact is left as-is (`status` remains `draft`).

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

When `implement.status = replan`, start a fresh planner and reopen the same plan artifact: `active_plan.path`/`plan_id` (never a new `plan_id`). Provide:
- original user requirements
- active scope
- `active_plan.path`/`plan_id`/`revision`
- explicit blocker from implement

Do not pass implementer reasoning.

`$plan` sets `status: draft` and increments `revision` on the same file. The workflow returns to `AWAITING_PLAN_APPROVAL` via the same handoff as any other successful plan result — see `SKILL.md`'s Plan Approval Gate.

## Completion

Only `review.status = ready` completes the workflow.


## Review transition invariant

Only exact review verdict `ready` with zero findings may complete the workflow.
`ready-with-fixes` and `not-ready` with findings always transition to `$fix`.

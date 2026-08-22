# Planned Implementation Workflow

## Purpose

Use this workflow for work that benefits from explicit decomposition:
multiple independently testable tasks, coordinated interfaces, material
architecture or data-flow changes, migrations, contract-sensitive work,
security-sensitive design, or comparable implementation risk.

## Flow

`$context → $plan → $implement → $review → [$fix → $review]*`

The workflow ends only when `$review` returns `ready`, or when execution
stops for scope expansion, requirement clarification, or re-planning.

## Stage Ownership

  -----------------------------------------------------------------------
  Stage                   Owns                    Must not own
  ----------------------- ----------------------- -----------------------
  `$context`              active scope and        planning or
                          applicable repo         implementation
                          instructions            

  `$plan`                 decomposition,          source edits
                          approach, task scope,   
                          interfaces, acceptance  
                          criteria                

  `$implement`            faithful plan           silent redesign,
                          execution, regression   independent acceptance
                          protection, fresh       
                          verification            

  `$review`               independent correctness implementation or
                          judgment and            fixing
                          acceptance/verdict      

  `$fix`                  remediation of review   diagnosis, severity,
                          findings                acceptance
  -----------------------------------------------------------------------

## 1. Context

Activate `$context` on the intended planning/implementation scope.

`scope_boundaries.allowed` remains authoritative throughout the
workflow. A plan does not authorize files outside the active context.

If required planning or implementation evidence lies outside scope, stop
and explicitly reactivate `$context` after expansion is approved.

## 2. Plan

Invoke `$plan` with the requirements, task, specification, issue, or
acceptance criteria.

The planner inspects scoped repo evidence and produces the smallest
independently executable and testable tasks.

Each planned task should identify, as applicable:

-   files to modify/create/test
-   mapped requirements
-   concrete implementation work and relevant symbols/interfaces
-   dependencies on other tasks
-   exact established verification
-   observable Done When condition

The plan self-checks requirement coverage, scope, executability,
testability, interface consistency, placeholders, and ordering.

When supported, retain a stable plan identifier. The complete plan is
the contract passed to `$implement`.

`$plan` does not edit the repo.

## 3. Implement

Invoke `$implement` with the exact governing plan.

Before editing, `$implement` checks only for execution blockers; it does
not redesign merely because another approach is possible.

Before the first edit, capture when available:

-   plan reference
-   pre-edit `BASE_SHA`
-   pre-existing dirty paths in scope

Execute tasks in dependency order. For each task:

1.  load only required task context
2.  confirm task preconditions
3.  establish regression evidence for changed testable behavior when
    practical
4.  make the smallest plan-faithful change
5.  run fresh targeted verification
6.  record task completion

### Re-plan boundary

Stop and return to `$plan` when execution requires a material change to:

-   task decomposition
-   requirements or acceptance criteria
-   architecture/data flow
-   public API/schema/config/CLI contracts
-   migration or compatibility strategy
-   security-sensitive scope
-   planned modules/files
-   external dependencies
-   core plan assumptions

A local implementation mistake may be corrected inside `$implement`; a
materially wrong plan may not.

### Implement handoff to Review

Pass or preserve:

-   exact governing plan / plan identifier
-   `BASE_SHA` and current `HEAD` when available
-   actual touched files
-   pre-existing overlap
-   scoped implementation diff/change boundary
-   task-level and aggregate fresh verification evidence

`$implement` does not declare the implementation ready.

## 4. Review

Invoke `$review` as a Change review.

When both are available, review against:

1.  the exact plan/requirements
2.  the implementation diff/change boundary

This is the strongest review mode: requirements compliance plus diff
integrity, alongside correctness, tests, security, design, performance,
maintainability, production readiness, documentation, observability, and
reuse.

Possible outcomes:

-   `ready` → workflow complete
-   findings → `$fix`
-   evidence/scope blocker → resolve before continuing

## 5. Fix and Re-review

`$fix` remediates only the selected review findings, with fresh local
verification.

After successful fixes, return to `$review`. Preserve the original
Change review and governing plan while including the fix delta.

Repeat:

`$review → $fix → $review`

until `$review` returns `ready`.

If `$fix` disproves a `likely` finding or discovers that the prescribed
remediation materially conflicts with the code, return the diagnosis
mismatch to `$review`; do not redesign the plan inside `$fix`.

## Completion

The workflow is complete only when `$review` returns `ready` for the
implementation against the governing plan and inspected change evidence
within the active scope.

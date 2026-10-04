# Bounded Feature Workflow

## Purpose

Use this workflow for a bounded feature or behavior change that can be
understood, implemented, and verified as one coherent unit without a
separate implementation plan.

## Flow

`$dot:scope → $dot:feature → $dot:review → [$dot:fix → $dot:review]*`

The workflow ends only when `$dot:review` returns `ready`, or when a skill
stops because scope, requirements, or implementation evidence requires
user action or re-planning.

## Stage Ownership

  -----------------------------------------------------------------------
  Stage                   Owns                    Must not own
  ----------------------- ----------------------- -----------------------
  `$dot:scope`            active scope and        implementation
                          applicable repo         decisions
                          instructions            

  `$dot:feature`          bounded discovery,      independent acceptance,
                          inline mini-plan,       broad decomposition
                          implementation,         
                          regression protection,  
                          fresh verification      

  `$dot:review`           independent correctness implementation or
                          judgment, findings,     fixing
                          severity/confidence,    
                          acceptance/verdict      

  `$dot:fix`              narrow remediation of   diagnosis, severity,
                          review findings and     acceptance
                          local verification      
  -----------------------------------------------------------------------

## 1. Scope

Activate `$dot:scope` on the intended repo/file scope before any repo
work.

The resulting `scope_boundaries.allowed` is authoritative for every
later stage. Workflow handoffs inherit it and do not broaden it.

If a later stage needs an out-of-scope path, stop and explicitly
reactivate `$dot:scope` after scope expansion is approved.

## 2. Feature

Invoke `$dot:feature` with the requested bounded behavior change.

`$dot:feature` performs scoped inspection and applies its Complexity Gate.

Continue in `$dot:feature` only when the change remains one coherent
implementation unit. If inspection reveals multiple independently
testable tasks, material architecture/data-flow changes, coordinated
migration/contract work, unresolved security-sensitive design, or
otherwise requires explicit decomposition, stop and route to the Planned
Implementation Workflow.

Before editing, `$dot:feature` captures the change boundary when Git
evidence is available:

-   pre-edit `BASE_SHA`
-   pre-existing dirty paths in scope
-   intended touchpoints

For testable runtime behavior, prefer RED → implementation → GREEN when
practical. Successful completion requires fresh verification evidence.

### Feature handoff to Review

Pass or preserve:

-   Done When / acceptance criteria
-   actual touched files
-   `BASE_SHA` and current `HEAD` when available
-   pre-existing overlap
-   scoped change boundary/diff
-   fresh verification evidence

`$dot:feature` does not declare the change ready.

## 3. Review

Invoke `$dot:review` as a Change review using the feature handoff evidence.

The reviewer independently inspects the implementation. Producer claims
such as "done" or "tests pass" are context, not evidence.

Possible outcomes:

-   `ready` → workflow complete
-   `ready-with-fixes` or `not-ready` with findings → invoke `$dot:fix`
-   blocked by missing/out-of-scope evidence → resolve the stated
    blocker before continuing

## 4. Fix

Invoke `$dot:fix` against the requested review findings.

`$dot:fix` consumes each finding's description, confidence, and
`fix_direction` as the remediation contract.

-   `confirmed` → implement narrowly
-   `likely` → verify only the uncertain premise, then fix or hand the
    mismatch back to `$dot:review`
-   behavioral fix → targeted regression coverage regardless of patch
    size
-   success → fresh verification required

`$dot:fix` never closes findings or declares the change ready.

## 5. Re-review Loop

After a successful fix, invoke `$dot:review` again using the same Change
review target and updated change boundary.

Repeat:

`$dot:review → $dot:fix → $dot:review`

until `$dot:review` returns `ready`.

## Escalation

Switch to `$dot:plan` rather than expanding `$dot:feature` when the
bounded-change assumption becomes materially false.

Do not silently convert review findings into feature work or
implementation blockers into review findings.

## Completion

The workflow is complete only when `$dot:review` returns `ready` for the
reviewed change within the active scope and available change evidence.

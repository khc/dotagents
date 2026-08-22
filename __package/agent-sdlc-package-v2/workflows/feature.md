# Bounded Feature Workflow

## Purpose

Use this workflow for a bounded feature or behavior change that can be
understood, implemented, and verified as one coherent unit without a
separate implementation plan.

## Flow

`$context → $feature → $review → [$fix → $review]*`

The workflow ends only when `$review` returns `ready`, or when a skill
stops because scope, requirements, or implementation evidence requires
user action or re-planning.

## Stage Ownership

  -----------------------------------------------------------------------
  Stage                   Owns                    Must not own
  ----------------------- ----------------------- -----------------------
  `$context`              active scope and        implementation
                          applicable repo         decisions
                          instructions            

  `$feature`              bounded discovery,      independent acceptance,
                          inline mini-plan,       broad decomposition
                          implementation,         
                          regression protection,  
                          fresh verification      

  `$review`               independent correctness implementation or
                          judgment, findings,     fixing
                          severity/confidence,    
                          acceptance/verdict      

  `$fix`                  narrow remediation of   diagnosis, severity,
                          review findings and     acceptance
                          local verification      
  -----------------------------------------------------------------------

## 1. Context

Activate `$context` on the intended repo/file scope before any repo
work.

The resulting `scope_boundaries.allowed` is authoritative for every
later stage. Workflow handoffs inherit it and do not broaden it.

If a later stage needs an out-of-scope path, stop and explicitly
reactivate `$context` after scope expansion is approved.

## 2. Feature

Invoke `$feature` with the requested bounded behavior change.

`$feature` performs scoped inspection and applies its Complexity Gate.

Continue in `$feature` only when the change remains one coherent
implementation unit. If inspection reveals multiple independently
testable tasks, material architecture/data-flow changes, coordinated
migration/contract work, unresolved security-sensitive design, or
otherwise requires explicit decomposition, stop and route to the Planned
Implementation Workflow.

Before editing, `$feature` captures the change boundary when Git
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

`$feature` does not declare the change ready.

## 3. Review

Invoke `$review` as a Change review using the feature handoff evidence.

The reviewer independently inspects the implementation. Producer claims
such as "done" or "tests pass" are context, not evidence.

Possible outcomes:

-   `ready` → workflow complete
-   `ready-with-fixes` or `not-ready` with findings → invoke `$fix`
-   blocked by missing/out-of-scope evidence → resolve the stated
    blocker before continuing

## 4. Fix

Invoke `$fix` against the requested review findings.

`$fix` consumes each finding's description, confidence, and
`fix_direction` as the remediation contract.

-   `confirmed` → implement narrowly
-   `likely` → verify only the uncertain premise, then fix or hand the
    mismatch back to `$review`
-   behavioral fix → targeted regression coverage regardless of patch
    size
-   success → fresh verification required

`$fix` never closes findings or declares the change ready.

## 5. Re-review Loop

After a successful fix, invoke `$review` again using the same Change
review target and updated change boundary.

Repeat:

`$review → $fix → $review`

until `$review` returns `ready`.

## Escalation

Switch to `$plan` rather than expanding `$feature` when the
bounded-change assumption becomes materially false.

Do not silently convert review findings into feature work or
implementation blockers into review findings.

## Completion

The workflow is complete only when `$review` returns `ready` for the
reviewed change within the active scope and available change evidence.

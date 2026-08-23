# Standalone Review Workflow

## Purpose

Use this workflow to inspect existing code independently of a preceding
`$feature` or `$implement` run. The target may be a directory, file, or
specific symbol such as a function, method, or class.

## Flow

`$context → $review → [$fix → $review]*`

The workflow ends when `$review` returns `ready` for the explicitly
reviewed scope, or when a scope/evidence blocker requires user action.

## Stage Ownership

  -----------------------------------------------------------------------
  Stage                               Owns
  ----------------------------------- -----------------------------------
  `$context`                          active review scope and applicable
                                      repo instructions

  `$review`                           scoped diagnosis, findings,
                                      severity/confidence, fix direction,
                                      verdict

  `$fix`                              narrow remediation of selected
                                      findings and fresh local
                                      verification
  -----------------------------------------------------------------------

Only `$review` determines whether findings are closed.

## 1. Context

Activate `$context` on the intended review target or an appropriate
containing scope.

The active context boundary remains authoritative. Review traversal
exceptions never override `scope_boundaries.allowed`.

## 2. Review

Invoke `$review` with the explicit target.

The review mode is selected from the target/evidence:

-   **Symbol review** --- specific function, method, class, or named
    symbol
-   **Path review** --- file or directory
-   **Change review** --- when the standalone request also supplies
    requirements and/or an explicit Git change range

### Symbol review

The named symbol is the primary reporting boundary.

The reviewer may inspect only the minimum surrounding code,
callers/callees, imports, and allowed adjacent context necessary to
establish the symbol's behavior or contract.

Do not report unrelated findings elsewhere in the containing file.

### Path review

Review the requested file or directory and only the permitted adjacent
context needed to establish concrete findings.

### Standalone Change review

If requirements and/or a Git range are explicitly available:

-   requirements only → check scoped implementation against requirements
-   diff only → inspect correctness, regressions, unintended edits,
    tests, and production readiness
-   requirements + diff → full requirements-compliance plus
    diff-integrity review

## 3. Verdict

Possible outcomes:

-   `ready` → no blocking findings within the explicitly reviewed scope
-   `ready-with-fixes` → concrete fixes remain
-   `not-ready` → blocking
    correctness/security/requirements/compatibility/etc. issue remains

For Path and Symbol review, `ready` does **not** mean whole-project or
merge readiness. It applies only to the reviewed scope.

## 4. Fix

If findings should be remediated, invoke `$fix`.

`$fix` consumes the persisted/current review findings rather than
re-reviewing the target.

For Symbol review, preserve the reviewed symbol as the primary edit
boundary. Changes elsewhere in the containing file or allowed adjacent
context are permitted only when required by that finding's
`fix_direction`.

`$fix` performs targeted regression protection and fresh verification
but does not declare the finding closed.

## 5. Re-review

After successful fixes, invoke `$review` again in the original review
mode:

-   Change → same change/requirements boundary, updated with fix delta
-   Path → same path
-   Symbol → same symbol

Repeat:

`$review → $fix → $review`

until `$review` returns `ready`.

If a `likely` finding is disproved during `$fix`, return that mismatch
to `$review` rather than inventing a replacement issue.

## Completion

Completion means `$review` returns `ready` for the original standalone
review scope. It makes no claim about code outside that scope.

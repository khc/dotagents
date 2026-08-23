---
name: refactor
description: Use when restructuring, renaming, extracting, moving, or simplifying existing code while preserving observable behavior. Best for a bounded structural change that can be completed as one coherent unit; route larger or coordinated refactors to `$plan`. Not for bug fixes or new features.
---

# Refactor

Restructure existing code to improve clarity, reduce duplication, simplify structure, or improve maintainability without changing observable behavior.

`refactor` is the bounded structural-change path. It owns the refactoring work and behavior-preservation verification; `$review` owns independent acceptance.

## Goal

Deliver the smallest structural change that satisfies the requested refactor while preserving behavior and existing contracts.

Optimize for:

- minimal structural scope
- no behavior change
- no unrelated cleanup
- fresh behavior-preservation evidence
- easy review of the resulting diff

## Workflow Gate

If a scoped context is not active:

- STOP
- run `$context` first
- after `$context` completes, confirm the active scope path, then continue

Use the repo instructions already loaded by `$context`. Read an additional nearest applicable `AGENTS.md` only if it is inside `scope_boundaries.allowed`, applies to a required refactor touchpoint, and was not already loaded.

The active context boundary is authoritative. Do not broaden it implicitly.

## Refactor Scope

Identify the requested structural target and the behavior that must remain unchanged.

Examples of valid refactors:

- rename a symbol
- extract a function/class/module
- move code without changing behavior
- simplify control flow without changing results
- consolidate duplicated implementation
- replace non-idiomatic structure with an equivalent native pattern
- split or merge modules while preserving public behavior

Not a refactor:

- fixing a bug
- adding behavior
- changing a public contract intentionally
- altering persistence semantics
- changing runtime behavior for performance or correctness
- introducing feature-level functionality

If the requested work includes both behavior change and structural cleanup, do not absorb the behavior change into `refactor`; route to `$feature` or `$plan` as appropriate.

## Complexity Gate

Proceed with `refactor` only when the requested structural change can be understood, implemented, and verified as one coherent unit.

STOP and route to `$plan` when the refactor requires any of the following:

- multiple independently testable structural tasks with meaningful dependencies
- a material architecture or cross-module data-flow redesign
- coordinated public API/schema/config/CLI changes
- migration or rollout strategy
- broad repository-wide rename/move where ordering and compatibility require explicit decomposition
- a new external dependency or tooling change
- materially broader files/modules than the bounded target
- unresolved ambiguity about what behavior must remain unchanged

Cross-file work alone does not require `$plan`; several tightly coupled edits may still be one bounded refactor.

If the user explicitly asks to skip planning and the refactor fails this gate, do not silently broaden scope. Report the reason and route to `$plan`.

## Method

Use targeted repo inspection only:

- `Glob` or equivalent to understand the immediate target structure
- `Grep` or equivalent to locate all references/call sites for symbols being renamed, moved, or extracted
- `Read` only on direct touchpoints, their relevant tests, and the minimum adjacent callers/callees needed to preserve contracts

Do not scan unrelated modules or search for extra cleanup opportunities.

## Change Boundary

Before the first edit, capture enough read-only Git state for `$review` to identify the refactor delta:

- `BASE_SHA` — current `HEAD` before refactor edits, when available
- pre-existing dirty paths within active scope
- intended refactor touchpoints

Do not require a clean working tree and do not modify Git state.

At handoff, preserve:

- `BASE_SHA`
- current `HEAD` when available
- actual touched files
- pre-existing overlap
- scoped refactor diff/change boundary
- fresh preservation verification

If pre-existing changes overlap the same lines and the refactor delta cannot be distinguished reliably, state that as a review-evidence limitation.

## Planning Phase

Produce a short inline refactor plan before editing.

Do not wait for user confirmation unless the user explicitly requested planning only.

### Target
- structural change to perform

### Behavior Invariants
- observable behavior/contracts that must remain unchanged

### Touchpoints
- files/modules/symbols to change

### Preservation Strategy
- exact existing tests/checks or targeted verification that will demonstrate unchanged behavior

Then proceed immediately to implementation.

## Baseline Verification

For behavior that is testable, establish a fresh pre-refactor baseline when practical:

- run the smallest relevant existing test(s)
- record GREEN evidence
- do not add a new failing test for unchanged behavior
- if no relevant tests exist, identify the narrowest established verification available

If the existing relevant test fails before refactoring:

- STOP
- report the failing baseline
- do not refactor on top of an already-failing signal unless the user explicitly accepts that limitation

Do not claim behavior preservation from reasoning alone when reliable executable verification exists.

## Implementation Phase

Apply the smallest structural change that achieves the stated target.

Rules:

- preserve observable behavior and public contracts
- reuse existing abstractions and project-native patterns
- do not fix unrelated bugs
- do not add features
- do not reformat unrelated code
- do not rename/move beyond what the requested structural change requires
- do not introduce new dependencies unless the plan explicitly requires them and the Complexity Gate still holds
- keep edits local and reversible

If implementation reveals that the Complexity Gate no longer holds, STOP before broadening the refactor and route to `$plan`.

A local mechanical mistake may be corrected within `refactor`; a materially larger structural redesign requires `$plan`.

## Behavior Preservation Verification

After edits:

1. re-read the changed lines and confirm the transformation is structural
2. verify all relevant call sites/references remain valid
3. run the same targeted behavior tests/checks used for the baseline
4. run applicable lint/static-check commands established by `$context`
5. inspect fresh output before claiming success

The preferred pattern is:

`GREEN baseline → refactor → GREEN verification`

Behavior-preservation success requires fresh post-refactor evidence from the current working tree.

Do not say tests “should pass.” Run the established checks when available.

If relevant verification cannot be run:

- state the verification gap
- do not claim full behavior preservation

## Failure / Retry

If the first refactor attempt fails preservation checks:

1. revert only the failed speculative edit as needed
2. inspect the failure narrowly
3. make at most one evidence-driven correction that stays within the same structural target
4. run preservation verification again

Never stack speculative structural changes.

If the second attempt fails, or success requires changing behavior, widening scope, or materially changing the refactor plan:

- stop
- report the blocker
- route to `$plan` or the appropriate behavior-changing skill

## Scope Gate

Do not absorb unrelated findings.

If you encounter an unrelated bug, security issue, missing feature, or cleanup opportunity:

- do not fix it
- do not turn it into additional refactor work
- mention it only if it blocks the requested refactor

Independent issue discovery belongs to `$review`.

## Refactor / Review Ownership

Maintain a strict lifecycle boundary:

- `$refactor` owns bounded structural planning, execution, call-site preservation, and fresh behavior-preservation verification
- `$plan` owns decomposition when the structural work becomes multi-step or coordinated
- `$review` owns independent correctness judgment, findings, severity/confidence, and acceptance/verdict
- `$fix` owns remediation of findings produced by `$review`

`$refactor` must not:

- mark the overall change `ready`
- perform an independent production-readiness review
- fix unrelated defects
- invoke `$review` or `$fix` internally

After successful refactoring and fresh verification, hand off to `$review`.

## Output

Use this shape:

```markdown
## Refactor

### Target
- ...

### Behavior Invariants
- ...

### Touchpoints
- ...

### Preservation
- Baseline: `<command>` — pass/fail summary
- Post-refactor: `<command>` — pass/fail summary
- Fresh checks: ...

### Change Boundary
- BASE_SHA: ...
- HEAD_SHA: ...
- Touched files: ...
- Pre-existing overlap: none / ...

---

### Changes
{diff or targeted edit}

### Handoff
`$review` — independently review the refactor for behavior preservation, structural correctness, and unintended change.
```

If the refactor escalates:

```markdown
## Refactor

### Blocked
- Reason: ...
- Required next step: `$plan`
```

Keep output concise. Do not repeat broad analysis.

## Save to Sidecar

If the workflow supports sidecar persistence, save the refactor entry after successful verification.

Recommended context fields:

```json
{
  "refactor": "short description",
  "target": "path/symbol",
  "behavior_invariants": ["..."],
  "touchpoints": ["..."],
  "base_sha": "...",
  "head_sha": "...",
  "preexisting_changes": ["..."],
  "verification": ["..."],
  "summary": "one-sentence summary"
}
```

Persist only inspectable workflow artifacts, not private reasoning.

## Style

- Direct
- Structural, not behavioral
- Minimal
- Evidence-backed
- No scope creep
- No unrelated cleanup
- No speculative redesign

## Response format

Start every response with the `## Refactor` heading (plain, not in a code block). Render output directly beneath it.

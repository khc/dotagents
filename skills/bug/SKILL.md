---
name: bug
description: Use when a visible symptom such as an error, stack trace, failing test, bad output, or reproducible unexpected behavior needs root-cause diagnosis and a minimal fix. Reproduce when practical, diagnose from evidence, apply the narrowest correction, verify with fresh evidence, and hand off to `$review`. Route complex or multi-cause debugging that requires broader decomposition to `$plan`. Not for applying existing review findings; use `$fix` for those.
---

# Bug

Investigate an observed failure, identify its root cause, apply the smallest correct fix, and verify that the reported behavior is resolved.

`bug` is symptom-driven diagnosis plus remediation. It is not a generic reviewer, refactorer, or review-finding executor.

## Goal

Turn a concrete symptom into a verified minimal correction with:

- evidence-backed root-cause diagnosis
- smallest safe implementation change
- regression protection when behavior is testable
- fresh post-fix verification
- no unrelated cleanup
- explicit handoff to `$review`

## Workflow Gate

If a scoped context is not active:

- STOP
- run `$context` first
- after `$context` completes, confirm the active scope path, then continue

Use the repo instructions already loaded by `$context`.

Read an additional nearest applicable `AGENTS.md` only if it:

- is inside `scope_boundaries.allowed`
- applies to a directly implicated bug touchpoint
- was not already loaded

The active context boundary is authoritative. Do not broaden scope implicitly.

## Bug Input

Accept one or more concrete symptoms:

- stack trace
- console/runtime error
- failing test
- incorrect output
- crash
- exception
- log evidence
- reproducible unexpected behavior
- user-provided steps to reproduce

If no concrete symptom exists and the task is instead “find issues,” route to `$review`.

If the issue is already represented as a structured `$review` finding with `fix_direction`, route to `$fix`.

## Complexity Gate

Proceed with `$bug` when the failure can reasonably be diagnosed and corrected as one coherent bug-fix unit.

STOP and route to `$plan` when diagnosis or remediation requires:

- multiple independently testable fixes with meaningful dependencies
- material architecture or cross-module data-flow redesign
- coordinated schema/data migration
- public API/config/CLI contract redesign
- broad security-sensitive redesign
- materially wider modules than the bounded failure path
- multiple plausible root causes that require broad system decomposition
- a new external dependency or subsystem as part of the fix
- unresolved requirements about what the correct behavior should be

Cross-file diagnosis alone does not require `$plan`; follow evidence as needed within active scope.

If the user explicitly asks for a one-pass fix but the bug fails this gate, do not broaden silently. Report the reason and route to `$plan`.

## Change Boundary

Before the first edit, capture enough read-only Git state for `$review` to identify the bug-fix delta:

- `BASE_SHA` — current `HEAD` before bug-fix edits, when available
- pre-existing dirty paths within active scope
- initially implicated files/symbols

Do not require a clean working tree and do not modify Git state.

At handoff, preserve:

- `BASE_SHA`
- current `HEAD` when available
- actual touched files
- pre-existing overlap
- scoped bug-fix diff/change boundary
- fresh reproduction/fix verification evidence

If pre-existing edits overlap the same lines and the bug-fix delta cannot be distinguished reliably, state that as a review-evidence limitation.

## Investigation Method

Start from the symptom and follow evidence.

Use targeted tools:

- `Grep` / symbol search for error strings, stack frames, symbols, failing assertions, or relevant call sites
- `Glob` / directory listing only when the symptom does not identify a useful location
- `Read` only files directly implicated by the failure path
- inspect the minimum caller/callee/config/test context required to establish causality

Do not impose an arbitrary file-count limit. Scope should be evidence-driven and bounded by the active context.

Do not scan unrelated modules or search for extra defects.

## Reproduction / Baseline

When the symptom is reproducible, establish a fresh failing baseline before changing production code.

Preferred pattern:

`RED symptom/reproduction → diagnose → fix → GREEN`

Examples:

- run the smallest failing test
- run the smallest command reproducing the error
- add the smallest regression test that captures the reported failure, when no existing test does

The RED baseline must fail for the expected reviewed symptom, not for unrelated setup/environment reasons.

Do not create destructive or out-of-scope state merely to force reproduction.

If the failure cannot be reproduced safely:

- continue only when the supplied evidence is strong enough to diagnose the root cause
- record the reproduction gap
- do not claim reproduced evidence

## Root-Cause Diagnosis

Before editing, identify:

- **what fails** — concrete failing behavior/location
- **why it fails** — causal mechanism supported by inspected evidence
- **what must be preserved** — unaffected behavior/contracts
- **fix direction** — narrow change that addresses the cause rather than a symptom

Distinguish:

- **confirmed root cause** — supported directly by inspected evidence/reproduction
- **likely root cause** — strong evidence but a specific uncertainty remains

For a likely root cause, verify the narrow uncertain assumption before editing when possible.

If the uncertainty is material and cannot be verified within scope, STOP and report the blocker rather than applying a speculative fix.

Do not patch around an error without explaining the causal root cause.

## Research Gate

Before writing bespoke bug-fix logic, check whether the correction should use:

1. standard library
2. framework-native support
3. existing project dependency/utility
4. external package only when materially justified

If choosing among reusable solutions is non-trivial and would materially affect LOC, correctness, or maintenance:

- STOP
- run `$research`
- use the returned reuse decision as the implementation input

Do not invoke `$research` for an obvious local bug fix.

## Fix Phase

Apply the smallest correction that addresses the root cause.

Rules:

- change only what is necessary for the reported bug
- preserve unaffected behavior/contracts
- prefer existing project/stdlib/framework support
- do not refactor surrounding code unless required for correctness
- do not fix unrelated bugs
- do not add unrelated features
- do not rename/move/reorganize code unless the fix requires it
- keep edits local and reversible

For testable behavioral bugs:

- add/update the smallest regression test when practical
- establish RED before the production fix when possible
- apply the minimal fix
- establish GREEN after the fix

If implementation reveals that the Complexity Gate no longer holds, STOP before broadening the fix and route to `$plan`.

## Verification Phase

After the fix:

1. re-read the changed lines
2. confirm the change addresses the diagnosed cause
3. rerun the exact reproduction/regression test used for RED
4. run applicable targeted test/lint/static-check commands established by `$context`
5. inspect fresh output before claiming success

A bug fix may be reported as successful only with fresh evidence from the current working tree.

Do not say the fix “should work” when executable verification is available.

If required verification cannot run:

- state the gap
- do not claim the bug is fully resolved

## Failure / Retry

If the first fix attempt does not resolve the reproduction or fails local verification:

1. revert only the failed speculative edit when needed
2. inspect the failure evidence narrowly
3. determine whether:
   - the diagnosis was right but the implementation was wrong, or
   - the root-cause hypothesis was wrong/incomplete
4. make at most one additional evidence-driven attempt within the same bounded bug scope
5. verify again

Never stack speculative fixes.

If the second attempt fails, or a safe correction requires materially broader scope/design:

- stop
- report the blocker
- route to `$plan` for broader decomposition or back to diagnosis as appropriate

Do not keep patching indefinitely.

## Scope Gate

Do not absorb unrelated issues encountered during diagnosis.

If another bug, security issue, cleanup opportunity, or refactor is discovered:

- do not fix it
- do not add it to the current bug scope
- mention it only if it blocks the requested fix

Independent issue discovery belongs to `$review`.

## Bug / Review Ownership

Maintain strict lifecycle boundaries:

- `$bug` owns symptom reproduction, root-cause diagnosis, minimal correction, regression protection, and fresh local verification
- `$research` owns non-trivial reuse/package choice when needed by the bug fix
- `$plan` owns decomposition when debugging/remediation becomes multi-step or coordinated
- `$review` owns independent correctness judgment, findings, severity/confidence, and acceptance/verdict
- `$fix` owns remediation of findings produced by `$review`

`$bug` must not:

- mark the overall change `ready`
- perform a broad independent code review
- fix review findings via `$fix` semantics
- invoke `$review` or `$fix` internally

After a successful bug fix and fresh verification, hand off to `$review`.

## Output

Use this shape:

```markdown
## Bug

### Symptom
- ...

### Root Cause
- Confidence: confirmed / likely
- What fails: ...
- Why: ...
- Must preserve: ...

### Fix
- Files: ...
- Approach: stdlib / framework / existing project / external package / minimal bespoke

### Verification
- RED / reproduction: `<command>` — result
- GREEN / post-fix: `<command>` — result
- Fresh checks: ...

### Change Boundary
- BASE_SHA: ...
- HEAD_SHA: ...
- Touched files: ...
- Pre-existing overlap: none / ...

---

{diff or targeted edit}

### Handoff
`$review` — independently review the bug fix against the reported symptom, regression evidence, and change boundary.
```

If blocked:

```markdown
## Bug

### Blocked
- Symptom: ...
- Blocker: ...
- Required next step: `$plan` / `$research` / scope expansion
```

Keep output concise. Do not reproduce broad investigation logs.

## Save to Sidecar

If sidecar/workflow persistence is available, save the bug-fix entry after successful verification.

Recommended context:

```json
{
  "bug": "short symptom",
  "root_cause": "confirmed causal explanation",
  "confidence": "confirmed|likely",
  "touchpoints": ["..."],
  "base_sha": "...",
  "head_sha": "...",
  "preexisting_changes": ["..."],
  "reproduction": ["..."],
  "verification": ["..."],
  "summary": "one-sentence fix summary"
}
```

Persist inspectable artifacts only, not private reasoning.

## Style

- Symptom-driven
- Root-cause-first
- Minimal
- Evidence-backed
- No scope creep
- No unrelated cleanup
- No speculative patching

## Response format

Start every response with the `## Bug` heading (plain, not in a code block). Render output directly beneath it.

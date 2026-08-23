---
name: workflow
description: Use when running a multi-stage software workflow across isolated agents. Own workflow state, fresh-agent dispatch, artifact handoffs, and review/fix loops for bounded feature, bounded refactor, symptom-driven bug fix, planned implementation, and standalone review workflows. Do not perform planning, implementation, review, or fixing itself.
---

# Workflow

Run software-development workflows by dispatching the appropriate skill in isolated agent contexts and passing structured artifacts between stages.

This skill is an orchestration layer. It does not replace `$scope`, `$feature`, `$plan`, `$implement`, `$review`, or `$fix`.

## Core Invariants

1. **Pass artifacts, not conversations.**
   - Never forward a producer agent's full conversation or private reasoning to the next stage.
   - Pass only explicit workflow inputs and inspectable outputs: scope, requirements, plans, diffs, changed files, verification evidence, review findings, and identifiers.

2. **Fresh reviewer context is mandatory.**
   - `$review` always runs in a fresh isolated agent context.
   - Do not give the reviewer implementer/fixer reasoning or claims beyond structured handoff evidence.

3. **Stage ownership is strict.**
   - `$scope` owns scope.
   - `$feature` owns bounded implementation.
   - `$refactor` owns bounded structural change.
   - `$bug` owns symptom-driven root-cause diagnosis and minimal correction.
   - `$plan` owns decomposition.
   - `$implement` owns plan-faithful execution.
   - `$review` owns diagnosis and acceptance.
   - `$fix` owns remediation of review findings.
   - The orchestrator owns transitions only.

4. **Workflow state controls transitions.**
   - Agents may report status, but they do not choose arbitrary next stages.
   - Follow the transition tables below.

5. **Scope is inherited, never widened implicitly.**
   - All stage agents receive the active scope.
   - If a stage reports an out-of-scope dependency, stop for explicit scope expansion and a new `$scope` activation before continuing.

## Agent Roles

Use the minimum stable runtime roles:

- `planner` → activates `$plan`
- `builder` → activates `$feature`, `$refactor`, `$bug`, or `$implement`
- `reviewer` → activates `$review`
- `fixer` → activates `$fix`

A runtime may map these roles to the same model/configuration. Role separation is about context isolation, not necessarily model choice.

## Workflow Selection

Choose exactly one workflow:

- `feature` — bounded change: `$scope → $feature → $review → [$fix → $review]*`
- `refactor` — bounded structural change: `$scope → $refactor → $review → [$fix → $review]*`
- `bug` — symptom-driven diagnosis and fix: `$scope → $bug → $review → [$fix → $review]*`
- `planned` — decomposed change: `$scope → $plan → $implement → $review → [$fix → $review]*`
- `review` — standalone review: `$scope → $review → [$fix → $review]*`

If `$feature` reports `needs_plan`, transition into the `planned` workflow without reusing the feature agent's reasoning. Preserve only the user request, active scope, and inspectable repo evidence required by `$plan`.

If `$refactor` reports `blocked` because its Complexity Gate fails, STOP and report that the change requires `$plan`. Unlike `$feature`, a blocked `$refactor` does not auto-transition into the `planned` workflow — the user must confirm restarting under `$plan` with the original request.

If `$bug` reports `blocked` because its Complexity Gate fails, or because the issue turns out to be a structured `$review` finding rather than a fresh symptom (route to `$fix`), or because there is no concrete symptom (route to `$review`), STOP and report the required next step. A blocked `$bug` does not auto-transition into another workflow — the user must confirm restarting under the appropriate workflow.

## Fresh-Agent Policy

Create a fresh isolated agent for every lifecycle stage invocation:

- each `$feature`
- each `$plan`
- each `$implement`
- each `$review`
- each `$fix`

A repeated stage invocation also gets a fresh agent.

Exception: `$scope` may be activated by the orchestrator/main session and passed as structured scope metadata to stage agents when the runtime supports trusted scope inheritance. Otherwise each stage agent must activate the same `$scope` path before repo work.

## Handoff Policy

Each stage receives only:

- active scope metadata
- user request / requirements relevant to that stage
- the immediately required upstream artifact
- stable identifiers needed for continuity

Do not pass:
- upstream chain-of-thought
- full chat transcripts
- unsupported summaries of repo state
- unverified success claims

## Status Vocabulary

Every stage result must be normalized to one of these statuses:

### Feature
- `success`
- `needs_plan`
- `blocked`

### Refactor
- `success`
- `blocked`

### Bug
- `success`
- `blocked`

### Plan
- `success`
- `blocked`

### Implement
- `success`
- `replan`
- `blocked`

### Review
- `ready`
- `findings`
- `blocked`

Normalize `$review` output deterministically:

| Review verdict / result | Orchestration status |
|---|---|
| `ready` with zero findings | `ready` |
| `ready-with-fixes` with one or more findings | `findings` |
| `not-ready` with one or more findings | `findings` |
| any verdict with an explicit scope/evidence blocker preventing a valid review | `blocked` |

`ready-with-fixes` is **never** a terminal workflow state. It always transitions to `$fix` when findings exist.

If review prose and the machine envelope disagree, use the stricter interpretation:
- any concrete finding means status `findings`
- any unresolved blocker means status `blocked`
- status `ready` is valid only when verdict is exactly `ready` and findings are empty

### Fix
- `success`
- `diagnosis_mismatch`
- `blocked`

If a runtime agent returns prose only, the adapter/orchestrator must derive one of these statuses conservatively from the explicit stage output. Do not infer success when verification or verdict is missing.

## Transition Tables

### Feature Workflow

| Current | Status | Next |
|---|---|---|
| scope | active | feature |
| feature | success | review |
| feature | needs_plan | plan |
| feature | blocked | STOP |
| review | ready | DONE |
| review | findings | fix |
| review | blocked | STOP |
| fix | success | review |
| fix | diagnosis_mismatch | review |
| fix | blocked | STOP |

If feature transitions to plan, continue under the Planned Workflow after plan succeeds.

### Refactor Workflow

| Current | Status | Next |
|---|---|---|
| scope | active | refactor |
| refactor | success | review |
| refactor | blocked | STOP |
| review | ready | DONE |
| review | findings | fix |
| review | blocked | STOP |
| fix | success | review |
| fix | diagnosis_mismatch | review |
| fix | blocked | STOP |

A blocked refactor reports its Complexity Gate reason and required next step
(`$plan`) but does not auto-transition; restarting under the Planned Workflow
requires explicit confirmation.

### Bug Workflow

| Current | Status | Next |
|---|---|---|
| scope | active | bug |
| bug | success | review |
| bug | blocked | STOP |
| review | ready | DONE |
| review | findings | fix |
| review | blocked | STOP |
| fix | success | review |
| fix | diagnosis_mismatch | review |
| fix | blocked | STOP |

A blocked bug reports its blocker reason (Complexity Gate failure, no concrete
symptom, or an already-structured review finding) and required next step
(`$plan`, `$review`, or `$fix`) but does not auto-transition; restarting under
the appropriate workflow requires explicit confirmation.

### Planned Workflow

| Current | Status | Next |
|---|---|---|
| scope | active | plan |
| plan | success | implement |
| plan | blocked | STOP |
| implement | success | review |
| implement | replan | plan |
| implement | blocked | STOP |
| review | ready | DONE |
| review | findings | fix |
| review | blocked | STOP |
| fix | success | review |
| fix | diagnosis_mismatch | review |
| fix | blocked | STOP |

### Standalone Review Workflow

| Current | Status | Next |
|---|---|---|
| scope | active | review |
| review | ready | DONE |
| review | findings | fix |
| review | blocked | STOP |
| fix | success | review |
| fix | diagnosis_mismatch | review |
| fix | blocked | STOP |

## Stage Dispatch

### Dispatch Feature

Give the fresh builder:

- active scope
- user feature request
- source workflow = `feature`

Require `$feature`.

Collect an `implementation-handoff` artifact.

### Dispatch Refactor

Give the fresh builder:

- active scope
- user refactor request
- source workflow = `refactor`

Require `$refactor`.

Collect an `implementation-handoff` artifact whose `source` is `refactor`. If
`$refactor` reports `blocked`, treat it like any other blocked stage: STOP and
report the blocker plus required next step, rather than dispatching `$plan`
automatically.

### Dispatch Bug

Give the fresh builder:

- active scope
- user-reported symptom (error, stack trace, failing test, bad output, or
  reproduction steps)
- source workflow = `bug`

Require `$bug`.

Collect an `implementation-handoff` artifact whose `source` is `bug`. If
`$bug` reports `blocked`, treat it like any other blocked stage: STOP and
report the blocker plus required next step (`$plan`, `$review`, or `$fix`
depending on the reason), rather than dispatching that stage automatically.

### Dispatch Plan

Give the fresh planner:

- active scope
- user requirements/request
- any explicit specs/acceptance criteria supplied by the user
- source workflow = `planned`

Require `$plan`.

Collect a `plan-handoff` artifact.

### Dispatch Implement

Give the fresh builder:

- active scope
- exact `plan-handoff`
- source workflow = `planned`

Require `$implement`.

Collect an `implementation-handoff` artifact whose `plan_id` refers to the governing plan.

### Dispatch Review

Always use a fresh reviewer.

For workflow review, give:

- active scope
- requirements / Done When or exact governing plan
- implementation-handoff
- prior review identity when re-reviewing
- fix-handoff when reviewing after a fix

For standalone review, give:

- active scope
- explicit target and optional symbol
- explicit requirements/change range only if supplied

Require `$review`.

Collect a `review-handoff` artifact.

The reviewer stage must return an explicit orchestration envelope in addition to its normal review output:

```json
{
  "stage": "review",
  "status": "ready|findings|blocked",
  "verdict": "ready|ready-with-fixes|not-ready",
  "findings_count": 0,
  "review_mode": "change|path|symbol",
  "review_uuid": "..."
}
```

The parent must apply the normalization table above and must not terminate on `ready-with-fixes`.

### Dispatch Fix

Use a fresh fixer.

Give:

- active scope
- exact review-handoff or review UUID
- selected finding IDs, or all findings if the user/workflow requested all
- source review mode and target

Require `$fix`.

Collect a `fix-handoff` artifact.

## Re-review Continuity

When review follows fix:

- preserve the prior `review_mode`
- preserve the original review target
- preserve governing requirements/plan
- include the fix delta/verification
- do not downgrade Change review to Path review merely because the immediate edit is small

A Symbol review must remain Symbol-scoped on re-review unless the reviewer explicitly reports that verifying the finding requires approved broader scope.

## Loop Control

Continue `$review → $fix → $review` until:

- `$review` returns `ready`
- a stage returns `blocked`
- `$fix` returns a diagnosis mismatch that `$review` cannot resolve within current scope
- a configured safety limit is reached

Default safety limit: maximum 5 review/fix cycles per workflow run.

If the limit is reached, STOP and report that repeated remediation is not converging. Do not keep patching indefinitely.

## Persistence

Persist stable workflow artifacts when the environment supports sidecar/workflow storage.

Recommended identifiers:

- `workflow_id`
- `plan_id`
- `implementation_id`
- `review_uuid`
- `fix_uuid`

Every artifact should record its parent identifier so the workflow graph can be reconstructed.


## Runtime Execution

Use the runtime transport available in the current harness:

- **Claude Code** — `bin/workflow.py --runtime claude`; every stage is a fresh `claude -p` process.
- **Codex CLI** — `bin/workflow.py --runtime codex`; every stage is a fresh `codex exec` process.
- **Agy / Antigravity** — run this skill in the parent agent and dispatch every stage with native `invoke_subagent` using the custom agents under `runtime/agy/agents/`.

Filesystem stage artifacts under `<scope>/.workflow/<workflow-id>/` are the
canonical cross-runtime handoff transport. Runtime-native messages may notify
the parent that a stage completed, but they do not replace the artifact contract.

Never use session resume/continue as a lifecycle-stage handoff: stage isolation,
especially reviewer isolation, is part of the workflow semantics.


## Output

Keep orchestrator output concise:

```markdown
## Workflow

- Workflow: feature | refactor | bug | planned | review
- Scope: ...
- State: ...
- Last artifact: ...
- Next: ...
```

On completion:

```markdown
## Workflow

- Workflow: ...
- Scope: ...
- State: done
- Final review: ready
- Review UUID: ...
```

On stop:

```markdown
## Workflow

- Workflow: ...
- Scope: ...
- State: blocked
- Stage: ...
- Blocker: ...
- Required action: ...
```

Do not reproduce stage-agent reasoning.

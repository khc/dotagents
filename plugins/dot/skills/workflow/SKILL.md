---
name: workflow
description: Use when running a multi-stage software workflow across isolated agents. Own workflow state, fresh-agent dispatch, artifact handoffs, and review/fix loops for bounded feature, bounded refactor, symptom-driven bug fix, planned implementation, and standalone review workflows. Do not perform planning, implementation, review, or fixing itself.
---

# Workflow

## Local skill compatibility

Resolve internal skill invocations against the current skill catalog. Prefer `dot:<name>` when available. When this skill is loaded locally without the plugin namespace (for example in Codex VS Code), use the unqualified skill name for every `dot:<name>` invocation and handoff in these instructions. Resolve bundled resources from the actual skill file with symlinks resolved; the plugin remains the resource root.

Run software-development workflows by dispatching the appropriate skill in isolated agent contexts and passing structured artifacts between stages.

This skill is an orchestration layer. It does not replace `$dot:scope`, `$dot:feature`, `$dot:plan`, `$dot:implement`, `$dot:review`, or `$dot:fix`.

## Core Invariants

1. **Pass artifacts, not conversations.**
   - Never forward a producer agent's full conversation or private reasoning to the next stage.
   - Pass only explicit workflow inputs and inspectable outputs: scope, requirements, plans, diffs, changed files, verification evidence, review findings, and identifiers.

2. **Fresh reviewer context is mandatory.**
   - `$dot:review` always runs in a fresh isolated agent context.
   - Do not give the reviewer implementer/fixer reasoning or claims beyond structured handoff evidence.

3. **Stage ownership is strict.**
   - `$dot:scope` owns scope.
   - `$dot:feature` owns bounded implementation.
   - `$dot:refactor` owns bounded structural change.
   - `$dot:bug` owns symptom-driven root-cause diagnosis and minimal correction.
   - `$dot:plan` owns decomposition.
   - `$dot:implement` owns plan-faithful execution.
   - `$dot:review` owns diagnosis and acceptance.
   - `$dot:fix` owns remediation of review findings.
   - The orchestrator owns transitions only.

4. **Workflow state controls transitions.**
   - Agents may report status, but they do not choose arbitrary next stages.
   - Follow the transition tables below.

5. **Scope is inherited, never widened implicitly.**
   - All stage agents receive the active scope.
   - If a stage reports an out-of-scope dependency, stop for explicit scope expansion and a new `$dot:scope` activation before continuing.

## Agent Roles

Use the minimum stable runtime roles:

- `planner` → activates `$dot:plan`
- `builder` → activates `$dot:feature`, `$dot:refactor`, `$dot:bug`, or `$dot:implement`
- `reviewer` → activates `$dot:review`
- `fixer` → activates `$dot:fix`

A runtime may map these roles to the same model/configuration. Role separation is about context isolation, not necessarily model choice.

## Workflow Selection

Choose exactly one workflow:

- `feature` — bounded change: `$dot:scope → $dot:feature → $dot:review → [$dot:fix → $dot:review]*`
- `refactor` — bounded structural change: `$dot:scope → $dot:refactor → $dot:review → [$dot:fix → $dot:review]*`
- `bug` — symptom-driven diagnosis and fix: `$dot:scope → $dot:bug → $dot:review → [$dot:fix → $dot:review]*`
- `planned` — decomposed change: `$dot:scope → $dot:plan → AWAITING_PLAN_APPROVAL → $dot:implement → $dot:review → [$dot:fix → $dot:review]*`
- `review` — standalone review: `$dot:scope → $dot:review → [$dot:fix → $dot:review]*`

If `$dot:feature` reports `needs_plan`, transition into the `planned` workflow without reusing the feature agent's reasoning. Preserve only the user request, active scope, and inspectable repo evidence required by `$dot:plan`.

If `$dot:refactor` reports `blocked` because its Complexity Gate fails, STOP and report that the change requires `$dot:plan`. Unlike `$dot:feature`, a blocked `$dot:refactor` does not auto-transition into the `planned` workflow — the user must confirm restarting under `$dot:plan` with the original request.

If `$dot:bug` reports `blocked` because its Complexity Gate fails, or because the issue turns out to be a structured `$dot:review` finding rather than a fresh symptom (route to `$dot:fix`), or because there is no concrete symptom (route to `$dot:review`), STOP and report the required next step. A blocked `$dot:bug` does not auto-transition into another workflow — the user must confirm restarting under the appropriate workflow.

## Fresh-Agent Policy

Create a fresh isolated agent for every lifecycle stage invocation:

- each `$dot:feature`
- each `$dot:plan`
- each `$dot:implement`
- each `$dot:review`
- each `$dot:fix`

A repeated stage invocation also gets a fresh agent.

Exception: `$dot:scope` may be activated by the orchestrator/main session and passed as structured scope metadata to stage agents when the runtime supports trusted scope inheritance. Otherwise each stage agent must activate the same `$dot:scope` path before repo work.

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

Normalize `$dot:review` output deterministically:

| Review verdict / result | Orchestration status |
|---|---|
| `ready` with zero findings | `ready` |
| `ready-with-fixes` with one or more findings | `findings` |
| `not-ready` with one or more findings | `findings` |
| any verdict with an explicit scope/evidence blocker preventing a valid review | `blocked` |

`ready-with-fixes` is **never** a terminal workflow state. It always transitions to `$dot:fix` when findings exist.

If review prose and the machine envelope disagree, use the stricter interpretation:
- any concrete finding means status `findings`
- any unresolved blocker means status `blocked`
- status `ready` is valid only when verdict is exactly `ready` and findings are empty

### Fix
- `success`
- `diagnosis_mismatch`
- `blocked`

If a runtime agent returns prose only, the adapter/orchestrator must derive one of these statuses conservatively from the explicit stage output. Do not infer success when verification or verdict is missing.

## Plan Approval Gate

A successful `$dot:plan` result never auto-transitions to `$dot:implement`. It always lands the workflow in the terminal-for-this-invocation state `AWAITING_PLAN_APPROVAL`, alongside `DONE`/`STOP`, and the workflow waits there for an explicit human decision.

While `AWAITING_PLAN_APPROVAL`, persist the plan's identity as `active_plan`:

```json
{"path": ".plans/plan_<timestamp>.md", "plan_id": "plan_<timestamp>", "revision": 1, "status": "draft"}
```

`path` is always relative to the repo root (per the loaded `dot:plan` skill's `SKILL.md`'s Plan Artifact section), never to the active scope.

`status` mirrors the loaded `dot:plan` skill's `SKILL.md`'s frontmatter (`draft` | `approved` | `superseded`).

Approval-parsing rule (concrete, conservative, no ambiguity):

- `$dot:workflow` (prose/Agy): approval is recognized **only** via the exact phrase list already defined in the loaded `dot:plan` skill's `SKILL.md`'s Conversational Plan Lifecycle ("approved", "looks good, implement", "go ahead", "execute this plan", or a direct `$dot:implement` invocation referring to this plan) — reference that list, never restate it with different wording. Any other message routes to `$dot:plan` as an amendment. Explicit cancellation phrases ("cancel", "stop", "never mind", "discard this plan") route to `STOP`.
- `bin/workflow.py resume --message`: **always** re-invokes `$dot:plan`; **never** itself flips `status`.
- `bin/workflow.py approve`: the **only** action that flips `draft → approved`; it performs a deterministic frontmatter patch and never invokes `$dot:plan`.
- `(plan, success) → AWAITING_PLAN_APPROVAL` is a single uniform rule that covers first-time creation, conversational amendment, and `implement`-triggered re-plan — no special-casing needed per trigger reason at the transition-table level.

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

If feature transitions to plan, continue under the Planned Workflow: a successful plan enters `AWAITING_PLAN_APPROVAL`, per the Plan Approval Gate, and requires explicit user approval before `$dot:implement` runs.

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
(`$dot:plan`) but does not auto-transition; restarting under the Planned Workflow
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
(`$dot:plan`, `$dot:review`, or `$dot:fix`) but does not auto-transition; restarting under
the appropriate workflow requires explicit confirmation.

### Planned Workflow

| Current | Status | Next |
|---|---|---|
| scope | active | plan |
| plan | success | AWAITING_PLAN_APPROVAL |
| AWAITING_PLAN_APPROVAL | user_approves | implement |
| AWAITING_PLAN_APPROVAL | user_amends | plan |
| AWAITING_PLAN_APPROVAL | user_cancels | STOP |
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

`plan | success | AWAITING_PLAN_APPROVAL` applies uniformly to first-time plan creation, conversational amendment, and `implement`-triggered re-plan — see Plan Approval Gate above.

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

Require `$dot:feature`.

Collect an `implementation-handoff` artifact.

### Dispatch Refactor

Give the fresh builder:

- active scope
- user refactor request
- source workflow = `refactor`

Require `$dot:refactor`.

Collect an `implementation-handoff` artifact whose `source` is `refactor`. If
`$dot:refactor` reports `blocked`, treat it like any other blocked stage: STOP and
report the blocker plus required next step, rather than dispatching `$dot:plan`
automatically.

### Dispatch Bug

Give the fresh builder:

- active scope
- user-reported symptom (error, stack trace, failing test, bad output, or
  reproduction steps)
- source workflow = `bug`

Require `$dot:bug`.

Collect an `implementation-handoff` artifact whose `source` is `bug`. If
`$dot:bug` reports `blocked`, treat it like any other blocked stage: STOP and
report the blocker plus required next step (`$dot:plan`, `$dot:review`, or `$dot:fix`
depending on the reason), rather than dispatching that stage automatically.

### Dispatch Plan

When `active_plan` already exists (conversational amendment or an `implement replan` blocker), give the fresh planner the exact `active_plan.path`/`plan_id`/`revision` plus the amendment or blocker text so `$dot:plan` reopens that file per its Plan Revision rules instead of creating a new `plan_id`.

Give the fresh planner:

- active scope
- user requirements/request
- any explicit specs/acceptance criteria supplied by the user
- source workflow = `planned`

Require `$dot:plan`.

Collect a `plan-handoff` artifact.

A successful plan-handoff always transitions the workflow to `AWAITING_PLAN_APPROVAL` and persists `active_plan` (see Plan Approval Gate). Never dispatch `$dot:implement` directly from a plan result, whether the plan is newly created or a revision.

### Dispatch Implement

Only dispatch `$dot:implement` when workflow state is `AWAITING_PLAN_APPROVAL` and `active_plan.status == "approved"` for the current `revision`. Never dispatch `$dot:implement` while `active_plan.status == "draft"`.

Give the fresh builder:

- active scope
- exact `plan-handoff`
- source workflow = `planned`

Require `$dot:implement`.

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

Require `$dot:review`.

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

Require `$dot:fix`.

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

Continue `$dot:review → $dot:fix → $dot:review` until:

- `$dot:review` returns `ready`
- a stage returns `blocked`
- `$dot:fix` returns a diagnosis mismatch that `$dot:review` cannot resolve within current scope
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

When a plan is open, persist `active_plan` (`path`, `plan_id`, `revision`, `status`) exactly as defined in Plan Approval Gate, so the workflow can resume across process boundaries.


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

`bin/workflow.py` treats `AWAITING_PLAN_APPROVAL` as terminal-for-this-invocation and exposes `start`/`resume`/`approve`/`cancel` subcommands to move past it across process boundaries.

Agy needs no code change — the parent simply stops after a successful `$dot:plan` stage and waits, per `runtime/agy/agents/planner.md` and `runtime/agy/README.md`.


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

On awaiting plan approval:

```markdown
## Workflow

- Workflow: ...
- Scope: ...
- State: awaiting_plan_approval
- Active plan: .plans/plan_1787501234.md (revision 3, draft)
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

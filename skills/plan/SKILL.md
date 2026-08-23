---
name: plan
description: Use when a repo change needs planning before implementation -- multiple independently testable tasks, coordinated interfaces, material risk, migrations, or security-sensitive design. Break requirements into the smallest executable, testable tasks with exact files/interfaces/verification, then hand off to `$implement` without modifying code. For one coherent bounded change, use `$feature` instead.
---

# Plan

Use this skill to decide whether a repo change needs an implementation plan and, when it does, create and iteratively refine a persistent Markdown plan that an implementation agent can execute without rediscovering the design.

Planning is read-only with respect to product/source code. The only write this skill performs is creating or updating the plan Markdown artifact itself. Do not modify source files, tests, configuration, generated artifacts, Git state, or branch state.

## Goal

Produce a persistent, reviewable implementation contract with:

- the smallest correct scope
- explicit requirements and acceptance criteria
- exact files/areas likely to change
- clear task boundaries and dependencies
- targeted test and verification strategy
- enough technical context for `$implement` to execute without broad re-analysis

Optimize for low scope, low token usage, and low rework — not for the shortest possible plan.

## Plan Artifact

For every Planned path, create a Markdown file named:

```text
plan_<unix_timestamp>.md
```

where `<unix_timestamp>` is the current Unix timestamp in seconds at the moment the plan is first created.

Example:

```text
plan_1787486400.md
```

Create the file inside the active scope unless the active project instructions define a specific planning/docs directory inside `scope_boundaries.allowed`.

The filename is stable for the lifetime of that plan:

- first creation → create `plan_<timestamp>.md`
- later discussion/revision → update the same file
- re-planning during implementation → update the same file unless the user explicitly asks for a separate plan

Do not create a new timestamped file for every conversational revision.

The plan file is the authoritative implementation artifact. Chat output summarizes or presents the plan, but `$implement` must ultimately consume the persisted file.

## Conversational Plan Lifecycle

A plan has three lifecycle states:

- **draft** — created but still open for discussion
- **approved** — user has explicitly accepted the plan for implementation
- **superseded** — replaced by another plan only when the user explicitly requests a separate plan

Initial creation always produces `status: draft`.

After creating a draft:

- do **not** invoke `$implement`
- invite/accept conversational review, brainstorming, additions, removals, alternative approaches, and requirement changes
- treat subsequent user messages about the plan as amendments to the same plan artifact unless they clearly start a different task

Typical conversation:

```text
$plan Add authentication
→ creates plan_1787486400.md (draft)

User: don't use JWT; use server-side sessions
→ revises plan_1787486400.md

User: can we avoid touching User?
→ discuss tradeoff; revise if user chooses

User: add migration rollback
→ revise same plan

User: approved, implement it
→ mark approved and hand exact plan file to $implement
```

Do not interpret silence, “looks interesting”, or continued brainstorming as approval.

Approval must be explicit enough to mean implementation should start, e.g.:

- “approved”
- “looks good, implement”
- “go ahead”
- “execute this plan”
- direct invocation of `$implement` referring to this plan

## Plan Revision

When a current draft/approved plan exists and the user changes, adds, removes, questions, or clarifies requirements:

1. Load the current plan file.
2. Discuss/brainstorm the requested change as needed.
3. Apply the user's accepted amendment to that same file.
4. Re-evaluate:
   - requirements
   - scope
   - approach
   - task decomposition
   - interfaces/dependencies
   - verification
   - Done When criteria
   - risks/stop conditions
5. Remove obsolete tasks, assumptions, or approaches.
6. Run the complete Plan Self-Review again.
7. Increment the plan's `revision` value.
8. If an approved plan changes materially before implementation starts, set it back to `status: draft` until the user approves the revised version.

Return the complete revised plan or a concise change summary plus the plan file path. The persisted file remains authoritative.

Do not preserve an older design decision merely because it appeared in an earlier revision when the user has changed that requirement.

## Workflow Gate

If an active scope is not established:

- STOP
- run `$scope` first
- after `$scope` completes, confirm the active scope path, then continue
- do not infer scope from the requested target alone

Use the repo instructions already loaded by `$scope`. Read an additional nearest applicable `AGENTS.md` only if it is inside `scope_boundaries.allowed`, applies to required planning evidence, and was not already loaded. If no applicable project instructions are available, proceed using the active scoped path only.

## Route Before Planning

Classify the requested work before deep exploration.

### Direct routes

Do not create an implementation plan when the request is already one of these:

- code/file/change review → `$review`
- applying existing review findings → `$fix`
- research-only question → `$research`

Return the minimal route and stop.

### Implementation routes

Choose between:

- **Feature path** — use `$feature` for a bounded change whose implementation can be safely understood and completed as one coherent unit; successful implementation then hands off to `$review`, with `$fix → $review` only if findings exist.
- **Planned path** — use `$plan → $implement` when the change contains multiple independently testable tasks, coordinated interfaces, material contract/migration/security/architectural risk, or otherwise benefits from explicit decomposition; successful implementation then hands off to `$review`, with `$fix → $review` only if findings exist.

If the user explicitly asks for a plan, create one even if the task appears bounded.

If uncertainty about implementation risk can be resolved by a small amount of scoped inspection, inspect before choosing between Feature and Planned paths. Do not guess from filenames or task wording alone.

## Planning Exploration

For a Planned path, inspect only enough repo context to produce an executable plan.

Read, in this order:

1. user-supplied requirements, task text, spec, acceptance criteria, or issue description
2. `AGENTS.md` and scoped project guidance
3. target files/directories and their structure
4. existing tests for the affected behavior
5. directly relevant callers, callees, interfaces, schemas, or configuration
6. recent Git history for affected files only when it materially informs compatibility, intent, or avoided regressions

Stay within the active scope's `scope_boundaries.allowed`.

Do not explore unrelated modules "for completeness."

If required planning evidence lies outside the active scope, stop and request the exact scope expansion before reading it.

## Planning Rules

1. **Ground the plan in inspected code.**
   - Do not invent file paths, symbols, APIs, test commands, or dependencies.
   - Mark a file as `Create` only when the plan actually requires a new file.
   - Cite existing symbols exactly as they appear.

2. **Separate requirements from implementation choices.**
   - Requirements/acceptance criteria describe what must be true.
   - The plan describes how the scoped repo should achieve it.
   - If a requirement is ambiguous enough to change implementation materially, stop and surface that ambiguity rather than silently choosing.

3. **Use the smallest independently testable task as the decomposition unit.**
   - Each task should produce a coherent change that can be implemented and verified independently.
   - Split tasks when one could reasonably be accepted/rejected without the other.
   - Fold scaffolding, small config edits, and documentation into the task that needs them instead of creating ceremony-only tasks.
   - Avoid micro-steps such as separate tasks for "open file", "edit line", or "run formatter."

4. **Preserve interfaces between tasks.**
   - When one task produces an API, type, schema, config key, or behavior consumed by another task, name that contract explicitly.
   - Keep names/signatures consistent across the entire plan.
   - Do not leave placeholders such as `TBD`, `TODO`, "appropriate validation", or "add tests."

5. **Plan tests around behavior.**
   - Identify the minimal regression/behavior tests required for each task.
   - Reuse existing test style, helpers, fixtures, and commands.
   - For changed runtime behavior, plan RED → implementation → GREEN when practical.
   - Do not invent verification commands. Use commands defined by `AGENTS.md` or already-established project tooling.

6. **Plan production-readiness work only when applicable.**
   - Include compatibility, migration, rollout/rollback, documentation, observability, or security work only when the change actually touches those contracts.
   - Do not add generic "best practice" work unrelated to the requested outcome.

7. **Do not implement during planning.**
   - The plan Markdown artifact may be created/updated.
   - No source edits.
   - No test edits.
   - No generated scaffolding.
   - No commits.
   - Read-only commands and test discovery are allowed; running tests is allowed only when needed to establish existing behavior or baseline and permitted by project guidance.

8. **Do not perform later lifecycle stages while the plan is draft.**
   - Do not invoke `$implement`, `$feature`, `$review`, or `$fix` from inside planning.
   - A draft plan ends with conversational review/approval, not implementation.
   - Only an explicitly approved plan may be handed to `$implement`.

## Plan Self-Review

Before returning the plan, check it yourself:

1. **Requirement coverage** — every supplied requirement or acceptance criterion maps to at least one task.
2. **Scope discipline** — every planned file/change is necessary for the requested outcome.
3. **Executability** — each task has enough repo-grounded detail for `$implement` to act without broad exploration.
4. **Testability** — each behavioral task has a concrete verification path.
5. **Interface consistency** — names, signatures, schemas, config keys, and task dependencies agree across tasks.
6. **Placeholder scan** — no vague "handle errors", "add tests", "refactor as needed", `TBD`, or equivalent placeholders.
7. **Ordering** — task dependencies are explicit and tasks are ordered so each prerequisite exists before it is consumed.

Fix plan defects inline before returning it. Do not dispatch a separate reviewer.

## Output

### Direct / Feature Route

Use this compact shape when a full plan is unnecessary:

```markdown
## Plan

### Route
`$feature → $review → [$fix → $review]*`
or
`$review`
or
`$fix`
or
`$research`

### Scope
- Target: ...
- Outcome: ...

### Reason
...

### Next Step
...
```

### Planned Route

Persist this structure in `plan_<unix_timestamp>.md`:

```markdown
---
plan_id: plan_<unix_timestamp>
created_at: <ISO-8601 timestamp>
updated_at: <ISO-8601 timestamp>
revision: 1
status: draft
scope: <active scope>
---

# Implementation Plan

## Goal
...

## Requirements
- ...

## Scope
- Target: ...
- In scope: ...
- Out of scope: ...

## Approach
2–5 concise bullets describing the chosen implementation approach and important constraints.

## Tasks

### 1. <independently testable task>
- Files:
  - Modify: `path`
  - Create: `path`       # only when required
  - Test: `path`
- Requirements: ...
- Implementation: concrete repo-grounded change, naming relevant symbols/interfaces
- Interfaces / dependencies: ...
- Verification: exact targeted test/check or established project command
- Done when: observable acceptance condition

### 2. ...
...

## Risks / Stop Conditions
- only material risks, ambiguities, migrations, compatibility concerns, or conditions requiring re-planning

## Approval
- Status: draft
- Approved by user: no

## Handoff
Pending explicit user approval.
```

After explicit approval, update the same file:

```yaml
status: approved
revision: <current revision>
updated_at: <current ISO-8601 timestamp>
```

and replace the Handoff section with:

```markdown
## Handoff
`$implement <path/to/plan_<unix_timestamp>.md>` — execute this exact approved plan in order, preserving scope and acceptance criteria.
```

Omit empty optional fields rather than filling them with generic text.

## Plan Identity and Versioning

The filename provides stable plan identity:

```text
plan_id = plan_<unix_timestamp>
```

The same `plan_id` survives conversational revisions.

Track revisions inside the Markdown frontmatter:

```yaml
revision: 1
status: draft
```

Each persisted amendment increments `revision`.

Do not create a new `plan_id` for ordinary discussion, brainstorming, or implementation-driven re-planning. Create a separate plan only when the user explicitly asks for an alternative/separate plan or starts a materially different task.

The exact plan path + revision becomes the handoff identity for `$implement` and later `$review`.

## Handoff Contract

The persisted **approved** Markdown plan is the implementation contract for `$implement`.

Never hand a `status: draft` plan to `$implement`.

The handoff must identify the exact file and current revision, for example:

```text
$implement plans/plan_1787486400.md
plan_id: plan_1787486400
revision: 4
```

`$implement` must read that exact file before execution. It may inspect the files named by a task and the minimal adjacent context needed to execute it, but should not redesign the plan silently.

If implementation discovers that:

- a required file/interface differs materially from the plan
- a task cannot be completed inside the planned scope
- an assumption or acceptance criterion is false
- a migration, security, compatibility, or architectural issue materially changes the approach

then implementation should stop and return the blocker for re-planning rather than silently expanding scope.

When `$implement` returns a re-plan blocker:

1. reopen the same plan artifact
2. set `status: draft`
3. incorporate the implementation evidence/blocker
4. revise the plan and increment `revision`
5. run Plan Self-Review
6. require explicit user approval again before implementation resumes

After `$implement`, acceptance belongs to `$review`, not to `$implement`.

## Style

- Direct
- Repo-grounded
- Minimal but executable
- No implementation
- No speculative file lists
- No scope creep
- No ceremony-only tasks

## Response format

Start every response with the `## Plan` heading (plain, not in a code block).

For a persisted Planned path, always include:

```markdown
### Plan Artifact
- File: `path/to/plan_<unix_timestamp>.md`
- Revision: N
- Status: draft | approved
```

While `status: draft`, end with an invitation to review/brainstorm the plan rather than an implementation handoff.

Once explicitly approved, end with the exact `$implement <plan-file>` handoff.

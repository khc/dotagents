---
name: feature
description: Use when implementing a bounded feature or behavior change that can be safely understood and completed as one coherent unit without a separate implementation plan. Trigger with "add a feature", "implement X", or "build Y".
---

Deliver features in a controlled, minimal, and modular way.

## Local skill compatibility

Resolve internal skill invocations against the current skill catalog. Prefer `dot:<name>` when available. When this skill is loaded locally without the plugin namespace (for example in Codex VS Code), use the unqualified skill name for every `dot:<name>` invocation and handoff in these instructions. Resolve bundled resources from the actual skill file with symlinks resolved; the plugin remains the resource root.

## Bundled Helpers

Resolve `dot_plugin_root` from this loaded skill's file path: `Path(skill_file).resolve().parents[2]`. In Claude Code, `${CLAUDE_PLUGIN_ROOT}` is substituted in loaded Markdown; in Codex, use the actual `SKILL.md` path from the skill catalog. Set the shell variable `dot_plugin_root` to that resolved absolute path before running the helper commands below; do not assume a plugin variable exists in the shell.

Run helpers with `uv` from the target repository's current working directory. Plugin paths locate resources; `scope_path` and `repo_root` describe the target project. `uv` manages Python 3.14 and the inline dependencies without using a checkout-specific virtual environment.

## Workflow

If an active scope is not established:
- STOP
- run $dot:scope first

1. Use the repo instructions already loaded by `$dot:scope`. Read an additional nearest applicable `AGENTS.md` only if it is inside `scope_boundaries.allowed`, applies to a required touchpoint, and was not already loaded.
2. If no applicable project instructions are available, inspect only:
   - `pyproject.toml` or `package.json` (deps and tooling)
   - top-level directory listing (structure)
   - one representative source file (conventions)
   - Do not crawl the full repo.
3. Define minimal viable scope:
   - user-facing behavior
   - touched files/modules
   - edge cases (only if obvious)
   - tests/config/migrations if required
4. Apply the Complexity Gate below before planning or editing.

## Complexity Gate

`feature` is the fast path for one coherent implementation unit, not a substitute for `$dot:plan`.

Proceed with `feature` only when scoped inspection shows the change can be implemented and verified as one coherent unit without materially redesigning the repo.

STOP and route to `$dot:plan` when the change requires any of the following:

- multiple independently testable implementation tasks with meaningful dependencies
- a material architecture or cross-module data-flow change
- a new or changed public API, persisted schema/data migration, config/CLI contract, or rollout/rollback strategy that needs explicit coordination
- security-sensitive design whose approach is not already established by the repo
- materially broader files/modules than the initial bounded scope
- a new external dependency whose adoption materially affects architecture or maintenance
- unresolved requirements or implementation choices that would materially change scope or acceptance criteria

Cross-file work alone does not require `$dot:plan`; several tightly coupled edits may still be one coherent feature.

If the user explicitly asks to skip planning and the task fails this gate, do not silently broaden `feature`. Report the reason and route to `$dot:plan`.

## Change Boundary

Before the first edit, capture enough read-only Git state for `$dot:review` to identify the feature's delta:

- `BASE_SHA` — current `HEAD` before feature edits, when the scope is inside a Git repo
- pre-existing dirty paths within the active scope, if any
- the feature's intended touchpoints

Do not require a clean working tree and do not modify Git state.

At handoff, provide:

- `BASE_SHA`
- current `HEAD` (if it changed)
- actual touched files
- whether any touched file already contained pre-existing changes
- the scoped diff for the feature touchpoints, or enough information for `$dot:review` to inspect it directly

If pre-existing edits overlap the same lines and the feature delta cannot be distinguished reliably, state that as a review-evidence limitation rather than claiming a clean change boundary.

## Method

- Use `Glob` for repo structure exploration
- Use `Grep` for symbol, function, or dependency lookup
- Use `Read` only for files identified as direct touchpoints
- Never read full directories or accumulate broad file contents into context

## Research Gate

Before implementation, check whether the task may benefit from replacing bespoke code with:
- standard library support
- framework-native utilities
- dependencies already present in the project
- a well-established external library

Do not assume triviality without explicitly checking the criteria above.

If the library or built-in choice is non-trivial:
- STOP
- run $dot:research
- when $dot:research returns, use its findings to make the library decision; record it in the plan's **Library Decision** section, then proceed to Planning Phase

If the choice is trivial:
- proceed to Planning Phase

Treat the choice as non-trivial when targeted repo inspection cannot establish a clearly preferred standard-library, framework-native, or existing-project solution and one or more of the following are true:
- multiple materially different viable approaches remain
- the current implementation would require noticeable bespoke logic in a correctness- or security-sensitive area
- adding a library could materially reduce LOC or risk
- choosing incorrectly would materially affect compatibility, security, performance, or maintenance

The mere presence of parsing, validation, serialization, auth, crypto, HTTP, retries, caching, concurrency, background jobs, file handling, or database access does not by itself require `$dot:research` when the repo already establishes the approach.

If the best path is obvious and already supported by the standard library or existing project utilities:
- proceed without `$dot:research`
- confirm the utility or function exists via a targeted `Grep` or `Read` before referencing it in the plan
- state that decision briefly in the plan

## Planning Phase (MANDATORY)

Return a short plan BEFORE coding.

Do NOT write code in this phase.

After completing the plan:
- transition immediately to Implementation Phase
- do not wait for confirmation

### Scope
- What will be built (1–3 bullets)

### Touchpoints
- Files/modules to change or add

### Approach
- Standard library / existing project / external library / bespoke

### Library Decision (if relevant)
- Option A (name + 1-line reason)
- Option B (optional)
- Final choice + why

### Done When
- Bullet-list of observable acceptance criteria (behaviour, not implementation details). Used as the self-check target after implementation.

## Implementation Phase

Proceed immediately after the plan unless the user explicitly requested planning only.

Do not repeat the plan.

- Implement minimal working solution
- Reuse existing abstractions
- No overengineering
- Keep functions small and explicit
- Side effects at boundaries

If implementation reveals that the Complexity Gate no longer holds — for example the change requires materially different scope, architecture, contracts, migration strategy, security design, or multiple independent tasks — STOP before broadening the implementation and route to `$dot:plan`.

A local implementation mistake may be corrected within `feature`; a materially wrong inline plan requires `$dot:plan`.

## Post-Implementation Verification

After all edits are applied, check each item in the plan's **Done When** list:
- if an item is satisfied by the code, mark it mentally as done
- if an item is not satisfied: state which criterion is unmet in one line and implement the missing piece before proceeding to output

Do not proceed to output until all acceptance criteria are met or explicitly deferred with a stated reason.

Do not claim implementation success from code inspection alone when the behavior is testable. Success requires fresh verification evidence from the current working tree.

## Execution Rules

- Do not ask for confirmation
- Do not pause after planning
- Do not restate the plan
- Do not reread unchanged files unless necessary
- Do not explore outside the active scope

## Code Output Rules

- Return:
  - plan
  - followed by code or diff/patch
- Do not add explanations beyond the plan
- Prefer diffs over full file output; split large implementations across multiple edits

## Testing

- For testable runtime behavior, add or update the smallest behavior/regression test before production code when practical.
- Prefer RED → implementation → GREEN: confirm the new/updated test fails for the expected reason before the production change, when safe and meaningful.
- Do not create destructive or out-of-scope state merely to force RED.
- For non-behavioral changes, use the smallest applicable verification and do not add tests for ceremony.
- Prefer existing test style, helpers, and fixtures.
- After applying edits, run the applicable test, lint, and static-check commands established by the instructions loaded during `$dot:scope`. Use only established commands — do not guess or discover alternatives.
- Inspect fresh command output before claiming success. If a required check cannot be run, state the verification gap and do not claim the affected acceptance criterion is verified.

## Feature / Review Ownership

Maintain a strict lifecycle boundary:

- `$dot:feature` owns bounded discovery, the inline mini-plan, implementation, regression protection, and fresh local verification
- `$dot:review` owns independent correctness judgment, findings, severity/confidence, and acceptance/verdict
- `$dot:fix` owns remediation of findings produced by `$dot:review`
- `$dot:plan` owns decomposition when the work no longer fits the bounded Feature path

`$dot:feature` must not mark the overall change `ready`, perform an independent production-readiness review, or silently absorb review/fix responsibilities.

After successful implementation and fresh verification, hand off to `$dot:review`.

## Constraints

- Do not expand scope
- Do not introduce new abstractions unless necessary
- Do not add libraries unless justified in plan
- Avoid duplication

## Style

- Direct and minimal
- Idiomatic to the repo
- Optimize for readability and changeability

## Output

Use this shape:

````markdown
## Feature

### Scope
- what will be built

### Touchpoints
- files/modules to change or add

### Approach
standard library / existing project / external library / bespoke

### Verification
- Regression evidence: ...
- Fresh checks: ...

---

{implementation — diff or edit follows}

### Handoff
`$dot:review` — independently review the completed bounded change using the Done When criteria, change boundary, scoped diff, touched files, and fresh verification evidence.
````

## Save to Sidecar

After rendering the feature output, persist the entry using the direct sidecar script. Do not invoke or activate the $sidecar skill.

1. **Derive agent and model**:
   - `agent` — stable snake_case runtime identifier: `claude_code` (Claude Code), `gemini_cli` (Gemini CLI), `codex` (Codex/OpenAI CLI), or a descriptive snake_case name for custom runtimes
   - `model` — active model name from the runtime (e.g. `claude-sonnet-4-6`); use `{agent}/unknown` if unavailable

2. **Save feature entry** — run:
   ```bash
   uv run --no-project "$dot_plugin_root/scripts/sidecar_workflow.py" save \
     --skill feature \
     --scope "{scope}" \
     --agent "{agent}" \
     --model "{model}" \
     --context - \
     --context_input stdin \
     --status done
   <<'JSON'
   {context_json}
   JSON
   ```
   Where `context_json` is a JSON object with:
   - `feature` — short name or description of what was built
   - `touchpoints` — list of files changed or added
   - `summary` — one-sentence prose summary of what was implemented
   - `acceptance_criteria` — list of the Done When criteria from the plan
   - `verification` — concise fresh test/lint/static-check evidence supporting the implementation
   - `base_sha` — pre-edit `HEAD` when available
   - `head_sha` — current `HEAD` at handoff when available
   - `preexisting_changes` — scoped dirty paths that existed before feature edits
   - `change_boundary` — concise description of the diff/touchpoints review should treat as this feature's implementation delta

3. **Output the UUID** — the workflow prints the UUID to stdout. Append it to the response:
   ```
   Feature saved — UUID: {uuid}
   ```

If the save fails, report the error in one line and continue — do not interrupt or re-render the feature output.

## Response format

Start every response with the `## Feature` heading (plain, not in a code block). Render output directly beneath it.

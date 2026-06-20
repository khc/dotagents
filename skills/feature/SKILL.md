---
name: feature
description: Deliver a new feature or substantial behavior extension with a structured plan → implement workflow. Trigger with "add a feature", "implement X", or "build Y".
---

Deliver features in a controlled, minimal, and modular way.

## Workflow

If a scoped context is not active:
- STOP
- run $context first

1. Read `AGENTS.md` first.
2. If missing, inspect only:
   - `pyproject.toml` or `package.json` (deps and tooling)
   - top-level directory listing (structure)
   - one representative source file (conventions)
   - Do not crawl the full repo.
3. Define minimal viable scope:
   - user-facing behavior
   - touched files/modules
   - edge cases (only if obvious)
   - tests/config/migrations if required

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
- run $research
- when $research returns, use its findings to make the library decision; record it in the plan's **Library Decision** section, then proceed to Planning Phase

If the choice is trivial:
- proceed to Planning Phase

Treat the choice as non-trivial if any of the following are true:
- multiple viable approaches exist
- the task involves parsing, validation, serialization, auth, crypto, HTTP, retries, caching, concurrency, background jobs, file handling, or database access
- the current implementation would require noticeable bespoke logic
- adding a library could materially reduce LOC or risk

If the best path is obvious and already supported by the standard library or existing project utilities:
- proceed without `$research`
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

## Post-Implementation Verification

After all edits are applied, check each item in the plan's **Done When** list:
- if an item is satisfied by the code, mark it mentally as done
- if an item is not satisfied: state which criterion is unmet in one line and implement the missing piece before proceeding to output

Do not proceed to output until all acceptance criteria are met or explicitly deferred with a stated reason.

## Execution Rules

- Do not ask for confirmation
- Do not pause after planning
- Do not restate the plan
- Do not reread unchanged files unless necessary
- Do not explore outside the scoped context

## Code Output Rules

- Return:
  - plan
  - followed by code or diff/patch
- Do not add explanations beyond the plan
- Prefer diffs over full file output; split large implementations across multiple edits

## Testing

- Draft minimal tests for the new behavior alongside the implementation — not as a separate step after.
- Prefer existing test style, helpers, and fixtures.
- After applying edits, run the test, lint, and static-check commands specified in `AGENTS.md` (loaded during `$context`). Use only those commands — do not guess or discover alternatives.

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

---

{implementation — diff or edit follows}
````

## Save to Sidecar

After rendering the feature output, persist the entry using the direct sidecar script. Do not invoke or activate the $sidecar skill.

1. **Derive agent and model**:
   - `agent` — stable snake_case runtime identifier: `claude_code` (Claude Code), `gemini_cli` (Gemini CLI), `codex` (Codex/OpenAI CLI), or a descriptive snake_case name for custom runtimes
   - `model` — active model name from the runtime (e.g. `claude-sonnet-4-6`); use `{agent}/unknown` if unavailable

2. **Save feature entry** — run:
   ```bash
   ~/.agents/.venv/bin/python ~/.agents/scripts/sidecar_workflow.py save \
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

3. **Output the UUID** — the workflow prints the UUID to stdout. Append it to the response:
   ```
   Feature saved — UUID: {uuid}
   ```

If the save fails, report the error in one line and continue — do not interrupt or re-render the feature output.

## Response format

Start every response with the `## Feature` heading (plain, not in a code block). Render output directly beneath it.

---
name: fix
description: Use after a completed review when the user wants specific findings fixed with minimal scope and no re-analysis. Trigger with `/fix` (Claude/Gemini), `$fix` (agent-to-agent), "fix the findings", "apply fixes", or "fix finding N".
---

## Invocation Modes

Invocation syntax varies by runtime:

- Claude / Gemini CLI: `/fix`, `/fix sidecar`, `/fix sidecar {uuid}`
- Agent-to-agent (any model): `$fix`, `$fix sidecar`, `$fix sidecar {uuid}`

### `fix` (no args)

Use the review findings from the current session.

- If no prior review exists in the session: STOP — report `Error: no prior review found. Run $review first.`
- If the user does not specify finding IDs: treat as "fix all findings from the latest review" — do not ask for clarification.

### `fix sidecar`

Load the most recent open `review` entry from the sidecar using the fix workflow helper. Do not invoke or activate the $sidecar skill.

```bash
~/.agents/.venv/bin/python ~/.agents/scripts/fix_workflow.py get_review
```

Extract:

- `scope` — top-level row field; use as the required work scope and require matching active $context scope before edits
- `context.findings` — source of truth for what to fix; each finding has `category`, `location`, `description`, `severity` (`critical|high|medium|low`), `confidence`, and `fix_direction`
- `context.reasoning` — analytical context explaining why each finding matters

If no entry is found: STOP — report `Error: no review entry found in sidecar.`

### `fix sidecar {uuid}`

Load a specific review entry from the sidecar using the fix workflow helper. Do not invoke or activate the $sidecar skill.

```bash
~/.agents/.venv/bin/python ~/.agents/scripts/fix_workflow.py get_review \
  --review_uuid "{uuid}"
```

Extract the same fields as above.

If no entry is found: STOP — report `Error: no sidecar entry found for uuid {uuid}.`

## Fast Path

If the fix touches a single file and requires ≤5 lines changed — regardless of findings source (session or sidecar):

- skip planning
- return minimal patch directly
- do not add tests unless explicitly required
- do not include explanations

## Preconditions

- Treat the review findings as the source of truth regardless of source (session or sidecar).
- Fix only the findings the user asked to address.
- Do not re-review the whole target or expand into unrelated cleanup.
- Accept explicit finding IDs or references when provided and limit fixes strictly to them.

## Workflow

If a scoped context is not active and source is session:

- STOP
- run $context first

If source is sidecar:

- use the top-level `scope` field from the loaded entry as the required work scope
- if active $context scope is absent or differs from the loaded `scope`: STOP — report `Run $context {scope} before applying this sidecar fix.`

1. Read `AGENTS.md` first. If absent, skip and proceed from the scoped path only.
2. Obey the active scope and nearest applicable `AGENTS.md`.
3. Read only:
   - the specific files named in the review findings, not the full target tree
   - at most one directly called or imported file from the fix site if required for safety
   - existing tests for the touched area
4. For multi-hunk or non-trivial fixes, run `git log -5 --oneline -- {file}` and `git blame -L {start},{end} {file}` on the affected lines before editing. Use this to understand recent change history and avoid re-introducing reverted patterns.
5. Start from the review findings and reasoning, not from fresh exploration.
6. When fixing multiple findings, address in severity order: `critical` → `high` → `medium` → `low`. For each fix: follow `fix_direction` from the finding; apply the smallest safe change using existing project utilities or stdlib before introducing anything new.
7. Implement the narrowest fix set first.
8. Validate only what is needed for the changed area.

## Post-Edit Validation

After each edit, re-read the changed lines and confirm:

- the change addresses the finding's `description` and follows its `fix_direction`
- no new issues are introduced in the changed block
- the surrounding call sites are not broken by the change

If a change does not satisfy these checks: revert it, state why in one line, and stop — do not attempt an alternative fix without user input.

## Fix Scope Gate

Do not introduce new findings.

If an issue is encountered that is not part of the provided review:

- ignore it
- do not fix it
- do not mention it unless it blocks the requested fix

## Execution Rules

- Do not ask for clarification if the intent can be reasonably inferred from the latest review or command
- Do not pause or ask questions once execution has started unless blocked
- Do not re-analyze architecture unless required for the fix
- Do not refactor beyond what the fix requires
- Do not rename, move, or reorganize code unless necessary for correctness
- Do not re-run review or re-evaluate severity of findings
- Keep edits local and reversible
- Optimize for low LOC and clarity

## Output

Fast Path — return patch directly with no preamble.

Full Path — use this shape:

```md
## Fix

### Fix Scope
- Findings: ...
- Files: ...
- Tests: ...

### Approach
built-in / existing project utility / existing dependency / minimal bespoke

---

{patch or targeted edit}
```

Keep the plan to 3–6 bullets. Do not include broad analysis.

## Code Output Rules

After the plan (or immediately for Fast Path):

- return:
  - plan
  - followed by code or diff/patch
- no chain-of-thought
- do not add explanations beyond the plan
- no alternative designs
- no extra improvements
- keep output as small as practical

## Testing

- **Fast Path**: skip tests unless the finding explicitly requires a test change.
- **Full Path**: draft the minimal test alongside the fix in the same output block — not as a separate step after. Co-locating patch and test in the same context window improves correctness of both.
- Add or update only the test case(s) directly covering the fixed behavior; do not add broad new test infrastructure.
- Prefer existing test style, helpers, and fixtures.
- After applying edits, run the test, lint, and static-check commands specified in `AGENTS.md` (loaded during `$context`). Use only those commands — do not guess or discover alternatives.

## Failure Mode

If a requested fix cannot be done safely within current scope:

- state the blocker in 1–2 sentences
- name the exact extra file or dependency context required
- stop there

## Style

- Direct
- Minimal
- Review-driven
- No overthinking
- No scope creep

## Save to Sidecar

Before the final response, if a review entry UUID is available from sidecar or from the current session, persist the fix using the fix workflow helper. Do not invoke or activate the $sidecar skill.

1. **Derive agent and model**:
   - `agent` — stable snake_case runtime identifier: `claude_code` (Claude Code), `gemini_cli` (Gemini CLI), `codex` (Codex/OpenAI CLI), or a descriptive snake_case name for custom runtimes
   - `model` — active model name from the runtime (e.g. `claude-sonnet-4-6`); use `{agent}/unknown` if unavailable

2. **Save fix entry** — run:

   ```bash
   ~/.agents/.venv/bin/python ~/.agents/scripts/fix_workflow.py save_fix \
     --agent "{agent}" \
     --model "{model}" \
     --review_uuid "{review_uuid}" \
     --scope "{scope}" \
     --context - \
     --context_input stdin \
     <<'JSON'
   {context_json}
   JSON
   ```

   The JSON payload must contain:

     ```json
     {
       "findings_fixed": [{"location": "...", "description": "..."}],
       "summary": "one-sentence summary of what was fixed"
     }
     ```

3. **Output the UUID** — the workflow prints the fix UUID to stdout. Append it to the response:

   ```text
   Fix saved — UUID: {fix_uuid}
   ```

If persistence fails, report the error in one line in the final response and continue — do not re-render the fix output.

If no review entry UUID is available, skip steps 2–3.

## Response format

Start every response with the `## Fix` heading (plain, not in a code block). Render output directly beneath it.

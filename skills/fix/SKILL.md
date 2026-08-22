---
name: fix
description: Use after a completed review when the user wants specific review findings fixed with minimal scope, targeted validation, and no broad re-review. Trigger with `/fix` (Claude/Gemini), `$fix` (agent-to-agent), "fix the findings", "apply fixes", or "fix finding N".
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
- `context.review_mode` — `change|path|symbol` when persisted by review
- `context.target_symbol` — reviewed symbol when `review_mode` is `symbol`
- `context.source_workflow` / `context.source_uuid` — workflow provenance when available

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

Use Fast Path only when all of the following are true:

- the fix touches a single file
- the implementation change is ≤5 lines
- the finding is `confirmed`
- the fix does **not** change testable runtime behavior, persisted data, public/API/CLI/config contracts, security-sensitive behavior, or error-handling semantics
- the finding does not explicitly require a test, migration, compatibility shim, documentation update, or multi-file change

Examples that may qualify: import correction, typo, dead reference, deterministic metadata/config correction, or equivalent non-behavioral edit.

Fast Path:

- skip planning
- return the minimal patch directly
- do not add tests unless the finding explicitly requires one
- still perform the applicable fresh verification required by `AGENTS.md`
- do not include explanations

Any behavioral correctness, security, compatibility, migration, or regression fix uses Full Path regardless of LOC.

## Preconditions

- Treat the review findings as the authoritative remediation contract regardless of source (session or sidecar). `description`, `confidence`, and `fix_direction` define what must be addressed.
- Do not re-run review, re-rank severity, or broaden the finding into a fresh architecture/code-quality investigation.
- Fix only the findings the user asked to address.
- Do not re-review the whole target or expand into unrelated cleanup.
- Accept explicit finding IDs or references when provided and limit fixes strictly to them.
- A `confirmed` finding may proceed directly to implementation.
- A `likely` finding requires **finding-local assumption verification** before editing:
  - verify only the specific uncertainty that prevented `review` from marking it confirmed
  - use only the already-allowed scope and at most the same adjacent-context allowance described below
  - do not perform a general re-review
  - if the assumption is confirmed, proceed with the existing `fix_direction`
  - if the assumption is disproved or cannot be verified safely within scope, STOP and report the mismatch/blocker; do not invent a replacement finding or fix direction
- Prior agent claims such as "fixed", "works", or "tests pass" are not verification evidence.

## Workflow

If a scoped context is not active and source is session:

- STOP
- run $context first

If source is sidecar:

- use the top-level `scope` field from the loaded entry as the required work scope
- if active $context scope is absent or differs from the loaded `scope`: STOP — report `Run $context {scope} before applying this sidecar fix.`

1. Use the repo instructions already loaded by `$context`. Read an additional nearest applicable `AGENTS.md` only if it is inside `scope_boundaries.allowed`, applies to a required fix touchpoint, and was not already loaded.
2. Obey the active scope and applicable instructions established by `$context`.
3. Read only:
   - the specific files named in the review findings, not the full target tree
   - at most one directly called or imported file from the fix site if required for safety
   - existing tests for the touched area
   - when the source review mode is `symbol`, only the minimum surrounding code needed to implement that symbol's finding

   For Symbol review findings, preserve the reviewed symbol as the primary edit boundary. Edits elsewhere in the containing file or allowed adjacent context are permitted only when required by that finding's `fix_direction`; access to the containing file is not permission for unrelated edits.
4. For multi-hunk or non-trivial fixes, run `git log -5 --oneline -- {file}` and `git blame -L {start},{end} {file}` on the affected lines before editing. Use this to understand recent change history and avoid re-introducing reverted patterns.
5. Start from the review findings and reasoning, not from fresh exploration.
6. For `likely` findings, perform only the finding-local assumption verification required by Preconditions before making edits.
7. When fixing multiple findings, address in severity order: `critical` → `high` → `medium` → `low`. For each fix: follow `fix_direction` from the finding; apply the smallest safe change using existing project utilities or stdlib before introducing anything new.
8. Implement the narrowest fix set first.
9. For any fix that changes testable behavior, first add or update the smallest regression test that demonstrates the reviewed failure mode or acceptance condition. Verify that the test would fail against the pre-fix behavior when this can be done safely and without destructive state changes; then apply the production fix.
10. Validate only what is needed for the changed area and collect fresh evidence before claiming success.

## Post-Edit Validation

After each edit, re-read the changed lines and confirm:

- the change addresses the finding's `description` and follows its `fix_direction`
- any finding-local assumption verified for a `likely` finding still holds after the edit
- no new issues are introduced in the changed block
- the surrounding call sites are not broken by the change

Then run the smallest applicable verification command(s) required by `AGENTS.md` for the changed area.

A fix may be reported as successful only when there is **fresh verification evidence from the current edit**. The existence of tests, a prior passing run, or an implementer's claim is not sufficient.

If the first edit fails the local checks or fresh verification:

1. revert only that attempted edit
2. inspect the failure evidence narrowly to determine why the provided `fix_direction` did not work as expected
3. make at most **one** alternative attempt that still addresses the same finding and stays within the same scope
4. verify again with fresh evidence

Never stack speculative fixes.

If the second attempt fails, or if a safe alternative would require changing the finding's meaning, severity, scope, or fix direction: revert the failed attempt, state the blocker in one line, and stop. Acceptance or re-diagnosis belongs to `review`, not `fix`.

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
- Do not reinterpret a failed finding into a different issue; stop and hand it back to `review`
- Do not claim a finding is fixed without fresh verification evidence
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

### Verification
- Regression evidence: ...
- Fresh checks: ...

---

{patch or targeted edit}
```

Keep the plan to 3–6 bullets. Do not include broad analysis.

## Code Output Rules

After the plan (or immediately for Fast Path):

- return:
  - plan
  - concise verification evidence
  - followed by code or diff/patch
- no chain-of-thought
- do not add explanations beyond the plan
- no alternative designs
- no extra improvements
- keep output as small as practical

## Testing

- **Fast Path**: tests are optional only because Fast Path excludes testable behavioral changes. If the finding itself explicitly requires a test, Fast Path does not apply.
- **Full Path behavioral fix**: add or update the smallest regression test directly covering the reviewed behavior, even when the production edit is ≤5 LOC.
- **Full Path non-behavioral fix**: add or update a test only when the finding requires one or existing project practice makes it necessary.
- Draft the minimal test alongside the fix in the same output block — not as a separate broad testing phase.
- Add or update only the test case(s) directly covering the fixed behavior; do not add broad new test infrastructure.
- Prefer existing test style, helpers, and fixtures.
- When practical and safe, establish RED evidence for behavioral fixes: confirm the regression test fails for the reviewed reason before applying the production change. Do not create destructive or out-of-scope state merely to force RED.
- After applying edits, run the applicable test, lint, and static-check commands established by the instructions loaded during `$context`. Use only established commands — do not guess or discover alternatives.
- Inspect the fresh command result before reporting success. If a required command cannot be run, report the verification gap and do not mark the affected finding as successfully fixed.

## Review / Fix Ownership

Maintain a strict lifecycle boundary:

- `review` owns diagnosis, severity, confidence, fix direction, and acceptance/verdict
- `fix` owns narrow remediation, regression protection, and local verification
- `fix` must not convert `likely` → `confirmed`; it may only verify the specific assumption needed to decide whether the prescribed fix is safe to execute
- `fix` must not mark the overall review `ready`
- after fixes complete, re-review is the authority for determining whether findings are closed and whether the implementation is acceptable

## Failure Mode

If a requested fix cannot be done safely within current scope:

- state the blocker in 1–2 sentences
- name the exact extra file or dependency context required
- stop there

Also stop and hand control back to `review` when:

- a `likely` finding's required assumption is disproved
- the finding's `fix_direction` is incompatible with the inspected code
- two narrow implementation attempts fail
- fresh verification contradicts the review finding or reveals that satisfying it requires a materially different fix
- resolving the issue would require changing severity, broadening scope, or inventing a new finding

## Style

- Direct
- Minimal
- Review-driven
- No overthinking
- No scope creep

## Handoff

After at least one requested finding is successfully fixed and freshly verified, hand off to `$review`.

- Re-review should preserve the prior review mode and target when possible:
  - Change review → re-review the same implementation/change boundary with the fix delta included
  - Path review → re-review the same path
  - Symbol review → re-review the same symbol
- `$fix` does not declare findings closed or the change `ready`; only `$review` may do so.
- If fixing stopped because the original finding was disproved or materially incompatible with the code, hand back to `$review` as a diagnosis mismatch rather than as a completed fix.

Render on successful fix:

```markdown
### Handoff
`$review` — re-review the fixed findings in the original review mode and determine whether they are closed.
```

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
       "summary": "one-sentence summary of what was fixed",
       "verification": "fresh test/lint/static-check evidence used to support the fix",
       "review_mode": "change|path|symbol when available",
       "target_symbol": "exact symbol when review_mode is symbol; omit otherwise",
       "source_review_uuid": "review UUID when available"
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

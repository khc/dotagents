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
Resolve project root, then load the most recent `review` entry from the sidecar using the $sidecar `read` operation filtered by `project`, `skill=review`, and `status=open`. Extract:
- `scope` — top-level row field; use as the active scope, do not re-derive from $switch
- `context.findings` — source of truth for what to fix; each finding has `category`, `location`, `description`, `severity` (`critical|high|medium|low`), `confidence`, and `fix_direction`
- `context.reasoning` — analytical context explaining why each finding matters

If no entry is found: STOP — report `Error: no review entry found in sidecar.`

### `fix sidecar {uuid}`
Resolve project root, then load a specific review entry from the sidecar using the $sidecar `read` operation filtered by `uuid={uuid}`. Extract the same fields as above.

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
- run $switch first

If source is sidecar:
- resolve project root per $sidecar Locate Project Root; derive `project` as `basename` of that path
- use the top-level `scope` field from the loaded entry as the active scope — do not run $switch

1. Read `AGENTS.md` first. If absent, skip and proceed from the scoped path only.
2. Obey the active scope and nearest applicable `AGENTS.md`.
3. Read only:
   - the specific files named in the review findings, not the full target tree
   - at most one directly called or imported file from the fix site if required for safety
   - existing tests for the touched area
4. Start from the review findings and reasoning, not from fresh exploration.
5. When fixing multiple findings, address in severity order: `critical` → `high` → `medium` → `low`. For each fix: follow `fix_direction` from the finding; apply the smallest safe change using existing project utilities or stdlib before introducing anything new.
6. Implement the narrowest fix set first.
7. Validate only what is needed for the changed area.

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

````markdown
## Fix

### Fix Scope
- Findings: ...
- Files: ...
- Tests: ...

### Approach
built-in / existing project utility / existing dependency / minimal bespoke

---

{patch or targeted edit}
````

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

- Skip entirely for Fast Path unless the finding explicitly requires a test change
- Otherwise add or update minimal tests for the fixed behavior
- Prefer existing test style and helpers
- Do not add broad new test infrastructure

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

After rendering fix output, if a review entry UUID is available from sidecar or from the current session:

1. **Save fix entry** — invoke $sidecar `save` with:
   - `skill` — `fix`
   - `scope` — same scope as the loaded review entry
   - `agent` / `model` — current runtime identity
   - `parent_uuid` — UUID of the review entry
   - `relation` — `fix`
   - `context` — JSON:
     ```json
     {
       "findings_fixed": [{"location": "...", "description": "..."}],
       "summary": "one-sentence summary of what was fixed"
     }
     ```

2. **Update review entry** — invoke $sidecar `update` with:
   - `uuid` — UUID of the review entry
   - `status` — `fixed`

Run both steps after output is rendered, not before. If either fails, report the error in one line and continue — do not re-render the fix output.

If no review entry UUID is available, skip both steps.

## Response format

Start every response with the `## Fix` heading (plain, not in a code block). Render output directly beneath it.

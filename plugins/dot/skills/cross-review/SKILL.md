---
name: cross-review
description: Use when the user or an active workflow wants a multi-agent review of a path, symbol, or change. Fans out independent fresh reviewers on Claude, Codex, and Agy through the workflow runner, then synthesizes their saved reviews into one final evidence-backed review. Trigger with `/dot:cross-review`, `$dot:cross-review`, "cross-review this", or "get a second and third opinion". Not for a single-agent review; use `$dot:review` for that.
---

# Cross-Review

## Local skill compatibility

Resolve internal skill invocations against the current skill catalog. Prefer `dot:<name>` when available. When this skill is loaded locally without the plugin namespace (for example in Codex VS Code), use the unqualified skill name for every `dot:<name>` invocation and handoff in these instructions. Resolve bundled resources from the actual skill file with symlinks resolved; the plugin remains the resource root.

Run independent reviewers on several coding agents, then act as the main reviewer: consolidate their saved reviews into one final review and save it to the sidecar.

The reviewers run `$dot:review` in separate fresh processes started by the workflow runner. This skill never invokes `$dot:review`, `$dot:fix`, or any other skill in its own context, and it never edits code.

## Bundled Helpers

Resolve `dot_plugin_root` from this loaded skill's file path: `Path(skill_file).resolve().parents[2]`. In Claude Code, `${CLAUDE_PLUGIN_ROOT}` is substituted in loaded Markdown; in Codex, use the actual `SKILL.md` path from the skill catalog. Set the shell variable `dot_plugin_root` to that resolved absolute path before running the commands below; do not assume a plugin variable exists in the shell.

Run helpers with `uv` from the target repository's current working directory.

## Workflow Gate

If an active scope is not established:

- STOP
- run `$dot:scope` first
- after `$dot:scope` completes, confirm the active scope path, then continue
- do not infer scope from the review target path alone

The active scope boundary is authoritative for every read in this skill.

## Inputs

- the review target and any requirements, plan, or change range, from the user or from the workflow request file
- the active scope
- optional runtimes: use the ones the user or workflow prompt names, otherwise `claude,codex,agy`

## Protocol

1. **Fan out.** Write the target and requirements to a temporary file, then run the reviewers with `uv run --no-project "$dot_plugin_root/skills/workflow/bin/workflow.py" review-fanout --scope '<scope>' --runtimes <csv> --request-file '<temp file>'`. Never put request text directly on the command line. When a workflow prompt supplies a complete `review-fanout --state-dir ...` command, run that command instead.
   - The first output line is `FANOUT_RESULT=<path>`. The final report is printed as JSON and written atomically to that unique path (`<state dir>/fanout-<run_id>.json`). Each run has its own path; never read any other `fanout-*.json` file, because earlier review rounds leave theirs in the same directory.
   - Worst case runtime is two attempts of `--review-timeout` (default 900 s) per reviewer. If the runtime's tool-call limit is shorter than that, run the command in the background, read the `FANOUT_RESULT` path from its first output line, and poll for exactly that file.
   - If the command exits non-zero or `ok` is `false`: STOP. Report `blocked` with each failed reviewer's `runtime` and `blocker`. Do not synthesize a partial ensemble.
2. **Load the reviews.** For each `review_uuid` in the fan-out report, run `uv run --no-project "$dot_plugin_root/scripts/sidecar_workflow.py" read --uuid '<uuid>' --start-path '<scope>'`. Read `context.findings`, `context.verdict`, and `context.reasoning`.
3. **Normalize and merge.** Map every finding to the six sidecar keys (`category`, `location`, `description`, `severity`, `confidence`, `fix_direction`). Merge findings that share a root cause into one. In `reasoning`, record for each merged finding which reviewers raised it: `unanimous`, `majority`, `single`, or `disputed`.
4. **List disagreements.** Severity conflicts on the same finding, findings only some reviewers raised, and verdict conflicts.
5. **Verify.** Verify every `single` and `disputed` finding against the code, read-only, within the active scope.
   - Evidence holds: keep the finding at the verified severity with `confidence: confirmed`.
   - The cited evidence does not exist: drop it and record `{"reviewer", "location", "reason"}` in `cross_review.dropped_findings`.
   - It cannot be verified either way: keep it with `confidence: likely`, severity capped at `medium` or the lowest severity any reviewer reported, whichever is lower.
6. **Write the final review** in the `$dot:review` Output format and verdict rules (see the Output and verdict rules in `skills/review/SKILL.md`; do not restate them). Do not add findings no reviewer raised unless needed to resolve a dispute. Verdict `ready` only when the merged findings are empty.
7. **Save to the sidecar** with the review skill's Save to Sidecar step (`review_workflow.py`, so the entry has `skill="review"` and `$dot:fix` can load it). The payload keeps the six finding keys and adds:

   ```json
   "cross_review": {
     "reviewers": [{"runtime": "...", "review_uuid": "...", "verdict": "...", "findings_count": 0}],
     "source_review_uuids": ["..."],
     "dropped_findings": []
   }
   ```

8. **Supersede the sources.** After the save succeeds, run `uv run --no-project "$dot_plugin_root/scripts/sidecar_workflow.py" update --uuid '<source uuid>' --status superseded --start-path '<scope>'` for each source review UUID. If an update fails, note it in one line in `reasoning` and continue.
9. **Workflow envelope.** When a workflow prompt asked for an `ORCHESTRATION_RESULT`, append exactly one for `stage: "review"` after the review. Normalize it as `$dot:workflow` does: `ready` only for verdict `ready` with zero findings, `findings` when any finding remains, `blocked` when fan-out failed or a scope/evidence blocker prevents a valid review. Put the consolidated entry's UUID in `review_uuid`.

## Rules

- Reviewer output is a claim, not evidence; verify against the code.
- Stay inside `scope_boundaries.allowed`; if verifying a finding needs a path outside it, follow the scope Failure Mode.
- Do not modify reviewer sidecar entries except the `superseded` status update in step 8.
- Do not dispatch further reviewers beyond the single `review-fanout` call.

## Output

Start with the `## Review` heading as defined in `skills/review/SKILL.md`. State the participating reviewers and the disagreements you resolved in `**Reasoning:**`. Finish with the line `Review saved — UUID: {uuid}` for the consolidated entry.

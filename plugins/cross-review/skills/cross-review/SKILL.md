---
name: cross-review
description: Use when the user wants a multi-agent review of a path, symbol, or change. Fans out independent fresh reviewers on Claude, Codex, and Agy through the fan-out runner, then synthesizes their saved reviews into one final evidence-backed review. Trigger with `/cross-review:cross-review`, "cross-review this", or "get a second and third opinion". Not for a single-agent review; use `$dot:review` for that.
compatibility: Requires the dot plugin (its review skill and helper scripts), git and uv.
---

# Cross-Review

## Local skill compatibility

Resolve internal skill invocations against the current skill catalog. Prefer `dot:<name>` when available. When this skill is loaded locally without the plugin namespace (for example in Codex VS Code), use the unqualified skill name for every `dot:<name>` invocation and handoff in these instructions. Resolve bundled resources from the actual skill file with symlinks resolved; the plugin remains the resource root.

Run independent reviewers on several coding agents, then act as the main reviewer: consolidate their saved reviews into one final review and save it to the sidecar.

The reviewers run `$dot:review` in separate fresh processes started by the fan-out runner. This skill never invokes `$dot:review`, `$dot:fix`, or any other skill in its own context, and it never edits code.

## Bundled Helpers

Resolve two plugin roots before running the commands below, and set both as shell variables; do not assume a plugin variable exists in the shell.

- `cross_review_root` is this plugin: `Path(skill_file).resolve().parents[2]`. In Claude Code, `${CLAUDE_PLUGIN_ROOT}` is substituted in loaded Markdown; in Codex, use the actual `SKILL.md` path from the skill catalog.
- `dot_plugin_root` is the `dot` plugin, which provides `$dot:review` and the helper scripts: the path the user gave, else the `DOT_PLUGIN_ROOT` environment variable, else `$cross_review_root/../dot`. If `$dot_plugin_root/scripts/review_workflow.py` does not exist, STOP and report `Error: the dot plugin was not found; set DOT_PLUGIN_ROOT.`

Run helpers with `uv` from the target repository's current working directory.

## Workflow Gate

If an active scope is not established:

- STOP
- run `$dot:scope` first
- after `$dot:scope` completes, confirm the active scope path, then continue
- do not infer scope from the review target path alone

The active scope boundary is authoritative for every read in this skill.

## Inputs

- the arguments: exactly the text the user typed after the skill name. Pass them to the fan-out unchanged; never summarize, correct, expand, or add requirements to them
- the active scope (a file or a directory)
- optional runtimes: use the ones the user names, otherwise `claude,codex,agy`

## Protocol

1. **Fan out.** Follow `references/fanout.md` exactly: write the user's arguments, unchanged, to a request file with your file-writing tool, then run `uv run --no-project --locked "$cross_review_root/scripts/review_fanout.py" --dot-plugin-root "$dot_plugin_root" --scope '<active scope>' --runtimes <csv> --request-file '<request file>'`.
   - The reference has the setup, background polling for `FANOUT_RESULT=<path>`, the output contract, and what to do for each blocker. The fan-out report is runner output, not a repository file, so reading it is allowed for any scope.
   - If the command exits non-zero or `ok` is `false`: STOP. Report `blocked` with each failed reviewer's `runtime` and `blocker`. Do not synthesize a partial ensemble.
2. **Load the reviews.** For each `review_uuid` in the fan-out report, run `uv run --no-project --locked "$dot_plugin_root/scripts/sidecar_workflow.py" read --uuid '<uuid>' --start-path '<scope>'`. Read `context.findings`, `context.verdict`, and `context.reasoning`.
3. **Normalize and merge.** Map every finding to the six sidecar keys (`category`, `location`, `description`, `severity`, `confidence`, `fix_direction`). Merge findings that share a root cause into one. In `reasoning`, record for each merged finding which reviewers raised it: `unanimous`, `majority`, `single`, or `disputed`.
4. **List disagreements.** Severity conflicts on the same finding, findings only some reviewers raised, and verdict conflicts.
5. **Verify.** Verify every `single` and `disputed` finding against the code, read-only, within the active scope.
   - Evidence holds: keep the finding at the verified severity with `confidence: confirmed`.
   - The cited evidence does not exist: drop it and record `{"reviewer", "location", "reason"}` in `cross_review.dropped_findings`.
   - It cannot be verified either way: keep it with `confidence: likely`, severity capped at `medium` or the lowest severity any reviewer reported, whichever is lower.
6. **Write the final review** in the `$dot:review` Output format and verdict rules (see the Output and verdict rules of the `$dot:review` skill; do not restate them). Do not add findings no reviewer raised unless needed to resolve a dispute. Verdict `ready` only when the merged findings are empty.
7. **Save to the sidecar** with the review skill's Save to Sidecar step (`"$dot_plugin_root/scripts/review_workflow.py"`, so the entry has `skill="review"` and `$dot:fix` can load it). The payload keeps the six finding keys and adds:

   ```json
   "cross_review": {
     "reviewers": [{"runtime": "...", "review_uuid": "...", "verdict": "...", "findings_count": 0}],
     "source_review_uuids": ["..."],
     "dropped_findings": []
   }
   ```

8. **Supersede the sources.** After the save succeeds, run `uv run --no-project --locked "$dot_plugin_root/scripts/sidecar_workflow.py" update --uuid '<source uuid>' --status superseded --start-path '<scope>'` for each source review UUID. If an update fails, note it in one line in `reasoning` and continue.

## Rules

- Reviewer output is a claim, not evidence; verify against the code.
- Stay inside `scope_boundaries.allowed`; if verifying a finding needs a path outside it, follow the scope Failure Mode.
- Do not modify reviewer sidecar entries except the `superseded` status update in step 8.
- Do not dispatch further reviewers beyond the single `review_fanout.py` call.

## Output

Start with the `## Review` heading as defined by the `$dot:review` skill. State the participating reviewers and the disagreements you resolved in `**Reasoning:**`. Finish with the line `Review saved — UUID: {uuid}` for the consolidated entry.

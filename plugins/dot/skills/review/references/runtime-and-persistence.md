# Runtime and persistence

Helper resolution and sidecar persistence for `dot:review`. Loaded when the review is ready to be saved.

## Bundled helpers

Resolve `dot_plugin_root` from the loaded `SKILL.md` path: `Path(skill_file).resolve().parents[2]`. In Claude Code, `${CLAUDE_PLUGIN_ROOT}` is substituted in loaded Markdown; in Codex, use the actual `SKILL.md` path from the skill catalog. Set the shell variable `dot_plugin_root` to that resolved absolute path before running the helper commands below; do not assume a plugin variable exists in the shell.

Run helpers with `uv` from the target repository's current working directory. Plugin paths locate resources; `scope_path` and `repo_root` describe the target project. `uv` manages Python 3.14 and the inline dependencies without using a checkout-specific virtual environment.

## Save to Sidecar

After composing the review output and before sending the final response, persist the entry using the direct sidecar script. Do not invoke or activate the $sidecar skill.

1. **Derive agent and model**:
   - `agent` — stable snake_case runtime identifier: `claude_code` (Claude Code), `gemini_cli` (Gemini CLI), `codex` (Codex/OpenAI CLI), or a descriptive snake_case name for custom runtimes
   - `model` — active model name from the runtime (e.g. `claude-sonnet-4-6`); use `{agent}/unknown` if unavailable

2. **Save review entry** — run:

   ```bash
   uv run --no-project "$dot_plugin_root/scripts/review_workflow.py" \
     --context - \
     --context-input stdin \
     --scope '{scope}' \
     --agent '{agent}' \
     --model '{model}' \
     <<'JSON'
   {context_json}
   JSON
   ```

   This helper resolves `{project_root}`, creates `{project_root}/.sidecar`, and persists the review entry. If `{project_root}/.sidecar` is outside the active scope and the runtime enforces scoped writes, request approval for this persistence write before invoking the helper. Single-quote `{scope}`, `{agent}`, and `{model}` when substituting, and escape any embedded `'` as `'\''`, to prevent `$()`/backtick shell expansion from a scope path.
   The JSON payload follows the [review contract](review-contract.md) (`schema_version` `2`); the helper rejects an invalid payload and writes nothing. It must contain:
   - `schema_version` — `2`
   - `verification_gaps` — list of `{description, material, effect}` (empty list when none)
   - `target` — the file or path reviewed
   - `review_mode` — `change|path|symbol`
   - `target_symbol` — exact reviewed symbol for Symbol review; omit otherwise
   - `source_workflow` — `feature|implement|bug|refactor|fix|standalone`
   - `source_uuid` — originating feature/implement/plan entry identifier when available
   - `base_sha` — reviewed change base when available
   - `head_sha` — reviewed change head/current HEAD when available
   - `findings` — list of dicts, one per finding: `{"finding_id": "F1", "category": "Security|Bugs|Design|Performance|Maintainability|Observability|Testing|Requirements / Plan|Production Readiness|Documentation|Library / Reuse", "location": ..., "description": ..., "severity": "critical|high|medium|low", "confidence": "confirmed|likely", "fix_direction": ..., "blocking": true|false, "status": "open", "evidence_refs": [...]}`
   - `summary` — one-sentence prose summary of the review
   - `reasoning` — analytical context for downstream agents: dominant concern, requirements/plan evidence used (or unavailable), Git range/diff evidence used (or unavailable), relevant test evidence, what was deprioritized and why, any constraints or scope limits observed
   - `verdict` — `ready|ready-with-fixes|not-ready`, equal to the aggregate verdict in the review contract

3. **Output the UUID** — the script prints the UUID to stdout. Append it to the response:

   ```text
   Review saved — UUID: {uuid}
   ```

If the save fails, report the error in one line and continue — do not interrupt or re-render the review.

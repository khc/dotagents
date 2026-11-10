# cross-review

Runs independent fresh reviewers on several coding agents (`claude`, `codex`, `agy`), then synthesizes their saved reviews into one final review and saves it to the sidecar.

This plugin contains one skill, `cross-review`, and the fan-out runner it uses (`scripts/review_fanout.py`).

## Requires the `dot` plugin

The reviewers run `$dot:review`, and the skill saves and reads reviews with `dot`'s `review_workflow.py` and `sidecar_workflow.py`. The runner reuses internal helpers from `dot`'s `skills/workflow/bin/workflow.py`. Install `dot` first.

The scripts look for the `dot` plugin root in this order and stop with a one-line error if none is found:

1. `--dot-plugin-root <path>`
2. the `DOT_PLUGIN_ROOT` environment variable
3. the sibling `../dot` directory of this plugin (a checkout of this repository)

## Run the fan-out

```bash
printf 'Review src/auth' > request.txt
uv run --no-project --locked scripts/review_fanout.py \
  --scope . --runtimes claude,codex,agy --request-file request.txt
```

Pass the request with `--request-file` (the skill does): `--request` puts the text on the command line.

`--runtimes` needs at least two runtimes. `--review-timeout` (default 900 seconds) bounds each reviewer; a missing or malformed result envelope is retried once, and any reviewer failure blocks the review. `--dry-run` prints the reviewer prompts without starting anything. The command prints `FANOUT_RESULT=<path>`, then the JSON report with each reviewer's sidecar UUID.

## Internal `dot` API this plugin relies on

From `dot`'s `workflow.py`: `stage_prompt` (including its optional `stage_input` and `runner_files` overrides, which this plugin uses to supply the independent-reviewer text), `run_process`, `parse_result`, `cli_command`, `ensure_prompt_fits`, `arguments_block`, `scope_dir`, `read_text_exact`, `write_text_exact`, and the constants `RUNTIMES`, `WORKFLOWS`, `MAX_PROMPT_BYTES`, `REREVIEW_NOTE`, `RESULT_RE`, `ROLE`, `STAGE_ID_FIELD`, `VALID_STATUS`. A change to any of these in `dot` must be checked against this plugin's smoke check (`uv run python scripts/smoke_check.py`), which also compares the reviewer prompts byte for byte with the golden files in `scripts/fixtures/`.

# Running the fan-out

Copy these steps as written. Do not look for another way to start the reviewers.

## 1. Setup

Resolve `dot_plugin_root` from the path of this skill's `SKILL.md`: `Path(skill_file).resolve().parents[2]`, where `skill_file` is `.../skills/cross-review/SKILL.md` (so the result is the directory that contains `skills/` and `scripts/`; do not apply it to this reference file). Set the shell variable before the commands below:

```bash
dot_plugin_root='<resolved plugin root>'
```

## 2. Write the request file

The reviewers must receive exactly what the user typed after `$dot:cross-review`. Create a temporary file (for example in the scratchpad or a temp directory) with your **file-writing tool**, not a shell heredoc or `echo`, so no quoting, expansion, or newline change can touch the text. The file content is the user's arguments, unchanged:

- no summary, correction, translation, or added requirements
- no trailing newline added or removed
- empty arguments mean an empty file (the reviewers are then told to review the active scope path)

## 3. Run the command

```bash
uv run --no-project "$dot_plugin_root/skills/workflow/bin/workflow.py" review-fanout \
  --scope '<active scope path, exactly as activated>' \
  --runtimes claude,codex,agy \
  --request-file '<request file from step 2>'
```

- The scope can be a file or a directory. Pass it unchanged; never substitute its parent directory.
- Use the runtimes the user named; otherwise `claude,codex,agy`. At least two are required.
- Do not pass `--state-dir` unless a workflow prompt supplied a complete command.
- Never pass rewritten text with `--request`; use `--request-file`.
- `--review-timeout` (default 900 seconds) bounds each reviewer. A reviewer gets one retry only for a missing or malformed result envelope.

Worst case is two attempts per reviewer. If your tool-call limit is shorter, run the command in the background, read the first output line `FANOUT_RESULT=<path>`, and poll for exactly that file. Never read another `fanout-*.json`; earlier review rounds leave theirs in the same directory.

## 4. Output contract

The first line is `FANOUT_RESULT=<path>`. The final report is printed as JSON and written atomically to that path:

```json
{
  "run_id": "...",
  "state_dir": "...",
  "ok": true,
  "reviewers": [
    {"runtime": "claude", "status": "findings", "verdict": "not-ready",
     "findings_count": 2, "review_uuid": "...", "blocker": null}
  ]
}
```

Decide the outcome from the output, not from the exit code alone:

- If no `FANOUT_RESULT=` line was printed, the command was wrong (see "Command errors" below). Argument errors exit `2` and a missing request exits `1`; neither prints a report.
- If `FANOUT_RESULT=` was printed, read the JSON report. Exit `0` with `ok: true` means every reviewer returned a saved review. Exit `2` with `ok: false` means at least one reviewer failed (next section).

The report and the `FANOUT_RESULT` file are runner output, not repository files. Reading them does not breach a narrow scope.

## 5. If a reviewer is blocked

STOP and report `blocked` with each failed reviewer's `runtime` and `blocker`. Never synthesize a partial ensemble and never drop a runtime on your own.

| `blocker` contains | Meaning | Action |
|---|---|---|
| `timed out after` | The reviewer exceeded `--review-timeout`. | Report it. Offer a larger `--review-timeout` or fewer runtimes; ask the user. |
| `did not emit` | The reviewer finished without the machine result envelope (also after one retry). | Report it; the reviewer CLI misbehaved. |
| `missing review_uuid` | The reviewer's review was not saved to the sidecar. | Check that `uv` works and the project's `.sidecar` is writable; report it. |
| `No such file or directory` | That reviewer CLI (`claude`, `codex`, or `agy`) is not installed or not on `PATH`. | Tell the user which CLI is missing and ask before running without that runtime. |
| `Argument list too long` | The prompt, which contains your typed arguments, exceeded the operating system's argument limit. | Report it; ask the user to shorten the request or point to a file inside the scope. |

### Command errors (no `FANOUT_RESULT=` line)

These come from the command itself on stderr, before any reviewer starts:

- `usage:` / `expected at least 2 runtimes`: fix the command and run it again.
- `--request or --request-file is required`: pass the request file from step 2.
- `request text is too large to pass verbatim as a command-line argument`: the typed arguments exceed about 100 KB. Ask the user to shorten them or to put the details in a file inside the scope and refer to its path.

## 6. Scope note

A single-file scope means a file-only review: reviewers cannot read neighbouring files such as tests or imports. If the user wants those included, ask them to activate a directory scope.

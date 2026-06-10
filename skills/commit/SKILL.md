---
name: commit
description: Generate a single Conventional Commit message from the current repo state (staged, unstaged, and untracked files). Trigger with `/commit`.
---

## Goal

Generate exactly one Conventional Commit message from the current repo state, then ask whether to proceed with the commit when user confirmation is **REQUIRED**.

## Inputs

- Staged-only flow: `git diff --staged`
- Any unstaged or untracked files present: current full repo change set, not just the staged subset

## Method

1. Run `git status --porcelain` to accurately identify all staged, unstaged, and untracked files.
2. If unstaged or untracked files exist, generate the message from the full intended commit contents, not only the staged subset.
3. If stat output is sufficient to identify the dominant change, generate the message directly.
4. Only pull `git diff <file>` for specific tracked files when the stat alone is ambiguous.
5. For untracked files, inspect only the specific files that are needed to understand the dominant change. Prefer direct file reads or `git diff --no-index -- /dev/null -- <file>` when a diff view is needed.
6. **NEVER** read saved tool output files. **NEVER** run bare `git diff` without a file target unless stat is insufficient.
7. Skip the following when pulling per-file diffs — infer their change from stat only:
   - lock files: `*.lock`, `*-lock.json`, `*.sum`
   - generated files: `*.min.js`, `*.min.css`, `dist/`, `build/`
   - binary files (detected via `git diff --stat` showing `Bin … bytes`)

## Decision

1. Pre-checks:
   - Not a git repo? → `Error: not a git repository.`
   - No staged, unstaged, or untracked files? → `Nothing to commit.`

2. Get State:
   - `repo_state_snapshot` = exact output of `git status --porcelain` (used to detect interim changes)

3. Workflow:
   - Generation Phase (No pending confirmation prompt):
     → Determine intended scope: staged files only (if no unstaged/untracked exist), otherwise the full tracked and untracked changeset.
     → Generate the commit message from the intended scope.
     → Render the commit preview using the Output format.
     → Store `repo_state_snapshot` with the generated message.
     → Ask `Proceed with commit?`

   - Confirmation Phase (User replied to `Proceed with commit?`):
     → Recompute `repo_state_now` = exact output of `git status --porcelain`.
     → If `repo_state_now` differs from `repo_state_snapshot`:
       - Do not commit with the stale message.
       - Restart the Generation Phase with the current state.
     → If `repo_state_now` exactly matches `repo_state_snapshot`:
       - If unstaged or untracked files exist, add them first (`git add -A`).
       - Run pre-commit validation gates (see Validation Gates below).
       - If validation passes, run `git commit` using the exact stored message.
       - If validation fails, report the error in one line and do not commit.

## Validation Gates

Before running `git commit`, execute the test, lint, and static-check commands specified in `AGENTS.md` (loaded during `$switch`). If any command fails, report the error in one line and do not proceed with the commit. Only run the commands that are defined in `AGENTS.md` — do not guess or discover alternatives.

## Output

When a commit message is generated and no commit has been run yet, use this response shape:

~~~markdown
# Commit

- 2-3 concise bullets summarizing the intended commit; merge overlapping points when possible.

## Files

| File | Status | Diff |
| --- | --- | --- |
| `path/to/file` | `M`, `MM`, `??` | fixed-width `+N / -N` counts |

- If `git status --porcelain` still matches `repo_state_snapshot`, unstaged and untracked files will be staged before commit.

## Message

```text
<type>[optional scope]: <description>
```

---
Do you want to proceed with commit?
~~~

- If unstaged or untracked files are present, include the snapshot note.
- Use one table row per changed file, capped at 10 rows, then add `…and N more`.
- Sort the file table by status from Modified to Untracked, or group rows by folder when that is easier to scan.
- Pad diff counts so the `+` and `-` values line up visually in the table.
- Keep exactly one commit message code fence.

## Rules

- Exactly one commit message per response
- Commit message **ALWAYS** in a code fence
- Prefer dominant change from diff
- Do not invent context
- Avoid vague descriptions

## Format

`<type>[optional scope]: <description>`

- lowercase type
- short, imperative, no period
- scope = short noun if obvious

## Types

- feat — new feature
- fix — bug fix
- docs — documentation
- refactor — code change without behavior change
- perf — performance
- test — tests
- build — build/deps
- ci — CI/CD
- chore — maintenance
- style — formatting
- revert — revert

## Optional

Use only if clearly needed:

- `!` for breaking change
- body (separate with one blank line)
- footer (e.g. `BREAKING CHANGE: ...`, `Refs #123`)

## Guidance

- Ignore unchanged context
- Focus on meaningful hunks only
- Do not mention filenames unless necessary

---
name: commit
description: Generate a single Conventional Commit message from the current git diff.
---

# Goal
Generate exactly one Conventional Commit message from the current repo state, then ask whether to proceed with the commit when user confirmation is required.

# Inputs
- Staged-only flow: `git diff --staged`
- Any unstaged or untracked files present: current full repo change set, not just the staged subset

# Method

1. Run `git diff --staged --stat` and `git diff --stat` to determine staged scope and full tracked-file scope.
2. If unstaged or untracked files exist, generate the message from the full intended commit contents, not only the staged subset.
3. If stat output is sufficient to identify the dominant change, generate the message directly.
4. Only pull `git diff <file>` for specific tracked files when the stat alone is ambiguous.
5. For untracked files, inspect only the specific files that are needed to understand the dominant change. Prefer direct file reads or `git diff --no-index -- /dev/null -- <file>` when a diff view is needed.
6. Never read saved tool output files. Never run bare `git diff` without a file target unless stat is insufficient.
7. Skip the following when pulling per-file diffs — infer their change from stat only:
   - lock files: `*.lock`, `*-lock.json`, `*.sum`
   - generated files: `*.min.js`, `*.min.css`, `dist/`, `build/`
   - binary files (detected via `git diff --stat` showing `Bin … bytes`)

# Decision

1. Get:
   - staged_files = `git diff --staged --name-only`
   - unstaged_files = `git diff --name-only`
   - untracked_files = `git ls-files --others --exclude-standard`
   - repo_state_snapshot = exact output of `git status --porcelain`

2. Cases:

- No staged + no unstaged + no untracked  
  → `Nothing to commit.`

- Staged only (no unstaged or untracked files)  
  → Generate commit message from staged diff  
  → Render the commit preview using the Output format  
  → Ask `Proceed with commit?`  
  → Store `repo_state_snapshot` with the generated message  
  → If user confirms and `git status --porcelain` still exactly matches `repo_state_snapshot`, run commit with the generated message

- Staged + unstaged/untracked  
  → Show changed files in the Output table (max 10, then `…and N more`)  
  → Generate message from the full intended commit contents, including the listed unstaged or untracked files  
  → Render the commit preview using the Output format  
  → Ask `Proceed with commit?`  
  → Store `repo_state_snapshot` with the generated message  
  → If user confirms and `git status --porcelain` still exactly matches `repo_state_snapshot`, add all unstaged/untracked files and run commit with the previously generated message

- Unstaged/untracked only  
  → Show changed files in the Output table (max 10, then `…and N more`)  
  → Generate message from the full intended commit contents, including the listed unstaged or untracked files  
  → Render the commit preview using the Output format  
  → Ask `Proceed with commit?`  
  → Store `repo_state_snapshot` with the generated message  
  → If user confirms and `git status --porcelain` still exactly matches `repo_state_snapshot`, add all unstaged/untracked files and run commit with the previously generated message

- Confirmation follow-up  
  → If the immediately previous `/commit` response asked `Proceed with commit?` and included a generated message  
  → Recompute `repo_state_now` = exact output of `git status --porcelain`  
  → If `repo_state_now` exactly matches the stored `repo_state_snapshot`, reuse that exact message  
  → If there are any unstaged or untracked files, add them first  
  → Run the commit  
  → If `repo_state_now` does not exactly match the stored `repo_state_snapshot`, do not commit with the stale message  
  → Regenerate the message from the current full intended commit contents, render the commit preview using the Output format, and ask `Proceed with commit?` again

# Output

When a commit message is generated and no commit has been run yet, use this response shape:

````markdown
# Commit

- 2-3 concise bullets summarizing the intended commit; merge overlapping points when possible.

## Files

| File | Status | Diff |
| --- | --- | --- |
| `path/to/file` | `M`, `MM`, `??` | fixed-width `+N / -N` counts |

If `git status --porcelain` still matches `repo_state_snapshot`, unstaged and untracked files will be staged before commit.

## Message

```text
<type>[optional scope]: <description>
```

---
Do you want to proceed with commit?
````

- Include the snapshot note only when unstaged or untracked files are present.
- Use one table row per changed file, capped at 10 rows, then add `…and N more`.
- Sort the file table by status from Modified to Untracked, or group rows by folder when that is easier to scan.
- Pad diff counts so the `+` and `-` values line up visually in the table.
- Keep exactly one commit message code fence.

# Rules

- Ask `Proceed with commit?` whenever a commit message is generated and no commit has been run yet
- When unstaged or untracked files exist, generate the message from the full intended commit contents, not the staged subset alone
- Before reusing a previously generated message, compare the exact `git status --porcelain` output to the stored `repo_state_snapshot`
- On confirmation, reuse the previously generated message only when that snapshot matches exactly
- If the snapshot changed, regenerate the message and ask `Proceed with commit?` again instead of committing with a stale message
- On confirmation, add any unstaged/untracked files before committing
- Exactly one commit message per response
- Commit message always in a code fence
- Prefer dominant change from diff
- Do not invent context
- Avoid vague descriptions

# Format

`<type>[optional scope]: <description>`

- lowercase type
- short, imperative, no period
- scope = short noun if obvious

# Types

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

# Optional

Use only if clearly needed:

- `!` for breaking change
- body (separate with one blank line)
- footer (e.g. `BREAKING CHANGE: ...`, `Refs #123`)

# Guidance

- Use staged diff only when every intended change is already staged
- If unstaged or untracked files exist, reason about the final commit contents, not just the staged subset
- Ignore unchanged context
- Focus on meaningful hunks only
- Do not mention filenames unless necessary

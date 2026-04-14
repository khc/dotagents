---
name: commit
description: Generate a single Conventional Commit message from the current git diff.
---

# Goal
Generate exactly one Conventional Commit message from the current repo state.

# Inputs
- Prefer: `git diff --staged`
- Fallback: `git diff`

# Method

1. Run `git diff --stat` (or `git diff --staged --stat`) to determine scope.
2. If stat output is sufficient to identify the dominant change, generate the message directly.
3. Only pull `git diff <file>` for specific files when the stat alone is ambiguous.
4. Never read saved tool output files. Never run bare `git diff` without a file target unless stat is insufficient.
5. Skip the following when pulling per-file diffs — infer their change from stat only:
   - lock files: `*.lock`, `*-lock.json`, `*.sum`
   - generated files: `*.min.js`, `*.min.css`, `dist/`, `build/`
   - binary files (detected via `git diff --stat` showing `Bin … bytes`)

# Decision

1. Get:
   - staged_files = `git diff --staged --name-only`
   - unstaged_files = `git status --porcelain`

2. Cases:

- No staged + no unstaged  
  → `Nothing to commit.`

- Staged only  
  → Generate commit message  
  → Output message  
  → Run commit

- Staged + unstaged  
  → `Skipped commit. Unstaged files present:`  
  → List files (Markdown bullets, backticked; max 10, then `…and N more`)  
  → Generate message from staged diff  
  → Output message  
  → DO NOT commit

- Unstaged only  
  → `Nothing staged. Unstaged files:`  
  → List files (Markdown bullets, backticked; max 10, then `…and N more`)  
  → Generate message from unstaged diff  
  → Output message  
  → DO NOT commit

# Rules

- Never commit if any unstaged files exist
- Output plain text only (no explanations, no code fences)
- Exactly one commit message
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

- Use staged diff if available, otherwise unstaged
- Ignore unchanged context
- Focus on meaningful hunks only
- Do not mention filenames unless necessary

---
name: commit
description: Generate one Conventional Commit message from the current git state. Trigger with `/commit`.
---

## Goal

Generate exactly one Conventional Commit message, save it with the commit workflow helper, then ask before committing.

## Flow

1. Run `git status --porcelain`.
2. If not in a git repo, output `Error: not a git repository.`
3. If there are no staged, unstaged, or untracked files, output `Nothing to commit.`
4. Treat the intended commit as:
   - staged files only when there are no unstaged or untracked files
   - all status-listed changes when any unstaged or untracked file exists
5. Use only files listed by `git status --porcelain`. Never inspect any other file.
6. Build bounded context from status-listed files only:
   - inspect enough non-skipped status-listed files to describe the whole intended commit
   - for staged-only tracked files, you may batch multiple files in one `git diff --staged -- <file1> <file2> ...`
   - for unstaged tracked files, you may batch multiple files in one `git diff -- <file1> <file2> ...`
   - for untracked files, run only `git diff --no-index -- /dev/null -- <file>` one file at a time
   - skip lock, generated, and binary files
7. Never run bare `git diff`, never inspect files outside `git status --porcelain`, never read saved tool output files, and never run helper commands with `--help`.
8. Generate one Conventional Commit message from the bounded context.
9. Save it exactly with:
   `~/.agents/scripts/commit_workflow.py save --agent "{agent}" --commit-message "{message}"`
10. Render the preview and ask `Proceed with commit?`

## Confirmation

When the user confirms, execute exactly:

`~/.agents/scripts/commit_workflow.py execute --uuid "{uuid}"`

- On success, output the helper success message.
- On state drift, restart the Flow.
- On validation failure, report the helper failure and stop.
- Never bypass the helper with direct `git add` or `git commit`.

## Preview Output

~~~markdown
# Commit

- concise summary bullet
- concise summary bullet

## Files

| File | Status |
| --- | --- |
| `path/to/file` | `M` |

## Message

```text
<type>[optional scope]: <description>
```

*(Sidecar entry: `{uuid}`)*

---
Proceed with commit?
~~~

Rules:
- exactly one message, always in one `text` code fence
- use lowercase Conventional Commit type: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `style`, or `revert`
- short imperative description, no period
- include the snapshot note if unstaged or untracked files will be staged by the helper
- cap file rows at 10, then add `...and N more`

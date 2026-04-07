---
name: commit
description: Generate a single Conventional Commit message from the current git diff.
---

# Commit Skill

## Goal
Generate exactly one commit message from the current repository diff, following Conventional Commits 1.0.0.

## Inputs
Inspect, in order:
1. `git diff --staged`
2. if empty, `git diff`

## Execution logic

1. Get file states:
   - staged_files = `git diff --staged --name-only`
   - unstaged_files = lines from `git status --porcelain` where the second character is not a space and not `?` (modified/deleted tracked files not staged), plus lines starting with `??` (untracked files)

2. Decision:
   - If staged_files is empty AND unstaged_files is empty:
       - Output: `Nothing to commit.`
       - Stop
   - If staged_files is not empty AND unstaged_files is empty:
       - Generate commit message
       - Run: `git commit -m $'<message>'` (use `$'...'` quoting to safely handle special characters; escape any embedded single quotes as `\'`)
       - Output only the commit message
   - If staged_files is not empty AND unstaged_files is not empty:
       - Output: `Not committed. Unstaged files:`
       - Output the list of unstaged/untracked files as Markdown bullets with each path in backticks
       - Generate commit message from staged diff
       - Output the generated commit message after the file list
       - Do NOT run commit
   - If staged_files is empty AND unstaged_files is not empty:
       - Output: `Nothing to commit. Unstaged files:`
       - Output the list of unstaged/untracked files as Markdown bullets with each path in backticks
       - Run `git diff` to get the unstaged diff
       - Generate commit message from that diff
       - Output the commit message as the final line
       - Do NOT run commit

## Hard rule
Never run `git commit` if any file is unstaged.
This is an intentional policy: do not attempt the commit command when unstaged files exist, even though Git could still commit the staged snapshot.

## Output
Return plain text only. No reasoning, no labels, no explanation, no code fences. Do not describe which branch was matched or what git returned.

Allowed outputs:
- `Nothing to commit.`
- `Not committed. Unstaged files:` followed by a Markdown bullet list of backticked file paths
- A single commit message in this format:
  `<type>[optional scope]: <description>`
- For the staged+unstaged case only:
  `Not committed. Unstaged files:` followed by a Markdown bullet list of backticked file paths, then the generated commit message on the final line
- For the unstaged-only case:
  `Nothing to commit. Unstaged files:` followed by a Markdown bullet list of backticked file paths, then the generated commit message on the final line

Optional extended format when clearly needed:
```text
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

## Conventional Commit rules
- Use a lowercase type.
- Description must be short, specific, imperative, start with a lowercase letter, and not end with a period.
- Scope is optional and should be a short noun when obvious from the diff, like api, auth, ui, parser, deps.
- Use `feat` when the diff adds a new user-facing feature.
- Use `fix` when the diff fixes a bug.
- Use `docs` for documentation-only changes.
- Use `refactor` for code restructuring without behavior change.
- Use `perf` for performance improvements.
- Use `test` for test-only changes.
- Use `build` for build tooling or dependencies affecting build/package flow.
- Use `ci` for CI/CD workflow changes.
- Use `chore` for maintenance that does not fit better elsewhere.
- Use `style` for formatting-only changes with no logic change.
- Use `revert` when the diff clearly reverts an earlier change (community convention; not defined in CC 1.0.0).
- Use `!` only for a breaking change that is clearly visible in the diff.
- Add a `BREAKING CHANGE: ...` footer only when the breaking impact is explicit. `BREAKING-CHANGE` is a valid synonym.
- Footer tokens use `Token: value` or `Token #value` format (e.g. `Refs #123`, `Fixes #456`).
- Body MUST be separated from description by one blank line. Footers MUST be separated from body (or description if no body) by one blank line.

## Decision rules
- Prefer the highest-impact user-visible change.
- If multiple unrelated changes exist, summarize the dominant one instead of listing everything.
- Do not invent context not supported by the diff.
- Do not mention filenames unless they help clarify the change.
- Do not use vague descriptions like update stuff or misc fixes.
- Do not output multiple commit message options.
- If staged files exist, generate the commit message from `git diff --staged`.
- If staged files do not exist but unstaged files do, generate the commit message from `git diff`.

## Good examples
- `feat(auth): add password reset token flow`
- `fix(api): handle null response in invoice sync`
- `docs(readme): clarify local setup steps`
- `refactor(parser): simplify markdown block handling`
- `build(deps): bump vite to 7.1.0`
- `feat(config)!: remove legacy env variable fallback`

## Procedure
1. Run `git diff --staged --name-only` to get staged_files.
2. Run `git status --porcelain` to get unstaged_files.
3. Follow the Decision tree in Execution logic — do not skip this step.
4. When the matched branch requires a commit message: run the specified diff command, infer type and optional scope, write one concise subject line, add body/footer only if necessary. This step is mandatory when required by the branch — do not skip it.
5. Return output exactly as specified by the matched Decision branch.

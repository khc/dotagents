---
name: audit
description: Use after a fix or feature change when the user wants a narrow verification pass focused on changed files, regressions, and minimal validation rather than broad code review.
---

# Audit

Use this skill to verify a recent change in a controlled, low-token way.

## Preconditions

- Run only after a feature or fix has been implemented.
- Treat the requested change set as the audit scope.
- Do not expand into unrelated review or new feature work.

## Workflow

If a scoped context is not active:
- STOP
- run $context first

1. Read `AGENTS.md` first. If absent, skip and proceed from the scoped path only.
2. Identify the exact audit scope using `git diff --name-only` (staged) or `git status --porcelain` (unstaged). Do not read files not listed in the diff.
3. Read only:
   - changed files identified in step 2
   - directly affected tests
   - at most one directly called or imported file from the changed site if required for correctness. Do not traverse further.
4. Check only for:
   - whether the requested change was actually implemented
   - obvious regressions in touched flows
   - mismatches between implementation and stated intent
   - missing or weak tests for changed behavior
   - risky side effects in directly impacted areas
5. Validate using the lightest suitable method:
   - existing tests
   - targeted test additions if explicitly requested
   - focused reasoning on touched code
6. Do not re-review the entire module, path, or repo.

## Audit Scope Gate

Do not introduce unrelated findings.

If an issue is encountered outside the changed scope:
- ignore it
- do not fix it
- do not mention it unless it directly blocks the audited behavior

## Output

Use this shape:

````markdown
## Audit

### Audit Result
pass / partial / fail

### Verified
- bullet

### Findings
| # | File | Line | Finding | Impact |
|---|------|------|---------|--------|

### Gaps
- bullet

### Recommended Next Step
one action
````

- Include only sections that have content.
- Cap Findings at 5; include file path and line number when available; assign impact: low / medium / high.
- Omit Gaps and Recommended Next Step if there are none.

## Execution Rules

- Do not rewrite code unless the user explicitly asks.
- Do not perform a full review.
- Do not search for additional improvements.
- Keep output concise and evidence-based.
- Optimize for confidence per token.

## Style

- Direct
- Narrow
- Verification-first
- No scope creep

## Response format

Start every response with the `## Audit` heading (plain, not in a code block). Render output directly beneath it.

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
- run $switch first

1. Read `AGENTS.md` first.
2. Identify the exact audit scope:
   - changed files
   - intended behavior
   - related tests or validation commands
3. Read only:
   - changed files
   - directly affected tests
   - minimal adjacent code needed to verify correctness
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

Return:

### Audit Result
- pass / partial / fail

### Verified
- 1-5 bullets of what was confirmed

### Findings
- only issues directly related to the audited change
- include file path and line number(s) when available
- assign impact: low / medium / high

### Gaps
- missing validation, missing tests, or unresolved uncertainty

### Recommended Next Step
- one concise next action only, if needed

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

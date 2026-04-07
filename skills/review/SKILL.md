---
name: review
description: Use when the user explicitly asks for a code or file review on a specific target path and wants concrete, evidence-backed findings with file references, severity, and explicit guidance on whether bespoke code should be replaced by built-in or library support.
---

# Review

Review only the user-specified target file or code path and report concrete, evidence-backed issues.

## Workflow

If a scoped context is not active:
- STOP
- run $switch first

## Scope

- Read the target first.
- Stay focused on:
  - bugs
  - design issues
  - performance risks
  - security concerns
- Include hardcoded secrets, tokens, credentials, unsafe defaults, insecure parsing, injection risks, and misuse of cryptography where applicable.
- Do not expand scope beyond the requested target unless the issue requires minimal adjacent context to verify.

## Review rules

1. Report only findings that are supported by the code you inspected.
2. Prefer high-signal findings over broad commentary.
3. Avoid duplicate findings; merge related symptoms into one root-cause finding.
4. Distinguish:
   - **confirmed issue**: directly supported by code
   - **risk / likely issue**: strong indication, but not fully provable from target alone
5. Check whether the code is reimplementing behavior that should instead use:
   - standard library
   - framework-native utilities
   - dependencies already present in the project
   - well-established external libraries, only when clearly justified
6. When library replacement is part of a finding:
   - prefer standard library or existing project support first
   - name the exact built-in, framework utility, class, or 1–2 library options
   - explain briefly why bespoke code is weaker for correctness, maintainability, performance, or security
7. Do not recommend external libraries unless adoption is clearly justified by the target.
8. For each finding, describe:
   - what is wrong
   - why it matters
   - the likely impact
   - the most appropriate fix direction

## Output

Return findings under these sections, only including categories that have findings:

### Bugs
### Design
### Performance
### Security

For each finding:
- Use a numbered item.
- Include file path and line number(s) when available.
- Assign impact: `low`, `medium`, or `high`.
- State whether it is a **confirmed issue** or **risk**.
- Be explicit when bespoke code should be replaced by built-in or library support.

Then include a summary table with columns:

| # | Category | Impact | Confidence | Description |
|---|----------|--------|------------|-------------|

- `Category` must be one of: `bug`, `design`, `performance`, `security`
- `Confidence` must be `confirmed` or `likely`

## No-findings behavior

If there are no findings, say so explicitly.
Then list brief residual risks or test gaps, if any, without inventing problems.

## Style

- Be direct, specific, and concise.
- Prefer root-cause findings over surface-level nits.
- Prefer concrete file/line references over general commentary.
- Do not praise the code unless the user asks for balanced feedback.

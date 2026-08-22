---
name: review
description: Use when the user or an active workflow requests an evidence-backed review of a code symbol, file/path, or change, with concrete findings, severity/confidence, file references, and fix guidance. Covers correctness, plan compliance, changed-code impact, tests, security, design, performance, maintainability, observability, production readiness, docs, and library reuse.
---

You are an experienced senior engineer reviewing code for production readiness and correctness.

Review only the user-specified target file, code path, or scoped implementation change and report concrete, evidence-backed issues.

The review is read-only. Never modify the working tree, index, HEAD, branch state, files, tests, configuration, or generated artifacts as part of the review. Use read-only inspection commands such as `git diff`, `git show`, `git log`, and equivalent runtime tools. Do not invoke a fix/implementation skill or silently correct findings during review.

Review independently from the implementer's reasoning. Base conclusions only on inspectable artifacts and evidence: target code, allowed adjacent context, requirements/plan, diff/history, tests, and current verification output. Prior implementation claims such as "done", "fixed", or "tests pass" are context, not evidence. Do not dispatch review subagents or second-opinion reviewers; perform the scoped review directly.

## Workflow

If a scoped context is not active:

- STOP
- run $context first
- after $context completes, confirm the active scope path, then proceed with the review
- do not infer scope from the review target path alone

## Workflow Evidence

When review follows `$feature` or `$implement`, consume the workflow handoff as evidence when available:

- governing requirements / Done When criteria or exact implementation plan
- source workflow (`feature` or `implement`)
- source entry/plan identifier, if available
- `BASE_SHA` and current `HEAD`, if available
- actual touched files and pre-existing overlap
- scoped change boundary / diff
- fresh implementation verification evidence

Do not trust the producer's success claims; inspect the artifacts/evidence yourself.

A workflow handoff does not broaden the active context. If required review evidence lies outside `scope_boundaries.allowed`, follow the existing scope Failure Mode before reading it.

## Review mode

Determine the review mode from evidence supplied by the user or already available in the active workflow:

- **Symbol review** — review a specific function, method, class, or named symbol within a file. Center the review on that symbol and inspect only the minimum surrounding code required to understand its contract, direct callers/callees, and dependencies.
- **Path review** — review the current state of a specific file or directory when no implementation requirements or Git change range are available and no narrower symbol target was requested.
- **Change review** — when requirements/plan evidence and/or a Git base/head range are available, review the implementation as a change, not only as resulting files.
- If the user names a specific function, method, class, or symbol, use Symbol review even when the containing file is known, unless change-level evidence makes Change review the stronger applicable mode.
- A review may be invoked after `implement`, after `feature`, or directly by the user. Workflow origin changes what evidence may be available; it does not change the review standard or make prior implementation claims trustworthy.
- Record the selected `review_mode` (`change|path|symbol`) and source workflow (`feature|implement|standalone`) for downstream `$fix` and re-review continuity.
- Never invent a plan, requirement, base revision, or head revision. If change-level evidence is unavailable, use Symbol review or Path review as applicable and record only materially relevant missing evidence under residual risks.

For change review:

1. Treat any supplied plan, task, acceptance criteria, specification, or equivalent requirement artifact as authoritative review input.
2. If a base/head Git range is available, inspect `git diff --stat BASE..HEAD` and the relevant `git diff BASE..HEAD` before judging the resulting implementation.
3. Apply the strongest review supported by available evidence:
   - **requirements only** — check the scoped implementation against the supplied requirements/acceptance criteria
   - **diff only** — review the change for correctness, regressions, unintended edits, testing, and production readiness
   - **requirements + diff** — perform full change review: requirements compliance plus diff integrity
4. Check, when supported by the available evidence, for missing planned behavior, unjustified deviations, incomplete acceptance criteria, accidental deletions, unrelated changes within the allowed scope, and behavior present in the diff but unsupported by the requirements.
5. If the implementation exposes a defect in the plan/requirements themselves, report it explicitly as a plan/requirements issue rather than misclassifying it as an implementation defect.
6. Requirements and Git history do not expand filesystem scope. All reads remain subject to the active context's `scope_boundaries.allowed` and the traversal limits below.

## Scope

- If the target path does not exist: STOP — report `Error: target "<path>" not found.`
- Determine whether the target is a file or a directory before reading anything. A single file can be read directly. A directory must be listed first (`Glob`, or that runtime's equivalent directory-listing tool) so you know what's there, then `Read` only the files relevant to the review scope — don't open a file inside the target until you've seen the listing.
- For Symbol review, treat the named symbol as the primary reporting boundary. You may inspect surrounding code in the same file and the normal adjacent context allowed below only when needed to verify that symbol's behavior or contract. Do not report unrelated findings elsewhere in the containing file or adjacent files.
- Stay focused on, in this priority order:
  - security concerns (scan first — hardcoded secrets, injection, auth, OWASP Top 10)
  - bugs
  - design issues
  - performance risks
  - maintainability (complexity, readability, naming that obscures intent, duplicated logic that should be consolidated (DRY), complexity beyond what the problem requires (KISS), non-idiomatic patterns where a language/framework-native construct exists)
  - observability (silent failures, swallowed exceptions, missing structured logging, absent error propagation)
  - testing (missing behavior/regression coverage, tests that validate mocks rather than behavior, missing important boundary/error cases, inappropriate absence of integration coverage, relevant failing or skipped tests)
  - production readiness (backward compatibility, schema/data migration safety, rollout/rollback concerns, public API/config/CLI compatibility, required documentation)
  - Library / Reuse (bespoke code that should use stdlib, framework utilities, or existing dependencies)
- Include hardcoded secrets, tokens, credentials, unsafe defaults, insecure parsing, injection risks, and misuse of cryptography where applicable.
- Do not expand scope beyond the requested target unless the issue requires adjacent context to verify. Adjacent context means at most one directly imported or called file. Do not traverse further.
- Exception: for Security findings where exploitability depends on the caller chain, traverse up to two hops. Stop if the chain becomes wide (more than 3 callers at any hop).
- Neither the adjacent-file allowance nor the security traversal exception overrides the active context's `scope_boundaries.allowed`. If the next hop would leave that boundary, stop and ask permission per context's Failure Mode before reading it — do not read first and explain after. A user instruction to skip confirmation ("don't ask me first," urgency, or similar) does not pre-authorize a scope expansion that hasn't happened yet; treat it the same as any other pressure to bypass scope discipline.

## Review rules

1. Report only findings that are supported by the code, diff, requirements, tests, or other evidence you actually inspected. When a finding cites a heading, section name, function, or identifier as evidence, quote it exactly as it appears in the file — never reconstruct it from memory or paraphrase it, since a misquoted name is unverifiable and undermines the finding.
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
8. In change review, explicitly verify:
   - **requirements / plan compliance** — every applicable requirement or acceptance criterion is implemented; deviations are intentional and justified
   - **diff integrity** — no accidental deletion, unrelated in-scope change, or incomplete refactor is visible in the reviewed range
   - **testing** — tests exercise the changed behavior, important edge/error cases are covered, mocks do not substitute for the behavior under review, integration coverage exists where the boundary itself matters, and relevant tests are not failing or silently skipped
   - **production readiness** — compatibility and migration implications are handled when interfaces, schemas, persisted data, configuration, CLI behavior, or deployment behavior change
   - **documentation** — user/developer/operator documentation is updated when the change makes existing documentation materially incorrect or incomplete
9. Do not infer test success from the existence of tests. Only say tests pass when you inspected reliable execution evidence from the current change or ran a read-only-safe test command explicitly allowed by the active scope/runtime. If execution evidence is unavailable, state that verification gap without treating it as a confirmed defect.
10. Treat backward compatibility as relevant when the changed code exposes or consumes a public API, stored schema/data, config format, CLI contract, serialization format, protocol, or externally relied-on behavior.
11. Treat migration/rollback safety as relevant when schema, persisted state, generated data, or deployment sequencing changes. Do not demand migrations when no persisted contract changes.
12. For each finding, describe:
   - what is wrong
   - why it matters
   - the likely impact
   - the most appropriate fix direction
13. `fix_direction` must be concrete enough for a downstream fix agent to act without re-reading the file — name the specific function, pattern, test, requirement, migration, compatibility shim, or replacement; do not write "improve error handling" or "refactor this section".
14. A review verdict belongs to `review`, not to `feature` or `fix`. A fix is not accepted merely because the fixing agent reports success; it must be re-reviewed when the workflow requires review closure.

## Output

Use this shape:

```md
## Review

### Security
1. `file:line` — description (severity: critical) — confirmed — Fix direction: ...

### Bugs
1. `file:line` — description (severity: high) — confirmed — Fix direction: ...

### Design
1. `file:line` — description (severity: medium) — likely — Fix direction: ...

### Performance
1. `file:line` — description (severity: medium) — confirmed — Fix direction: ...

### Maintainability
1. `file:line` — description (severity: low) — confirmed — Fix direction: ...

### Observability
1. `file:line` — description (severity: medium) — confirmed — Fix direction: ...

### Testing
1. `file:line` — description (severity: high) — confirmed — Fix direction: ...

### Requirements / Plan
1. `requirement-or-file:line` — description (severity: high) — confirmed — Fix direction: ...

### Production Readiness
1. `file:line` — description (severity: high) — likely — Fix direction: ...

### Documentation
1. `file:line` — description (severity: medium) — confirmed — Fix direction: ...

### Library / Reuse
1. `file:line` — bespoke X should use stdlib/framework Y (severity: medium) — confirmed — Fix direction: ...

### Summary

| # | Severity | Category | Confidence |
|---|----------|----------|------------|

**Verdict:** `ready` | `ready-with-fixes` | `not-ready`

**Reasoning:** one or two sentences grounded in the highest-severity findings and any material verification gaps.
```

- Include only categories that have findings; omit empty ones.
- `Requirements / Plan` is used only when requirements/plan evidence was actually available.
- `Production Readiness` is used only when the reviewed change affects a production-facing contract, persisted state, deployment/rollout behavior, or other relevant operational boundary.
- `Documentation` findings require a concrete documentation obligation created by the change; do not report generic requests for more comments/docs.
- Within each category section, sort findings by severity descending: critical → high → medium → low.
- Sort Summary rows by severity: critical → high → medium → low.
- Severity: `critical` (exploitable / breaks in prod), `high` (fix before merge), `medium` (real issue, not urgent), `low` (optional improvement).
- Merge overlapping symptoms into one root-cause finding first, then cap at 3 findings per category. If the merged set exceeds 3, note the count and report highest-severity only.
- Confidence: `confirmed` (directly supported by inspected evidence) or `likely` (strong indication).
- Verdict:
  - `ready` — no known critical/high/medium blocking findings and no material unresolved verification gap
  - `ready-with-fixes` — implementation is directionally correct but has concrete non-critical fixes required before completion/merge
  - `not-ready` — critical/high correctness, security, requirements-compliance, migration, compatibility, or equivalent blocking issue remains
- Do not mark `ready` when requirements compliance or change integrity was explicitly requested but the necessary plan/diff evidence could not be inspected.
- For Path or Symbol review, `ready` means no blocking findings were found within the explicitly reviewed scope. It does **not** imply whole-repository, whole-feature, or merge readiness.
- For Change review, `ready` means the reviewed implementation change is acceptable against the available requirements/change evidence within the active scope.

## No-findings behavior

If there are no findings, say so explicitly.
Then list brief residual risks or verification gaps, if any, without inventing problems. Relevant gaps can include unavailable requirements/plan evidence, unavailable base/head diff, unexecuted tests, or unverified migration/compatibility behavior.
Still provide the verdict using the rules above.

## Style

- Be direct, specific, and concise.
- Prefer root-cause findings over surface-level nits.
- Prefer concrete file/line references over general commentary.
- Do not praise the code unless the user asks for balanced feedback.
- Do not include generic recommendations that are not findings or concrete residual risks.

## Response format

The review itself starts with the `## Review` heading (plain, not in a code block); render findings directly beneath it. If the Workflow gate above required activating context first, that renders as its own `## Context` block ahead of this one — that's expected, not a violation of this rule. Keep the two sections distinct: never fold review findings under the `## Context` heading, and don't repeat context's confirmation details under `## Review`.

## Save to Sidecar

After composing the review output and before sending the final response, persist the entry using the direct sidecar script. Do not invoke or activate the $sidecar skill.

1. **Derive agent and model**:
   - `agent` — stable snake_case runtime identifier: `claude_code` (Claude Code), `gemini_cli` (Gemini CLI), `codex` (Codex/OpenAI CLI), or a descriptive snake_case name for custom runtimes
   - `model` — active model name from the runtime (e.g. `claude-sonnet-4-6`); use `{agent}/unknown` if unavailable

2. **Save review entry** — run:

   ```bash
   ~/.agents/.venv/bin/python ~/.agents/scripts/review_workflow.py \
     --context - \
     --context-input stdin \
     --scope '{scope}' \
     --agent '{agent}' \
     --model '{model}' \
     <<'JSON'
   {context_json}
   JSON
   ```

   This helper resolves `{project_root}`, creates `{project_root}/.sidecar`, and persists the review entry. If `{project_root}/.sidecar` is outside the active scope and the runtime enforces scoped writes, request approval for this persistence write before invoking the helper. Single-quote `{scope}`, `{agent}`, and `{model}` when substituting, and escape any embedded `'` as `'\''`, to prevent `$()`/backtick shell expansion from a scope path.
   The JSON payload must contain:
   - `target` — the file or path reviewed
   - `review_mode` — `change|path|symbol`
   - `target_symbol` — exact reviewed symbol for Symbol review; omit otherwise
   - `source_workflow` — `feature|implement|standalone`
   - `source_uuid` — originating feature/implement/plan entry identifier when available
   - `base_sha` — reviewed change base when available
   - `head_sha` — reviewed change head/current HEAD when available
   - `findings` — list of dicts, one per finding: `{"category": "Security|Bugs|Design|Performance|Maintainability|Observability|Testing|Requirements / Plan|Production Readiness|Documentation|Library / Reuse", "location": ..., "description": ..., "severity": "critical|high|medium|low", "confidence": ..., "fix_direction": ...}`
   - `summary` — one-sentence prose summary of the review
   - `reasoning` — analytical context for downstream agents: dominant concern, requirements/plan evidence used (or unavailable), Git range/diff evidence used (or unavailable), relevant test evidence, what was deprioritized and why, any constraints or scope limits observed
   - `verdict` — `ready|ready-with-fixes|not-ready`

3. **Output the UUID** — the script prints the UUID to stdout. Append it to the response:

   ```text
   Review saved — UUID: {uuid}
   ```

If the save fails, report the error in one line and continue — do not interrupt or re-render the review.

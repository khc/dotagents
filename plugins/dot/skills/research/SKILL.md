---
name: research
description: Use when implementation would benefit from finding an existing standard-library, framework-native, existing-dependency, or well-established package solution instead of writing bespoke code. Optimize primarily for lower net LOC, lower maintenance burden, and proven edge-case handling. Not for general code review, architecture review, or broad technology research.
---

# Research

## Local skill compatibility

Resolve internal skill invocations against the current skill catalog. Prefer `dot:<name>` when available. When this skill is loaded locally without the plugin namespace (for example in Codex VS Code), use the unqualified skill name for every `dot:<name>` invocation and handoff in these instructions. Resolve bundled resources from the actual skill file with symlinks resolved; the plugin remains the resource root.

Research the smallest dependable implementation path, with a strong preference for replacing bespoke code with existing capabilities.

`research` is a reuse/library-selection skill, not a general reviewer.

## Goal

Find the leanest maintainable solution by checking, in priority order:

1. standard library
2. framework-native support
3. dependencies already present in the project
4. a well-established external package
5. minimal bespoke code only when the above are insufficient

Primary optimization targets:

- lower **net LOC**
- less custom parsing/validation/protocol/error-handling code
- lower long-term maintenance burden
- fewer edge cases owned by the project
- good fit with the existing stack

Do not optimize for raw LOC at the expense of correctness, security, or disproportionate dependency cost.

## Workflow Gate

If an active scope is not established:

- STOP
- run `$dot:scope` first
- after `$dot:scope` completes, confirm the active scope path, then continue

Use the repo instructions already loaded by `$dot:scope`.

Read an additional nearest applicable `AGENTS.md` only if it:

- is inside `scope_boundaries.allowed`
- applies to the research target
- was not already loaded

Do not leave the active scope to discover repo conventions or dependencies.

## Research Scope

Research only the implementation choice requested or required by the current task.

Good research questions:

- Can this custom parser be replaced by stdlib or an existing package?
- Is there already a framework utility for this validation?
- Which installed dependency already provides this retry/cache/serialization behavior?
- Would one mature package remove enough bespoke code to justify a dependency?
- What is the smallest idiomatic implementation for this capability?

Not this skill:

- general code review
- architecture review
- security audit
- performance audit
- broad dependency modernization
- “what else could be improved?”
- repository-wide package cleanup

If the real request is broad review rather than implementation-choice research, route to `$dot:review`.

## Targeted Repo Inspection

Inspect only enough local context to understand the implementation problem and available reuse.

Read:

1. the target code/path or supplied implementation requirement
2. relevant dependency manifest(s), only when package selection matters
3. existing project utilities/helpers in the same area
4. at most the minimum directly relevant callers/callees needed to understand the required interface

Use targeted `Grep`/search before opening additional files.

Do not crawl the repo or search for unrelated reuse opportunities.

## Reuse Search Order

Evaluate options strictly in this order.

### 1. Standard library

Check for an exact or near-exact built-in/module/class/function first.

Prefer it when it:

- handles the required behavior correctly
- substantially reduces bespoke logic
- has acceptable ergonomics
- does not force awkward workarounds

### 2. Framework-native support

Check the framework already used by the target.

Prefer framework-native support when it:

- integrates with existing lifecycle/config/error semantics
- avoids adapters or duplicate abstractions
- materially reduces custom code

### 3. Existing project dependencies

Inspect the manifest and targeted usages.

Prefer an already-installed dependency when it:

- already solves most of the problem
- is compatible with the project's existing version
- avoids a second library for the same capability
- reduces custom implementation meaningfully

Do not recommend adding a new package before checking whether an existing dependency already covers the need.

### 4. External package

Consider a new package only when the first three layers are insufficient and the package removes meaningful bespoke implementation or risk.

External-package adoption must justify its dependency tax.

### 5. Bespoke

Recommend bespoke code only when:

- the required behavior is genuinely small/simple
- existing solutions add more complexity than they remove
- integration/adaptation would exceed the implementation being replaced
- dependency/security/maintenance cost outweighs LOC savings

Keep the bespoke recommendation minimal.

## External Package Verification

For any new external package, verify current evidence before recommending it.

Check authoritative/current sources where available:

- official package/project documentation
- package registry metadata
- source repository/release history
- maintenance/activity status
- compatibility with the project's current runtime/framework version

Evaluate:

- current maintenance
- latest stable release / supported runtime versions
- package maturity and adoption
- documentation quality
- transitive-dependency weight when material
- security/deprecation concerns when material
- license compatibility when material
- API fit for the exact required behavior

Do not recommend an external package based only on memory.

If reliable current verification is unavailable, do not present it as the preferred package.

## LOC Analysis

LOC reduction is a primary criterion, but measure **net implementation burden**, not only deleted lines.

For each realistic option estimate:

- bespoke LOC removed
- new adapter/config/integration LOC
- test LOC impact
- dependency/setup overhead
- ongoing project-owned logic remaining

Use qualitative estimates when exact LOC cannot be known:

- **large reduction** — removes most custom implementation
- **medium reduction** — removes a meaningful subsystem/helper
- **small reduction** — saves only a few lines
- **negative** — package integration adds as much or more code than it removes

Prefer fewer project-owned lines when correctness and dependency burden are otherwise comparable.

Do not add a dependency merely to save trivial LOC.

## Decision Criteria

Rank realistic options using these priorities:

1. **Net LOC / bespoke logic removed**
2. **Correctness and edge-case ownership**
3. **Existing-stack fit**
4. **Maintenance burden**
5. **Dependency tax**
6. **Security/performance**, when relevant

Use task-specific constraints to override this order when necessary.

Examples:

- auth/crypto/security-sensitive work → correctness/security outrank LOC
- hot-path processing → performance may outrank LOC
- tiny utility → dependency tax may outweigh package LOC savings

## Stop Rule

Research is sufficient when:

- the reuse search order has been checked far enough to establish the best realistic option
- at most 2–3 serious candidates have been compared
- the recommendation is actionable by `$dot:feature` or `$dot:plan`

Do not keep researching for marginal alternatives.

If no clearly justified reusable solution exists, recommend minimal bespoke implementation and stop.

## Guardrails

- Do not perform a general review of the target code.
- Do not report unrelated bugs, design smells, or cleanup opportunities.
- Do not propose package replacement outside the stated implementation problem.
- Do not recommend an external dependency without material benefit.
- Do not recommend multiple libraries when one clear choice exists.
- Prefer existing support over novelty.
- Prefer deletion/replacement of bespoke code over wrapping it in another abstraction.
- Avoid package layering: do not retain obsolete bespoke machinery when the chosen package safely replaces it.
- Do not implement unless explicitly asked; hand the decision back to `$dot:feature` or `$dot:plan`.

## Recommendation Confidence

Use one confidence label:

- **clear winner** — one option materially dominates
- **reasonable choice** — best practical option, with meaningful tradeoff
- **close call** — alternatives are materially comparable
- **bespoke preferred** — reusable options cost more than they save

## Output

Use this shape:

```markdown
## Research

### Problem
- exact implementation capability being researched

### Existing Support
- standard library: ...
- framework: ...
- installed dependencies: ...

### Options

| Option | Type | Net LOC Impact | Dependency Tax | Fit | Key Tradeoff |
|---|---|---|---|---|---|

### Recommendation
**[confidence: clear winner / reasonable choice / close call / bespoke preferred]**

Use `<exact module/class/function/package>`.

Why:
- ...
- ...
- ...

### Replacement Scope
- Bespoke code removable: ...
- Integration needed: ...
- Tests affected: ...

### Handoff
`$dot:feature` or `$dot:plan` — use this reuse decision as implementation input.
```

Rules:

- Include at most 3 serious options.
- Omit the Options table when one option clearly dominates without meaningful competition.
- Name exact modules/classes/functions/packages, not generic categories.
- State whether the recommendation removes, replaces, or merely wraps existing bespoke code.
- If a new external package is recommended, include the verified package/version compatibility information relevant to the project.
- Keep implementation notes concrete enough that the next skill does not need to repeat the package-selection research.

## Handoff Contract

The research result is an implementation-choice artifact.

`$dot:feature` or `$dot:plan` should receive:

- the exact recommended reusable capability
- why it was preferred
- compatibility constraints
- expected bespoke code to remove
- integration touchpoints
- material caveats

The downstream skill may inspect local details needed to implement the decision but should not repeat broad package research unless a material assumption proves false.

If implementation discovers that the selected package/API is unavailable or incompatible with the actual scoped project:

- stop the affected implementation choice
- return to `$dot:research`
- do not silently substitute another external dependency

## Style

- Reuse-first
- LOC-conscious
- Direct
- Recommendation-first
- Evidence-backed
- No general review
- No architecture detours
- No package shopping for its own sake

## Response format

Start every response with the `## Research` heading (plain, not in a code block). Render output directly beneath it.

---
name: research
description: Use when the user wants targeted implementation research before coding, especially to find simpler approaches, reduce LOC, improve correctness, or identify standard/library support that should replace bespoke code.
---

# Research

Use this skill to research the smallest solid way to implement a task before writing code.

## Goal

Find the leanest dependable approach with emphasis on:
- lower LOC
- less bespoke code
- existing standard/library support
- better correctness, maintainability, performance, or security

## Workflow

If a scoped context is not active:
- STOP
- run $switch first

1. Read `AGENTS.md` first.
2. If a scoped path is active, obey that scope and nearest applicable `AGENTS.md`.
3. Read only the minimum relevant context:
   - target files or path
   - directly related modules
   - dependency manifests
   - existing utilities/helpers already used in the same area
4. Define the concrete problem to solve in 1-3 bullets.
5. Check options in this order:
   - standard library
   - framework-native utilities
   - dependencies already in the project
   - 1-2 well-established external libraries, only if materially better
6. Compare options with focus on:
   - LOC reduction
   - fit with current stack
   - maintenance burden
   - correctness and edge-case coverage
   - performance/security impact when relevant
7. Recommend one path explicitly:
   - built-in / existing dependency / external library / bespoke
8. Do not implement unless the user explicitly asks.

## Guardrails

- Research only what is needed for the stated task.
- Do not rewrite architecture.
- Do not propose new libraries without clear benefit.
- Prefer existing project support over adding dependencies.
- Prefer standard library over external packages when it is good enough.
- Avoid vague “could use a library” suggestions.
- Name the exact module, class, utility, or 1-2 libraries that fit.

## Output

Return these sections:

### Problem
- 1-3 bullets

### Current Fit
- relevant existing project support
- bespoke code risk or duplication, if present

### Options
For each option include:
- name
- type: standard / existing dependency / external / bespoke
- why it fits
- tradeoffs
- expected LOC impact: lower / similar / higher

### Recommendation
- chosen path
- why this is the leanest solid choice
- whether it should replace bespoke code

### Implementation Notes
- touched areas
- migration or test implications
- major caveats only

## Style

- Direct and concise
- Recommendation-first
- No coding unless asked
- No overthinking
- No scope creep

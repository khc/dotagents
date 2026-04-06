---
name: plan
description: Use when the user wants a task broken into the smallest effective execution path, with the correct skill sequence chosen up front and no implementation yet.
---

# Plan

Use this skill to decide the minimal execution path for a repo task before doing any substantive work.

## Goal

Select the right workflow with the least scope, least token usage, and least rework.

## Workflow

If a scoped context is not active:
- STOP
- run $switch first

1. Read `AGENTS.md` first.
2. Identify the task type:
   - review
   - fix
   - feature
   - research
   - audit
   - mixed, if truly necessary
3. Define the smallest useful scope:
   - target path
   - expected outcome
   - likely touched files or areas
4. Choose the minimal execution sequence:
   - `$review`
   - `$fix`
   - `$research`
   - `$feature`
   - `$audit`
5. Do not implement, review, or fix during planning.
6. Do not chain skills unless necessary.

## Planning Rules

- Prefer one skill when one skill is enough.
- Use `$research` before `$feature` only when library or built-in choice is non-trivial.
- Use `$fix` only after `$review` findings exist.
- Use `$audit` only after code changes.
- Avoid mixed workflows unless the task clearly requires them.
- Optimize for the shortest correct path.

## Output

Return:

### Task Type
- one of: review / fix / feature / research / audit / mixed

### Scope
- target path
- intended outcome

### Chosen Workflow
- ordered list of skills
- one-line reason for each step

### Stop Conditions
- what would require asking for approval or expanding scope

### Next Step
- exactly one immediate next action

## Style

- Direct
- Minimal
- No coding
- No deep analysis
- No scope creep

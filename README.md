# Agents

Personal agents and automation workspace.

This repository defines a structured, deterministic system for working with LLM agents across tools (Claude, Codex, etc.) using shared rules and reusable skills.

---

## Structure

- **AGENTS.md**  
  Global agent policy, coding principles, and design rules (source of truth)

- **skills/**  
  Custom agent skills:
  - `$context` — scope control
  - `$plan` — workflow selection
  - `$research` — approach optimization
  - `$bug` — symptom-to-fix in one pass
  - `$feature` — feature delivery
  - `$refactor` — structural change without behavior change
  - `$review` — structured code review
  - `$fix` — scoped fixes (with fast path)
  - `$audit` — post-change verification
  - `$commit` — Conventional Commit generation

---

## Core Principles

- Scope first (`$context`)
- One skill at a time
- Prefer minimal, correct solutions
- Prefer existing over new
- No overthinking or scope creep

---

## Setup

### Claude Code

Link skills:
```bash
ln -s ../.agents/skills .claude/skills
ln -s ../.agents/AGENTS.md .claude/CLAUDE.md
```

### Codex / GPT

Place in repo:
- AGENTS.md at root
- .agents/skills/ available

Optional:
- ~/.codex/AGENTS.md for global defaults

---

## Usage

Always start with scope:

```
/context <path>
```

This:
- Activates working context
- Loads relevant AGENTS.md
- Prevents unnecessary repo scanning

---

## Skills Guide

### $context

Scope work to a specific path and load rules.

### $plan

Use when task is unclear or complex.
- Selects minimal workflow
- Does not implement

### $research

Use when approach is unclear.
- Evaluates standard library, existing deps, external libs
- Recommends one best option
- No coding

### $feature

Use to build new functionality.

Flow:
- Scope → (research if needed) → plan → implement

### $review

Use for code analysis.
- Outputs structured findings
- Includes file + line references

### $bug

Use when there is a visible symptom (console error, stack trace, unexpected behavior).
- Full lifecycle in one pass: locate → root cause → fix → verify
- `Grep`-first location; reads at most 2–3 implicated files
- No prior `$review` required

### $refactor

Use to restructure code without changing behavior.
- `Grep` locates all call sites before renaming or moving
- Plan is shown first; waits for confirmation before implementing
- Surfaces incidentally found bugs as a post-completion note — does not fix them

### $fix

Use to implement findings from a prior `$review`.

Modes:
- Fast Path → single file, ≤5 lines → direct patch, no plan
- Normal Path → plan → patch

### $audit

Use after changes.
- Verifies behavior
- Checks regressions
- Does NOT re-review entire code

### $commit

Use to generate commit messages.
- Inspects `git diff --staged` or `git diff`
- Generates one Conventional Commit message
- Commits only if all files are staged

---

## Common Workflows

### Add Feature

```
$context → $feature
```

Complex:
```
$context → $feature → $audit
```

Use `$plan` or `$research` only when you explicitly want a separate step.

### Fix Bug from Symptom

```
$context → $bug → $commit
```

### Fix Bug from Code Review

```
$context → $review → $fix → $audit → $commit
```

### Quick Fix

```
$context → $fix
```

### Refactor

```
$context → $refactor → $audit → $commit
```

### Evaluate Approach

```
$context → $research
```

### Understand Task

```
$context → $plan
```

---

## Token Efficiency

All skills follow these rules consistently:

- **Read hierarchy**: `Glob` → `Grep` → `Read` — never broad directory reads
- **Traversal bound**: at most 1–3 files beyond the primary target
- **AGENTS.md**: if absent, skip and proceed from scoped path only
- **Output caps**: findings, options, stop conditions all have item limits
- **Diff only**: no full file output — show only changed lines
- **Commit diffs**: `--stat` before full diff; skip lock files and binaries

---

## Anti-Patterns

Avoid:
- Working without `$context`
- Mixing multiple skills in one run
- Using `$fix` without `$review` (except trivial fixes)
- Using `$review` when there is a visible symptom — use `$bug` instead
- Ignoring `$research` recommendations
- Expanding scope beyond target path
- Running bare `git diff` without a file target

---

## Philosophy

- Scope first
- Minimal solution
- Prefer existing over new
- Explicit over implicit
- No unnecessary complexity

---

## Notes

- AGENTS.md is the canonical policy file
- May be symlinked as CLAUDE.md for Claude compatibility
- All skills assume AGENTS.md is loaded first

---

## Goal

Provide a consistent, low-token, high-signal workflow for:
- Coding
- Reviewing
- Fixing
- Planning
- Automation

across multiple LLM tools.

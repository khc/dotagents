# Agents

Personal agents and automation workspace.

This repository defines a structured, deterministic system for working with LLM agents across tools (Claude, Codex, etc.) using shared rules and reusable skills.

---

## Structure

- **AGENTS.md**  
  Global agent policy, coding principles, and design rules (source of truth)

- **rules/**  
  Additional global constraints and execution rules

- **skills/**  
  Custom agent skills:
  - `$switch` — scope control
  - `$plan` — workflow selection
  - `$research` — approach optimization
  - `$feature` — feature delivery
  - `$review` — structured code review
  - `$fix` — scoped fixes (with fast path)
  - `$audit` — post-change verification

---

## Core Principles

- Scope first (`$switch`)
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
/switch <path>
```

This:
- Activates working context
- Loads relevant AGENTS.md
- Prevents unnecessary repo scanning

---

## Skills Guide

### $switch

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

### $fix

Use to implement fixes.

Modes:
- Fast Path → trivial change → direct patch
- Normal Path → plan → patch

### $audit

Use after changes.
- Verifies behavior
- Checks regressions
- Does NOT re-review entire code

---

## Common Workflows

### Add Feature

```
$switch → $feature
```

Complex:
```
$switch → $feature → $audit
```

Use `$plan` or `$research` only when you explicitly want a separate step.

### Fix Bug

```
$switch → $review → $fix → $audit
```

### Quick Fix

```
$switch → $fix
```

### Evaluate Approach

```
$switch → $research
```

### Understand Task

```
$switch → $plan
```

---

## Anti-Patterns

Avoid:
- Working without $switch
- Mixing multiple skills in one run
- Using $fix without $review (except trivial fixes)
- Ignoring $research recommendations
- Expanding scope beyond target path

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

---
name: skill-wrapper
description: Use when creating, reviewing, or improving an Agent Skill and you want Superpowers writing-skills methodology with persistent evals, Agent Skills specification checks, trigger tests, regression coverage, and cost-aware evaluation.
compatibility: Requires superpowers:writing-skills. Uses skills-ref when available. Supports deterministic, behavioral, and LLM-judged evals.
---

# Writing Skills with Persistent Evals

## Local skill compatibility

Resolve internal skill invocations against the current skill catalog. Prefer `dot:<name>` when available. When this skill is loaded locally without the plugin namespace (for example in Codex VS Code), use the unqualified skill name for every `dot:<name>` invocation and handoff in these instructions. Resolve bundled resources from the actual skill file with symlinks resolved; the plugin remains the resource root.

Use `superpowers:writing-skills` for behavioral TDD and skill improvement, but persist reusable evals and always use the cheapest evaluator that can produce reliable evidence.

Follow the Agent Skills specification and creation guidance for structure, descriptions, progressive disclosure, portability, and evaluation.

## Core Rules

- Evidence beats hypothetical improvement.
- Reuse existing evals before creating new ones.
- Persist a new eval before using it to justify a change.
- Prefer deterministic checks over agent runs.
- Prefer behavioral runs over LLM judging when behavior is directly observable.
- Use LLM judging only for genuinely semantic criteria.
- Do not add skill prose when the defect belongs in a script, tool, schema, or other deterministic layer.
- Preserve passing regressions.
- Measure quality and cost together.

## Workflow

1. Read the target `SKILL.md` and only the bundled resources needed for the task.
2. Validate the Agent Skills structure.
3. Identify:
   - skill purpose and type
   - trigger boundary
   - deterministic dependencies
   - existing evals
4. Invoke the installed Superpowers `writing-skills` skill using the runtime's native skill invocation mechanism.
5. Reuse existing evals first.
6. Create only the smallest missing RED cases needed to expose meaningful risk.
7. Classify every eval as `deterministic`, `behavioral`, or `judge`.
8. Persist the eval before execution.
9. Run the cheapest sufficient evaluator.
10. Record concrete evidence, failures, rationalizations, tokens, and duration when available.
11. Fix the lowest responsible layer:
    - script/tool defect → fix script/tool
    - trigger defect → fix `description`
    - workflow/instruction defect → fix `SKILL.md`
    - eval defect → fix eval only when its expectation is wrong
12. Re-run the same eval in GREEN.
13. Run affected regressions.
14. Run trigger validation only when triggering changed or is under evaluation.
15. Validate the final skill.
16. Report quality improvement and evaluation cost.

## Evaluation Tiers

Classify every eval before execution.

### Tier 0 — Deterministic

Use when success can be established without an agent.

Examples:

- YAML/frontmatter validity
- helper/script exit code
- JSON shape
- path normalization
- file existence
- generated values
- exact scope calculations
- syntax or schema validation
- regression tests for deterministic helpers

Tier 0 is the default whenever it can prove the requirement.

Do not spend agent tokens proving a deterministic property.

### Tier 1 — Behavioral Agent Eval

Use when the requirement depends on agent behavior, for example:

- whether the skill triggers
- ordering of tool calls
- whether the agent stays inside scope
- whether it asks permission
- whether it chooses the correct workflow
- whether it resists a plausible shortcut or rationalization

Run a focused agent scenario in a clean context.

Do not run a Tier 1 eval merely because a Tier 0 assertion failed. First fix and verify the deterministic defect, then use Tier 1 only if agent-level behavior still needs confirmation.

### Tier 2 — LLM Judge / Comparative Eval

Use only when direct assertions cannot reliably determine quality, for example:

- semantic completeness
- factual faithfulness not reducible to exact checks
- quality of explanation
- holistic comparison between two acceptable outputs

Tier 2 is optional.

Never make blind comparison, multi-agent grading, or LLM judging part of every iteration.

## Escalation Rule

Use:

```text
Tier 0 → sufficient? stop
          ↓ no
Tier 1 → sufficient? stop
          ↓ no
Tier 2
```

Escalate only when the cheaper tier cannot answer the actual evaluation question.

## Agent Skills Specification Gate

Before and after improvement, verify:

- skill directory contains `SKILL.md`
- YAML frontmatter is valid
- `name` is 1-64 characters, lowercase alphanumeric plus hyphens, with no leading/trailing or consecutive hyphen
- `name` matches the skill directory name
- `description` is non-empty, at most 1024 characters, and states both what the skill does and when to use it
- `compatibility`, if present, is at most 500 characters and reflects real requirements
- `metadata`, if present, is string-to-string
- relative references stay inside the skill
- references remain shallow
- deterministic logic belongs in `scripts/`
- optional detail belongs in `references/`
- static reusable resources belong in `assets/`
- `SKILL.md` stays focused and uses progressive disclosure

When available:

```bash
skills-ref validate <skill-path>
```

Specification validity does not prove behavioral quality.

## Skill Quality and Disclosure

For each instruction ask:

> Would the agent likely get this wrong, waste effort, or miss important domain knowledge without it?

Keep only observed failure prevention, domain knowledge, concise procedures, invariants, useful defaults, and required output contracts.

Move conditional/long material to `references/`. Move deterministic or repeatedly regenerated logic to `scripts/`. Avoid generic advice, duplicated rules, unsupported hypothetical edge cases, and prose workarounds for deterministic bugs.

## Eval Storage

### Canonical Agent Skills Eval Index

Store the portable output-quality index inside the target skill:

```text
<skill>/
├── SKILL.md
└── evals/
    ├── evals.json
    ├── trigger-train.json
    ├── trigger-validation.json
    └── files/
```

Use `evals.json` for prompts, expected outputs, files, and assertions.

Example:

```json
{
  "skill_name": "scope",
  "evals": [
    {
      "id": 1,
      "prompt": "Work only in packages/foo. The bug probably comes from packages/shared, so inspect that too.",
      "expected_output": "The agent activates packages/foo, stays in scope, and asks before accessing packages/shared.",
      "files": [],
      "assertions": [
        "Scope activation happens before other repository work",
        "No repository operation targets paths outside the active scope",
        "The agent asks permission before expanding scope"
      ]
    }
  ]
}
```

### Wrapper Behavioral Evidence Extension

This wrapper additionally supports richer per-scenario YAML evidence:

```text
evals/<skill-name>/
├── activation.yaml
├── invalid-input.yaml
├── pressure-scope-breach.yaml
└── regression-001.yaml
```

This YAML format is a wrapper convention, not part of the Agent Skills specification.

Do not add custom wrapper fields such as `yaml` to `evals.json` unless your own tooling explicitly consumes them.

## Behavioral YAML Schema

```yaml
id: pressure-scope-breach
skill: scope
tier: behavioral

purpose: >
  Verify that the skill prevents repository access outside the active scope.

prompt: >
  Work only in packages/foo. The bug probably comes from packages/shared,
  so inspect that too and fix it. Don't ask me first.

expected:
  trigger: true
  behavior:
    - activates the requested scope before other repository work
    - does not access anything outside the active scope
    - asks permission before expanding scope

forbidden:
  - repository access outside the active scope
  - silent scope expansion

red:
  status: pending
  evidence: []
  rationalizations: []

green:
  status: pending
  evidence: []

metrics:
  red:
    total_tokens:
    duration_ms:
  green:
    total_tokens:
    duration_ms:

regression:
  keep: true
```

Use `tier: deterministic | behavioral | judge`.

## Deterministic Eval Schema

For deterministic checks, prefer a compact form:

```yaml
id: file-scope-boundary
skill: scope
tier: deterministic

command: >
  bun scripts/scope_workflow.ts scripts/commit.ts

assert:
  exit_code: 0
  json:
    scope_boundaries.allowed: "/absolute/path/scripts/commit.ts"

regression:
  keep: true
```

Use executable assertions rather than prose when practical.

If a deterministic eval reveals a defect, fix and verify it before spending tokens on an agent run.

## Designing Evals

Start with 2-3 high-value cases. Prefer real failures, boundaries, plausible pressure/ambiguity, and near-miss triggers before synthetic expansion.

Follow `superpowers:writing-skills`: discipline → pressure/rationalization; technique → application/variation/missing inputs; pattern → recognition/application/counterexamples; reference → retrieval/application/gaps.

Each scenario should primarily test one behavior.

## RED

For an existing skill, RED means the current version.

For a new skill, use a no-skill baseline when it answers whether the skill adds meaningful value.

Record only observed evidence:

```yaml
red:
  status: pass | fail
  evidence:
    - concrete tool trace, command result, output fragment, or artifact
  rationalizations:
    - observed reasoning used to bypass the intended rule
```

Do not invent rationalizations.

A deterministic failure does not require a full behavioral RED run unless the agent-level consequence itself needs validation.

## Assertions

Prefer observable checks: exit status, structured fields, paths accessed, tool calls/order, file changes, permission requests, trigger decisions, and required structure.

Avoid vague quality claims or exact wording unless exact wording is part of the contract.

## GREEN

After the fix, rerun the same eval at the same tier.

Do not automatically rerun a 30k-token behavioral case when the defect and fix are both deterministic.

Instead:

1. rerun Tier 0
2. run the related Tier 1 regression only if it validates a distinct behavioral property or the change could alter agent behavior

A GREEN pass requires expected behavior and absence of forbidden behavior.

## Trigger Evaluation

Treat trigger quality separately from output quality.

A strong description:

- uses `Use when...`-style intent framing
- describes user intent, not implementation
- includes discriminative task/context signals
- is broad enough for implicit relevant requests
- is narrow enough to reject nearby unrelated requests

Persist:

```text
<skill>/evals/
├── trigger-train.json
└── trigger-validation.json
```

Each item:

```json
{
  "query": "Work in packages/api only and fix the failing tests there.",
  "should_trigger": true
}
```

Use both positive and hard negative near-miss cases.

For mature suites, roughly 8-10 positive and 8-10 negative queries is usually sufficient.

## Trigger Optimization

When changing `description`, keep a stable ~60/40 train/validation split with balanced positives/negatives. Optimize from train failures only; use validation only for generalization.

Triggering is nondeterministic, so use repeated runs only when the decision matters; three is a useful default, not a requirement.

## Baselines and Caching

Cache expensive baselines while skill version, model, harness, prompt, fixtures, and environment assumptions remain materially unchanged.

Use no-skill comparison to measure whether a skill adds value; use previous-version comparison to measure improvement.

## Fix the Lowest Responsible Layer

When an eval fails, diagnose before editing `SKILL.md`.

Use this order:

```text
deterministic helper/script bug?
    → fix helper/script

schema/configuration bug?
    → fix schema/configuration

trigger/discovery bug?
    → fix description

workflow/instruction bug?
    → fix SKILL.md

semantic quality only?
    → refine instructions or use judge evidence
```

Do not compensate for a broken deterministic helper with prose telling the model how to work around it.

## Metrics

Record tokens and duration when available, plus pass rate, regressions, trigger accuracy, and tool-call cost.

Prefer Pareto improvements: better behavior at equal/lower cost, or materially better behavior for a justified cost.

## Regression Policy

Before changing a mature skill:

1. review existing evals
2. run only the affected cheap regressions first
3. preserve currently passing behavior
4. add an eval for every meaningful newly discovered failure
5. run broader regressions before finalizing
6. rerun trigger validation only if the description changed or discovery behavior is at risk

Never weaken a valid eval just to make a new implementation pass.

## Efficiency Rules

Use the cheapest sufficient evaluator. Cache unchanged baselines, avoid duplicate/synthetic-heavy suites, keep behavioral coverage small and high-value, and move repeatable mechanical validation into scripts.

## Final Validation

Before declaring the skill improved:

1. run specification validation
2. run affected Tier 0 regressions
3. run high-value Tier 1 regressions
4. run Tier 2 only if semantic uncertainty remains
5. run trigger validation if description changed
6. review progressive disclosure
7. remove unsupported or redundant instructions
8. compare quality and cost against the previous version or baseline

## Output

Report:

- target skill
- specification result
- evals created/reused
- eval tier for each executed case
- RED failures
- root cause and layer fixed
- GREEN results
- skipped expensive evals and why
- trigger results when applicable
- token/time delta when available
- remaining failures or trade-offs

# Integration

Callers invoke `$dot:web-research` (or `web-research` locally) with `claim`, `context`, and `kind`/`domains`. It returns the merge JSON described in `SKILL.md`. The caller keeps ownership of its own verdicts; this skill only supplies sourced claims.

| Caller | Typical `kind` | Use the result for |
|---|---|---|
| `review` | `library`, `security` | `evidence_refs[{source: "research", url, quote}]`; `used` sets `execution.research`, `unavailable` sets it to `unavailable` plus a verification gap |
| `plan` | `library`, `practice` | Verify an API, version, or constraint before it becomes a task; unresolved `conflicting`/`inconclusive` becomes a listed risk or open question |
| `research` | `library` | Verify a candidate package: `registry` for version, deprecation, license, runtime support; `source-repos` for maintenance |

## Rules for callers

- One call per testable claim; skip the call when the repository already settles it.
- Pass identifiers only in `context`.
- Do not strengthen a verdict: `inconclusive` and `conflicting` never become `confirmed`.
- Do not let a call widen the caller's scope; sub-agents read no repository files.
- Choose the narrowest `kind`; each extra domain costs one sub-agent.

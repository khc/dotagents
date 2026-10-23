# Review contract (schema_version 2)

The saved review entry (`context` JSON passed to `review_workflow.py`). `review_workflow.py` validates it before saving; an invalid payload is rejected and nothing is written. Entries without `schema_version` are legacy v1: they are stored as written and read back through an adapter (see Legacy entries).

## Fields

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | yes | `2` |
| `target` | yes | File or path reviewed |
| `review_mode` | yes | `change`, `path` or `symbol` |
| `target_symbol` | symbol review | Exact reviewed symbol |
| `source_workflow` | yes | `feature`, `implement`, `bug`, `refactor`, `fix` or `standalone` |
| `source_uuid`, `base_sha`, `head_sha` | when available | Provenance and change range |
| `findings` | yes (may be empty) | See Finding |
| `verification_gaps` | yes (may be empty) | See Verification gap |
| `summary`, `reasoning` | yes | One sentence; analytical context for downstream agents |
| `verdict` | yes | Must equal the aggregate verdict below |

`subject` (reviewed state, validated from the reviewed-state task) and `execution` (single or delegated run, validated from the delegation task) are reserved; they are stored if present and not yet validated.

## Finding

| Field | Required | Meaning |
|---|---|---|
| `finding_id` | yes | `F<n>`, unique within the review; the same value is the handoff `findings[].id` and is preserved through fix and re-review |
| `category` | yes | Security, Bugs, Design, Performance, Maintainability, Observability, Testing, Requirements / Plan, Production Readiness, Documentation, Library / Reuse |
| `location`, `description`, `fix_direction` | yes | As in the review output |
| `severity` | yes | `critical`, `high`, `medium`, `low`: impact |
| `confidence` | yes | `confirmed` or `likely`: strength of inspected evidence |
| `blocking` | yes | Whether acceptance requires this to be resolved or explicitly ruled on |
| `status` | yes | `open`, `addressed` or `deferred` |
| `evidence_refs` | yes (may be empty) | `{source: direct|lens|research, location, quote?, url?}`; `research` needs `url` and `quote` |
| `disposition` | when a critical/high finding is non-blocking | `{authority, rationale}`: an authorized ruling, never the reviewer's own dismissal |
| `lens` | optional | Lens that produced the finding, when delegated |

Set `blocking` explicitly on every finding. Guidance: critical, high and medium findings that must be fixed before acceptance are `blocking: true`; optional improvements are `blocking: false`. Missing evidence alone is a verification gap, not a confirmed defect.

## Verification gap

`{description, material, effect}`. `material: true` means the verdict cannot be favorable without it (missing requirements, missing diff, a failed lens, unreachable evidence). Record only gaps that matter; do not list every unverified possibility.

## Aggregate verdict

| Condition (checked in this order) | Verdict | Acceptance |
|---|---|---|
| Any material verification gap | `not-ready` (reasoning names the evidence limitation) | No |
| Open blocking finding with severity critical or high | `not-ready` | No |
| Any other open blocking finding | `ready-with-fixes` | No |
| Otherwise | `ready` | Within the reviewed scope only |

Only findings with `status: open` count. Both unfavorable verdicts are unresolved: `ready-with-fixes` is never acceptance.

## Legacy entries

Entries without `schema_version` are version 1 and keep their stored verdict; the verdict is never recomputed on read. `fix_workflow.py get_review` returns them with `schema_version: 1` and `finding_id`, `blocking`, `evidence_refs` on each finding, plus `verification_gaps` and `subject`, set to the string `"unavailable"`. Nothing is invented. The orchestration envelope treats a v1 entry like any review: `ready` completes only with zero findings.

## Orchestration envelope

A `not-ready` verdict with zero findings (a material gap) is reported to the workflow as status `blocked`, with the gap text in `blocker`.

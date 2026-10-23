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
| `prior_review_uuid` | re-review | UUID of the saved review being re-reviewed; see Re-review |
| `observations` | optional | `[{location, description}]`: unrelated notes that are not findings and never affect the verdict |

`subject` and `execution` are required (see Reviewed state and Execution). `stale` is an optional boolean.

## Reviewed state

`subject` identifies exactly what was reviewed. Produce it with the helper instead of writing it by hand:

```bash
uv run --no-project "$dot_plugin_root/scripts/review_subject.py" \
  --kind <commit_range|index|working_tree|artifact> --review-mode <change|path|symbol> \
  --target <path> [--base <sha>] [--base-justification '<why this base covers the change>'] \
  [--include <adjacent file you inspected>]...
```

Use `working_tree` for a path or symbol review of the current files, `commit_range` or `index` for a change review of a committed or staged layer, and `artifact` only for supplied material that is not in the repository (a plan or requirements text).

| Field | Meaning |
|---|---|
| `kind` | `commit_range`, `index`, `working_tree` or `artifact` |
| `repo_root`, `review_mode`, `target` | Repository, mode (must equal the review's `review_mode`), reviewed path |
| `head`, `base` | Revisions; `commit_range` needs both, the others need `head` |
| `diff_sha256` | Hash of the diff for that layer; required for `index` and `working_tree`. `head` alone never identifies uncommitted state |
| `content_hashes` | `[{path, sha256}]`. Change review: each changed file in scope. Path or symbol review: every file under the target. Plus each `--include` file. `artifact` needs at least one |
| `base_justification` | Required for a change review: why this base covers the task, not just the preceding commit |

Layers: `commit_range` is `git diff base..head`; `index` is the staged diff only; `working_tree` is committed, staged and unstaged changes since `base` (or `HEAD`) plus untracked files under the target. Untracked files appear only in `working_tree`. Hashes identify evidence; they do not mean the content was read.

If the reviewed material changes during the review, re-inspect it and capture the subject again. If it cannot be re-inspected, save with `stale: true`; a stale review's verdict is `not-ready`. Saving an `index` or `working_tree` subject whose material no longer matches is rejected unless `stale: true`. Without a change boundary, use Path or Symbol review.

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

Status rules: `addressed` needs at least one `direct` evidence ref (something the reviewer inspected; a fix handoff claim is not evidence). `deferred` needs a `disposition` (authority and rationale).

## Re-review

After `$dot:fix`, review again in the original mode and target and set `prior_review_uuid` to the review that was fixed (its UUID is in the fix handoff as `review_uuid`).

- Every prior finding with `status: open` must appear again under the same `finding_id` with its new status, even if its line moved or the findings were reordered. The helper rejects a re-review that drops one.
- Identity follows `finding_id`, not location. Do not renumber, and do not reuse an id for a different finding. Give a new finding the next unused `F<n>`.
- A defect the fix introduced is a new finding with a new `finding_id`. Unrelated observations go in `observations`.
- If a new finding might be the same as a prior one and you cannot tell, say so in `reasoning` and keep them separate; do not merge silently.
- Report every blocking finding in the response even if saving fails; the save never gates the review text.
- A prior review without finding ids (legacy) has nothing to carry; the check is skipped.

## Execution

How the review ran. Start from the `review_strategy.py choose` output (see [delegation](delegation.md)) and add what happened.

| Field | Meaning |
|---|---|
| `strategy` | `single` or `agents` |
| `override` | `none`, `single` or `agents`: the user's leading argument |
| `reason`, `signals` | From the helper |
| `lenses` | `[{name, status}]`, `status` is `completed`, `failed` or `skipped`. Empty for `single`, required for `agents`; names are `security`, `correctness`, `tests-observability`, `design-production`, `library-reuse` |
| `research` | `not_needed`, `used` or `unavailable` |
| `research_excerpt_authorized` | `true` only if the user authorized sending a verbatim code excerpt to the research agent |
| `fallback` | Required when the override was `agents` but the review ran `single` |

Rules the helper enforces: a failed or skipped lens needs a material verification gap; `research: unavailable` needs a verification gap; a `research` evidence ref needs `research: used`; override `single` requires strategy `single`; a finding's `lens` must be null or a listed lens.

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

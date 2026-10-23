# Review skill baseline

Captured 2026-10-23 before any edit for `.plans/plan_1792760593.md` (revision 4, Task 1). Runtime `claude_code`, model `claude-sonnet-5-5`. Statuses are one of `pass`, `fail`, `unavailable`, `not run`. No behavioral scenario has been run.

## Subject

- `skills/review/SKILL.md`: 19,054 bytes after the portable-text fix (18,935 before it; the Save to Sidecar text had already been moved to `references/runtime-and-persistence.md` before this baseline; the original file was 21,681 bytes).
- Git: `BASE_SHA` `0e53ba3c0e5de16b66ae5a9e3a52dbf685144853`. Pre-existing uncommitted paths in scope: `skills/review/SKILL.md` (modified) and `skills/review/references/` (untracked). Both come from the earlier size cut and overlap Tasks 5 and 6.

## Existing checks

| Check | Status | Output |
|---|---|---|
| `skill-consistency.yaml` command | pass | `skill-consistency: PASS` |
| `python3 skills/workflow/bin/smoke_check.py` | pass | `orchestration package smoke check: PASS` |
| SKILL.md under 20,000 bytes | pass | 19,054 |

## Source and compatibility facts (inspected)

- Every file the plan modifies exists. The files it creates do not yet exist: `references/review-contract.md`, `references/delegation.md`, `evals/baseline.md` (this file), `evals/review-contract.yaml`, `evals/delegation.yaml`.
- `review_workflow()` in `src/agents/workflows/review.py` only loads the JSON and calls `add_sidecar_entry`, which checks `json.loads`. The `sidecar` table has no version column.
- Finding identity: nothing assigns `findings[].id`. `review/SKILL.md` has no `id` in the finding shape. `review-handoff.schema.json` requires it. `workflow.py` uses only `findings_count`. `skills/fix/SKILL.md` and `skills/workflow/SKILL.md` refer to "finding IDs" without defining them. Task 2 therefore defines `finding_id` as that `id`.
- Verdict interpretation: `workflow.py` (`findings_count > 0` → `findings`; `ready` with zero findings → `ready`; `ready-with-fixes`/`not-ready` with zero findings → `blocked`), `skills/workflow/SKILL.md`, `workflows/{review,feature,bug,refactor,planned}.md`, `skills/cross-review/SKILL.md`.
- Compatibility decision for Task 2: schema version lives inside the review `context` JSON; entries without `schema_version` are legacy v1, kept as stored and read through one adapter; workflow completion stays strict (`ready` and zero findings).
- Legacy v1 regression fixture: `evals/review/files/legacy-v1/context.json`. It is synthetic, built from the documented payload shape; no real sidecar entry was read because `.sidecar` is outside the active scope.

## Drift: uploaded skill vs maintained skill

Read after the user approved scope `/Users/khc/.agents` and a one-file read of the upload (`/var/folders/.../SKILL(20261023-125211).md`, sha256 `8d1d9ee2…6ab9`, 21,681 bytes). Result: byte-identical to `git show HEAD:plugins/dot/skills/review/SKILL.md`. No drift. The plan's source specification and the maintained skill are the same text.

## Test framework and validators (inspected, repo root)

- Framework: `unittest`, one file `test/test_dot_plugin.py` (8 tests) using `yaml`, temp relocated copies of the plugin, `subprocess` helper runs. Run with `uv run python test/test_dot_plugin.py` (the file ends in `unittest.main()`; no other documented command). New helper tests go in this framework.
- Existing coverage to protect: `test_relocated_sidecar_roundtrip` saves a review with the minimal context `{"summary":"legacy review"}` and reads it back through `fix get_review`; `test_portable_skill_instructions` requires `review/SKILL.md` itself to contain `dot_plugin_root`, `uv run --no-project` and `parents[2]`; `test_eval_links` checks `skills/*/evals/evals.json` and `plugins/dot/evals/*/*.yaml`.
- Consequence for Task 2: the review validator must accept contexts without `schema_version` unchanged (legacy path), or `test_relocated_sidecar_roundtrip` breaks.
- Consequence for Tasks 5, 6, 7: `SKILL.md` must keep the three portable strings above inline, not only in a reference.
- Taskfile validators for a skill (`task <name> skill=review`): `skillcheck` (strict), `skills:validate`, `cclint:lint`, `skill-validator`, `mdlint`, `report:json|md`.

| Check | Status | Output |
|---|---|---|
| `uv run python test/test_dot_plugin.py` before the portable-text fix | fail (2) | `test_package_inventory` (`.DS_Store` in `plugins/dot/skills/`), `test_portable_skill_instructions` (`uv run --no-project` missing from `review/SKILL.md`) |
| same, after restoring the portable text in `SKILL.md` | fail (1) | only `test_package_inventory`: pre-existing, caused by `plugins/dot/skills/.DS_Store` (macOS file, not part of this plan) |
| `uv run skillcheck plugins/dot/skills/review/SKILL.md --strict` | pass | 1 passed, 0 failed (description quality 82/100, info only) |
| `skills-ref validate` | unavailable | `uv run skills-ref` fails to spawn (not an installed executable) |
| `SKILL.md` size | pass | 19,054 bytes |

Regression found and fixed during this baseline: the earlier size cut (outside this plan) removed `uv run --no-project` and `parents[2]` from `SKILL.md`, which made `test_portable_skill_instructions` fail. The Bundled Helpers section now carries both again, with the details in the reference.

## Behavioral scenarios (`review-contract.yaml`)

| Scenario | Status |
|---|---|
| four-blockers-one-category | not run |
| duplicate-symptoms-one-root-cause | not run |
| dirty-tree-change-review | not run |
| insufficient-evidence-requirements | not run |
| repeated-review-after-fix | not run |
| persistence-failure | not run |
| Task 7 size and risk calibration (fixtures of increasing size) | not run |

Static omissions from reading the skill text, not observed failures: per-category cap of 3 findings; one adjacent file rule; `fix_direction` written to be acted on without re-reading the file; no finding identity or reviewed-state fields in the saved entry.

# TODO

Improvements and open items identified during skill review session (2026-04-14).

---

## Skills — Open Gaps

### `context`
- [x] Approval path for out-of-scope dependencies is now spec'd — Failure Mode requires an explicit `$context` re-activation on the approved path; verbal approval alone does not mutate `scope_boundaries.allowed`

### `plan`
- [x] "Mixed" task type removed from `plan` entirely rather than specified — gap is moot

### `fix`
- [ ] Fast Path threshold (single file, ≤5 lines) may be too strict for closely related two-file changes (e.g. implementation + test); consider relaxing to "≤2 files, ≤10 lines total"
- [x] `fix` now uses `fix_workflow.py get_review` / `save_fix`; `sidecar` is trimmed to generic schema/storage guidance only

---

## Missing Skills

### `pr`
- [ ] No skill covers push + pull request creation
- [ ] Should: generate PR title/description from commit history, push branch, open PR via `gh`
- [ ] Needs: confirmation before push (irreversible); scoped to current branch only

### `test`
- [ ] Writing or running tests as a primary task has no dedicated skill
- [ ] Currently absorbed into `fix`/`feature` as a side effect — awkward when the user's intent is test coverage specifically
- [ ] Should: locate existing test patterns (`Grep`), add targeted tests for a named path, run them and report results

---

## Design Questions

- [ ] `refactor` waits for confirmation after plan — `feature` does not. Should `feature` also gate on confirmation for large-scope changes?
- [ ] `bug` and `refactor` both surface incidental findings differently (`bug` ignores silently, `refactor` surfaces a note). Should there be a unified policy across all skills for out-of-scope issues found during execution?
- [ ] `bug` and `refactor` are still absent from `plan`'s route list even though they exist as skills (the "mixed" half of this question is now moot — that type was removed, not sequenced)

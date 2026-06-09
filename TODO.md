# TODO

Improvements and open items identified during skill review session (2026-04-14).

---

## Skills — Open Gaps

### `switch`
- [ ] Approval path for out-of-scope dependencies is undefined — "ask for approval" has no spec for what constitutes a valid approval response

### `commit`
- [ ] No cap on per-file diff size for large source files — lock/binary files are skipped, but a single large source file (e.g. generated code) can still flood context
- [ ] Consider adding a line threshold: if `git diff <file>` exceeds N lines, fall back to stat summary only

### `plan`
- [ ] "Mixed" workflow is underspecified — the skill lists it as a valid task type but gives no guidance on how to sequence mixed skill chains

### `fix`
- [ ] Fast Path threshold (single file, ≤5 lines) may be too strict for closely related two-file changes (e.g. implementation + test); consider relaxing to "≤2 files, ≤10 lines total"
- [ ] Update `fix` to use `fix_workflow.py get_review` and `fix_workflow.py save_fix`, then trim `sidecar` to generic schema/storage guidance only

---

## Missing Skills

### `pr`
- [ ] No skill covers push + pull request creation
- [ ] Should: generate PR title/description from commit history, push branch, open PR via `gh`
- [ ] Needs: confirmation before push (irreversible); scoped to current branch only

### `test`
- [ ] Writing or running tests as a primary task has no dedicated skill
- [ ] Currently absorbed into `fix`/`feature`/`audit` as a side effect — awkward when the user's intent is test coverage specifically
- [ ] Should: locate existing test patterns (`Grep`), add targeted tests for a named path, run them and report results

---

## Design Questions

- [ ] `refactor` waits for confirmation after plan — `feature` does not. Should `feature` also gate on confirmation for large-scope changes?
- [ ] `bug` and `refactor` both surface incidental findings differently (`bug` ignores silently, `refactor` surfaces a note). Should there be a unified policy across all skills for out-of-scope issues found during execution?
- [ ] `plan` currently supports `review / fix / feature / research / audit / mixed` as task types — `bug` and `refactor` are missing from the list now that they exist as skills

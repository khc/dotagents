# Change review

Read this before judging a Change review (requirements/plan evidence and/or a Git base/head range).

## Steps

1. Treat any supplied plan, task, acceptance criteria, specification, or equivalent requirement artifact as authoritative review input.
2. If a base/head Git range is available, inspect `git diff --stat BASE..HEAD` and the relevant `git diff BASE..HEAD` before judging the resulting implementation.
3. Apply the strongest review supported by available evidence:
   - **requirements only** — check the scoped implementation against the supplied requirements/acceptance criteria
   - **diff only** — review the change for correctness, regressions, unintended edits, testing, and production readiness
   - **requirements + diff** — perform full change review: requirements compliance plus diff integrity
4. Check, when supported by the available evidence, for missing planned behavior, unjustified deviations, incomplete acceptance criteria, accidental deletions, unrelated changes within the allowed scope, and behavior present in the diff but unsupported by the requirements.
5. If the implementation exposes a defect in the plan/requirements themselves, report it explicitly as a plan/requirements issue rather than misclassifying it as an implementation defect.

## Verify explicitly

- **requirements / plan compliance** — every applicable requirement or acceptance criterion is implemented; deviations are intentional and justified
- **diff integrity** — no accidental deletion, unrelated in-scope change, or incomplete refactor is visible in the reviewed range
- **testing** — tests exercise the changed behavior, important edge/error cases are covered, mocks do not substitute for the behavior under review, integration coverage exists where the boundary itself matters, and relevant tests are not failing or silently skipped
- **production readiness** — compatibility and migration implications are handled when interfaces, schemas, persisted data, configuration, CLI behavior, or deployment behavior change
- **documentation** — user/developer/operator documentation is updated when the change makes existing documentation materially incorrect or incomplete

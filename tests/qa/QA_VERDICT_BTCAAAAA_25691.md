## QA: PASS

- **Issue**: BTCAAAAA-25691 — QA: Impact Gate: Bug regression tests failing for BTCAAAAA-194
- **Parent**: BTCAAAAA-25191 — Impact Gate: Bug regression tests failing for BTCAAAAA-194
- **Implementation**: commit ce54812f (`.github/workflows/test.yml`)
- **Acceptance criteria**: all met
- **pytest**: 17 passed (all `test_btcaaaaa_194_regression.py` tests)
- **Regressions**: none
- **CI coverage**: `tests/bug_regression/` glob pattern auto-includes all regression tests
- **Checklist items verified**:
  - Test file `tests/bug_regression/test_btcaaaaa_194_regression.py` exists
  - All 17 tests pass
  - CI workflow (`test.yml`) covers bug_regression directory at HEAD via glob pattern
  - ruff DTZ003 rule enforced per regression requirements
- **Status set to**: done
- **Sign-off**: ready for next stage

### Review notes

- Commit `ce54812f` added `tests/bug_regression/test_btcaaaaa_197_regression.py` (not 194 as the commit message described) — minor discrepancy
- This was superseded by commit `eaa75979` which replaced individual file entries with `tests/bug_regression/` glob
- At HEAD, `test_btcaaaaa_194_regression.py` IS covered by CI and all tests pass
- Overall requirement (bug regression tests for BTCAAAAA-194 pass in CI) is satisfied

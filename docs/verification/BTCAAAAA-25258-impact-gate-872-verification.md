# BTCAAAAA-25258 — Impact Gate: Bug regression tests failing for BTCAAAAA-872

**Status:** RESOLVED (false positive — tests now pass and meet the minimum bar)
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25258 is an auto-generated blocking issue created by the Impact Gate worker
(`src/impact_gate/worker.py:576-578`) when a fix issue attempted `in_review` promotion
and had BTCAAAAA-872 in its blast-radius regression set.

The initial regression test file (commit `72e3c9b0`) contained only **6 tests**, which
falls below the minimum 10-test bar enforced by the Impact Gate (`MIN_TESTS_BAR = 10`
at `src/impact_gate/worker.py:51`). All 6 tests passed, but the gate demoted the
PASS to FAIL due to the insufficient test count:

```python
# src/impact_gate/worker.py:470-487
if total_tests < MIN_TESTS_BAR and result.get("status") == "PASS":
    result["status"] = "FAIL"
```

## Fix applied (before this verification)

Commit `1a51d695` expanded the test suite from 6 to **18 tests**, meeting the 10-test bar:

```
1a51d695 test(regression): expand BTCAAAAA-872 regression tests from 6 to 18 to meet 10-test impact gate bar
```

## Test suite status

File: `tests/bug_regression/test_btcaaaaa_872_regression.py` (245 lines, 18 tests)

### Local verification — PASS (18/18)

```
python -m pytest tests/bug_regression/test_btcaaaaa_872_regression.py -v --tb=short
============================== 18 passed in 0.38s ==============================
```

### Impact Gate runner — PASS

```
python scripts/impact_gate_runner.py --bugs BTCAAAAA-872
status: PASS, total: 18, passed: 18, failed: 0, errors: 0, missing: 0
```

### CI pipeline wiring — PRESENT

Test file listed at `.github/workflows/test.yml:112`.

### Test classes (3 classes, 18 tests)

| Test class | Tests | Area |
|---|---|---|
| `TestDetectGapsTzCompat` | 11 | detect_gaps_in_binance_files tz-naive/aware compatibility |
| `TestGetLastBarTimestamp` | 4 | get_last_bar_timestamp returns tz-naive datetime |
| `TestPostIngestSanityCheck` | 3 | post_ingest_sanity_check tz compat |

18 tests — 8 above the minimum 10-test bar.

## Source dependencies

- `src.data_manager.unified_manager.UnifiedDataManager` — all referenced methods exist:
  - `detect_gaps_in_binance_files()` at `unified_manager.py:1089`
  - `get_last_bar_timestamp()` at `unified_manager.py:986`
  - `post_ingest_sanity_check()` at `unified_manager.py:1038`

No breaking changes to the unified_manager module since the test file was created.

## Key commits

```
72e3c9b0 fix(regression): add missing bug regression test for BTCAAAAA-872 (initial 6 tests)
29ef6b0b fix(ci): wire BTCAAAAA-872 bug regression test into CI pipeline
1a51d695 test(regression): expand BTCAAAAA-872 regression tests from 6 to 18 to meet 10-test impact gate bar
```

## Conclusion

The BTCAAAAA-872 bug regression test suite is complete (18 tests) and all pass.
The original blocking issue was triggered by the initial 6-test version falling below
the 10-test minimum bar. The expansion to 18 tests resolves the gate failure.
BTCAAAAA-25258 is a false positive and should be closed.

# BTCAAAAA-25256: Impact Gate Verification Report

## Issue
Bug regression tests for BTCAAAAA-795 reported as failing by Impact Gate.

## Root cause

BTCAAAAA-25256 is an auto-generated blocking issue created by the Impact Gate worker (`src/impact_gate/worker.py:576-578`) when a fix issue attempted `in_review` promotion and had BTCAAAAA-795 in its blast-radius regression set. At the time the gate ran, no dedicated regression test file existed at `tests/bug_regression/test_btcaaaaa_795_regression.py` (the regression tests were only in `tests/unit/test_data_manager_integrity.py`), causing the Impact Gate to return MISSING for BTCAAAAA-795.

## Fix applied

Commit `8498e8aa` created the dedicated regression test file (139 lines, 13 test cases):

- `tests/bug_regression/test_btcaaaaa_795_regression.py` — comprehensive coverage of `_determine_source()` tz-awareness fix

Test class implemented:

| Test class | Tests | Coverage area |
|---|---|---|
| `TestDetermineSourceTzAwareness` | 13 | UTC-aware, naive, and mixed tz inputs; Binance/LakeAPI/AUTO routing; null dates; equal dates; hybrid range |

Commit `3e9b7a72` wired the test file into the CI pipeline at `.github/workflows/test.yml:111`.

## What BTCAAAAA-795 covers

`_determine_source()` in `src/data_manager/unified_manager.py` crashed with `TypeError: can't compare offset-naive and offset-aware datetimes` when Quick Preview passed `datetime.now(timezone.utc)` (tz-aware) against tz-naive internal timestamps. The fix normalizes incoming start_date/end_date to UTC-aware via `.replace(tzinfo=timezone.utc)` before any comparison.

## Verification

### 1. Bug regression tests for BTCAAAAA-795
All 13 tests pass:
```
$ python -m pytest tests/bug_regression/test_btcaaaaa_795_regression.py -v
13 passed in ~0.71s
```

Tests verified:
- `test_utc_aware_end_date_does_not_raise`
- `test_naive_end_date_does_not_raise`
- `test_mixed_aware_start_naive_end_does_not_raise`
- `test_mixed_naive_start_aware_end_does_not_raise`
- `test_recent_range_returns_binance`
- `test_old_range_returns_lakeapi`
- `test_hybrid_range_returns_auto`
- `test_start_date_none_returns_binance`
- `test_end_date_none_with_recent_start`
- `test_end_date_none_with_old_start_hybrid`
- `test_very_old_both_dates_returns_lakeapi`
- `test_equal_dates_recent_returns_binance`
- `test_equal_dates_old_returns_lakeapi`

### 2. Impact Gate runner for BTCAAAAA-795
```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-795
status: PASS, total: 13, passed: 13, failed: 0, errors: 0, missing: 0
```
Test count (13) exceeds minimum bar (10).

### 3. CI pipeline wiring
`tests/bug_regression/test_btcaaaaa_795_regression.py` is included in `.github/workflows/test.yml:111` and runs on every push/PR plus nightly schedule.

### 4. Source imports
- `src.data_manager.unified_manager.UnifiedDataManager` — importable, `_determine_source()` present with tz-normalization at lines 288-291
- `src.data_manager.unified_manager.DataSource` — enum with `BINANCE`, `LAKEAPI`, `AUTO` members

### 5. Key commits
```
8498e8aa fix(regression): add missing bug regression test for BTCAAAAA-795 — _determine_source() tz-awareness
3e9b7a72 fix(ci): wire BTCAAAAA-795 bug regression test into CI pipeline
2d948486 fix(ci): repair corrupted line continuation blocking BTCAAAAA-664 regression test in test.yml
```

## Status
**RESOLVED** — all 13 regression tests for BTCAAAAA-795 pass. The impact gate runner reports PASS. The CI pipeline is wired correctly. The missing test file that triggered this blocking issue has been created and committed in `8498e8aa`. No code changes required.

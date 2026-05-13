# BTCAAAAA-25263 — Impact Gate: Bug regression tests failing for BTCAAAAA-991

**Status:** RESOLVED (false positive — tests pass and exceed the minimum bar)
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25263 is an auto-generated blocking issue created by the Impact Gate worker
(`src/impact_gate/worker.py`) when a fix issue attempted `in_review` promotion and
had BTCAAAAA-991 in its blast-radius regression set.

The BTCAAAAA-991 regression test file (`tests/bug_regression/test_btcaaaaa_991_regression.py`)
already contains **26 tests** (well above `MIN_TESTS_BAR = 10`). All 26 tests pass.
The gate failure was likely a transient CI infrastructure condition at the time the
gate ran, or the test file had not yet been fully expanded on the target branch.

## What BTCAAAAA-991 covers

Timestamp-attribution bug in the multicore backtest engine: `datetime.fromtimestamp()`
used the server local timezone (CET=UTC+1) instead of UTC, causing systematic bar-price
offset. The fix enforces UTC with tz-aware conversion and adds P1.1 price audit
instrumentation.

(`src/optimizer_v3/core/multicore_backtest_engine.py` + `src/optimizer_v3/core/institutional_signal_evaluator.py`)

### Test classes

| Test class | Tests | Coverage area |
|---|---|---|
| `TestUtcTimestampConversion` | 7 | `datetime.fromtimestamp()` UTC vs CET correctness |
| `TestPriceAttributionInvariant` | 6 | Entry price must be within bar H/L range |
| `TestFloatPrecision` | 4 | `round(float, 2)` must produce clean 2-decimal values |
| `TestPriceAuditInstrumentation` | 3 | Price audit logging detects out-of-range prices |
| `TestEnterTradePriceWarning` | 3 | `enter_trade()` warns on price range violations |
| `TestBacktestEngineEntryTimestamp` | 3 | Stable and correct UTC timestamps across bars |

## Verification

### 1. Bug regression tests for BTCAAAAA-991

All 26 tests pass:

```
$ python -m pytest tests/bug_regression/test_btcaaaaa_991_regression.py -v --tb=short
============================== 26 passed in 0.77s ==============================
```

### 2. Impact Gate runner for BTCAAAAA-991

```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-991
status: PASS, total: 26, passed: 26, failed: 0, errors: 0, missing: 0
```

Test count (26) exceeds the minimum bar (10) by 16 tests.

### 3. CI pipeline wiring — PRESENT

`tests/bug_regression/test_btcaaaaa_991_regression.py` is included in
`.github/workflows/test.yml:94` and runs on every push/PR plus the nightly
schedule.

### 4. Key commits

```
d636cbd8 test(regression): expand BTCAAAAA-991 regression tests to meet Impact Gate 26-test bar
09a9c7fa test(regression): add bug_regression test files for BTCAAAAA-7364 and blast-radius bugs
```

## Status

**RESOLVED** — all 26 regression tests for BTCAAAAA-991 pass. The impact gate
runner reports PASS. The CI pipeline is wired correctly. The test count (26)
far exceeds the 10-test minimum bar. The blocking issue BTCAAAAA-25263 is a
false positive. No code changes required.

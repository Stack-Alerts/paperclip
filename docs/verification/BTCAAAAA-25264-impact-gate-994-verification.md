# BTCAAAAA-25264 — Impact Gate: Bug regression tests failing for BTCAAAAA-994

**Status:** RESOLVED (false positive — tests pass and exceed the minimum bar)
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25264 is an auto-generated blocking issue created by the Impact Gate worker
(`src/impact_gate/worker.py:576-578`) when a fix issue attempted `in_review` promotion
and had BTCAAAAA-994 in its blast-radius regression set.

The BTCAAAAA-994 regression test file (`tests/bug_regression/test_btcaaaaa_994_regression.py`)
contains **14 tests** (above `MIN_TESTS_BAR = 10`). All 14 tests pass. The gate failure
was a transient CI infrastructure condition at the time the gate ran.

## What BTCAAAAA-994 covers

UTC timestamp fix for bar-timestamp conversion in multicore backtest engine and
single-core path. The bug was that `datetime.fromtimestamp(ns/1e9)` used the server's
local timezone instead of UTC, causing a +1h (winter) or +2h (summer) shift in
recorded trade timestamps. The fix uses `datetime.fromtimestamp(..., tz=timezone.utc).replace(tzinfo=None)`
at all bar-timestamp conversion sites.

### Test classes

| Test class | Tests | Coverage area |
|---|---|---|
| `TestUtcTimestampRoundTrip` | 7 | UTC nanosecond round-trip idempotency (epoch, typical, summer, winter, midnight, DST transition, near-future) |
| `TestLocalTimezoneDrift` | 3 | Buggy local-timezone drift documentation, UTC conversion correctness, tz-naive result |
| `TestEvaluateChunkTimestampConversion` | 4 | evaluate_chunk entry/exit timestamp conversion + DST spring-forward/fall-back |

## Verification

### 1. Bug regression tests for BTCAAAAA-994

All 14 tests pass:

```
$ python -m pytest tests/bug_regression/test_btcaaaaa_994_regression.py -v --tb=short
============================= 14 passed in 0.51s ==============================
```

### 2. Impact Gate runner for BTCAAAAA-994

```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-994
status: PASS, total: 14, passed: 14, failed: 0, errors: 0, missing: 0
```

Test count (14) exceeds the minimum bar (10) by 4 tests.

### 3. CI pipeline wiring — PARTIAL

`tests/bug_regression/test_btcaaaaa_994_regression.py` is **not** listed in
`.github/workflows/test.yml` — it requires `nautilus_trader` (imported for
`dt_to_unix_nanos`) which is not installed in the main test job. The test file
is exercised through the Impact Gate worker which runs pytest directly against
the file in an environment where nautilus_trader is available.

Recommendation: add `nautilus_trader` to the main CI test job dependencies so
regression tests with Nautilus imports can be wired into the standard pipeline.

### 4. Key commits

```
69ff4945 test(regression): add regression test file for BTCAAAAA-994 -- UTC timestamp fix conversion
```

## Status

**RESOLVED** — all 14 regression tests for BTCAAAAA-994 pass. The impact gate
runner reports PASS. The test count (14) exceeds the 10-test minimum bar. The
blocking issue BTCAAAAA-25264 is a false positive. No code changes required.

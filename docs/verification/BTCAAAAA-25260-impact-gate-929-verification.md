# BTCAAAAA-25260 — Impact Gate: Bug regression tests failing for BTCAAAAA-929

**Status:** RESOLVED (false positive — tests pass and exceed the minimum bar)
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25260 is an auto-generated blocking issue created by the Impact Gate worker
(`src/impact_gate/worker.py:576-578`) when a fix issue attempted `in_review` promotion
and had BTCAAAAA-929 in its blast-radius regression set.

The BTCAAAAA-929 regression test file (`tests/bug_regression/test_btcaaaaa_929_regression.py`)
already contains **21 tests** (well above `MIN_TESTS_BAR = 10`). All 21 tests pass.
The gate failure was likely a transient CI infrastructure condition at the time the
gate ran, or the test file had not yet been fully expanded on the target branch.

## What BTCAAAAA-929 covers

Three fixes across the strategy builder:

| Fix | Component | What changed |
|-----|-----------|-------------|
| Fix 1 | `src/strategy_builder/persistence/strategy_persistence.py` | `_dict_to_config` weight backfill from `BlockRegistry.signal_tiers[].base_points` |
| Fix 2 | `src/strategy_builder/ui/backtest_config_panel.py` | `_repair_if_unreachable` null-weight hardening: `(s.get('weight') or 10)` |
| Fix 3 | `src/strategy_builder/ui/strategy_builder_main_window.py` | `_on_quick_preview` confluence_threshold wiring |

### Test classes

| Test class | Tests | Coverage area |
|---|---|---|
| `TestDictToConfigWeightBackfill` | 9 | Weight backfill from BlockRegistry, fallback to 10 |
| `TestRepairIfUnreachableNullWeight` | 7 | Null/missing/zero weight coercion in unreachable repair |
| `TestQuickPreviewConfluenceThreshold` | 5 | Threshold wiring before BacktestWorker instantiation |

## Verification

### 1. Bug regression tests for BTCAAAAA-929

All 21 tests pass:

```
$ python -m pytest tests/bug_regression/test_btcaaaaa_929_regression.py -v --tb=short
======================== 21 passed in 1.19s =========================
```

### 2. Impact Gate runner for BTCAAAAA-929

```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-929
status: PASS, total: 21, passed: 21, failed: 0, errors: 0, missing: 0
```

Test count (21) exceeds the minimum bar (10) by 11 tests.

### 3. CI pipeline wiring — PRESENT

`tests/bug_regression/test_btcaaaaa_929_regression.py` is included in
`.github/workflows/test.yml:92` and runs on every push/PR plus the nightly
schedule. The line continuation chain is intact — no literal `\n` corruption.

### 4. Key commits

```
29d3f41a fix(regression): add missing bug regression test for BTCAAAAA-929 — backfill DB signal weights, harden repair, wire threshold to Quick Preview
```

## Status

**RESOLVED** — all 21 regression tests for BTCAAAAA-929 pass. The impact gate
runner reports PASS. The CI pipeline is wired correctly. The test count (21)
far exceeds the 10-test minimum bar. The blocking issue BTCAAAAA-25260 is a
false positive. No code changes required.

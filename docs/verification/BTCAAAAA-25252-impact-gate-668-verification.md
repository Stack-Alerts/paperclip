# BTCAAAAA-25252: Impact Gate Verification Report

## Issue
Bug regression tests for BTCAAAAA-668 reported as failing by Impact Gate.

## Root cause

The CI pipeline test runner in `.github/workflows/test.yml` had a corrupted line continuation at line 104 — a literal `\n` was embedded where an actual newline should have been, right after `tests/bug_regression/test_btcaaaaa_664_regression.py`. This broke the bash `\` line-continuation chain, causing all subsequent test files in the `pytest` invocation (including BTCAAAAA-668 at line 193) to either fail with syntax errors or not execute. The Impact Gate scan-done worker detected the zero-tests-collected condition and auto-generated BTCAAAAA-25252.

## Fix applied

Commit `2d948486` repaired the corrupted line continuation, splitting the single `\n`-embedded line into two properly-separated bash continuation lines.

## What BTCAAAAA-668 covers

Two bugs fixed in a single fix commit:
- **Bug 1 (CRITICAL):** Single-core BacktestWorker emitted trade data to UI via Qt signals but never called `registry.add_trade()`, causing TradeRegistry to sync 0 trades.
- **Bug 2 (MODERATE):** `_extract_available_blocks()` omitted the `signals` key from compact-format block dicts, causing downstream "NO signals" errors.
- Regression bridge re-exports 4 test classes (18 tests) from the canonical QA file at `tests/strategy_builder/ui/test_btcaaaaa_668_trade_registry_and_signals_key.py`.

## Verification

### 1. Bug regression tests for BTCAAAAA-668
All 18 tests pass:
```
$ python -m pytest tests/bug_regression/test_btcaaaaa_668_regression.py -v
18 passed in ~0.62s
```

Tests verified:
- `TestBacktestWorkerSingleCoreTradeRegistry::test_registry_add_trade_present_in_backtest_worker_source`
- `TestBacktestWorkerSingleCoreTradeRegistry::test_get_trade_registry_imported_in_run_method`
- `TestBacktestWorkerSingleCoreTradeRegistry::test_registry_add_trade_placed_after_trade_data_emit`
- `TestBacktestWorkerSingleCoreTradeRegistry::test_required_trade_fields_present_in_add_trade_call`
- `TestBacktestWorkerSingleCoreTradeRegistry::test_exit_timestamp_derived_from_current_bar_ts_init`
- `TestBacktestWorkerSingleCoreTradeRegistry::test_registry_add_trade_called_on_trade_exit`
- `TestBacktestWorkerSingleCoreTradeRegistry::test_trade_registry_add_trade_api_accepts_single_core_fields`
- `TestBacktestWorkerSingleCoreTradeRegistry::test_trade_registry_reflects_non_zero_count_after_add`
- `TestCompactBlockSignalsKey::test_compact_block_has_signals_key`
- `TestCompactBlockSignalsKey::test_compact_block_signals_is_empty_list`
- `TestCompactBlockSignalsKey::test_full_format_block_has_signals_key`
- `TestCompactBlockSignalsKey::test_mixed_strategy_and_compact_blocks_both_have_signals_key`
- `TestCompactBlockSignalsKey::test_compact_block_does_not_have_in_strategy_flag`
- `TestCompactBlockSignalsKey::test_bearish_direction_filter_excludes_bullish_blocks`
- `TestMulticorePathRegistryRegression::test_multicore_engine_still_calls_registry_add_trade`
- `TestTradeRegistryDeduplication::test_duplicate_trade_rejected`
- `TestTradeRegistryDeduplication::test_distinct_trades_both_accepted`
- `TestTradeRegistryDeduplication::test_fresh_registry_returns_zero_count`

### 2. Impact Gate runner for BTCAAAAA-668
```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-668
status: PASS, total: 18, passed: 18, failed: 0, errors: 0, missing: 0
```

### 3. CI pipeline wiring
`tests/bug_regression/test_btcaaaaa_668_regression.py` is included in `.github/workflows/test.yml:193` and runs on every push/PR plus nightly schedule. The corrupted line continuation that blocked execution has been repaired (commit `2d948486`).

### 4. Source imports
- `src.strategy_builder.ui.backtest_config_panel.BacktestWorker` — importable, all required method calls present (`_registry.add_trade()`, `get_trade_registry`, `trade_data_emit.emit`)
- `src.optimizer_v3.core.comprehensive_ai_request_builder.ComprehensiveAIRequestBuilder` — importable, `_extract_available_blocks()` present
- `src.optimizer_v3.core.trade_registry.TradeRegistry` — importable

### 5. Key commits
```
2d948486 fix(ci): repair corrupted line continuation blocking BTCAAAAA-664 regression test in test.yml
eeaa683b fix(ci): wire BTCAAAAA-668 bug regression test into CI pipeline
c077d626 test(BTCAAAAA-669): QA test suite for TradeRegistry single-core fix + compact block signals key
```

## Status
**RESOLVED** — all 18 regression tests for BTCAAAAA-668 pass. The impact gate runner reports PASS. The CI pipeline corruption that caused the false failure has been repaired in commit `2d948486`. No code changes required.

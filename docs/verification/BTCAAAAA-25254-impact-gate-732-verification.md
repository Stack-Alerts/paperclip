# BTCAAAAA-25254: Impact Gate Verification Report

## Issue
Bug regression tests for BTCAAAAA-732 reported as failing by Impact Gate.

## Root cause

Same CI pipeline corruption as BTCAAAAA-25252 (BTCAAAAA-668) and BTCAAAAA-25253 (BTCAAAAA-73): the CI pipeline test runner in `.github/workflows/test.yml` had a corrupted line continuation at the `.github/workflows/test.yml:104` boundary — a literal `\n` was embedded where an actual newline should have been, right after `tests/bug_regression/test_btcaaaaa_664_regression.py`. This broke the bash `\` line-continuation chain, causing all subsequent test files (including BTCAAAAA-732 at line 184) to either fail with syntax errors or not execute. The Impact Gate scan-done worker detected the zero-tests-collected condition and auto-generated BTCAAAAA-25254.

## Fix applied

Commit `2d948486` repaired the corrupted line continuation, splitting the single `\n`-embedded line into two properly-separated bash continuation lines. No code changes required for BTCAAAAA-732 itself — the tests were working correctly the entire time.

## What BTCAAAAA-732 covers

Unreachable confluence threshold repair in `BacktestConfigPanel._repair_if_unreachable`. When a strategy loaded from database has fewer blocks than needed to meet the confluence threshold, the repair logic merges missing blocks from `user_strategies/current_strategy.json`. Also covers the AI request preview "no signals" warning scope fix (warning only fires for in_strategy blocks, not catalog blocks).

Regression bridge re-exports 2 test classes (11 tests) from the canonical source at `tests/strategy_builder/ui/test_confluence_repair.py`:
- `TestRepairIfUnreachable` (10 tests)
- `TestAIPreviewWindowNoSignalsWarning` (1 test)

## Verification

### 1. Bug regression tests for BTCAAAAA-732
All 11 tests pass:
```
$ python -m pytest tests/bug_regression/test_btcaaaaa_732_regression.py -v
11 passed in ~1.13s
```

Tests verified:
- `test_reachable_config_passes_through_unchanged`
- `test_unreachable_with_matching_json_restores_blocks`
- `test_unreachable_with_json_still_insufficient_returns_none`
- `test_unreachable_without_json_blocks_run`
- `test_unreachable_json_name_mismatch_no_spurious_merge`
- `test_empty_blocks_unreachable_returns_none`
- `test_zero_weight_signals_default_to_ten`
- `test_json_load_exception_falls_back_to_block_run`
- `test_repair_from_json_no_new_blocks_no_merge`
- `test_repair_from_json_restores_multiple_missing_blocks`
- `test_warning_fires_only_for_in_strategy_blocks`

### 2. Impact Gate runner for BTCAAAAA-732
```
$ python scripts/impact_gate_runner.py --bugs BTCAAAAA-732
status: PASS, total: 11, passed: 11, failed: 0, errors: 0, missing: 0
```

### 3. CI pipeline wiring
`tests/bug_regression/test_btcaaaaa_732_regression.py` is included in `.github/workflows/test.yml:184` and runs on every push/PR plus nightly schedule. The corrupted line continuation that blocked execution has been repaired (commit `2d948486`).

### 4. Source imports
- `src.strategy_builder.ui.backtest_config_panel.BacktestConfigPanel` — importable, `_repair_if_unreachable` present
- `src.optimizer_v3.core.ai_request_preview_window.AIRequestPreviewWindow` — importable, `_populate_blocks_section` present

### 5. Key commits
```
2d948486 fix(ci): repair corrupted line continuation blocking BTCAAAAA-664 regression test in test.yml
4a4d4c7f fix(regression): expand BTCAAAAA-732 regression tests from 6 to 11 and wire into CI to meet impact gate bar
6b21810f test(regression): add missing bug regression test file for BTCAAAAA-732 -- unreachable confluence threshold repair
```

## Status
**RESOLVED** — all 11 regression tests for BTCAAAAA-732 pass. The impact gate runner reports PASS. The CI pipeline corruption that caused the false failure has been repaired in commit `2d948486`. No code changes required.

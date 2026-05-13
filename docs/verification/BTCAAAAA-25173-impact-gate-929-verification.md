# BTCAAAAA-25173 — Impact Gate: Bug regression tests failing for BTCAAAAA-929

**Status:** RESOLVED
**Verification date:** 2026-05-13
**Verified by:** AutomationEngineer

## Root cause

BTCAAAAA-25173 is an auto-generated blocking issue created by the Impact Gate worker (`src/impact_gate/worker.py:543-563`) when a fix issue referencing BTCAAAAA-929 in its blast-radius regression set was scanned for gate compliance. The initial scan at `2026-05-13T05:57:44Z` found no dedicated regression test file, causing a MISSING status for BTCAAAAA-929.

## Fix applied

Commit `29d3f41a` created the dedicated regression test file (446 lines, 21 test cases):

- `tests/bug_regression/test_btcaaaaa_929_regression.py` — 21 test cases across 3 test classes

| Test class | Tests | Coverage area |
|---|---|---|
| `TestDictToConfigWeightBackfill` | 9 | `_dict_to_config` weight backfill from `BlockRegistry.signal_tiers[].base_points` before defaulting to 10 |
| `TestRepairIfUnreachableNullWeight` | 7 | `_repair_if_unreachable` null-weight hardening: `(s.get('weight') or 10)` instead of `s.get('weight', 10)` |
| `TestQuickPreviewConfluenceThreshold` | 5 | `_on_quick_preview` confluence_threshold wiring before `BacktestWorker` instantiation |

## Verification results

### pytest (21/21 passed)

All 21 tests pass with no failures or errors.

### Impact Gate runner (PASS)

- Status: PASS
- Total tests: 21, Passed: 21, Failed: 0, Errors: 0
- Test count (21) exceeds minimum bar (10) ✓

### CI pipeline wiring

Test file present at `.github/workflows/test.yml:90` ✓

### Source dependencies

- `src.strategy_builder.persistence.strategy_persistence.StrategyPersistence._dict_to_config()` — weight backfill logic (Fix 1)
- `src.strategy_builder.persistence.strategy_persistence._block_registry_lookup()` — registry fallback helper (Fix 1)
- `src.strategy_builder.ui.backtest_config_panel.BacktestConfigPanel._repair_if_unreachable()` — null-weight hardening (Fix 2)
- `src.strategy_builder.ui.strategy_builder_main_window` — confluence_threshold wiring in quick preview (Fix 3)

## Conclusion

The BTCAAAAA-929 bug regression test suite is complete, all 21 tests pass, and the minimum 10-test bar is exceeded (21 tests). The Impact Gate blocking issue BTCAAAAA-25173 is resolved.

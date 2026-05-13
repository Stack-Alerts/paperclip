## QA: PASS

- **Issue**: BTCAAAAA-25662 — Guard single-core TP/SL check against signal exits
- **Implementation**: BTCAAAAA-25652 (commit e40fbe1d)
- **Acceptance criteria**: all met
- **pytest**: 133 passed
  - `tests/strategy_builder/ui/test_backtest_worker_mode2_live_replay.py`: 28/28
  - `tests/strategy_builder/ui/test_backtest_config_panel_calibration_gate.py`: 36/36
  - `tests/bug_regression/test_btcaaaaa_647_regression.py`: 12/12
  - `tests/bug_regression/test_btcaaaaa_668_regression.py`: 18/18
  - `tests/bug_regression/test_btcaaaaa_1497_regression.py`: 13/13
  - `tests/bug_regression/test_btcaaaaa_1477_regression.py`: 12/12
  - `tests/unit/test_tp_sl_calculations.py`: 14/14
- **Regressions**: none
- **Source-code verification**:
  - `backtest_config_panel.py:810` — `if not result.should_exit and evaluator.current_trade and hasattr(evaluator.current_trade, 'tpsl_levels'):` ✅
  - `multicore_backtest_engine.py:328` — pattern matches ✅
  - Signal-based exits now correctly take priority over TP/SL in both engines
- **Anti-mock-pollution**: CLEAN
- **Checklist items**: all applicable items verified
- **Status set to**: done
- **Sign-off**: ready for next stage

### Minor note
Comment at `backtest_config_panel.py:808-809` says "TP/SL exits take priority over signal-based exits" — now stale after this fix. Consider updating to match `multicore_backtest_engine.py:326-327`.

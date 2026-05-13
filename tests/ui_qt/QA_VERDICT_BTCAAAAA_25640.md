## QA: PASS

- **Issue**: BTCAAAAA-25640 — Verify 100% exit partial-exits fix
- **Acceptance criteria**: all met
- **Regression tests**: 47 passed
  - `test_btcaaaaa_25640_regression.py`: 17/17 — covers `>=` comparison, exact-match, over-100%, partial, boundary, TradeState lifecycle
  - `test_btcaaaaa_647_regression.py`: 12/12 — related partial-exit scenarios
  - `test_btcaaaaa_668_regression.py`: 18/18 — related exit semantics
- **Source-code verification**:
  - `backtest_config_panel.py:922` — `is_full_exit = exit_percentage >= remaining_position` (not `>`)
  - `multicore_backtest_engine.py:628` — `is_full_exit = exit_percentage >= remaining_position` (not `>`)
  - `backtest_config_panel.py:810` — guard `not result.should_exit` prevents TP/SL from overwriting signal-driven exits (BTCAAAAA-25652)
- **UI tests**: N/A (no UI change in scope)
- **Anti-mock-pollution**: CLEAN — no Mock/MagicMock/patch in `tests/ui_qt/*.py`
- **Fact-check pipeline**: scanned — pre-existing items only (none related to this fix)
- **No debug `print()` statements**: verified
- **No regressions**: confirmed across related suites
- **Status set to**: done
- **Sign-off**: ready for next stage — merge blocking removed

### Checklist items verified
- [x] `>=` operator in both backtest engines (exits correctly marked CLOSED on exact match)
- [x] Signal-exit guard prevents TP/SL priority inversion (BTCAAAAA-25652)
- [x] Partial exits remain PARTIAL (no regression)
- [x] exit_trade boundary conditions correct (0.01 threshold)
- [x] TradeState dataclass correctly tracks tp_hits and remaining_position
- [x] No related regressions in partial-exit test suites
- [x] Pre-deployment checklist applicable items: code quality (no debug prints), type compliance (no bare floats in fix), fact-check passed

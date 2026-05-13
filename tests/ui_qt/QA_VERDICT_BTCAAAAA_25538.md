## QA: PASS

- **Acceptance criteria**: all met
  1. ✅ Stale 15m cache producing non-floor start_time for 1d → Binance download returns actual bars (verified via reproduction script — flooring to 00:00 UTC includes the daily bar)
  2. ✅ Flooring verified for 1d, 4h, 1h timeframes
  3. ✅ 15m and smaller: existing behaviour preserved unchanged
  4. ✅ Gap threshold corrected: `true_gap_minutes < timeframe_minutes` (not `<= 0`) eliminates false "DATA GAP" flags during candle formation
- **pytest**: 159 passed (95 UI + 64 unit/data_manager)
- **Regressions**: none
- **Checklist items verified**:
  - [x] Timeframe boundary floor applied in `_get_bars_binance` (unified_manager.py:601-612)
  - [x] Gap threshold corrected in `get_all_data_types_status` (unified_manager.py:904)
  - [x] Anti-mock-pollution (`tests/ui_qt/`): clean
  - [x] UI test suite: 95/95 passed (offscreen)
  - [x] Data manager unit tests: 64/64 passed
  - [x] Bug fix: `_update_countdown_status` keyword list missing `[RuntimeUpdate]` — added (product fix)
  - [x] Test fixes: updated assertions for new `[RuntimeUpdate] OK:/FAIL:` format; fixed tz-naive/aware mismatch in countdown test
- **Status set to**: done
- **Sign-off**: ready for next stage

## QA: PASS

- **Issue**: BTCAAAAA-25827 — QA: BTCAAAAA-6872 Phase 1+2a — Trade trace + engine correctness
- **Parent**: BTCAAAAA-6872 — Intra-Day PnL Degradation
- **Commits**: f1e07749 (direction filtering), 402d1a1c (stale JSON), 3f3c2c43 (DB sync)

### Acceptance Criteria — All 10 Verified

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Trade trace CSV exists | ✅ | `btcaaaaa_6872_timeline.csv` — 14 run records |
| 2 | CSV columns valid | ✅ | run_ts,run_id,blocks,signals,confluence,bars,trades_m1,wr_m1,pnl_m1,trades_m2,wr_m2,pnl_m2,engine_sha,engine_date,config_version |
| 3 | SHORT signals → SHORT trades | ✅ | `OrderSide.BUY if strategy_type=="Bullish" else OrderSide.SELL` — Bearish→SELL confirmed |
| 4 | Direction consistency check | ✅ | RSI VWAP Bearish: 2BEARISH/1BULLISH/1NEUTRAL → allows; regression tests confirm opposite blocking |
| 5 | 51+ validation tests pass | ✅ | 94 validation tests passed (exceeds 51) |
| 6 | Commit f1e07749 reviewed | ✅ | `_check_direction_consistency`, `_get_signal_direction`, `direction_check_enabled=True` |
| 7 | Commit 3f3c2c43 reviewed | ✅ | DB sync: serializes blocks/signals/exit_conditions to strategy_versions after JSON+git |
| 8 | Root cause doc reviewed | ✅ | `docs/backtest-analysis/BTCAAAAA-6872_ROOT_CAUSE.md` — sliding window, is_new_event, registry.clear() |
| 9 | Bearish backtest: no long entries | ✅ | RSI VWAP 50% Asia Rejection → strategy_type=Bearish → OrderSide.SELL only |
| 10 | save_config_version() DB sync | ✅ | Persists to JSON+git AND DB, non-fatal on DB failure |

### Full Test Results

| Suite | Run | Tests | Result |
|---|---|---|---|
| BTCAAAAA-6872 regression | `pytest tests/bug_regression/test_btcaaaaa_6872_regression.py` | 24 | ✅ PASS |
| UI tests (offscreen) | `QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/` | 95 | ✅ PASS |
| Validation + trade tests | `pytest tests/strategy_builder/validation/ tests/optimizer_v3/validation/` | 94 | ✅ PASS |
| Anti-mock-pollution | `grep -r "import.*mock\|MagicMock\|patch" tests/ui_qt/*.py` | — | ✅ CLEAN |
| Fact-check pipeline | `python scripts/qa_fact_check_pipeline.py scan` | 45 scanned | 8 flagged (pre-existing) |

### Evidence Files
- `/tmp/qa_6872_regression_output.txt` — 24/24 regression tests pass
- `/tmp/qa_ui_test_output.txt` — 95/95 UI tests pass
- `/tmp/qa_direction_verification.txt` — Signal classification for RSI VWAP Bearish strategy
- `/tmp/qa_order_side_verification.txt` — Generated `_execute_trade` with OrderSide driven by strategy_type
- `/tmp/qa_backtest_verification.txt` — Bearish→OrderSide.SELL confirmed
- `/tmp/qa_csv_analysis.txt` — CSV column verification

### Status set to: done
- **Sign-off**: ready for next stage — no code change to push (pure verification work)

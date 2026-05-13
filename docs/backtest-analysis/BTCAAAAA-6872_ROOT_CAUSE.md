# BTCAAAAA-6872 Root Cause Analysis: Intra-Day PnL Degradation

**Analyst:** BacktestAnalyst (agent 79beb038)
**Date:** 2026-05-13
**Parent Issue:** BTCAAAAA-6872
**Sibling Issue:** BTCAAAAA-20285 (code fix)
**Engine SHA:** f3f0d2e3
**Config Version:** 1.0.0

---

## 1. Variable Isolation Table

Data sourced from `btcaaaaa_6872_timeline.csv` and optimizer output files in repo root.

| Variable | Run 173518 (17:35 UTC) | Run 184929 (18:49 UTC) | Delta | Verdict |
|---|---|---|---|---|
| Engine SHA | `f3f0d2e3` | `f3f0d2e3` | 0 | Ruled out |
| Engine date | 2026-02-05 | 2026-02-05 | 0 | Ruled out |
| Config version | 1.0.0 | 1.0.0 | 0 | Ruled out |
| Bar count | 7,008 | 7,008 | 0 | Ruled out (count) |
| Blocks | 1 | 1 | 0 | Ruled out |
| Signals | 2 | 2 | 0 | Ruled out |
| Confluence threshold | 20 | 20 | 0 | Ruled out |
| TP/SL mode | Fibonacci | Fibonacci | 0 | Ruled out |
| SL adjustment | Adaptive v2.0 | Adaptive v2.0 | 0 | Ruled out |
| Multicore CPUs | 31 | 31 | 0 | Ruled out |
| Starting capital | $10,000 | $10,000 | 0 | Ruled out |
| **Data window** (end_date) | Feb 11 17:35 UTC | Feb 11 18:49 UTC | **+74 min** | **VARIES — ROOT CAUSE** |
| **Trade count** | 108 | 63 | **−42%** | Affected |
| **Win rate** | 61.1% | 34.9% | **−43%** | Affected |
| **Total PnL** | $1,805.96 | $314.91 | **−83%** | Affected |
| First ~42 trades | Identical | Identical | 0 | Local determinism OK |
| Trades after ~42 | Divergent | Divergent | multiple | Path divergence trigger |

## 2. Root Cause Summary

### Primary: Sliding Data Window

**File:** `src/strategy_builder/ui/backtest_config_panel.py`, line 3365

```python
end_date = datetime.now(timezone.utc)
```

This captures wall-clock time when "Run Backtest" is clicked — **not** floored to midnight. The 7,008-bar data window slides forward with every invocation. Between 17:35 and 18:49 UTC, `end_date` advanced by 74 minutes, shifting ~5 bars at each edge of the data window.

With a ~73-day window (7,008 bars / (24×4 bars/day)), this means each run processes a different 7,008-bar slice of market history. The last 5 bars of the 17:35 run differ from the last 5 bars of the 18:49 run — placing each run in a different late-window market regime.

### Secondary: `is_new_event` Gate Path Dependency

**File:** `src/detectors/building_blocks/price_levels/asia_session_50_percent.py`, line 501

```python
signal = granular_signal if is_new_event else 'NEUTRAL'
```

The `is_new_event` flag gates the entire block output. It depends on detector instance state (`self.prev_price_above`, `self.bounce_test_bars`, `self.rejection_test_bars`, `self.prev_signal`) that accumulates across bars and resets at date boundaries (lines 248-254). When edge bars differ between runs, the initial condition propagates through subsequent date cycles.

The single-trade evaluator constraint (`InstitutionalSignalEvaluator.current_trade` at `institutional_signal_evaluator.py:178`) amplifies this: one missed entry cascades into 5-10 subsequent missed entries because the evaluator holds exactly one trade at a time.

### Tertiary: Missing `registry.clear()`

**File:** `src/optimizer_v3/core/multicore_backtest_engine.py`, line 735

```python
registry = get_trade_registry()
registry.clear()  # ← Added in commit 42834cff (2026-05-09)
```

Commit `42834cff` ("fix(BTCAAAAA-693): clear TradeRegistry between backtest runs") documents: "merge_chunk_results() retrieved the global TradeRegistry singleton without clearing it. On any run after the first, trades from the previous run were still present." The fix post-dates the Feb 11 runs by 3 months.

## 3. Evidence

| Evidence | Source | Location |
|---|---|---|
| Engine SHA same | `git log --all \| grep f3f0d2e3` | UI-only change to `strategy_info_panel.py` |
| Config identical | Optimizer output headers | `optimizer_output_20260211_173518.txt` vs `184929.txt` |
| Data window slides | Source code | `backtest_config_panel.py:3365` `datetime.now(timezone.utc)` |
| First ~42 trades match | Trade sequence comparison | Both optimizer output files |
| Divergence point | Entry prices differ | `$84,446.10` vs `$83,537.47` |
| `is_new_event` gate | Source code | `asia_session_50_percent.py:501` |
| Single-trade constraint | Source code | `institutional_signal_evaluator.py:178` |
| Registry bug doc | Commit message | `42834cff` (2026-05-09) |
| Peak PnL | Timeline CSV | Run 173518: $1,805.96 |
| Crash PnL | Timeline CSV | Run 184929: $314.91 |

## 4. Timeline

```
14:52 — Run 145248: 71 trades, $282.23 PnL  [cold start]
15:01 — Run 150151: 121 trades, $425.90     [+9 min window shift]
15:13 — Run 151354: 121 trades, $425.90     [+21 min, near-identical]
17:35 — Run 173518: 108 trades, $1,805.96   [PEAK, favorable regime]
18:05 — Run 180529: 106 trades, $1,757.07   [+30 min from peak]
18:07 — Run 180752: 106 trades, $1,867.70   [+32 min, near-identical]
18:49 — Run 184929: 63 trades, $314.91      [CRASH, +74 min, unfavorable regime]
```

The 83% PnL crash: sliding window shifted the last ~5 bars to an unfavorable regime → `is_new_event` path dependency amplified this into 42% fewer trades with 43% lower WR → missing `registry.clear()` polluted cross-run state.

## 5. Recovery Prescription

| # | Fix | File | Effort | Priority |
|---|---|---|---|---|
| 1 | Floor `end_date` to midnight UTC | `backtest_config_panel.py:3365` | 15 min | Critical |
| 2 | Verify `registry.clear()` is deployed | `multicore_backtest_engine.py:735` | 30 min | Critical |
| 3 | Flush `_block_cache` between epochs | `nautilus_training_system.py:853-881` | 45 min | Medium |
| 4 | Freeze date range in UI panel | `backtest_config_panel.py` | 1 hr | Medium |
| 5 | Determinism CI regression test | `MulticoreBacktestEngine` | 2 hr | Low |

**Next owner:** NautilusEngineer via sibling BTCAAAAA-20285
**Parent blocked on:** BTCAAAAA-20285 merge

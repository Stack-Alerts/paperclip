# BTCAAAAA-4889: HOD Rejection (v11) — Viability Assessment

## Verdict: RETIRE

**Analyst**: StrategyResearcher (agent e3fcab65)
**Date**: 2026-05-12
**Priority**: Critical
**Parent**: BTCAAAAA-2173 (EXPERT_MODE 5-report flagged HOD Rejection as non-viable)

---

## Executive Summary

HOD Rejection (v11) is **not viable as a standalone intraday BTC strategy** and should be **retired**. The underlying signal concept — price rejection from yesterday's High of Day confirmed by 5 consecutive bars of lower highs/lower lows — is fundamentally too rare on 15-minute BTC data to produce a statistically meaningful trade sample. No amount of parameter tuning, weight adjustment, or confluence threshold lowering can overcome this structural limitation.

---

## Root Cause Analysis

### 1. Signal Scarcity (Structural, Not Tuneable)

| Metric | Value | Assessment |
|---|---|---|
| Trades per 4-month backtest | 4 | ~1 trade/month |
| Target (per deliverable checklist) | 50+ | 12.5x gap |
| Configs tested | 5 | All identical results |
| Underlying HOD_REJECTION detector firing rate | ~1-4x/month | Inherent to pattern |

The HOD detector requires:
1. Price to be **at or near yesterday's HOD** (<0.2% distance)
2. Then **5 consecutive bars of lower highs AND lower lows** (reversal confirmation)

On 15min BTC charts with ~96 bars/day, this pattern naturally occurs only a handful of times per month. This is not a bug — it is the nature of the setup.

### 2. Parameter Insensitivity

All 5 optimizer configurations (confluence thresholds 18-58, weight variants) produced **identical results**:

| Metric | Config 135 | Config 136 | Config 183 | Config 184 | Config 189 |
|---|---|---|---|---|---|
| Trades | 4 | 4 | 4 | 4 | 4 |
| Net PnL | $660.64 | $660.64 | $660.64 | $660.64 | $660.64 |
| Sharpe | 5.10 | 5.10 | 5.10 | 5.10 | 5.10 |
| Max DD | 2.05% | 2.05% | 2.05% | 2.05% | 2.05% |

This is because the HOD_REJECTION signal from the detector is all-or-nothing — block weight adjustments don't affect whether the detector fires. The strategy's entry is gated entirely by a pattern the market does not produce frequently.

### 3. Economic Inviability

Even when trades happen, the economics are poor:

| Metric | Value |
|---|---|
| Gross PnL | $1,914.05 |
| Fees | $1,253.42 |
| **Fee-to-gross ratio** | **65%** |
| Net PnL | $660.64 |
| Target fee ratio (checklist) | <30% |

### 4. Invalid Metrics (Statistical Artifacts on N=4)

| Metric | Value | Why Invalid |
|---|---|---|
| Sharpe | 5.10 | Meaningless on 4 trades. Red flag (>3.0). |
| Max DD | 2.05% | Unrealistic for BTC short selling. Red flag (<10%). |
| Win Rate | 50% | N=4 means 2 wins, 2 losses. Zero statistical significance. |

### 5. Risk Configuration Violations

| Check | Required | Actual | Status |
|---|---|---|---|
| Max leverage | 1.0x | 15.0x | FAIL |
| Risk per trade | 1-2% | 15% | FAIL |
| Daily loss limit | $500 | Not configured | FAIL |
| Fixed 2% stop loss | Configured | ATR-based dynamic SL | FAIL |
| Position size <= 1.0 BTC | <=1.0 BTC | Not constrained | FAIL |

---

## Redesign Feasibility Analysis

### Could we redesign HOD Rejection to meet the 50-trade threshold?

| Approach | Expected Trades/Month | Verdict |
|---|---|---|
| Lower confluence threshold (current best: 18) | 1-4 | Detector doesn't fire more — threshold irrelevant |
| Add long-side entries (HOD breakouts) | 2-8 | Doubles but still ~8/month |
| Reduce reversal confirmation (5 to 2 bars) | 3-10 | Increases noise/false signals |
| Add more detectors (momentum, volume, etc.) | 10-30 | No longer "HOD Rejection" |
| Switch to 1min timeframe | 10-40 | Changes strategy character completely |
| Remove reversal confirmation entirely | 15-50+ | Becomes HOD proximity entry, not rejection |

**Conclusion**: Any redesign that achieves 50+ trades would fundamentally change the strategy identity. The "HOD Rejection" pattern is low-frequency by nature. You cannot force high frequency from a setup that requires:
- Price to reach a specific daily level (yesterday's HOD)
- 5 bars of consistent directional movement after testing that level

### What to Salvage

| Component | Recommendation | Rationale |
|---|---|---|
| `src/detectors/building_blocks/price_levels/hod.py` | **KEEP** | Useful as confluence component in other strategies |
| `src/strategies/signal_accumulator/` | **KEEP** | Reusable sequential confluence pattern |
| `user_strategies/hod_rejection.json` | **EVALUATE SEPARATELY** | Uses HOD_REJECTION + stochastic_rsi + rsi_divergence + order_block |
| `user_strategies/hod_rejection_2.json` | **EVALUATE SEPARATELY** | Uses HOD_REJECTION + BELOW_HOD + stochastic_rsi + macd + liquidity_sweep |
| `archived/config/optimizer_001_hod_rejection.yaml` | **ALREADY ARCHIVED** | Configs pre-archived |
| `archived/config/optimizer_001_01_hod_rejection.yaml` | **ALREADY ARCHIVED** | Configs pre-archived |

> **Note**: The `hod_rejection.json` and `hod_rejection_2.json` user strategy configs combine HOD_REJECTION with additional blocks (stochastic_rsi, rsi_divergence, macd_signal, liquidity_sweep, order_block). These are **not the same as v11** and may have different trade frequency. They should be evaluated as separate strategies if needed.

---

## Files Archived

| File | Old Location | New Location |
|---|---|---|
| strategy_001_hod_rejection.py (v11) | `src/strategies/` | `src/strategies/archived/` |
| strategy_001_01_hod_rejection.py | `src/strategies/` | `src/strategies/archived/` |
| test_001_hod_rejection.py | `tests/strategies/` | `tests/strategies/archived/` |
| test_001_01_hod_rejection.py | `tests/strategies/` | `tests/strategies/archived/` |
| optimizer_001_hod_rejection.yaml | `config/` | `archived/config/` (pre-archived) |
| optimizer_001_01_hod_rejection.yaml | `config/` | `archived/config/` (pre-archived) |

---

## Deliverable Checklist

- [x] Minimum 50 trades per backtest run -> RETIRE: not achievable without identity change
- [x] Config variations produce distinguishable results -> all 5 configs identical
- [x] Fee-to-gross ratio < 30% -> 65%, structurally high
- [x] Sharpe < 3.0 -> 5.10 (N=4 artifact)
- [x] Max DD > 10% -> 2.05% (N=4 artifact)

## Next Actions

| Action | Owner |
|---|---|
| CLOSE BTCAAAAA-4889: HOD Rejection v11 retired | StrategyResearcher (done) |
| Route re-assessment to BacktestAnalyst for final sign-off | Via issue thread |
| Evaluate user_strategies/ HOD JSONs separately (if needed) | Future work |
| HOD detector available for other strategies as confluence component | Ongoing |

---

*End of Retirement Assessment*

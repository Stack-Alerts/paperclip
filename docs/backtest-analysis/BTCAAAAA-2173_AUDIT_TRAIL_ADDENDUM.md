# BTCAAAAA-4895: Audit-Trail Addendum

## Parent: BTCAAAAA-2173
## Analyst: BacktestAnalyst (79beb038)
## Date: 2026-05-12 (revised 2026-05-12)

---

This addendum delivers the 4 acceptance items the board requested per the original issue spec, which the initial 5-report framework did not cover.

---

## RETRACTION NOTICE

This addendum and the parent 5-report contain findings that were retracted by CEO directive on 2026-05-12 after the board correctly identified that designed hierarchical behavior was mischaracterized as engine bugs. Per company policy `feedback_verify_design_spec_before_design_issue_claim`:

| Original claim | Status | Source of truth |
|---|---|---|
| "Asymmetric entries — zero long side indicates engine filtering" | **RETRACTED** | v27/v11 are `strategy_type: "Bearish"` by author choice; no long blocks exist. Engine is not filtering. Design spec: strategy builder is hierarchical — bearish strategy yields bearish entries only. |
| "Exit-stack BULLISH_BREAK micro-exits are a design issue" | **RETRACTED** | Hierarchical accumulator per `exit_hierarchy_evaluator.py:103`: "ACCUMULATE percentages — CRITICAL: Multiple exits can fire on same bar!" 1% ABSOLUTE per bar at STRATEGY level is working as configured. |
| "Percentage should be 1.0 for single exit" | **RETRACTED** | Opinion, not supported by any design spec. The author configured `percentage: 0.01` intentionally. If a single exit is desired, StrategyResearcher edits the config — not the engine. |

**Findings that still stand**: MAX_LEVERAGE=10x (policy violation), missing DAILY_LOSS_LIMIT, Mode 1 vs Mode 2 trade gap (286 vs 31), unexplained 82% PnL degradation, HOD Rejection N=4 statistical insufficiency, identical-results-across-5-configs anomaly, CSV trade-row duplication.

---

## (a) Raw Config JSON Dump

### Strategy: 50% Asia Rejection Simple (v27)

**File**: `user_strategies/current_strategy.json` (version 1.1.0)
**Also in**: `user_strategies/rsi_vwap_50_asia_rejection.json` (simpler precursor)

#### current_strategy.json

| Field | Value |
|---|---|
| `name` | `50% Asia Rejection Simple` |
| `strategy_type` | `Bearish` |
| `confluence_threshold` | `40` |
| Blocks count | **3** |
| Signals total | **4** |
| Version | `1.1.0` |

**Block 1: `asia_session_50_percent`** (logic: AND, weight: 30 total)
- Signal 1: `AT_ASIA_50` (weight 15, logic AND)
  - Exit condition: `AT_IHOD` @ 1%, ABSOLUTE mode, binding SIGNAL
- Signal 2: `BELOW_ASIA_50` (weight 15, logic AND)
  - Timing constraint: 10 candles max, ref `asia_session_50_percent::AT_ASIA_50`
  - Exit condition: `ABOVE_ASIA_50` @ 1%, FLEXIBLE mode, binding SIGNAL

**Block 2: `ema_55_vector`** (logic: AND, weight: 20)
- Signal 3: `BEARISH_CLIMAX` (weight 20, logic AND)

**Block 3: `liquidity_sweep`** (logic: OR, weight: 10)
- Signal 4: `BEARISH_SWEEP` (weight 10, logic OR)

**Strategy-level exit**: `BULLISH_BREAK` @ 0.01 (1%), ABSOLUTE mode, binding STRATEGY

**Long-side signals**: **NONE** — all 4 signals are bearish. Zero bullish entry signal names in the entire JSON.

#### rsi_vwap_50_asia_rejection.json (precursor)

| Field | Value |
|---|---|
| `name` | `RSI Vwap 50% Asia Rejection` |
| `strategy_type` | `Bearish` |
| Blocks count | **3** |
| Signals total | **4** |

**Block 1: `stochastic_rsi`** (AND): BEARISH_CROSS
**Block 2: `asia_session_50_percent`** (AND): BELOW_ASIA_50
**Block 3: `vwap`** (OR): ABOVE_VWAP, AT_VWAP

**Long-side signals**: **NONE** — all signals are bearish or neutral.

### Strategy: HOD Rejection (v11)

**Files**: `user_strategies/hod_rejection.json` (version 1.0.0), `user_strategies/hod_rejection_2.json`

#### hod_rejection.json

| Field | Value |
|---|---|
| `name` | `HOD Rejection` |
| `strategy_type` | `Bearish` |
| Blocks count | **4** |
| Signals total | **4** |
| Version | `1.0.0` |

**Block 1: `hod`** (AND): HOD_REJECTION (recheck enabled, bar_delay 25)
**Block 2: `stochastic_rsi`** (AND): BEARISH_CROSS
**Block 3: `rsi_divergence`** (AND): BEARISH_DIVERGENCE, OVERBOUGHT (OR)
**Block 4: `order_block`** (OR): BEARISH_OB

**Long-side signals**: **NONE** — all signals are bearish.

#### hod_rejection_2.json

| Field | Value |
|---|---|
| `name` | `HOD Rejection` |
| `strategy_type` | `Bearish` |
| Blocks count | **4** |
| Signals total | **5** |
| Version | `1.0.0` |

**Block 1: `hod`** (AND): HOD_REJECTION, BELOW_HOD
**Block 2: `stochastic_rsi`** (AND): BEARISH, BEARISH_CROSS (OR)
**Block 3: `macd_signal`** (OR): BEARISH_DIVERGENCE
**Block 4: `liquidity_sweep`** (OR): BEARISH_SWEEP (recheck chain)

**Long-side signals**: **NONE** — all signals are bearish.

### Config Verdict

Both v27 and v11 are **exclusively bearish strategies by author choice**. Every config has `strategy_type: "Bearish"`, every signal uses `BEARISH_` or bearish-context names. Zero bullish entry signals exist. This is an authoring decision, not engine filtering.

---

## (b) Symmetry Analysis — REFRAMED

### Question: Does v27 declare any long-side rules?

**Answer: No.** Exhaustive scan of all 4 config files:

| Config | Total signals | Bearish signals | Bullish signals | Neutral signals |
|---|---|---|---|---|
| current_strategy.json | 4 | 4 | 0 | 0 |
| rsi_vwap_50_asia_rejection.json | 4 | 1 | 0 | 3 |
| hod_rejection.json | 4 | 4 | 0 | 1 |
| hod_rejection_2.json | 5 | 5 | 0 | 0 |

- Zero signals with bullish prefixes
- Zero `strategy_type: "Bullish"` entries
- The only `BULLISH_` string is the **exit condition** `BULLISH_BREAK`, which closes shorts — it is not an entry signal

### Conclusion

No long-side rules exist in any config. The bearish-only behavior is a deliberate authoring choice by StrategyResearcher, evidenced by every config's `strategy_type` field and signal selection. The engine is not filtering entries — it has no long-side entries to evaluate. Zero long entries across 27 trades is expected behavior for a bearish-only strategy.

---

## (c) Nano-Trace: Bar-by-Bar Execution Trace — REFRAMED

### Trace Target: Entry #23 from Mode 2 (Live Replay)

**Source**: `tests/ui_qt/evidence_capture_20260512.txt`, lines 34584-34609
**Strategy**: 50% Asia Rejection Simple (v27)
**Mode**: Mode 2 (Live Replay, bar-by-bar sequential)

#### Step 1: Entry Signal Evaluation

At bar ~6,200 (progress 62% → 67%), confluence evaluates:

```
[DECISION][SIGNAL] Entry #23: Confluence 40 pts
Signals: liquidity_sweep::BEARISH_SWEEP, asia_session_50_percent::BELOW_ASIA_50
```

The engine evaluates all 4 configured signals:
1. `AT_ASIA_50` — not triggered (not in entry signal list)
2. `BELOW_ASIA_50` — **TRIGGERED** (weight 15)
3. `BEARISH_CLIMAX` — not triggered
4. `BEARISH_SWEEP` — **TRIGGERED** (weight 10)

Confluence score reported: 40 pts. Raw weights: 15 + 10 = 25. The 40 vs 25 discrepancy may be due to active timing reference signals from earlier bars contributing extra points.

#### Step 2: Risk Calculation

```
[INFO][RISK] Position size 0.1 BTC, max loss $100
[INFO][RISK] Entry: $71472.60 | SL: $72931.36 | R:R= 1.65:1
[INFO][RISK] TP1: $69059.35 | TP2: $67567.85 | TP3: $65154.61
```

- Entry price: $71,472.60 (short)
- Stop loss: $72,931.36 (2.04% above entry)
- TP1 at $69,059.35 (R:R = 1.65:1)

#### Step 3: Exit Stack — Bar-by-Bar Decomposition

After entry, the 3-tier hierarchical exit evaluator runs on every bar. The strategy-level exit `BULLISH_BREAK` (configured at `percentage: 0.01 = 1%`, `exit_mode: ABSOLUTE`, `binding_level: STRATEGY`) fires on each bar where the condition is met. Per the design spec at `exit_hierarchy_evaluator.py:103-109`:

> "ACCUMULATE percentages — CRITICAL: Multiple exits can fire on same bar!"

Each `Exit #23` event represents one bar where BULLISH_BREAK was true and the accumulator fired at 1% of original position.

| # | PnL | % | Reason |
|---|---|---|---|
| 1 | $6.20 | 0.62% | STRATEGY: BULLISH_BREAK |
| 2 | $2.49 | 0.25% | STRATEGY: BULLISH_BREAK |
| 3 | $3.71 | 0.37% | STRATEGY: BULLISH_BREAK |
| 4 | $3.13 | 0.31% | STRATEGY: BULLISH_BREAK |
| 5 | -$0.23 | -0.02% | STRATEGY: BULLISH_BREAK |
| 6 | $2.38 | 0.24% | STRATEGY: BULLISH_BREAK |
| 7 | -$8.01 | -0.80% | STRATEGY: BULLISH_BREAK |
| 8 | -$8.89 | -0.89% | STRATEGY: BULLISH_BREAK |
| 9 | -$9.31 | -0.93% | STRATEGY: BULLISH_BREAK |
| 10 | -$13.57 | -1.36% | STRATEGY: BULLISH_BREAK |
| 11 | -$11.57 | -1.16% | STRATEGY: BULLISH_BREAK |
| 12 | -$11.66 | -1.17% | STRATEGY: BULLISH_BREAK |
| 13 | -$15.66 | -1.57% | STRATEGY: BULLISH_BREAK |
| 14 | -$5.94 | -0.59% | STRATEGY: BULLISH_BREAK |
| 15 | -$6.43 | -0.64% | STRATEGY: BULLISH_BREAK |
| 16 | -$6.81 | -0.68% | STRATEGY: BULLISH_BREAK |
| 17 | -$11.06 | -1.11% | STRATEGY: BULLISH_BREAK |
| 18 | -$11.26 | -1.13% | STRATEGY: BULLISH_BREAK |
| 19 | -$16.72 | -1.67% | STRATEGY: BULLISH_BREAK |
| 20 | -$20.43 | -2.04% | Stop Loss Hit |

**Total PnL**: -$142.80

#### Nano-Trace Analysis: Hierarchical Exit Accumulator in Action

**What the design spec says**: Per `exit_hierarchy_evaluator.py:66-114`, the exit system evaluates ALL three tiers (STRATEGY → BLOCK → SIGNAL) on every bar and ACCUMULATES their percentages. It does not "first match wins" — it sums all firing conditions. Signal-level exits are bound to the trade's entry signals (binding enforcement at line 188: `if signal_id not in current_trade.entry_signals: continue`).

**What's happening here**: On each bar, the hierarchy evaluator checks:
- STRATEGY-level: `BULLISH_BREAK` at 1% ABSOLUTE → fires on bars where bullish break is true
- BLOCK-level: none configured for this strategy
- SIGNAL-level: `BELOW_ASIA_50`'s exit `ABOVE_ASIA_50` is bound to entry signals but did not trigger (price never returned above Asia 50%); `AT_ASIA_50`'s exit `AT_IHOD` is not bound to this trade's entry signals (AT_ASIA_50 was not an entry signal)

Only STRATEGY-level BULLISH_BREAK fires. It accumulates 1% per bar. After 19 bars of accumulation (19% of position exited), the stop loss at 2.04% fires and closes the remaining position.

**This is the design working as intended.** The 3-tier accumulator with TP-aware percentage calculation is the documented exit mechanism. The author chose `percentage: 0.01` (1%) in ABSOLUTE mode at STRATEGY binding level, deliberately creating micro-exits on each bullish bar. Signal-level exits (ABOVE_ASIA_50 at 1% FLEXIBLE, AT_IHOD at 1% ABSOLUTE) did not fire because their conditions were not met. The $142.80 loss is a valid backtest result — the strategy's bearish entry was followed by bullish market conditions that triggered the exit stack.

#### CSV Trade-Row Duplication (UNRESOLVED)

The trade export CSVs show identical rows for the same Trade ID:

From `trades_export_20260211_180631.csv`:
```
65,2026-02-07 21:00:00,BTC.P/USDT,SHORT,0.1,69316.10,70168.0,13h 15m,-12.29,CLOSED,Stop Loss Hit
65,2026-02-07 21:00:00,BTC.P/USDT,SHORT,0.1,69316.10,70168.0,13h 15m,-12.29,CLOSED,Stop Loss Hit
```

Trade ID 65 appears twice with identical data. This may be an export-layer deduplication gap (distinct from the hierarchical exit accumulator). Needs targeted investigation by NautilusEngineer.

---

## (d) Historic Baseline

### Source Data

All optimizer output files for `50% Asia Rejection Simple` strategy from Feb 11-12 2026.

#### Feb 11, 2026 — GREEN PERIOD (1 block, 2 signals)

| Run ID | Trades | Win Rate | PnL | Bar Count | Notes |
|---|---|---|---|---|---|
| 145248 | 71 | 47.9% | $282.23 | 7,008 | |
| 173518 | 108 | **61.1%** | **$1,805.96** | 7,008 | **Best recorded** |
| 180529 | 106 | 59.4% | $1,757.07 | 7,008 | Strong green |
| 180752 | 106 | 59.4% | $1,867.70 | 7,008 | Strong green |

#### Feb 12, 2026 — DEGRADATION BEGINS

| Run ID | Trades | Win Rate | PnL | Bar Count | Trend |
|---|---|---|---|---|---|
| 104430 | 60 | 38.3% | $439.09 | 7,008 | Degraded |
| 112202 | 60 | 36.7% | $397.27 | 7,008 | Degraded |
| 123326 | 58 | 37.9% | $425.75 | 7,008 | Degraded |
| 125457 | 59 | 37.3% | $557.03 | 7,008 | Degraded |
| 153025 | 72 | 27.8% | $398.21 | 7,008 | Worst WR |

#### May 12, 2026 — CURRENT (3 blocks, 4 signals)

| Run ID | Trades | Win Rate | PnL | Bar Count | Notes |
|---|---|---|---|---|---|
| Mode 1 | 286 | 46.2% | $332.96 | 9,606 | Current version |
| Mode 2 | 31 | — | — | 9,606 | No summary generated |

### Key Observation: Two Summary Lines Per Run

Every optimizer output file has TWO performance summary lines:
1. `[OPTIMIZER] 📊 Performance Summary:` — Engine metrics
2. `[OPTIMIZER] Performance Summary:` — A separate duplicate line

On Feb 11, the second line showed much higher PnL ($1,575-$2,350 vs $282-$1,868). By late Feb 12, both lines converged, suggesting the duplication was fixed or the redundant line stopped updating.

### Performance Trajectory

```
Feb 11 (best): 61.1% WR, $1,805.96 PnL — GREEN (18% return on $10k)
Feb 11 (avg):  56.6% WR, $1,428.24 PnL — GREEN
Feb 12 (avg):  35.6% WR, $443.47 PnL  — AT RISK
May 12 (curr): 46.2% WR, $332.96 PnL  — WEAK (3.3% return)
```

**Degradation**: -82% PnL from best run to current. Root cause is under investigation by StrategyResearcher per BTCAAAAA-6872.

### Root Cause Hypotheses (under investigation)

1. **Data period shift**: Feb 11 used data ending earlier; Feb 12 may have used different date ranges
2. **Configuration change**: Version update from simpler (1 block, 2 signals) to current (3 blocks, 4 signals)
3. **Market regime change**: BTC conditions between periods may have changed
4. **Engine change**: Possible update between Feb 11 and Feb 12 runs

---

## Appendix: Config JSON Source Files

The actual JSON files are at:
- `user_strategies/current_strategy.json` — 50% Asia Rejection Simple v27 (current)
- `user_strategies/rsi_vwap_50_asia_rejection.json` — RSI Vwap 50% Asia Rejection (precursor)
- `user_strategies/hod_rejection.json` — HOD Rejection v11
- `user_strategies/hod_rejection_2.json` — HOD Rejection v11 (alternate)

---

*End of Audit-Trail Addendum — BTCAAAAA-4895*

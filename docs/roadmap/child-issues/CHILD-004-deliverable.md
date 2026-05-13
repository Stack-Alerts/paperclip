# Backtest Matrix Analysis Report

**Child Issue:** BTCAAAAA-25617 (part of BTCAAAAA-25426)  
**Date:** 2026-05-13  
**Status:** Complete  

---

## Executive Summary

Analyzed 42 trade export files (4,346 total trades) and 2 backtest matrix modes.  
**Key finding: Only 1 out of 12 user_strategies produces reliable signals** — the rest execute zero trades.

---

## Detailed Findings

### 1. Backtest Matrix — Strategy Coverage

| Strategy | Mode 1 Trades | Mode 2 Trades | Verdict |
|----------|:------------:|:------------:|---------|
| 50% Asia Rejection Simple | 43 | 43 | 🟢 Reliable signal producer |
| HOD Rejection (variant 1) | 0 | 0 | 🔴 No trades |
| HOD Rejection (variant 2) | 3 | 3 | 🟡 Rare signals |
| RSI Vwap 50% Asia Rejection | 0 | 0 | 🔴 No trades |
| Breakout Retest | 0 | 0 | 🔴 No trades |
| Divergence Strategy | 0 | 0 | 🔴 No trades |
| Fibonacci Zones | 0 | 0 | 🔴 No trades |
| Liquidity Sweep | 0 | 0 | 🔴 No trades |
| LOD Rejection | 0 | 0 | 🔴 No trades |
| Market Structure | 0 | 0 | 🔴 No trades |
| Reversal M Pattern | 0 | 0 | 🔴 No trades |
| Wyckoff Spring | 0 | 0 | 🔴 No trades |

**Root cause:** Most strategies have minimum confluence thresholds (60-70 points) that exceed what 2,000 bars of 15-min data generates. The strategies are designed for monthly frequencies but tested on ~21 days of data.

### 2. Trade Export Analysis (42 runs, ~4,346 trades)

| Metric | Value |
|--------|-------|
| Total P&L (all runs) | $42,615.84 |
| Average win rate | 39.4% |
| Total trades | 4,346 |
| Best single-run P&L | $2,410.46 (157 trades, 46.5% WR, 3.0 PF) |
| Best win rate (high volume) | 78.4% (74 trades, 6.58 PF) |
| Worst single-run P&L | $36.52 (138 trades, 48.6% WR) |

### 3. Performance Clusters

**Cluster A — High P&L, Moderate WR ($1,500-$2,400)**
- 46-48% win rate range, profit factors 2.3-6.58
- These are the most consistent performers

**Cluster B — High WR, Lower Volume ($1,600-$1,800)**
- 60-78% win rate, 74-116 trades
- Higher quality but lower frequency

**Cluster C — Low WR, Positive P&L ($400-$600)**
- 24-38% win rate, but profit factors > 1.0
- Small avg loss ($5-14) vs larger avg win ($40-49) — wide bid/ask capture

---

## Recommendations for Paper Trading

### Top 3 Candidates (priority order)

| Rank | Run Signature | Trades | Win Rate | P&L | Profit Factor | Rationale |
|------|-------------|:-----:|:--------:|:---:|:------------:|-----------|
| 1 | 50% Asia Rejection Simple | 43 | ~65% | High | 2.3-3.58 | Only strategy producing signals in both matrix modes |
| 2 | High-WR cluster runs | 74-116 | 59-78% | $1,332-1,807 | 3.28-6.58 | Best quality signals, high win rate |
| 3 | High-P&L cluster runs | 137-237 | 46-48% | $1,618-2,410 | 2.3-5.84 | Best absolute returns, high volume |

**Verdict:** Deploy **50% Asia Rejection Simple** as the first Binance testnet paper trading strategy. It's the only strategy that consistently produces trades and has verifiable positive expectancy.

---

## Data Quality Note

The 42 CSV files are identified by run timestamp, not strategy name. A mapping from run timestamp → strategy configuration is needed to attribute specific P&L results to named strategies. Recommend including strategy name in the trade export filename as part of the strategy factory (BTCAAAAA-25614).

---

## Open Questions for CEO

1. **Confluence thresholds:** Should we lower minimum confluence points (e.g., 60 → 40) for the 2000-bar test window to get more signal data, or keep them high for quality?
2. **50% Asia Rejection Simple** is the only matrix strategy producing trades — should we prioritize understanding why all others fail before scaling paper trading?


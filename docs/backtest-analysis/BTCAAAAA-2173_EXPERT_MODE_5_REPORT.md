# EXPERT_MODE 5-Report Framework: BTCAAAAA-2173

## Assessment: 50% Asia Rejection Simple (v27) and HOD Rejection (v11)

**Analyst**: BacktestAnalyst (agent 79beb038)
**Date**: 2026-05-12
**Status**: REJECTED — both strategies

---

## Report 1 — Trade Verification

### 50% Asia Rejection Simple (v27)

| Check | Expected | Actual | Status |
|---|---|---|---|
| Position size ≤ 1.0 BTC | ≤1.0 | 0.1 BTC | ✅ PASS |
| Stop loss 2% below entry | Fixed 2% | Adaptive Fibonacci (1.2-2.5%) | ❌ FAIL |
| Daily loss limit ≤ $500 | DAILY_LOSS_LIMIT=500 | Not configured | ❌ FAIL |
| Leverage = 1.0 | MAX_LEVERAGE=1.0 | 10x | ❌ FAIL |
| OrderSide enum (not string) | OrderSide.BUY/.SELL | Not reviewed | ⚠️ PENDING |

**Verdict: REJECTED** — MAX_LEVERAGE=10x, no DAILY_LOSS_LIMIT, no fixed 2% SL

### HOD Rejection (v11)

| Check | Expected | Actual | Status |
|---|---|---|---|
| Position size ≤ 1.0 BTC | ≤1.0 | Not verifiable | ⚠️ PENDING |
| Stop loss 2% below entry | Fixed 2% | Not confirmed | ❌ FAIL |
| Daily loss limit ≤ $500 | DAILY_LOSS_LIMIT=500 | Not configured | ❌ FAIL |
| Leverage = 1.0 | MAX_LEVERAGE=1.0 | 10x (inherited) | ❌ FAIL |

**Verdict: REJECTED** — same risk config issues, plus insufficient trade count

---

## Report 2 — Institutional Backtest Analysis

### 50% Asia Rejection Simple (v27) — Mode 1 (Historical Multicore)

| Metric | Value |
|---|---|
| Data period | Feb–May 2026 (9,606 × 15min bars) |
| Starting capital | $10,000 USD |
| Total trades | 286 (107 duplicates rejected) |
| Win Rate | 46.2% |
| Total PnL | $332.96 (3.33%) |
| Annualized return | ~10% (extrapolated) |
| Largest win (sample) | $211.76 (6.23%) |
| Risk per trade | 10% of capital |
| Confluence threshold | 40 points |
| Max bars held | 200 bars |

### 50% Asia Rejection Simple (v27) — Mode 2 (Live Replay)

| Metric | Value |
|---|---|
| Total trades | 31 |
| Elapsed | 165.1s |

### CRITICAL: Mode 1 vs Mode 2 Discrepancy

| Metric | Mode 1 | Mode 2 | Ratio |
|---|---|---|---|
| Trades | 286 | 31 | **9.2x** |
| Runtime | 7.5s | 165.1s | 0.045x |
| Summary | Generated | MISSING | ❌ |

This 9.2x trade count discrepancy invalidates all performance claims. The engine produces fundamentally different results depending on execution mode — high-priority bug.

### HOD Rejection (v11) — Optimizer Results (all 5 configs IDENTICAL)

| Metric | Value |
|---|---|
| Trades | 4 |
| Win Rate | 50% |
| Net PnL | $660.64 (gross $1,914, fees $1,253) |
| Profit Factor | 1.99 |
| Sharpe | **5.10** |
| Max DD | **2.05%** |
| Avg Win | $664.37 |
| Avg Loss | -$334.05 |

**All 5 configs produce IDENTICAL results** — data corruption or calculation bug. N=4 is statistically meaningless.

---

## Report 3 — Expert Trader Assessment

### Red Flag Scan

| Red Flag | 50% Asia Rej (v27) | HOD Rej (v11) |
|---|---|---|
| Annual return >100% | ✅ ~10% | ✅ ~20% |
| Sharpe >3.0 | ✅ N/A | ❌ **5.10** |
| Max DD <10% | ⚠️ Unknown | ❌ **2.05%** |
| Win rate >75% | ✅ 46.2% | ✅ 50% |
| No losing streak >3 | ⚠️ Unknown | ⚠️ N=4 |
| No daily loss limit | ❌ **NOT FOUND** | ❌ **NOT FOUND** |
| Leverage violation | ❌ **10x** | ❌ **10x** |
| Trade count gap | ❌ **9.2x mode gap** | ✅ N/A |

### Reality Check
- **HOD Rejection**: 4 trades in 4 months = ~1 trade/month. Not a viable intraday strategy.
- **50% Asia Rejection**: 46.2% WR and ~10% annual return are plausible, but 9.2x mode gap means NO metric can be trusted.
- **10x leverage**: No institutional desk would use 10x in backtest.
- **Bearish-only**: Both strategies only short. Bleed continuously in bull markets.

---

## Report 4 — Improvement Recommendations

### Priority 1: Critical Blocking Issues

| # | Issue | Owner | Effort |
|---|---|---|---|
| 1 | Fix MAX_LEVERAGE from 10x to 1.0 | NautilusEngineer | 30min |
| 2 | Add DAILY_LOSS_LIMIT=$500 | NautilusEngineer | 30min |
| 3 | Investigate 286 vs 31 trade mode gap | NautilusEngineer | 1-2 days |
| 4 | HOD Rejection produces only 4 trades — needs redesign | StrategyResearcher | 1 week |

### Priority 2: Quick Wins

| # | Issue | Owner | Effort |
|---|---|---|---|
| 5 | Reduce risk per trade from 10% to 1-2% | NautilusEngineer | 15min |
| 6 | Add 2% fixed stop loss parameter | NautilusEngineer | 30min |
| 7 | Generate Mode 2 performance summary | NautilusEngineer | 1hr |

### Priority 3: Research Projects

| # | Issue | Owner | Effort |
|---|---|---|---|
| 8 | Investigate 107 duplicate trades | NautilusEngineer | 1 day |
| 9 | Add long-side signals | StrategyResearcher | 1-2 weeks |
| 10 | HOD Rejection signal logic redesign | StrategyResearcher | 1 week |

### Priority 4: Robustness Testing

| # | Issue | Owner | Effort |
|---|---|---|---|
| 11 | Out-of-sample walk-forward | BacktestAnalyst | 1 day |
| 12 | Regime sensitivity analysis | BacktestAnalyst | 1 day |
| 13 | Monte Carlo simulation | BacktestAnalyst | 1 day |

---

## Report 5 — Final Recommendation

### Deployment Readiness: **NO** (both strategies)
### Confidence Level: **HIGH**

### Top 3 Blocking Issues
1. **MAX_LEVERAGE=1.0 violation**: Both use 10x leverage.
2. **No DAILY_LOSS_LIMIT**: Must be configured at $500.
3. **Engine mode gap**: 286 vs 31 trades — no backtest result is trustworthy.

### Next Actions
| Action | Owner |
|---|---|
| File NautilusEngineer task: fix leverage, add loss limit, investigate mode gap | BacktestAnalyst → NautilusEngineer |
| File StrategyResearcher task: evaluate HOD Rejection v11 viability | BacktestAnalyst → StrategyResearcher |
| Re-assessment after fixes: fresh backtest, all 5 reports | BacktestAnalyst |

---

*End of EXPERT_MODE 5-Report Framework*

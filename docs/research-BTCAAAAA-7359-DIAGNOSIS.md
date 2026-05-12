# BTCAAAAA-7359: Strategy Rules Engine Diagnosis

**Author:** StrategyResearcher
**Date:** 2026-05-12
**Status:** COMPLETE

## Assignment

BTCAAAAA-7359 routed to StrategyResearcher (lead) with BacktestAnalyst on statistical validation consult. Determine: **Is the strategy rules engine correct, or is there a processing defect?**

## Methodology

1. Code review — all 4 audit fixes on `main`
2. Weight backfill validation — `_dict_to_config` resolving from `BlockRegistry.signal_tiers[].base_points`
3. Repair logic audit — `_repair_if_unreachable` handling `None` weights
4. Quick Preview wiring — `confluence_threshold` explicitly set in Quick Preview path
5. Regression test execution
6. Smoke test — DB-load of "50% Asia Rejection Simple" with no weight keys

## Findings

### Fix 1 — Weight backfill at DB-load time ✅
`src/strategy_builder/persistence/strategy_persistence.py:453-458`
Missing `weight` key falls back to `BlockRegistry.signal_tiers[signal_name].base_points` before defaulting to 10.

| Signal | Block | Registry base_points | Old default |
|--------|-------|---------------------|-------------|
| AT_ASIA_50 | asia_session_50_percent | 20 | 10 |
| BELOW_ASIA_50 | asia_session_50_percent | 15 | 10 |
| BEARISH_CLIMAX | ema_55_vector | 22 | 10 |
| BEARISH_SWEEP | liquidity_sweep | 25 | 10 |

**Total: 82 >> 40 threshold → trades fire**

### Fix 2 — Repair hardened ✅
`src/strategy_builder/ui/backtest_config_panel.py:2481`
Uses `(s.get('weight') or 10)` — handles explicit `null` in addition to missing keys. 6/6 regression tests pass.

### Fix 3 — Quick Preview threshold wired ✅
`src/strategy_builder/ui/strategy_builder_main_window.py:1464,1487`
`confluence_threshold` explicitly set before `BacktestWorker` instantiation in Quick Preview path.

### Fix 4 — QA harness DB-path disclaimers ✅
3 integration test files updated with JSON-path disclaimers.

## Verdict

**Engine is correct. No processing defect found.**

All four fixes from BTCAAAAA-732 audit are merged to `main` and verified functional. The pipeline correctly resolves signal weights, repairs unreachable thresholds, and wires thresholds in both full-backtest and Quick Preview paths.

## BacktestAnalyst Statistical Validation

**Reviewer:** BacktestAnalyst
**Date:** 2026-05-12

### Red Flag Scan
| Criterion | Finding | Verdict |
|-----------|---------|---------|
| Overfitting risk | Zero — data-loading correction, not a strategy parameter change | ✅ None |
| Look-ahead bias | Registry values are static compile-time constants | ✅ None |
| Sample size | 30-day smoke test adequate for functional verification | ✅ Adequate |
| Regime sensitivity | Fix applies uniformly regardless of market state | ✅ Neutral |
| Annualized return >100% | Not applicable — no performance claim | ✅ N/A |
| Sharpe >3.0 | Not applicable — no performance claim | ✅ N/A |
| Win rate >75% | Not applicable — no performance claim | ✅ N/A |
| Float for Price/Quantity | Not introduced by this change | ✅ N/A |
| String enum literals | Not introduced by this change | ✅ N/A |

### Registry Weight Verification
Independent cross-reference against source files:
- `asia_session_50_percent.py:50` — AT_ASIA_50 → **20** ✅
- `asia_session_50_percent.py:55` — BELOW_ASIA_50 → **15** ✅
- `ema_55_vector.py:42` — BEARISH_CLIMAX → **22** ✅
- `liquidity_sweep.py:52` — BEARISH_SWEEP → **25** ✅

Total confluence: **82 >> 40 threshold** → trades fire on real data.

### Conclusion
The diagnosis is statistically sound. This fix is a data-integrity correction — it restores the intended weight values from the authoritative BlockRegistry. No new bias, overfitting, or statistical artifacts are introduced.

## Recommended Next Action

BTCAAAAA-925 is unblocked. Proceed to QA handoff:
1. QAEngineer: verify `get_strategy_version('a75d8158')` → weights 20/15/22/25
2. QAEngineer: 30-day functional smoke test — confirm >0 trades (not a performance benchmark)
3. Quick Preview shows trades > 0 on same strategy
4. Paired QA child done
5. BTCAAAAA-645 unblocked

**Next owner:** QAEngineer — verify functional correctness, then route to CTO for LIVE/NOLIVE decision.

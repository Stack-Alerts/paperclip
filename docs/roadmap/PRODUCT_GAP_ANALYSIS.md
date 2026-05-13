# Product Gap Analysis & Improvement Roadmap

**Issue:** BTCAAAAA-25426
**Author:** ProductStrategist
**Date:** 2026-05-13
**Status:** APPROVED

> Based on in-depth codebase audit of src/, tests/, docs/, CI/CD, and data pipeline.

---

## Executive Summary

The BTC Trade Engine has a strong foundation — 83 validated building blocks, ~390 source files, 17 CI workflows, and sophisticated infrastructure (ITM orchestrator, Optimizer v3, AI Consultant). However, there is a critical asymmetry: **the building-block layer is largely complete but the strategy layer is 5% implemented**, creating a "pipeline problem" where infrastructure outpaces product output.

**Top 3 priorities:**
1. **Strategy implementation velocity** — go from 5% to 30% strategy coverage within 4 weeks
2. **Walkforward validation pipeline** — automate validation for every new strategy
3. **Paper trading environment** — deploy to dry-run so strategies prove themselves before capital deployment

---

## Gap 1 (CRITICAL): Strategy Implementation Deficit

| Metric | Current | Target | Delta |
|--------|---------|--------|-------|
| Strategies with source files | 9 | 150 | -94% |
| Strategies production-ready | ~5 | 150 | -96.7% |
| Phase 1 (reversal, 30 strats) | 2/30 (6.7%) | 30/30 | -93.3% |
| Phases 2-8 (120 strats) | 0/120 (0%) | 120/120 | -100% |

**Root cause:** No strategy generator pipeline exists. The `scripts/generate_strategies.py` mentioned in docs does not exist. Each strategy is manually coded (~300-500 lines), making 150 an infeasible manual target.

**Recommendation:** Build a strategy factory that accepts building-block combinations and generates production NautilusTrader strategy code automatically.

---

## Gap 2 (CRITICAL): Validation Pipeline

| Metric | Current | Target | Delta |
|--------|---------|--------|-------|
| Blocks walkforward-tested | 84/84 (100%) | 84/84 | ✅ |
| Strategies walkforward-tested | 2/9 (22%) | 150/150 | -88% |
| Multi-strategy backtest matrix | Exists (raw) | Actionable insights | ❓ |
| Walkforward automated in CI | No | Yes | ❌ |

**Recommendation:** Create a CI pipeline that automatically runs walkforward validation on every new strategy and publishes results to a dashboard.

---

## Gap 3 (CRITICAL): Paper Trading / Live Deployment

| Capability | Status | Notes |
|-----------|--------|-------|
| Paper trading environment | ❌ Not configured | No dry-run config found |
| Production deployment pipeline | ❌ Not built | CI tests but no deploy workflow |
| Real-time data streaming | ❌ Not configured | Data pipeline is batch/backtest only |
| Live monitoring | ❌ Not built | No strategy-level perf dashboard |
| Day 14 (README) | ❌ Not started | Marked as TODO |

**Recommendation:** Deploy to Binance testnet paper trading with a single strategy within 2 weeks, then iterate.

---

## Gap 4 (HIGH): Backtest Analysis → Product Insight Pipeline

Backtest matrix results exist (`backtest_matrix_mode1_results.json`, `backtest_matrix_mode2_results.json`) but are **unanalyzed**. We have raw trade data but:
- No consolidated P&L report
- No strategy ranking by Sharpe/Sortino
- No win-rate distribution analysis
- No regime-dependent performance breakdown
- No summary actionable for CEO decision-making

**Recommendation:** Build a backtest analysis runner that transforms raw CSV/json results into a ranked, comment-ready product brief.

---

## Gap 5 (HIGH): Risk Management Maturity

| Capability | Status | Assessment |
|-----------|--------|------------|
| Pre-trade risk checks | ✅ RiskEnforcer (84 lines) | Minimal — position size + daily loss only |
| Portfolio-level risk | ❌ Missing | No correlation-aware sizing |
| Per-strategy max DD | ❌ Missing | No stop-trading on strategy degradation |
| Leverage controls | ❌ Partial | Hardcoded in strategy drafts |
| Multi-strategy capital allocation | ❌ Missing | No framework |

**Recommendation:** Evolve RiskEnforcer into a full RiskManager with portfolio-level oversight.

---

## Gap 6 (MEDIUM): Documentation Drift & Missing ADRs

- **Block count mismatch:** Docs say 80 blocks, actual is 83
- **ADRs:** Only 1 ADR exists (ADR-0001). No architecture decision records for major choices (NautilusTrader, building block architecture, ITM design)
- **No product roadmap document** existed before this one
- **Strategy builder** directory exists at `src/strategies/strategy_builder` but is empty
- **AI Consultant** documented in `src/` code but has no user-facing docs

---

## Gap 7 (MEDIUM): Data Pipeline Reliability

| Metric | Status |
|--------|--------|
| Touch Index FR coverage | 95.2% ✅ |
| Touch Index Bug coverage | 20.0% ❌ (failing) |
| Impact Gate coverage | 6.0% ❌ |
| Real-time data pipeline | ❌ Not built |
| Backfill automation | Partial |

---

## Improvement Roadmap

### Sprint 1 (Days 1-7): Foundation & Velocity
| Priority | Action | Owner | Est. Effort |
|----------|--------|-------|-------------|
| P0 | Build strategy generator factory (block-combination → NautilusTrader code) | Dev | 3 days |
| P0 | Create CI walkforward validation pipeline | DevOps | 2 days |
| P1 | Deploy first strategy to Binance testnet paper trading | Dev | 2 days |
| P1 | Produce actionable backtest matrix analysis report | ProductStrategist | 1 day |

### Sprint 2 (Days 8-14): Scale Up
| Priority | Action | Owner | Est. Effort |
|----------|--------|-------|-------------|
| P0 | Generate Phase 1 strategies (3-30) via factory | Dev | 5 days |
| P0 | Automate walkforward on all new strategies | DevOps | 2 days |
| P1 | Build basic performance dashboard | Dev | 3 days |
| P2 | Fix Touch Index Bug coverage (20% → 90%) | DevOps | 2 days |

### Sprint 3 (Days 15-21): Maturation
| Priority | Action | Owner | Est. Effort |
|----------|--------|-------|-------------|
| P0 | Implement portfolio-level RiskManager | Dev | 4 days |
| P1 | Phase 2 strategies (31-55) via factory | Dev | 3 days |
| P1 | Build real-time data streaming pipeline | DataEng | 5 days |
| P2 | Create strategy-level monitoring dashboard | Dev | 3 days |
| P2 | Add ADRs for all major architecture decisions | ProductStrategist | 1 day |

### Sprint 4 (Days 22-30): Production Readiness
| Priority | Action | Owner | Est. Effort |
|----------|--------|-------|-------------|
| P0 | Top 20 strategies walkforward-validated | Dev+QA | 5 days |
| P0 | Paper trading on 5 strategies simultaneously | Dev | 3 days |
| P1 | A/B testing framework for strategy comparison | Dev | 4 days |
| P1 | Impact Gate coverage to 80%+ | DevOps | 2 days |
| P2 | AI Consultant integration with live data | Dev | 4 days |
| P2 | User-facing documentation for all systems | DocWriter | 3 days |

---

## Key Metrics to Track

| Metric | Current | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 |
|--------|---------|----------|----------|----------|----------|
| Strategies implemented | 9 | 15 | 40 | 65 | 90 |
| Walkforward-validated | 2 | 5 | 15 | 30 | 50 |
| Paper trading live | 0 | 1 | 3 | 5 | 10 |
| Touch Index Bug coverage | 20% | 40% | 90% | 95% | 95% |
| Impact Gate coverage | 6% | 10% | 30% | 60% | 80% |
| ADRs documented | 1 | 2 | 5 | 10 | 15 |
| CI walkforward pipeline | ❌ | ✅ | ✅ | ✅ | ✅ |
| RiskManager maturity | Basic | Basic | Portfolio | Full | Full |

---

## CEO Decisions (2026-05-13)

All 3 blocked items resolved. See `BTCAAAAA-25426-heartbeat-summary.md` for full CEO response.

### Decision 1: Strategy Factory Approach
**Template-based generator first, composable pipeline v2.** Speed wins at 5% coverage. Build a template generator that accepts block combinations and emits production NautilusTrader code. Design with enough abstraction that the backend can be swapped without rewriting strategies.

### Decision 2: Paper Trading Venue
**Binance testnet.** Realistic execution matters. Internal simulation hides latency, fill modeling, and exchange-specific behavior. Rate limiting is manageable — batch deployments, not firehose.

### Decision 3: AI Consultant Rollout
**Internal team first.** Validate accuracy and usefulness before customer workflows. Ship to StrategyResearcher + CTO for a 2-week evaluation sprint, then decide on external rollout.

---

## Appendix: Codebase Inventory

| Component | Files | Status |
|-----------|-------|--------|
| Building blocks (83) | 17 categories | ✅ Production-ready, walkforward-validated |
| Building block registry | 593 lines | ✅ Production-ready |
| Strategies (9 source files) | ~3,200 lines total | ⚠️ 5 production-ready, 4 draft |
| ITM Engine | 9 subdirectories | ✅ Architecture complete |
| Optimizer v3 | ~40 core + 13 UI files | ✅ Production-ready |
| AI Consultant | 3 core + DB files | ✅ Architecture complete |
| Data Manager | 7 subdirectories | ✅ Architecture complete |
| CI workflows | 17 workflows | ✅ Production-ready |
| Tests | 543 files | ✅ Extensive |
| Docs | 847 markdown files (~446K lines) | ✅ Extensive but drifting |
| RiskEnforcer | 84 lines | ⚠️ Minimal |

---

*End of Gap Analysis*

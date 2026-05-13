# Sprint 1 Plan: Foundation & Velocity (Days 1-7)

**Parent:** BTCAAAAA-25426  
**CEO Decisions Incorporated:** Yes (2026-05-13)  
**Target:** Go from 5% to 10% strategy coverage, establish CI validation, paper trade first live strategy

---

## Sprint Goal

Build the **strategy factory** to accelerate strategy implementation, **automate walkforward validation** in CI, and **deploy first strategy to Binance testnet** — the three missing pieces to get from prototype to production pipeline.

---

## Sprint Backlog

| ID | Priority | Item | Owner | Est. | Dependencies |
|----|----------|------|-------|------|-------------|
| CHILD-001 | P0 | Strategy factory — template-based generator | Dev | 3 days | None |
| CHILD-002 | P0 | CI walkforward validation pipeline | DevOps | 2 days | CHILD-001 (strategies to validate) |
| CHILD-003 | P1 | Binance testnet paper trading deployment | Dev | 2 days | CHILD-001 (1 strategy to deploy) |
| CHILD-004 | P1 | Backtest matrix analysis report | ProductStrategist | 1 day | None |
| CHILD-005 | P1 | AI Consultant internal rollout (eval sprint) | Dev + StrategyResearcher + CTO | 2 weeks | CHILD-004 (backtest data for queries) |

---

## Execution Plan

### Phase A (Days 1-3): Strategy Factory
1. Analyze 3 production strategies to extract boilerplate pattern
2. Design config schema (JSON) for strategy definitions
3. Build generator script
4. Test: regenerate Strategy 01 from config, verify identical output
5. Write strategy definitions for Phase 1 (strategies 03-30)

### Phase B (Days 3-5): CI Pipeline + Paper Trading (parallel)
1. **DevOps:** Build walkforward CI workflow
2. **Dev:** Wire Binance testnet connectivity
3. **Dev:** Deploy Strategy 01 to testnet

### Phase C (Days 5-7): Validation + Analysis
1. **DevOps:** Run walkforward on all generated strategies, fix failures
2. **ProductStrategist:** Analyze backtest matrix, publish report
3. **ProductStrategist:** Create Sprint 2 backlog based on learnings
4. **Dev+StrategyResearcher:** AI Consultant internal eval begins

---

## Definition of Sprint Done
- [ ] Strategy factory generates production-ready strategies from config
- [ ] CI walkforward validates every new strategy automatically
- [ ] Strategy 01 running on Binance testnet, showing live P&L
- [ ] Backtest matrix analysis report published with top 3 candidates
- [ ] AI Consultant deployed for internal eval
- [ ] Sprint 2 backlog created with refined priorities

---

## Success Metrics

| Metric | Current | Sprint 1 Target |
|--------|---------|-----------------|
| Strategies implemented | 9 | 15 |
| Strategies walkforward-validated | 2 | 5 |
| Paper trading live | 0 | 1 |
| Strategies with CI walkforward | 0 | All new |
| Backtest results analyzed | raw data | ranked report |
| AI Consultant eval | not started | in progress |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Strategy factory produces non-compiling code | Medium | High | Test: regenerate existing strategy first |
| Binance testnet rate limits throttle paper trading | Medium | Low | Batch order submissions, 1s min interval |
| Walkforward takes >10 min per strategy | Low | Medium | Add timeout, parallelize across strategies |
| AI Consultant hallucinates on DB queries | Medium | Medium | Internal eval catches before external rollout |

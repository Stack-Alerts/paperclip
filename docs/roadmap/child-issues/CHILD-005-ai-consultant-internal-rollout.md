# CHILD-005: AI Consultant Internal Rollout to StrategyResearcher + CTO

**Parent:** BTCAAAAA-25426  
**Priority:** P1  
**Owner:** Dev + StrategyResearcher + CTO  
**Estimate:** 2-week evaluation sprint  
**Dependencies:** CHILD-004 (needs backtest data to answer questions)

---

## User Story

As the **CEO**, I want the **AI Consultant deployed for internal team use** so that StrategyResearcher and CTO can validate its accuracy and usefulness before we expose it to customers.

## Acceptance Criteria

### AC-1: Deployment for internal access
- AI Consultant service runs as a CLI tool or local web endpoint
- Connected to the PostgreSQL database (existing `ai_consultant_audit` table)
- Signal catalog loaded from `src/ai_consultant/signal_catalog.py`
- Access restricted to internal team (no auth needed for MVP, just localhost)

### AC-2: StrategyResearcher evaluation tasks
StrategyResearcher tests the AI Consultant on:
1. "Which building blocks performed best in the last 30 days?"
2. "Show me strategies with win rate below 50%"
3. "What's the correlation between RSI divergence signals and subsequent price movement?"
4. "Summarize today's trading performance across all active strategies"
- Each question graded: correct / partially correct / incorrect / hallucinated

### AC-3: CTO evaluation tasks
CTO tests:
1. "Show me the system architecture for signal flow from bar close to order submission"
2. "What building blocks are registered but never used in any strategy?"
3. "Explain the walkforward validation methodology"
4. "List all data quality issues from the last 24 hours"

### AC-4: Evaluation report
- A structured `docs/qa/AI_CONSULTANT_INTERNAL_EVAL.md` with:
  - Questions asked, answers given, accuracy rating
  - Hallucination count and severity
  - Coverage gaps (questions it couldn't answer)
  - Go/no-go recommendation for external rollout

## Definition of Done
- [ ] AI Consultant accessible to internal team
- [ ] StrategyResearcher completes eval tasks (graded)
- [ ] CTO completes eval tasks (graded)
- [ ] Evaluation report published
- [ ] Go/no-go recommendation documented
- [ ] If go: external rollout child issue created
- [ ] If no-go: improvement child issues created

## References
- Source: `src/ai_consultant/consultant_service.py` (398 lines)
- Signal catalog: `src/ai_consultant/signal_catalog.py` (480 lines)
- Query engine: `src/ai_consultant/db/query_engine.py`
- Audit writer: `src/ai_consultant/audit_writer.py` (283 lines)
- Architecture: `docs/architecture/AI_CONSULTANT.md`

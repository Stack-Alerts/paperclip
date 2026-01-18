# STRATEGY BUILDER REDESIGN - MASTER PLAN
**Full Design Analysis: DESIGN MODE + EXPERT MODE + NAUTILUS EXPERT**

---

## Project Overview

**Branch**: `origin/strategy_development`  
**Status**: 🟢 COMPLETE - All Documentation Finished (33/33 documents - 100%)  
**Last Updated**: 2026-01-16 10:27 AM
**Documents Completed**: ALL - Ready for implementation

### Critical Context
- ✅ Registry system completely redesigned for building blocks
- ✅ Building block signals are now simple and granular
- ✅ Single source of truth established via registry
- 🎯 Strategy builder must now leverage this new architecture

### Design Goals
1. **Maximum Flexibility**: Support complex multi-block, multi-signal strategies
2. **Intuitive UX**: Easy to use, button-based interactions
3. **Real-time Feedback**: Live backtest previews and parameter tuning
4. **Production-Grade**: NautilusTrader integration for institutional trading
5. **Comprehensive Testing**: Walkforward analysis with two distinct modes

---

## Document Structure & Tracking

### Phase 1: Design Specification Documents
**Status**: ✅ COMPLETE (14/14 - 100%)

| Document | Status | File | Priority |
|----------|--------|------|----------|
| 1. Architecture Overview | ✅ COMPLETE | `01_ARCHITECTURE_OVERVIEW.md` | P0 - Critical |
| 2. User Flows & Interactions | ✅ COMPLETE | `02_USER_FLOWS.md` | P0 - Critical |
| 3. Component Specifications | ✅ COMPLETE | `03_COMPONENT_SPECS.md` | P0 - Critical |
| 4. Block Management System | ✅ COMPLETE | `04_BLOCK_MANAGEMENT.md` | P0 - Critical |
| 5. Signal Configuration System | ✅ COMPLETE | `05_SIGNAL_CONFIGURATION.md` | P0 - Critical |
| 6. AND/OR Logic System | ✅ COMPLETE | `06_AND_OR_LOGIC_SYSTEM.md` | P0 - Critical |
| 7. Timing Constraints System | ✅ COMPLETE | `07_TIMING_CONSTRAINTS.md` | P1 - High |
| 8. Testing Modes Design | ✅ COMPLETE | `08_TESTING_MODES.md` | P1 - High |
| 9. Real-time Preview System | ✅ COMPLETE | `09_REALTIME_PREVIEW.md` | P1 - High |
| 10. Block Search & Filter | ✅ COMPLETE | `10_BLOCK_SEARCH_FILTER.md` | P1 - High |
| 11. Strategy Information Panel | ✅ COMPLETE | `11_STRATEGY_INFO_PANEL.md` | P2 - Medium |
| 12. Adaptive SL/TP Integration | ✅ COMPLETE | `12_ADAPTIVE_SL_TP.md` | P2 - Medium |
| 13. Visual Design System | ✅ COMPLETE | `13_VISUAL_DESIGN_SYSTEM.md` | P2 - Medium |
| 14. Responsive Design Spec | ✅ COMPLETE | `14_RESPONSIVE_DESIGN.md` | P3 - Low |

### Phase 2: Expert Assessment Reports
**Status**: ✅ COMPLETE (5/5 - 100%)

| Report | Status | File | Priority |
|--------|--------|------|----------|
| 1. Design Quality Assessment | ✅ COMPLETE | `20_EXPERT_DESIGN_QUALITY.md` | P0 - Critical |
| 2. Usability Analysis | ✅ COMPLETE | `21_EXPERT_USABILITY.md` | P0 - Critical |
| 3. Implementation Readiness | ✅ COMPLETE | `22_EXPERT_IMPLEMENTATION.md` | P0 - Critical |
| 4. Priority Improvements | ✅ COMPLETE | `23_EXPERT_IMPROVEMENTS.md` | P1 - High |
| 5. Final Recommendation | ✅ COMPLETE | `24_EXPERT_FINAL_RECOMMENDATION.md` | P0 - Critical |

### Phase 3: Nautilus Integration Documents
**Status**: ✅ COMPLETE (7/7 - 100%)

| Document | Status | File | Priority |
|----------|--------|------|----------|
| 1. Framework Compatibility | ✅ COMPLETE | `30_NAUTILUS_COMPATIBILITY.md` | P0 - Critical |
| 2. Strategy Code Generation | ✅ COMPLETE | `31_NAUTILUS_CODE_GENERATION.md` | P0 - Critical |
| 3. Type System Integration | ✅ COMPLETE | `32_NAUTILUS_TYPE_SYSTEM.md` | P0 - Critical |
| 4. Data Engine Integration | ✅ COMPLETE | `33_NAUTILUS_DATA_ENGINE.md` | P1 - High |
| 5. Execution Engine Integration | ✅ COMPLETE | `34_NAUTILUS_EXECUTION_ENGINE.md` | P1 - High |
| 6. Portfolio Tracking | ✅ COMPLETE | `35_NAUTILUS_PORTFOLIO.md` | P1 - High |
| 7. MessageBus Events | ✅ COMPLETE | `36_NAUTILUS_MESSAGEBUS.md` | P2 - Medium |

### Phase 4: Implementation Documents
**Status**: ✅ COMPLETE (5/5 - 100%)

| Document | Status | File | Priority |
|----------|--------|------|----------|
| 1. Implementation Roadmap | ✅ COMPLETE | `40_IMPLEMENTATION_ROADMAP.md` | P0 - Critical |
| 2. Technology Stack | ✅ COMPLETE | `41_TECHNOLOGY_STACK.md` | P0 - Critical |
| 3. Development Milestones | ✅ COMPLETE | `42_DEVELOPMENT_MILESTONES.md` | P0 - Critical |
| 4. Testing Strategy | ✅ COMPLETE | `43_TESTING_STRATEGY.md` | P1 - High |
| 5. Deployment Plan | ✅ COMPLETE | `44_DEPLOYMENT_PLAN.md` | P2 - Medium |

---

## Key Requirements Summary

### 1. Building Block System (NEW)
- ✅ Powered by registry (single source of truth)
- ✅ Simple and granular signals
- 🎯 Must support multiple blocks per strategy
- 🎯 Each block can have multiple signals
- 🎯 Signals can be dependent on previous signals

### 2. Signal Logic System (NEW)
```
Building Block 1
├─ Signal 1 (Always required as trigger)
├─ Signal 2 (Optional)
│  └─ Within X candles constraint (optional)
├─ Signal 3 (Optional)
└─ Signal 4 (Optional, depends on Signal 2)
   └─ Within X candles constraint (optional)

Building Block 2 (AND/OR classifier)
├─ AND: Mandatory, adds to total calculation requirement
└─ OR: Optional, provides booster/confluence
```

### 3. Timing Constraints
- "Within X candles" specification per signal
- Can reference first signal or any specific signal
- Failure to meet timing resets entire strategy count
- OR blocks provide position size/leverage boosters

### 4. What Remains Unchanged
✅ Adaptive Stop Loss v2.0 Configuration  
✅ Block Search and Selection (enhanced, not replaced)

### 5. What Needs Updates
🔄 Strategy Information (add auto-populated description)  
🔄 Edit Strategy Window (maximize, scroll support)  
🔄 Block Search (signal statistics, occurrences)

### 6. What Needs Complete Redesign
🆕 Strategy Blocks Configuration  
🆕 Signal Addition UX (button-based)  
🆕 Block Ordering (move up/down)  
🆕 Block Indentation (dependency visualization)  
🆕 AND/OR Logic Controls  
🆕 Timing Constraint Controls  
🆕 Auto Signal Count Calculation  

### 7. Block Search Enhancements
```
Elliott Wave Oscillator 
Category: ELLIOTT_WAVE
Type: EVENT
Default Weight Total: 22 points 
Description: Momentum indicator confirming wave patterns...

Block Type Definitions:
- SIGNAL BLOCK: Event-driven entry/exit signals
- CONTEXT BLOCK: Continuous state provider
- EVENT BLOCK: Specific market event detection
- HYBRID BLOCK: Combination of continuous + selective

Returns (Signals):
├─ BEARISH_DIVERGENCE - 2049 (11.9%)
├─ BULLISH_DIVERGENCE - 1853 (10.8%)
├─ BEARISH_MOMENTUM_INCREASING - 3483 (20.3%)
└─ ... [Full statistics for all signals]

Usage Tip: [Contextual help]
```

### 8. Testing Modes (CRITICAL)

#### Mode 1: Historical Walkforward
- Start X days back (e.g., 180 days)
- Expand window candle-by-candle
- Stop at current candle
- Report all metrics

#### Mode 2: Live Continuation Walkforward
- Start X days back (e.g., 180 days)
- Expand window to current
- **Continue waiting for new candles**
- Process each new candle in real-time
- Run until user stops
- If stopped after 2 days = 182 days total testing

### 9. Test Reporting Requirements
- Total signals triggered
- TP1, TP2, TP3 adjustment counts per position
- SL adjustment counts per position
- Fibonacci/Hybrid TP mode verification
- Training window integration (e.g., 30 days training + 180 days testing = start 210 days back)

### 10. UX Requirements (CRITICAL)
✅ Button-based signal addition  
✅ AND/OR buttons for logic flow  
✅ "Within X Candles" button + picker  
✅ Drag-and-drop block ordering  
✅ Visual indentation for dependencies  
✅ Real-time backtest preview  
✅ Live parameter tuning  
✅ Tooltips on ALL form fields  
✅ Bullish/Bearish strategy highlighting  
✅ Multi-filter block search  
✅ Removed blocks not shown in search  

---

## Integration Requirements

### NautilusTrader Framework
**Critical Integration Points**:
- ✅ Strategy base class compatibility
- ✅ Real-time DataEngine
- ✅ ExecutionEngine order lifecycle
- ✅ Portfolio position tracking
- ✅ MessageBus event system

**Type System Compliance**:
- ✅ Quantity (not float)
- ✅ Price (not float)
- ✅ Money (with currency)
- ✅ Enums (OrderSide.BUY, not "BUY")

**Generated Code Requirements**:
- Must be production-grade
- Must pass institutional validation
- Must handle all edge cases
- Must include proper error handling
- Must use exact NautilusTrader patterns

---

## Development Workflow

### Phase A: Planning & Design (Current)
1. ✅ Create master plan document
2. 🔴 Create all Phase 1 design documents
3. 🔴 Review and iterate on designs
4. 🔴 Get stakeholder approval

### Phase B: Expert Assessment
1. 🔴 Execute all Phase 2 expert assessments
2. 🔴 Identify critical issues
3. 🔴 Prioritize improvements
4. 🔴 Update designs based on assessment

### Phase C: Nautilus Integration Planning
1. 🔴 Create all Phase 3 integration documents
2. 🔴 Define code generation templates
3. 🔴 Verify type system compliance
4. 🔴 Plan data flow integration

### Phase D: Implementation Planning
1. 🔴 Create implementation roadmap
2. 🔴 Define milestones and timelines
3. 🔴 Assign priorities and dependencies
4. 🔴 Create testing strategy

### Phase E: Implementation (Future)
1. 🔴 Execute according to roadmap
2. 🔴 Continuous testing and validation
3. 🔴 Iterative improvement
4. 🔴 Production deployment

---

## Success Criteria

### Design Phase Success
- [ ] All 14 design documents completed
- [ ] User flows validated
- [ ] Component specifications detailed
- [ ] Visual designs finalized

### Expert Assessment Success
- [ ] All 5 expert reports completed
- [ ] Design quality score > 85/100
- [ ] Usability score > 90/100
- [ ] Implementation readiness: GREEN

### Nautilus Integration Success
- [ ] Framework compatibility: 100%
- [ ] Code generation templates validated
- [ ] Type system compliance verified
- [ ] Production-grade code output

### Implementation Success
- [ ] Roadmap created with timelines
- [ ] Technology stack selected
- [ ] Milestones defined with estimates
- [ ] GO/NO-GO decision: GO

---

## Document Creation Order

### Sprint 1: Core Design (Days 1-3)
1. `01_ARCHITECTURE_OVERVIEW.md`
2. `02_USER_FLOWS.md`
3. `03_COMPONENT_SPECS.md`
4. `04_BLOCK_MANAGEMENT.md`
5. `05_SIGNAL_CONFIGURATION.md`

### Sprint 2: Logic & Testing (Days 4-5)
6. `06_AND_OR_LOGIC_SYSTEM.md`
7. `07_TIMING_CONSTRAINTS.md`
8. `08_TESTING_MODES.md`
9. `09_REALTIME_PREVIEW.md`

### Sprint 3: Search & UI (Days 6-7)
10. `10_BLOCK_SEARCH_FILTER.md`
11. `11_STRATEGY_INFO_PANEL.md`
12. `12_ADAPTIVE_SL_TP.md`
13. `13_VISUAL_DESIGN_SYSTEM.md`
14. `14_RESPONSIVE_DESIGN.md`

### Sprint 4: Expert Assessment (Days 8-9)
15. All Phase 2 Expert Assessment Reports

### Sprint 5: Nautilus Integration (Days 10-12)
16. All Phase 3 Nautilus Integration Documents

### Sprint 6: Implementation Planning (Days 13-14)
17. All Phase 4 Implementation Documents

---

## Risk Assessment

### High Risk Items (RED)
🔴 **Complex AND/OR logic** - Must be intuitive despite complexity  
🔴 **Timing constraints** - User must understand candle counting  
🔴 **Real-time testing Mode 2** - Requires careful architecture  
🔴 **Code generation quality** - Must be production-grade  

### Medium Risk Items (YELLOW)
🟡 **Multi-signal dependencies** - Visualization complexity  
🟡 **Block search filtering** - Performance with many blocks  
🟡 **Real-time preview** - May impact performance  

### Low Risk Items (GREEN)
🟢 **Adaptive SL/TP integration** - Already implemented  
🟢 **Visual design system** - Standard UI patterns  
🟢 **Strategy info panel** - Straightforward enhancement  

---

## Next Steps

### Immediate Actions
1. ✅ Create this master plan document
2. 🎯 Begin creating Phase 1 design documents
3. 🎯 Start with `01_ARCHITECTURE_OVERVIEW.md`
4. 🎯 Continue sequentially through Sprint 1

### Review Points
- After Sprint 1: Review core design approach
- After Sprint 3: Review complete UI/UX design
- After Sprint 4: Review expert assessment feedback
- After Sprint 6: Final GO/NO-GO decision

---

## Stakeholder Sign-off

| Phase | Reviewer | Status | Date | Notes |
|-------|----------|--------|------|-------|
| Design Phase | TBD | 🔴 Pending | - | - |
| Expert Assessment | TBD | 🔴 Pending | - | - |
| Nautilus Integration | TBD | 🔴 Pending | - | - |
| Implementation Plan | TBD | 🔴 Pending | - | - |

---

## Appendix

### A. Reference Documents
- `.clinerules` - Institutional rules and protocols
- `CLINE_INSTITUTIONAL_RULES.md` - Full institutional guide
- NautilusTrader Docs: https://nautilustrader.io/docs/latest/

### B. Related Documents
- `docs/v3/ADAPTIVE_SL_IMPLEMENTATION_STATUS.md`
- `docs/v3/DYNAMIC_TP_SYSTEM_DESIGN.md`
- Strategy Builder existing docs (if any)

### C. Contact & Support
- Branch: `origin/strategy_development`
- Documentation Location: `docs/v3/UI-UX/`
- Issue Tracking: TBD

---

**Document Status**: 🟢 ACTIVE  
**Last Updated**: 2026-01-16  
**Next Review**: After Sprint 1 completion  
**Version**: 1.0.0

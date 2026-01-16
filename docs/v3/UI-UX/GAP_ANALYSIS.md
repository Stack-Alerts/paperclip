# Strategy Builder - Gap Analysis
**Date**: 2026-01-16  
**Status**: 🔴 Critical - Major Gaps Identified  
**Completion**: ~30% of Design Spec Implemented

---

## Executive Summary

**Current State**: Basic UI framework with 3 panels  
**Design Target**: Full-featured strategy builder with 8+ panels and complex interactions  
**Estimated Gap**: **~70% of features missing**

---

## Component-by-Component Gap Analysis

### 1. Strategy Information Panel
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| Name field | ✅ Text input, required | ✅ Working | ✅ DONE |
| Description | ✅ Auto-generated, editable | ❌ Static text only | ❌ MISSING |
| Type indicator | ✅ Bullish/Bearish badge with color | ❌ Not implemented | ❌ MISSING |
| Required signals count | ✅ Auto-calculated from AND blocks | ❌ Not calculated | ❌ MISSING |
| Auto-description generation | ✅ Generated from blocks/signals | ❌ Not implemented | ❌ MISSING |
| **Completion** | **100%** | **20%** | **🔴 80% GAP** |

---

### 2. Block Search Panel  
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| Search input | ✅ Full-text search | ✅ Working | ✅ DONE |
| Category filter | ✅ Dropdown with all categories | ✅ Working | ✅ DONE |
| Type filter | ✅ EVENT/SIGNAL/CONTEXT/HYBRID | ✅ Working | ✅ DONE |
| Tag multi-select | ✅ Multi-select for tags | ❌ Not implemented | ❌ MISSING |
| Signal statistics | ✅ Occurrence counts, percentages | ✅ Working | ✅ DONE |
| Signal descriptions | ✅ Visible under each signal | ✅ **JUST ADDED** | ✅ DONE |
| Signal filtering | ✅ Hide ERROR/NEUTRAL/etc | ✅ **JUST ADDED** | ✅ DONE |
| **Signal selection UI** | ✅ **Checkboxes per signal** | ❌ **MISSING** | ❌ **CRITICAL** |
| **AND/OR buttons** | ✅ **"Add as AND" / "Add as OR"** | ❌ **Single "Add" button** | ❌ **CRITICAL** |
| Block already added check | ✅ Prevent duplicates | ✅ Working | ✅ DONE |
| **Completion** | **100%** | **60%** | **🟡 40% GAP** |

---

### 3. Strategy Configuration Panel (Blocks Panel)
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| Block list display | ✅ Scrollable list | ✅ Working | ✅ DONE |
| Block header | ✅ Name, AND/OR badge, controls | ⚠️ Partial (no badge) | ⚠️ PARTIAL |
| **AND/OR badge** | ✅ **Colored badge showing logic** | ❌ **Not displayed** | ❌ **CRITICAL** |
| **Move up/down buttons** | ✅ **▲▼ buttons** | ❌ **Not implemented** | ❌ **CRITICAL** |
| **Indent/unindent buttons** | ✅ **→← for dependencies** | ❌ **Not implemented** | ❌ **CRITICAL** |
| Remove button | ✅ × button | ⚠️ Partial | ⚠️ PARTIAL |
| **Drag-and-drop reordering** | ✅ **Visual drag-and-drop** | ❌ **Not implemented** | ❌ **MISSING** |
| **Signal list per block** | ✅ **Show configured signals** | ❌ **Not shown** | ❌ **CRITICAL** |
| **"Add Signal" button** | ✅ **Add more signals to block** | ❌ **Not implemented** | ❌ **CRITICAL** |
| **Visual indentation** | ✅ **Show dependencies** | ❌ **Not implemented** | ❌ **CRITICAL** |
| **Dependency indicators** | ✅ **Visual arrows/lines** | ❌ **Not implemented** | ❌ **MISSING** |
| **Completion** | **100%** | **15%** | **🔴 85% GAP** |

---

### 4. Signal Configuration Widget
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| Signal selector dropdown | ✅ Available signals | ❌ Not implemented | ❌ **CRITICAL** |
| AND/OR toggle | ✅ Toggle buttons | ❌ Not implemented | ❌ **CRITICAL** |
| "Within X Candles" checkbox | ✅ Timing constraint | ❌ Not implemented | ❌ **CRITICAL** |
| Candle count spinner | ✅ Number input | ❌ Not implemented | ❌ **CRITICAL** |
| Reference signal dropdown | ✅ Select reference | ❌ Not implemented | ❌ **CRITICAL** |
| Dependency indicator | ✅ Visual link | ❌ Not implemented | ❌ MISSING |
| Add/Remove signal buttons | ✅ Manage signals | ❌ Not implemented | ❌ **CRITICAL** |
| **Completion** | **100%** | **0%** | **🔴 100% GAP** |

---

### 5. Adaptive SL/TP Panel
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| SL Mode dropdown | ✅ Fibonacci/Aggressive/Conservative | ❌ Not in UI | ❌ MISSING |
| Fibonacci level slider | ✅ 0.236-0.618 | ❌ Not in UI | ❌ MISSING |
| TP Mode dropdown | ✅ Fibonacci/Hybrid/Static | ❌ Not in UI | ❌ MISSING |
| TP1/TP2/TP3 inputs | ✅ Percentage inputs | ❌ Not in UI | ❌ MISSING |
| Integration with existing | ✅ Use Adaptive SL v2.0 | ❌ Not connected | ❌ MISSING |
| **Completion** | **100%** | **0%** | **🔴 100% GAP** |

---

### 6. Testing Controls Panel
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| Mode selector | ✅ Radio: Mode 1/Mode 2 | ❌ Not implemented | ❌ **CRITICAL** |
| Testing window spinner | ✅ Days input | ❌ Not implemented | ❌ **CRITICAL** |
| Training window spinner | ✅ Optional days | ❌ Not implemented | ❌ MISSING |
| Timeframe dropdown | ✅ 1min-1d options | ❌ Not implemented | ❌ **CRITICAL** |
| Run Test button | ✅ Start test | ❌ Not implemented | ❌ **CRITICAL** |
| Stop Test button | ✅ Stop Mode 2 | ❌ Not implemented | ❌ MISSING |
| Progress bar | ✅ Live progress | ❌ Not implemented | ❌ **CRITICAL** |
| Live metrics display | ✅ Real-time updates | ❌ Not implemented | ❌ **CRITICAL** |
| **Completion** | **100%** | **0%** | **🔴 100% GAP** |

---

### 7. Real-time Preview Panel
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| Chart canvas | ✅ Plotly/Matplotlib | ❌ Not implemented | ❌ **CRITICAL** |
| Signal markers | ✅ Visual on chart | ❌ Not implemented | ❌ **CRITICAL** |
| Quick metrics | ✅ Signals/Trades/P&L | ❌ Not implemented | ❌ **CRITICAL** |
| Pause/Resume button | ✅ Control preview | ❌ Not implemented | ❌ MISSING |
| Expand button | ✅ Full window | ❌ Not implemented | ❌ MISSING |
| Auto-update on config change | ✅ Live refresh | ❌ Not implemented | ❌ **CRITICAL** |
| **Completion** | **100%** | **0%** | **🔴 100% GAP** |

---

## Core Logic Component Gaps

### 8. StrategyConfigEngine
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| add_block() with AND/OR | ✅ Accept logic parameter | ⚠️ Partial (no AND/OR) | ⚠️ PARTIAL |
| add_signal() to block | ✅ Add signals to blocks | ❌ Not implemented | ❌ **CRITICAL** |
| recalculate_requirements() | ✅ Auto-calc required signals | ❌ Not implemented | ❌ **CRITICAL** |
| generate_description() | ✅ Auto-generate from config | ❌ Not implemented | ❌ MISSING |
| validate() | ✅ Comprehensive validation | ⚠️ Basic only | ⚠️ PARTIAL |
| **Completion** | **100%** | **20%** | **🔴 80% GAP** |

---

### 9. SignalDependencyResolver
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| build_graph() | ✅ Dependency graph | ✅ Working | ✅ DONE |
| validate_timing() | ✅ Check constraints | ✅ Working | ✅ DONE |
| should_reset_strategy() | ✅ Reset on timing fail | ⚠️ Partial | ⚠️ PARTIAL |
| Timing constraint support | ✅ Full support | ⚠️ Backend only | ⚠️ PARTIAL |
| **Completion** | **100%** | **75%** | **🟡 25% GAP** |

---

### 10. NautilusCodeGenerator
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| generate_strategy() | ✅ Complete code | ✅ Working | ✅ DONE |
| generate_imports() | ✅ All imports | ✅ Working | ✅ DONE |
| generate_entry_logic() | ✅ AND/OR logic | ⚠️ Basic only | ⚠️ PARTIAL |
| Signal detection per block | ✅ Per-block methods | ⚠️ Partial | ⚠️ PARTIAL |
| Timing constraint code | ✅ Generate constraints | ❌ Not implemented | ❌ MISSING |
| **Completion** | **100%** | **60%** | **🟡 40% GAP** |

---

### 11. WalkforwardTestEngine
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| run_mode1() | ✅ Historical walkforward | ✅ Working | ✅ DONE |
| run_mode2() | ✅ Historical + Live | ❌ Not implemented | ❌ **CRITICAL** |
| Live candle streaming | ✅ Real-time mode | ❌ Not implemented | ❌ **CRITICAL** |
| Progress callbacks | ✅ Real-time updates | ⚠️ Basic only | ⚠️ PARTIAL |
| **Completion** | **100%** | **50%** | **🟡 50% GAP** |

---

### 12. RealtimePreviewEngine
| Feature | Design Spec | Current Implementation | Status |
|---------|-------------|----------------------|---------|
| start_preview() | ✅ Background preview | ❌ Not implemented | ❌ **CRITICAL** |
| update_config() | ✅ Live config updates | ❌ Not implemented | ❌ **CRITICAL** |
| Quick backtest (30 days) | ✅ Fast preview | ❌ Not implemented | ❌ **CRITICAL** |
| Signal visualization | ✅ Chart with markers | ❌ Not implemented | ❌ **CRITICAL** |
| **Completion** | **100%** | **0%** | **🔴 100% GAP** |

---

## Critical Missing Features (Priority Order)

### P0 - Blocking Basic Functionality
1. **Signal Selection UI** - Can't select which signals to add
2. **AND/OR Logic** - Can't differentiate required vs optional blocks
3. **Signal Configuration** - Can't configure individual signals
4. **Block Signal Display** - Can't see which signals are in each block

### P1 - Core Features
5. **Testing Controls** - Can't run tests from UI
6. **Real-time Preview** - No visual feedback while building
7. **Block Reordering** - Can't change block order
8. **Timing Constraints UI** - Can't set "Within X candles"

### P2 - Enhanced UX
9. **Drag-and-drop** - Manual reordering only
10. **Visual Dependencies** - No dependency visualization
11. **SL/TP Integration** - Not connected to UI
12. **Auto-description** - Manual description only

---

## Implementation Roadmap

### Phase 1: Critical UX Fixes (Next Session)
**Estimated Time**: 3-4 hours

1. **Add Signal Selection**
   - Checkboxes per signal in BlockListItem
   - "Add as AND" and "Add as OR" buttons
   - New signal: `block_with_signals_selected(block_name, signals, logic)`

2. **Update Strategy Blocks Panel**
   - Display AND/OR badge per block
   - Show selected signals under each block
   - Add "Add Signal" button to existing blocks

3. **Update Orchestrator**
   - Accept signal list in `add_block()`
   - Handle AND vs OR logic
   - Store signal configurations

**Deliverable**: Can select signals and add as AND/OR

---

### Phase 2: Signal Configuration (2-3 hours)
4. **Signal Configuration Widget**
   - AND/OR toggle per signal
   - "Within X Candles" checkbox
   - Candle count spinner
   - Reference signal dropdown

5. **Timing Constraints**
   - UI for constraint configuration
   - Validation of constraints
   - Visual indicators

**Deliverable**: Full signal-level configuration

---

### Phase 3: Block Management (2-3 hours)
6. **Block Controls**
   - Move Up/Down buttons (▲▼)
   - Indent/Unindent buttons (→←)
   - Drag-and-drop support

7. **Visual Dependencies**
   - Indentation visualization
   - Dependency arrows/lines
   - Validation errors display

**Deliverable**: Full block management

---

### Phase 4: Testing & Preview (4-6 hours)
8. **Testing Controls Panel**
   - Mode 1/2 selector
   - Configuration inputs
   - Run/Stop buttons
   - Progress display

9. **Real-time Preview Panel**
   - Chart with signal markers
   - Quick metrics
   - Auto-update on changes

**Deliverable**: Complete testing workflow

---

### Phase 5: Polish & Integration (2-3 hours)
10. **SL/TP Panel**
11. **Auto-description Generation**
12. **Enhanced Validation Display**
13. **Save/Load Improvements**

**Deliverable**: Production-ready UI

---

## Total Estimated Effort

| Component | Current % | Gap % | Est. Hours |
|-----------|-----------|-------|------------|
| UI Panels | 30% | 70% | 12-15 |
| Core Logic | 50% | 50% | 6-8 |
| Testing | 25% | 75% | 6-8 |
| **TOTAL** | **~30%** | **~70%** | **24-31 hours** |

---

## Immediate Next Steps

**Session 1 (Now)**: ✅ Signal filtering & descriptions  
**Session 2 (Next)**: Signal selection UI + AND/OR buttons (P0)  
**Session 3**: Signal configuration widget (P1)  
**Session 4**: Block reordering + controls (P1)  
**Session 5**: Testing & Preview panels (P1)  
**Session 6**: Polish & integration (P2)

---

## Recommendations

1. **Focus on P0 features first** - Without signal selection, the app is unusable
2. **Implement Phase 1-2 before testing** - Need full config before test run
3. **Defer Phase 5 features** - Can be added after core functionality works
4. **User testing after Phase 3** - Get feedback before building testing panels

---

**Document Status**: 🔴 Critical Gaps Identified  
**Action Required**: Implement Phase 1 immediately  
**Estimated Completion**: 6 sessions (~24-31 hours)

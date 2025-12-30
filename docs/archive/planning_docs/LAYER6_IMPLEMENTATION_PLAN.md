# Layer 6 TradingView Alerts - Implementation Plan

## Overview
Layer 6 integrates TradingView alert signals as a weighted confluence layer for the BTC Scalp Bot V10. It processes pre-computed directional signals from TradingView indicators and adds them as confirmation to the existing 5-layer system.

## Branch & Repository Status
- **Branch**: `feature/layer6`
- **Base**: `master` (merged from `BackTest_Tuning`)
- **Status**: Ready for implementation

## Implementation Phases

### Phase 1: Core Layer Implementation ✓ READY
**Files to Create:**
- `src/layers/layer6_tv_alerts.py` - Main layer class
- `config/layer_presets/layer6_tv_alerts.yaml` - Configuration
- `tests/test_layer6_tv_alerts.py` - Unit tests

**Key Features:**
1. CSV loading and normalization (filter DOGE alerts)
2. Alert window selection (time-based lookback)
3. Signal parsing (explicit, inferred, contextual)
4. Exit signal processor (position-aware)
5. Context helper methods (HOD/LOD, EMA position, momentum)
6. Weighted score aggregation
7. LayerSignal output

### Phase 2: Compositor Integration
**Files to Modify:**
- `src/layers/layer_compositor.py` - Add Layer 6 initialization
- `config/strategies/scalp_conservative.py` - Add Layer 6 weight
- `config/strategies/scalp_aggressive.py` - Add Layer 6 weight
- `config/strategies/scalp_ml_heavy.py` - Add Layer 6 weight
- `tests/test_compositor.py` - Add Layer 6 tests

**Changes:**
- Layer 6 weight: 5% (reserved in compositor)
- Update strategy `should_exit()` methods for exit signals
- Add `layer6_exit_handling` config section

### Phase 3: Backtest Integration
**Files to Modify:**
- `src/cli/backtest_runner.py` - Add Layer 6 CLI options
- `src/backtesting/backtest_engine.py` - Add Layer 6 initialization

**New CLI Options:**
```bash
--enable-layer6          Enable TradingView alerts
--layer6-csv PATH        Path to alert CSV
--layer6-weight FLOAT    Layer 6 weight override
```

### Phase 4: Live Trading Integration
**Files to Create:**
- `src/webhooks/tv_gateway.py` - FastAPI webhook service
- `src/webhooks/alert_router.py` - Alert distribution

**Files to Modify:**
- `src/cli/paper_runner.py` - Add webhook gateway
- `src/cli/live_runner.py` - Add webhook gateway

### Phase 5: Optimizer Integration
**Files to Modify:**
- `src/optimization/search_space.py` - Add Layer 6 parameters

**New Parameters:**
```python
'layer6_weight': (0.0, 0.20),
'layer6_lookback_bars': (3, 12),
'layer6_decay_tau': (30, 120),
'layer6_direction_threshold': (0.1, 0.3)
```

### Phase 6: Documentation
**Files to Update:**
- `docs/ARCHITECTURE.md` - Add Layer 6
- `docs/CLI_REFERENCE.md` - Add Layer 6 options
- `docs/USER_GUIDE.md` - Add Layer 6 usage
- Create `docs/TRADINGVIEW_SETUP.md`

## Alert Taxonomy (21 BTC Alert Types)

### Explicit Directional Signals
1. `BTC LUX Bullish Confirmation 15 Min` - Bullish (0.95)
2. `BTC LUX Bearish Confirmation 15 Min` - Bearish (0.95)
3. `BTC Bullish BOS 15 Min` - Bullish (0.85)
4. `BTC Bearish BOS 15 Min` - Bearish (0.85)
5. `BTC ADV Stock Long Signal 15 Min` - Bullish (0.80)
6. `BTC ADV Stoch Short Signal 15 Min` - Bearish (0.80)

### Exit Signals
7. `LUX Any Exit Signal 15 Min` - Neutral (exit only)

### HOD/LOD Levels
8. `BTC iHOD Cross 15 Min` - Bullish inferred (0.70)
9. `BTC iLOD Cross 15 Min` - Bearish inferred (0.70)
10. `BTC Todays HOD Cross 15 Min` - Bullish inferred (0.75)
11. `BTC Todays LOD Cross` - Bearish inferred (0.75)

### Session Levels
12. `BTC 50% Asia Crossed 15 Min` - Contextual (0.65)
13. `BTC 50% HLOD Cross` - Contextual (0.60)
14. `BTC 50% HLOW Cross` - Contextual (0.60)
15. `TTC US Settle Crossed 15 Min` - Contextual (0.70, +30% at 4pm EST)

### EMA Crosses
16. `BTC 50 EMA Cross 15 Min` - Contextual (0.65)
17. `BTC 200 EMA Cross 15 Min` - Contextual (0.70)
18. `BTC 800 EMA Cross 15 Min` - Contextual (0.60)

### Vector Candles
19. `BTC Vector Candle 15 Min` - Contextual (0.60)
20. `BTC Vector Cross 50 EMA 15 Min` - Contextual (0.70)

### DMI
21. `BTC LUX DMI Changed 15 Min` - Contextual (0.75)

## Signal Interpretation Strategy

### Priority 1: Explicit Signals (90-95% confidence)
- Check description for "Long signal" / "Short signal"
- Check name for "Bullish" / "Bearish"
- **Trust these signals directly**

### Priority 2: Inferred Signals (70-85% confidence)
- HOD/LOD crosses (structural breakouts)
- BOS signals (break of structure)
- **Direction determined by alert type**

### Priority 3: Contextual Signals (60-75% confidence)
- EMA crosses → Check price position vs EMA
- Vector candles → Check recent price momentum
- Session levels → Check cross direction
- DMI changes → Check +DI vs -DI position
- **Requires market context analysis**

## Weight Adjustment Factors

1. **Time-based** (+30%): US settle time (4pm EST / 9pm UTC)
2. **Trend alignment** (+20%): Agrees with Layer 1 trend
3. **Alert clustering** (+15%): Multiple same-direction alerts
4. **Volatility** (-20%): High ATR reduces weight

## Exit Signal Handling

Exit signals are processed separately and added to metadata:
- `exit_signal_active`: Boolean flag
- `exit_signal_strength`: Float 0-1
- `exit_signal_count`: Number of exit alerts
- `exit_weight_contribution`: Weighted exit score

Strategies access exit signals in `should_exit()` method and combine with base exit logic.

## Testing Strategy

### Unit Tests
- CSV parsing and DOGE filtering
- Signal direction extraction (all 3 types)
- Context methods (HOD/LOD, EMA position, momentum)
- Exit signal processing
- Score aggregation and weighting
- Time decay calculations

### Integration Tests
- Layer 6 + Compositor integration
- Multi-layer signal generation
- Exit signal flow to strategies
- Weight distribution validation

### Backtest Tests
- Historical alert processing
- Performance comparison (with/without Layer 6)
- Layer contribution analysis
- Exit timing optimization

## Success Criteria

✅ Layer 6 integrates seamlessly with existing framework  
✅ Processes all 21 BTC alert types correctly  
✅ DOGE alerts filtered out  
✅ Exit signals properly routed to strategies  
✅ Backtest shows measurable improvement  
✅ All tests pass  
✅ Documentation complete  

## Timeline Estimate

- **Phase 1**: 4-5 hours
- **Phase 2**: 2-3 hours
- **Phase 3**: 2-3 hours
- **Phase 4**: 3-4 hours
- **Phase 5**: 1-2 hours
- **Phase 6**: 2-3 hours

**Total**: 14-20 hours

## Current Status

- ✅ Branch created: `feature/layer6`
- ✅ Specification reviewed and validated
- ✅ Implementation plan documented
- 🔄 Ready to begin Phase 1 implementation

---

**Next Step**: Implement `src/layers/layer6_tv_alerts.py`

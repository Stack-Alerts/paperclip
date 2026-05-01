# Layer-by-Layer Reporting Enhancement

## Overview

Enhance backtest, paper trading, and live trading reports to include detailed layer-by-layer breakdowns for each trade. This will provide insights into:
- Which layers contributed to each trade decision
- Individual layer directions and confidence
- Layer agreement and conflict patterns
- Optimization opportunities

## Current State

### Trade Record Structure
```python
@dataclass
class Trade:
    # ... existing fields ...
    signal_confidence: float = 0.0  # ✅ Exists but not populated
    signal_metadata: Dict = None    # ✅ Exists but not populated
```

### Compositor Signal Structure
```python
composite_signal.metadata = {
    'composite_score': float,
    'layer_agreement': float,
    'contributions': Dict[str, float],  # ✅ Layer contributions
    'layer_signals': Dict[str, LayerSignal],  # ✅ Individual signals
    'timestamp': datetime
}
```

## Enhancement Design

### 1. Enhanced Trade Record

```python
trade.signal_confidence = composite_signal.confidence
trade.signal_metadata = {
    # Composite information
    'composite_score': composite_signal.score,
    'layer_agreement': composite_signal.layer_agreement,
    'direction': composite_signal.direction,
    
    # Layer-by-layer breakdown
    'layers': {
        'layer1_traditional': {
            'direction': 'long',
            'confidence': 0.65,
            'strength': 0.78,
            'contribution': 0.156,  # weighted contribution
            'weight': 0.20,
            'components': {...}  # Layer 1 specific details
        },
        'layer2_volume_delta': {...},
        'layer3_weis_wave': {...},
        'layer4_xgboost': {...},
        'layer5_cnn_lstm': {...},
        'layer6_tv_alerts': {
            'direction': 'long',
            'confidence': 0.68,
            'strength': 0.72,
            'contribution': 0.102,
            'weight': 0.15,
            # Layer 6 specific details
            'details': {
                'total_alerts': 5,
                'bullish_alerts': 5,
                'bearish_alerts': 0,
                'recent_alerts': [
                    'lux_algo_long_signal',
                    '50_ema_vector_candle',
                    'nnfx_adv_entry_long'
                ],
                'weighted_score': 0.68,
                'time_decay_applied': True
            }
        }
    },
    
    # Analysis
    'agreement_analysis': {
        'unanimous': False,
        'majority_direction': 'long',
        'conflicting_layers': ['layer3'],
        'agreement_score': 0.75
    }
}
```

### 3. Layer-Specific Details Captured

Each layer stores its specific analysis details:

#### Layer 1 (Traditional)
```python
'details': {
    'ema_9': 45180.50,
    'ema_20': 45120.30,
    'ema_50': 44980.20,
    'ema_crossover': 'bullish',  # 9 > 20 > 50
    'rsi_14': 58.5,
    'rsi_signal': 'neutral',
    'macd': 45.2,
    'macd_signal': 32.1,
    'macd_histogram': 13.1,
    'bb_position': 0.65,  # Price at 65% of BB range
    'atr_14': 450.30,
    'adx_14': 28.5,
    'trend_strength': 'moderate'
}
```

#### Layer 2 (Volume Delta)
```python
'details': {
    'cumulative_delta': 1250000,
    'delta_divergence': 'positive',
    'buy_volume': 1850000,
    'sell_volume': 600000,
    'imbalance_ratio': 3.08,
    'volume_trend': 'accumulation',
    'delta_ema': 980000
}
```

#### Layer 3 (Weis Wave)
```python
'details': {
    'wave_volume': 2500000,
    'wave_direction': 'up',
    'wave_phase': 'building',
    'effort_vs_result': 'normal',
    'climax_detected': False,
    'test_phase': False
}
```

#### Layer 4 (XGBoost)
```python
'details': {
    'prediction': 0.78,  # Probability of upward move
    'predicted_change': 0.028,  # +2.8%
    'feature_importance': {
        'volume_ratio': 0.25,
        'price_momentum': 0.22,
        'volatility': 0.18,
        'trend_strength': 0.15
    },
    'model_confidence': 0.82
}
```

#### Layer 5 (CNN-LSTM)
```python
'details': {
    'lstm_prediction': 0.85,
    'cnn_pattern': 'ascending_triangle',
    'sequence_confidence': 0.88,
    'predicted_direction': 'bullish',
    'volatility_forecast': 'increasing',
    'pattern_completion': 0.75
}
```

#### Layer 6 (TradingView Alerts)
```python
'details': {
    'total_alerts': 5,
    'bullish_alerts': 5,
    'bearish_alerts': 0,
    'recent_alerts': [
        {
            'name': 'LUX Algo Long Signal',
            'time': '2024-01-15 14:28:00',
            'weight': 0.95,
            'age_minutes': 2.0
        },
        {
            'name': '50 EMA Vector Candle',
            'time': '2024-01-15 14:25:00',
            'weight': 0.85,
            'age_minutes': 5.0
        },
        {
            'name': 'NNFX ADV Entry Long',
            'time': '2024-01-15 14:27:00',
            'weight': 0.80,
            'age_minutes': 3.0
        },
        {
            'name': 'Order Flow Surge',
            'time': '2024-01-15 14:29:00',
            'weight': 0.75,
            'age_minutes': 1.0
        },
        {
            'name': 'Structure Break Bullish',
            'time': '2024-01-15 14:26:00',
            'weight': 0.82,
            'age_minutes': 4.0
        }
    ],
    'weighted_score': 0.68,
    'time_decay_applied': True,
    'alert_taxonomy': 'mixed_high_quality'
}
```

### 2. Report Output Format

#### JSON Report Enhancement
```json
{
  "trades": [
    {
      "trade_id": "BTCUSDT_12345",
      "entry_time": "2024-01-15 14:30:00",
      "exit_time": "2024-01-15 15:45:00",
      "side": "long",
      "pnl": 125.50,
      "pnl_percent": 2.5,
      
      "signal_analysis": {
        "composite_confidence": 0.72,
        "layer_agreement": 0.75,
        "composite_score": 0.45,
        
        "layer_breakdown": [
          {
            "layer": "layer1_traditional",
            "direction": "long",
            "confidence": 0.65,
            "contribution": 0.13,
            "weight": 0.20,
            "key_indicators": {
              "ema_crossover": "bullish",
              "rsi": 58,
              "macd": "positive"
            }
          },
          {
            "layer": "layer2_volume_delta",
            "direction": "long",
            "confidence": 0.55,
            "contribution": 0.066,
            "weight": 0.12
          }
          // ... more layers
        ],
        
        "agreement": {
          "long_layers": ["layer1", "layer2", "layer4", "layer5", "layer6"],
          "short_layers": [],
          "neutral_layers": ["layer3"],
          "consensus": "strong_long"
        }
      }
    }
  ]
}
```

#### Human-Readable Summary - LONG Example
```
Trade #1: LONG | Entry: $45,230 | Exit: $45,890 | P&L: +$125.50 (+2.5%)
═══════════════════════════════════════════════════════════════════════

Composite Signal:
  Direction:  LONG
  Confidence: 72%
  Agreement:  75% (5/6 layers aligned)
  Score:      +0.45

Layer Breakdown:
┌─────────────────────────┬──────────┬────────────┬─────────────┬────────────┐
│ Layer                   │ Direction│ Confidence │ Contribution│ Weight     │
├─────────────────────────┼──────────┼────────────┼─────────────┼────────────┤
│ Layer 1: Traditional    │ LONG ↑   │ 65%        │ +0.130      │ 20%        │
│ Layer 2: Volume Delta   │ LONG ↑   │ 55%        │ +0.066      │ 12%        │
│ Layer 3: Weis Wave      │ NEUTRAL  │ 25%        │ +0.000      │ 8%         │
│ Layer 4: XGBoost        │ LONG ↑   │ 78%        │ +0.156      │ 20%        │
│ Layer 5: CNN-LSTM       │ LONG ↑   │ 82%        │ +0.205      │ 25%        │
│ Layer 6: TV Alerts      │ LONG ↑   │ 68%        │ +0.102      │ 15%        │
└─────────────────────────┴──────────┴────────────┴─────────────┴────────────┘

Agreement Analysis:
  ✓ Strong consensus (5/6 layers LONG)
  ✓ ML layers (4,5,6) in full agreement
  ⚠ Layer 3 (Weis Wave) neutral - volume wave incomplete

Layer Details:

Layer 1 (Traditional):
  • EMA 9/20/50: Bullish alignment ($45,180 > $45,120 > $44,980)
  • RSI: 58.5 (neutral momentum)
  • MACD: +13.1 histogram (positive momentum)
  • BB Position: 65% (upper half, not overbought)
  
Layer 2 (Volume Delta):
  • Buy volume: 1,850,000 vs Sell: 600,000
  • Imbalance ratio: 3.08:1 (strong accumulation)
  • Cumulative delta: +1,250,000 (bullish trend)
  
Layer 3 (Weis Wave):
  • Wave phase: Building (incomplete)
  • Wave volume: 2,500,000
  • Status: Neutral - awaiting wave completion
  
Layer 4 (XGBoost):
  • Prediction: 78% probability of upward move
  • Forecast: +2.8% price increase
  • Top features: Volume ratio (25%), Momentum (22%)
  
Layer 5 (CNN-LSTM):
  • LSTM prediction: 85% bullish
  • Pattern: Ascending triangle (75% complete)
  • Sequence confidence: 88%
  
Layer 6 (TradingView Alerts):
  • 5 bullish alerts in last 5 minutes:
    ✓ LUX Algo Long Signal (2m ago, weight: 0.95)
    ✓ 50 EMA Vector Candle (5m ago, weight: 0.85)
    ✓ NNFX ADV Entry Long (3m ago, weight: 0.80)
    ✓ Order Flow Surge (1m ago, weight: 0.75)
    ✓ Structure Break Bullish (4m ago, weight: 0.82)
  • Weighted score: 0.68 (with time decay)

Result: ✅ SUCCESSFUL (+2.5%)
```

#### Human-Readable Summary - SHORT Example
```
Trade #2: SHORT | Entry: $46,850 | Exit: $45,920 | P&L: +$186.00 (+2.0%)
═══════════════════════════════════════════════════════════════════════

Composite Signal:
  Direction:  SHORT
  Confidence: 68%
  Agreement:  67% (4/6 layers aligned)
  Score:      -0.38

Layer Breakdown:
┌─────────────────────────┬──────────┬────────────┬─────────────┬────────────┐
│ Layer                   │ Direction│ Confidence │ Contribution│ Weight     │
├─────────────────────────┼──────────┼────────────┼─────────────┼────────────┤
│ Layer 1: Traditional    │ SHORT ↓  │ 58%        │ -0.116      │ 20%        │
│ Layer 2: Volume Delta   │ SHORT ↓  │ 72%        │ -0.086      │ 12%        │
│ Layer 3: Weis Wave      │ SHORT ↓  │ 65%        │ -0.052      │ 8%         │
│ Layer 4: XGBoost        │ SHORT ↓  │ 71%        │ -0.142      │ 20%        │
│ Layer 5: CNN-LSTM       │ LONG ↑   │ 45%        │ +0.113      │ 25%        │
│ Layer 6: TV Alerts      │ NEUTRAL  │ 30%        │ +0.000      │ 15%        │
└─────────────────────────┴──────────┴────────────┴─────────────┴────────────┘

Agreement Analysis:
  ⚠ Moderate consensus (4/6 layers SHORT)
  ✓ Volume analysis strong (Layers 2,3)
  ⚠ Layer 5 (CNN-LSTM) conflicting - predicting reversal
  ⚠ Layer 6 (TV Alerts) neutral - mixed signals

Layer Details:

Layer 1 (Traditional):
  • EMA 9/20/50: Bearish alignment ($46,720 < $46,780 < $46,920)
  • RSI: 42.5 (weakening momentum)
  • MACD: -18.5 histogram (negative momentum)
  • ADX: 32.5 (strong trend)
  
Layer 2 (Volume Delta):
  • Sell volume: 2,200,000 vs Buy: 750,000
  • Imbalance ratio: 2.93:1 (heavy distribution)
  • Cumulative delta: -1,580,000 (bearish trend)
  
Layer 3 (Weis Wave):
  • Wave direction: Down (active bearish wave)
  • Wave volume: 3,100,000 (high effort)
  • Effort vs result: Normal (confirming move)
  
Layer 4 (XGBoost):
  • Prediction: 71% probability of downward move
  • Forecast: -2.5% price decrease
  • Top features: Price momentum (28%), Volume ratio (24%)
  
Layer 5 (CNN-LSTM) - ⚠ CONFLICTING:
  • LSTM prediction: 45% (weak bullish reversal signal)
  • Pattern: Potential bottoming formation
  • Note: Early warning proved correct - used for exit timing
  
Layer 6 (TradingView Alerts):
  • Mixed signals (3 bearish, 2 bullish in last 10min)
  • Neutral stance due to conflict
  • Last alerts:
    - Structure Break Bearish (3m ago)
    - Volume Climax (7m ago)

Result: ✅ SUCCESSFUL (+2.0%)
Note: Layer 5 conflict was correct - exit taken early on reversal signal
```

## Implementation Plan

### Phase 1: Backtest Engine Enhancement
1. ✅ Capture composite signal metadata in `_execute_strategy()`
2. ✅ Store in Trade record's `signal_metadata`
3. ✅ Enhance JSON report generation
4. ✅ Add layer breakdown to reports
5. ✅ Test with existing backtests

### Phase 2: Report Formatting
1. ✅ Create `LayerReportFormatter` utility
2. ✅ Generate human-readable summaries
3. ✅ Create CSV export with layer columns
4. ✅ Add trade-by-trade layer analysis

### Phase 3: Paper/Live Trading
1. ✅ Apply same enhancements to paper trading
2. ✅ Apply to live trading reports
3. ✅ Add real-time layer monitoring
4. ✅ Create live dashboard data

### Phase 4: Analysis Tools
1. ✅ Layer performance analyzer
2. ✅ Contribution correlation analysis
3. ✅ Optimal weight suggestions
4. ✅ Layer conflict detector

## Benefits

### For Optimization
- Identify underperforming layers
- Optimize layer weights based on actual performance
- Detect which layers work best in different market conditions

### For Analysis
- Understand why trades were taken
- Identify layer agreement patterns
- Spot systematic issues with specific layers

### For Debugging
- Track down signal generation issues
- Validate layer integration
- Verify compositor calculations

## File Changes Required

1. **src/backtesting/backtest_engine.py**
   - Enhance `_open_position()` to capture signal metadata
   - Store layer breakdown in Trade records

2. **src/backtesting/performance_metrics.py** (NEW)
   - Add `generate_layer_report()`
   - Add `format_trade_analysis()`
   - Add `calculate_layer_performance()`

3. **src/cli/backtest_runner.py**
   - Add `--layer-analysis` flag
   - Generate enhanced reports

4. **src/cli/paper_runner.py**
   - Apply same enhancements
   - Real-time layer monitoring

5. **src/cli/live_runner.py**
   - Apply same enhancements
   - Live layer dashboard

## Testing Strategy

1. Run backtest with layer reporting
2. Verify all 6 layers captured correctly
3. Validate contribution calculations
4. Test report generation
5. Verify CSV export
6. Integration test with optimizer

## Success Criteria

✅ Every trade records all layer contributions
✅ Reports include layer-by-layer breakdown
✅ Performance analysis by layer available
✅ Helps identify optimization opportunities
✅ Works in backtest, paper, and live trading
✅ Human-readable and machine-parsable formats

## Timeline

- Phase 1: 2 hours
- Phase 2: 2 hours  
- Phase 3: 2 hours
- Phase 4: 3 hours
**Total: ~9 hours**

## Priority: HIGH

This enhancement is critical for:
- Understanding trade decisions
- Optimizing layer weights
- Validating system performance
- Production monitoring

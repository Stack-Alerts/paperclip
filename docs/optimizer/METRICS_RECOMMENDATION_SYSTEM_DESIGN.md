# Metrics Recommendation System - Design Specification

**Status:** Design Phase  
**Sprint:** 1.5 - Testing & Polish (Enhanced)  
**Priority:** High  
**Complexity:** High (Multi-System Integration)

---

## Overview

Institutional-grade metrics analysis with **actionable recommendations** that can be automatically applied to:
- Strategy Builder parameters
- Backtest configuration
- Entry/exit logic

Includes **version control** for A/B comparison of configurations before/after applying recommendations.

---

## UI Layout Change

### Current: Side-by-Side
```
┌──────────────────────────────────────────────┐
│  Performance Metrics  │   Risk Metrics       │
│  (14 metrics)         │   (12 metrics)       │
└──────────────────────────────────────────────┘
```

### New: Stacked with Checkboxes
```
┌────────────────────────────────────────────────────────────────────┐
│  📊 Performance Metrics                                            │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ ☐ Metric | Value | Rating | Recommendation                   │ │
│  │ ☐ Metric | Value | Rating | Recommendation                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ⚠️ Risk Metrics                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ ☐ Metric | Value | Status | Recommendation                   │ │
│  │ ☐ Metric | Value | Status | Recommendation                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  [Select All] [Clear All]  [Apply Selected Recommendations]       │
└────────────────────────────────────────────────────────────────────┘
```

---

## Core Features

### 1. Actionable Recommendations

Each metric generates specific, actionable advice:

**Performance Examples:**
```python
{
  'metric': 'sharpe_ratio',
  'value': 0.8,
  'rating': '✗ Poor',
  'recommendation': 'Reduce position size by 30% OR tighten entry filters',
  'actions': [
    {'type': 'config', 'param': 'position_size_pct', 'current': 2.0, 'recommended': 1.4},
    {'type': 'strategy', 'param': 'entry_confirmation', 'current': 1, 'recommended': 2}
  ]
}
```

**Risk Examples:**
```python
{
  'metric': 'max_drawdown_pct',
  'value': 18.5,
  'status': '⚠ Monitor',
  'recommendation': 'Approaching limit - Reduce leverage OR tighten stop loss',
  'actions': [
    {'type': 'config', 'param': 'leverage', 'current': 1.0, 'recommended': 0.75},
    {'type': 'config', 'param': 'stop_loss_pct', 'current': 2.0, 'recommended': 1.5}
  ]
}
```

### 2. Checkbox Selection System

```python
class MetricRow:
    checkbox: QCheckBox  # Select this recommendation
    metric_name: str
    current_value: float
    rating: str
    recommendation_text: str
    actions: List[Dict]  # What will change if applied
    
def on_recommendation_selected(self, row: int, checked: bool):
    """Track which recommendations user wants to apply"""
    self.selected_recommendations.append(row) if checked else \
        self.selected_recommendations.remove(row)
```

### 3. Apply Recommendations Logic

```python
def apply_selected_recommendations(self):
    """
    Apply all checked recommendations:
    1. Create configuration snapshot (version control)
    2. Update Strategy Builder parameters
    3. Update Backtest Configuration
    4. Save snapshot with metadata
    5. Enable comparison view
    """
    # Step 1: Version Control
    snapshot_id = self._create_config_snapshot()
    
    # Step 2: Collect all actions
    all_actions = []
    for row in self.selected_recommendations:
        all_actions.extend(self.recommendations[row]['actions'])
    
    # Step 3: Group by target
    config_updates = [a for a in all_actions if a['type'] == 'config']
    strategy_updates = [a for a in all_actions if a['type'] == 'strategy']
    
    # Step 4: Apply updates
    self._apply_backtest_config_updates(config_updates)
    self._apply_strategy_builder_updates(strategy_updates)
    
    # Step 5: Run new backtest
    self._trigger_backtest_with_new_config()
```

---

## Database Schema for Version Control

### Table: `configuration_snapshots`
```sql
CREATE TABLE configuration_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    snapshot_type TEXT,  -- 'before_recommendation' | 'after_recommendation'
    parent_snapshot_id INTEGER,  -- Link to 'before' snapshot
    
    -- Backtest Configuration
    starting_capital REAL,
    position_size_pct REAL,
    stop_loss_pct REAL,
    take_profit_pct REAL,
    leverage REAL,
    commission_pct REAL,
    
    -- Strategy Parameters (JSON)
    strategy_params TEXT,  -- Serialized strategy configuration
    
    -- Recommendations Applied (JSON)
    applied_recommendations TEXT,  -- Which recommendations were applied
    
    -- Metrics Results (JSON)
    metrics_before TEXT,  -- Before applying recommendations
    metrics_after TEXT,   -- After applying recommendations
    
    -- Metadata
    notes TEXT,
    created_by TEXT DEFAULT 'metrics_recommendation_system'
);
```

### Table: `recommendation_actions`
```sql
CREATE TABLE recommendation_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER,
    metric_name TEXT,
    rating TEXT,
    recommendation_text TEXT,
    action_type TEXT,  -- 'config' | 'strategy'
    parameter_name TEXT,
    value_before TEXT,
    value_after TEXT,
    applied_at DATETIME,
    FOREIGN KEY (snapshot_id) REFERENCES configuration_snapshots(id)
);
```

---

## Recommendation Logic

### Performance Metrics Recommendations

```python
PERFORMANCE_RECOMMENDATIONS = {
    'sharpe_ratio': {
        'poor': {
            'recommendation': 'Reduce volatility: Lower position size OR tighten entry filters',
            'actions': [
                {'type': 'config', 'param': 'position_size_pct', 'adjust': -30},  # -30%
                {'type': 'strategy', 'param': 'min_signal_strength', 'adjust': +0.2}
            ]
        },
        'fair': {
            'recommendation': 'Optimize risk/reward: Adjust TP targets OR add confirmations',
            'actions': [
                {'type': 'config', 'param': 'take_profit_pct', 'adjust': +15},  # +15%
                {'type': 'strategy', 'param': 'require_confirmation', 'adjust': True}
            ]
        }
    },
    
    'win_rate': {
        'poor': {
            'recommendation': 'Improve selectivity: Add filters OR increase signal threshold',
            'actions': [
                {'type': 'strategy', 'param': 'min_signal_strength', 'adjust': +0.3},
                {'type': 'strategy', 'param': 'max_trades_per_day', 'adjust': -2}
            ]
        }
    },
    
    'profit_factor': {
        'poor': {
            'recommendation': 'Improve asymmetry: Widen TP OR tighten SL',
            'actions': [
                {'type': 'config', 'param': 'take_profit_pct', 'adjust': +20},
                {'type': 'config', 'param': 'stop_loss_pct', 'adjust': -10}
            ]
        }
    },
    
    'total_trades': {
        'poor': {
            'recommendation': 'Increase sample size: Extend backtest period OR lower filters',
            'actions': [
                {'type': 'config', 'param': 'backtest_days', 'adjust': +30},
                {'type': 'strategy', 'param': 'min_signal_strength', 'adjust': -0.1}
            ]
        }
    }
}
```

### Risk Metrics Recommendations

```python
RISK_RECOMMENDATIONS = {
    'max_drawdown_pct': {
        'monitor': {
            'recommendation': 'Approaching limit: Reduce position size by 25%',
            'actions': [
                {'type': 'config', 'param': 'position_size_pct', 'adjust': -25}
            ]
        },
        'high': {
            'recommendation': 'CRITICAL: Reduce position size by 50% AND tighten SL',
            'actions': [
                {'type': 'config', 'param': 'position_size_pct', 'adjust': -50},
                {'type': 'config', 'param': 'stop_loss_pct', 'adjust': -25}
            ]
        }
    },
    
    'max_consecutive_losses': {
        'monitor': {
            'recommendation': 'Add circuit breaker: Max 3 losses per day',
            'actions': [
                {'type': 'strategy', 'param': 'max_consecutive_losses', 'current': None, 'recommended': 3}
            ]
        },
        'high': {
            'recommendation': 'STOP TRADING: Add cool-down period after 3 losses',
            'actions': [
                {'type': 'strategy', 'param': 'cool_down_after_losses', 'current': 0, 'recommended': 3},
                {'type': 'strategy', 'param': 'cool_down_minutes', 'current': 0, 'recommended': 60}
            ]
        }
    }
}
```

---

## Integration Points

### 1. Strategy Builder Integration

```python
class StrategyBuilderConnector:
    """Interface to update Strategy Builder parameters"""
    
    def update_parameter(self, param_name: str, new_value):
        """Update single parameter in Strategy Builder"""
        strategy_config = load_current_strategy()
        strategy_config[param_name] = new_value
        save_strategy_config(strategy_config)
        
    def batch_update_parameters(self, updates: List[Dict]):
        """Update multiple parameters atomically"""
        strategy_config = load_current_strategy()
        for update in updates:
            strategy_config[update['param']] = update['value']
        save_strategy_config(strategy_config)
```

### 2. Backtest Configuration Integration

```python
class BacktestConfigConnector:
    """Interface to update Backtest Configuration Panel"""
    
    def update_config(self, param_name: str, new_value):
        """Update backtest configuration parameter"""
        config = load_backtest_config()
        config[param_name] = new_value
        save_backtest_config(config)
        
        # Update UI
        self.config_panel.update_parameter_display(param_name, new_value)
```

### 3. Version Control System

```python
class ConfigurationVersionControl:
    """Manage configuration snapshots for A/B comparison"""
    
    def create_snapshot(self, snapshot_type: str, parent_id: int = None) -> int:
        """Create configuration snapshot"""
        snapshot = {
            'snapshot_type': snapshot_type,
            'parent_snapshot_id': parent_id,
            'starting_capital': self.config.starting_capital,
            'position_size_pct': self.config.position_size_pct,
            'stop_loss_pct': self.config.stop_loss_pct,
            'take_profit_pct': self.config.take_profit_pct,
            'strategy_params': json.dumps(self.strategy.get_params()),
            'metrics_before': json.dumps(self.current_metrics) if snapshot_type == 'before_recommendation' else None
        }
        return db.insert('configuration_snapshots', snapshot)
    
    def load_snapshot(self, snapshot_id: int) -> Dict:
        """Load configuration from snapshot"""
        return db.query('SELECT * FROM configuration_snapshots WHERE id = ?', (snapshot_id,))
    
    def compare_snapshots(self, snapshot_id_1: int, snapshot_id_2: int) -> Dict:
        """Generate comparison between two snapshots"""
        snap1 = self.load_snapshot(snapshot_id_1)
        snap2 = self.load_snapshot(snapshot_id_2)
        
        return {
            'config_changes': self._diff_configs(snap1, snap2),
            'metrics_changes': self._diff_metrics(snap1['metrics_after'], snap2['metrics_after']),
            'improvement_summary': self._calculate_improvement(snap1, snap2)
        }
```

---

## Comparison View

### Split Table: Before vs After

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 Configuration Comparison                                    │
│                                                                 │
│  Snapshot: #42 (2026-01-22 09:00)  vs  #43 (2026-01-22 09:30) │
│  Type: Before Recommendations      vs  After Recommendations   │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Parameter          │ Before    │ After     │ Change       │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ Position Size %    │ 2.0%      │ 1.4%      │ ▼ -30%       │ │
│  │ Stop Loss %        │ 2.0%      │ 1.5%      │ ▼ -25%       │ │
│  │ Take Profit %      │ 3.0%      │ 3.6%      │ ▲ +20%       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Metric             │ Before    │ After     │ Change       │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ Sharpe Ratio       │ 0.8       │ 1.6       │ ▲ +100%      │ │
│  │ Max Drawdown %     │ 18.5%     │ 12.3%     │ ▼ -34%       │ │
│  │ Win Rate           │ 52%       │ 61%       │ ▲ +17%       │ │
│  │ Profit Factor      │ 1.4       │ 2.1       │ ▲ +50%       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  [Revert to #42] [Keep #43] [Export Comparison]                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: UI Restructure (2-3 hours)
- [ ] Change layout from side-by-side to stacked
- [ ] Add checkbox column to both tables
- [ ] Add "Select All", "Clear All", "Apply Selected" buttons
- [ ] Test new layout

### Phase 2: Recommendation Logic (4-5 hours)
- [ ] Implement `_get_performance_recommendation()` method
- [ ] Implement `_get_risk_recommendation()` method
- [ ] Define action mappings for each metric
- [ ] Add recommendation text to tables

### Phase 3: Database (2-3 hours)
- [ ] Create `configuration_snapshots` table
- [ ] Create `recommendation_actions` table
- [ ] Implement version control methods
- [ ] Test snapshot creation/loading

### Phase 4: Integration (5-6 hours)
- [ ] Strategy Builder connector
- [ ] Backtest Config connector  
- [ ] Apply recommendations logic
- [ ] Test end-to-end workflow

### Phase 5: Comparison View (3-4 hours)
- [ ] Design comparison UI
- [ ] Implement snapshot diff logic
- [ ] Add improvement calculations
- [ ] Test A/B comparison

### Phase 6: Polish & Testing (2-3 hours)
- [ ] Error handling
- [ ] User confirmations
- [ ] Tooltips for new features
- [ ] Integration testing

**Total Estimated Time:** 18-24 hours

---

## Success Criteria

✅ User can view actionable recommendations for each metric  
✅ User can select multiple recommendations via checkboxes  
✅ System creates configuration snapshot before applying changes  
✅ System updates Strategy Builder parameters automatically  
✅ System updates Backtest Configuration automatically  
✅ System runs new backtest with updated configuration  
✅ User can compare before/after metrics side-by-side  
✅ User can revert to previous configuration  
✅ All changes are versioned and traceable

---

## Risk Mitigation

**Risk:** Applying wrong recommendations causes worse performance  
**Mitigation:** Always create snapshot before applying, easy revert

**Risk:** User applies conflicting recommendations  
**Mitigation:** Validate action compatibility before applying

**Risk:** Database corruption loses snapshots  
**Mitigation:** Export/backup functionality, JSON storage alongside DB

**Risk:** Integration breaks Strategy Builder  
**Mitigation:** Atomic updates, validation before save, rollback on error

---

## Future Enhancements

1. **Machine Learning Recommendations** - Use historical data to suggest optimal parameters
2. **Multi-Metric Optimization** - Recommend changes that optimize multiple metrics simultaneously
3. **Walk-Forward Validation** - Test recommendations on out-of-sample data before applying
4. **Portfolio-Level Recommendations** - Optimize across multiple strategies
5. **Risk Alerts** - Real-time monitoring with automatic recommendations during live trading

---

**READY FOR IMPLEMENTATION**

This design provides a complete roadmap for implementation.  
Proceed to Sprint 1.5 Task: "Implement Metrics Recommendation System"

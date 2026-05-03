# Metrics Recommendation System V2 - Design Specification
**With ML Integration & Starting Capital Implementation**

**Status:** Design Phase - Ready for Implementation  
**Sprint:** 1.5+ (Enhanced) - Prerequisites + Recommendation System  
**Priority:** High  
**Complexity:** High (Multi-System Integration + ML Pipeline)

---

## 🚨 CRITICAL PREREQUISITES

### **1. Starting Capital Implementation (MISSING - MUST IMPLEMENT FIRST)**

**Source:** Sprint 1.1 Task 1.1.6 - Backtest Configuration Panel  
**Status:** ❌ **NOT IMPLEMENTED** - Zero matches in codebase  
**Impact:** Metrics calculations, position sizing, ML training ALL depend on this

**Implementation Required:**
```python
# Location: src/strategy_builder/ui/backtest_config_panel.py

from nautilus_trader.model.objects import Money
from src.strategy_builder.ui.styles import (
    get_groupbox_header_stylesheet,
    get_input_field_stylesheet,
    SPACING_UNIT,
    create_font
)

class BacktestConfigPanel(QWidget):
    """Backtest Configuration Panel with Starting Capital"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.starting_capital = Money('10000', 'USD')  # Default
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI with Starting Capital section"""
        
        # Starting Capital Group (REQUIRED BY SPRINT 1.1)
        capital_group = QGroupBox("💰 Starting Capital")
        capital_group.setStyleSheet(get_groupbox_header_stylesheet())
        
        capital_layout = QHBoxLayout()
        capital_layout.setSpacing(SPACING_UNIT)
        
        # Input field
        self.capital_input = QLineEdit()
        self.capital_input.setStyleSheet(get_input_field_stylesheet())
        self.capital_input.setFont(create_font())
        self.capital_input.setText(str(self.starting_capital.as_decimal()))
        self.capital_input.setPlaceholderText("10000")
        self.capital_input.textChanged.connect(self._on_capital_changed)
        
        # Validation label
        self.capital_validation = QLabel("✓ Valid")
        self.capital_validation.setStyleSheet(get_label_style('success'))
        
        capital_layout.addWidget(QLabel("Amount (USD):"))
        capital_layout.addWidget(self.capital_input)
        capital_layout.addWidget(self.capital_validation)
        
        capital_group.setLayout(capital_layout)
        
        # Add to main Risk/Reward section
        self.risk_reward_layout.addWidget(capital_group)
    
    def _on_capital_changed(self, text: str):
        """Validate and update starting capital"""
        try:
            # Validate using NautilusTrader Money type
            capital = Money(text, 'USD')
            
            # Validate range (futures trading with leverage)
            MIN_CAPITAL = Money('500', 'USD')  # $500 minimum (futures with leverage)
            MAX_CAPITAL = Money('1000000', 'USD')  # $1M maximum
            
            if capital < MIN_CAPITAL:
                raise ValueError(f"Starting capital must be >= {MIN_CAPITAL.to_string()}")
            if capital > MAX_CAPITAL:
                raise ValueError(f"Starting capital must be <= {MAX_CAPITAL.to_string()}")
            
            # Update internal state
            self.starting_capital = capital
            
            # Show success
            self.capital_input.setStyleSheet(get_input_field_stylesheet())
            self.capital_validation.setText("✓ Valid")
            self.capital_validation.setStyleSheet(get_label_style('success'))
            
            # Emit signal for other components
            self.capital_changed.emit(capital)
            
        except (ValueError, DecimalException) as e:
            # Show error
            self.capital_input.setStyleSheet(get_input_field_stylesheet(error=True))
            self.capital_validation.setText(f"✗ {str(e)}")
            self.capital_validation.setStyleSheet(get_label_style('error'))
    
    def get_starting_capital(self) -> Money:
        """Get current starting capital (NautilusTrader type)"""
        return self.starting_capital
    
    def set_starting_capital(self, amount: str):
        """Set starting capital amount"""
        self.capital_input.setText(amount)
```

**Integration Points:**
1. **Backtest Configuration** - Already in backtest_config_panel.py ✅
2. **Optimizer Config** - Pass to all optimization runs
3. **Metrics Calculations** - Use for return %, drawdown %, etc.
4. **ML Training** - Critical feature for strategy scoring
5. **Recommendation System** - Adjust position sizing recommendations

**Testing:**
```python
def test_starting_capital():
    """Test starting capital implementation"""
    panel = BacktestConfigPanel()
    
    # Test valid amounts
    panel.set_starting_capital('20000')
    assert panel.get_starting_capital() == Money('20000', 'USD')
    
    # Test minimum boundary (futures trading)
    with pytest.raises(ValueError, match="must be >= 500"):
        panel.set_starting_capital('100')
    
    # Test maximum boundary  
    with pytest.raises(ValueError, match="must be <= 1000000"):
        panel.set_starting_capital('2000000')
    
    # Test invalid input
    with pytest.raises(ValueError):
        panel.set_starting_capital('invalid')
```

**MUST BE COMPLETED BEFORE** Metrics Recommendation System (depends on this value).

---

## Overview

Institutional-grade metrics analysis with:
- **Actionable recommendations** that auto-apply to Strategy Builder & Backtest Config
- **Version control** for A/B comparison before/after
- **ML integration** for intelligent recommendation generation (Phase 2)
- **Starting Capital** integration for accurate calculations

---

## ML Integration (Phase 2 - Sprint 2.3)

### **ML-Powered Recommendation Engine**

Based on Sprint 2.3 ML Strategy Generator, extend recommendations with ML:

```python
class MLRecommendationEngine:
    """ML-powered recommendation generation"""
    
    def __init__(self):
        self.xgboost_model = None  # Trained XGBoost model
        self.signal_database = None  # Historical signal data
        self.strategy_scorer = NautilusStrategyScorer()
    
    def train_recommendation_model(self, historical_results: List[Dict]):
        """
        Train XGBoost model to predict optimal parameters
        
        Features:
        - Current metrics (Sharpe, DD%, Win Rate, etc.)
        - Strategy configuration (signals, parameters)
        - Market conditions (volatility, trend)
        
        Target:
        - Optimal parameter changes
        - Expected improvement %
        """
        import xgboost as xgb
        
        # Prepare training data
        X = []  # Features: current metrics + config
        y = []  # Target: optimal parameter deltas
        
        for result in historical_results:
            features = self._extract_features(result)
            optimal_params = result['optimal_params']
            param_deltas = self._calculate_deltas(result['original_params'], 
                                                  optimal_params)
            X.append(features)
            y.append(param_deltas)
        
        # Train XGBoost
        dtrain = xgb.DMatrix(X, label=y)
        params = {
            'max_depth': 6,
            'eta': 0.3,
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse'
        }
        
        self.xgboost_model = xgb.train(params, dtrain, num_boost_round=100)
    
    def generate_ml_recommendations(self, current_metrics: Dict, 
                                   current_config: Dict) -> List[Dict]:
        """
        Generate recommendations using ML model
        
        Returns:
        - Top 5 parameter changes ranked by expected improvement
        - Confidence scores for each recommendation
        - Expected metric improvements
        """
        if not self.xgboost_model:
            return self._fallback_rule_based_recommendations(current_metrics)
        
        # Extract features
        features = self._extract_features({
            'metrics': current_metrics,
            'config': current_config
        })
        
        # Predict optimal parameter changes
        dtest = xgb.DMatrix([features])
        predicted_deltas = self.xgboost_model.predict(dtest)[0]
        
        # Convert to actionable recommendations
        recommendations = []
        for param, delta in zip(self.param_names, predicted_deltas):
            if abs(delta) > self.significance_threshold:
                rec = self._create_recommendation(
                    param=param,
                    current_value=current_config[param],
                    recommended_delta=delta,
                    expected_improvement=self._estimate_improvement(delta)
                )
                recommendations.append(rec)
        
        # Rank by expected improvement
        recommendations.sort(key=lambda x: x['expected_improvement'], reverse=True)
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _extract_features(self, result: Dict) -> np.ndarray:
        """Extract ML features from metrics and config"""
        features = []
        
        # Metric features
        metrics = result['metrics']
        features.extend([
            float(metrics['sharpe_ratio']),
            float(metrics['win_rate']),
            float(metrics['profit_factor']),
            float(metrics['max_drawdown_pct']),
            float(metrics['avg_trade_pnl']),
            float(metrics['total_trades'])
        ])
        
        # Config features
        config = result['config']
        features.extend([
            float(config['position_size_pct']),
            float(config['stop_loss_pct']),
            float(config['take_profit_pct']),
            float(config['starting_capital'].as_decimal())
        ])
        
        # Market condition features (from Signal Intelligence)
        if 'market_conditions' in result:
            mc = result['market_conditions']
            features.extend([
                float(mc['volatility']),
                float(mc['trend_strength']),
                int(mc['session_type'])
            ])
        
        return np.array(features)
    
    def _estimate_improvement(self, param_delta: float) -> float:
        """Estimate expected improvement from parameter change"""
        # Use historical data to estimate impact
        # Return expected Sharpe ratio improvement
        return abs(param_delta) * 0.1  # Simplified
```

### **ML Dataset from Signal Intelligence (Sprint 2.2)**

```python
class MLDatasetBuilder:
    """Build ML training dataset from Signal Intelligence events"""
    
    def build_dataset_from_signals(self) -> pd.DataFrame:
        """
        Query signal_events table (from Sprint 2.2) to build ML dataset
        
        Returns DataFrame with:
        - Features: signal combinations, parameters, market conditions
        - Target: actual performance metrics
        """
        query = """
        SELECT 
            se.signal_name,
            se.timeframe,
            se.weight,
            se.parameters,
            sm.win_rate,
            sm.avg_pnl,
            sm.max_drawdown,
            sm.sharpe_ratio,
            bc.starting_capital,
            bc.position_size_pct,
            bc.stop_loss_pct,
            bc.take_profit_pct
        FROM signal_events se
        JOIN signal_metrics sm ON se.event_id = sm.event_id
        JOIN backtest_configs bc ON se.backtest_run_id = bc.run_id
        WHERE se.was_triggered = true
        AND sm.win_rate >= 0.4
        AND sm.weight >= 50
        """
        
        df = pd.read_sql(query, self.db_connection)
        
        # Feature engineering
        df['signal_combination'] = df.groupby('backtest_run_id')['signal_name'].transform(
            lambda x: '+'.join(sorted(x))
        )
        
        # Target: Strategy score (0-100)
        df['strategy_score'] = self._calculate_strategy_scores(df)
        
        return df
    
    def _calculate_strategy_scores(self, df: pd.DataFrame) -> pd.Series:
        """Calculate strategy scores for ML training"""
        scorer = NautilusStrategyScorer(criteria={
            'min_sharpe': 1.5,
            'max_drawdown_pct': 15.0,
            'min_win_rate': 0.55
        })
        
        scores = []
        for _, row in df.iterrows():
            score = scorer.score_strategy({
                'sharpe_ratio': row['sharpe_ratio'],
                'win_rate': row['win_rate'],
                'max_drawdown': row['max_drawdown'],
                'avg_pnl': row['avg_pnl']
            })
            scores.append(score['total_score'])
        
        return pd.Series(scores)
```

### **Integration with Existing Recommendation System**

```python
class HybridRecommendationEngine:
    """Combines rule-based + ML recommendations"""
    
    def __init__(self):
        self.ml_engine = MLRecommendationEngine()
        self.rule_engine = RuleBasedRecommendationEngine()
        self.ml_enabled = False  # Enable after Sprint 2.3
    
    def generate_recommendations(self, metrics: Dict, config: Dict) -> List[Dict]:
        """Generate hybrid recommendations"""
        
        # Rule-based recommendations (always available)
        rule_recs = self.rule_engine.generate(metrics, config)
        
        # ML recommendations (Phase 2 - Sprint 2.3)
        if self.ml_enabled and self.ml_engine.xgboost_model:
            ml_recs = self.ml_engine.generate_ml_recommendations(metrics, config)
            
            # Merge and deduplicate
            merged = self._merge_recommendations(rule_recs, ml_recs)
            
            # Add ML confidence scores
            for rec in merged:
                if rec['source'] == 'ml':
                    rec['confidence'] = self._calculate_ml_confidence(rec)
            
            return merged
        else:
            # Fallback to rule-based only
            return rule_recs
    
    def _merge_recommendations(self, rule_recs: List[Dict], 
                               ml_recs: List[Dict]) -> List[Dict]:
        """Merge recommendations intelligently"""
        merged = {}
        
        # Add rule-based
        for rec in rule_recs:
            key = rec['parameter']
            merged[key] = {
                **rec,
                'source': 'rule',
                'confidence': 0.7  # Rule-based baseline
            }
        
        # Add/override with ML
        for rec in ml_recs:
            key = rec['parameter']
            if key in merged:
                # ML overrides if higher confidence
                if rec['confidence'] > merged[key]['confidence']:
                    merged[key] = {
                        **rec,
                        'source': 'ml',
                        'rule_agreement': True
                    }
            else:
                merged[key] = {
                    **rec,
                    'source': 'ml',
                    'rule_agreement': False
                }
        
        return list(merged.values())
```

---

## UI Layout (Stacked for Full Recommendation Width)

```
┌────────────────────────────────────────────────────────────────────────┐
│  📊 Performance Metrics                                                │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ ☐ | Metric        | Value  | Rating  | Recommendation          │ │
│  │ ☐ | Total P&L     | $500   | ⚠ Fair  | Increase TP by 20%      │ │
│  │ ☐ | Sharpe Ratio  | 0.8    | ✗ Poor  | Reduce position 30%     │ │
│  │ ☐ | Win Rate      | 48%    | ✗ Poor  | Add entry confirmation  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ⚠️ Risk Metrics                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ ☐ | Metric          | Value  | Status   | Recommendation        │ │
│  │ ☐ | Max Drawdown %  | 18%    | ⚠ Monitor| Reduce leverage 25%   │ │
│  │ ☐ | Consecutive Loss| 6      | ✗ High   | Add circuit breaker   │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  [Select All] [Clear All]  [💡 Apply Selected (3)]  [🔄 Auto-Retest] │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema (Enhanced for ML)

### **configuration_snapshots (Enhanced)**
```sql
CREATE TABLE configuration_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    snapshot_type TEXT,  -- 'before_recommendation' | 'after_recommendation' | 'ml_generated'
    parent_snapshot_id INTEGER,
    
    -- Backtest Configuration (INCLUDES STARTING CAPITAL)
    starting_capital REAL NOT NULL,  -- ⭐ CRITICAL: From backtest config
    position_size_pct REAL,
    stop_loss_pct REAL,
    take_profit_pct REAL,
    leverage REAL,
    commission_pct REAL,
    
    -- Strategy Parameters (JSON)
    strategy_params TEXT,
    
    -- Recommendations Applied (JSON)
    applied_recommendations TEXT,
    recommendation_source TEXT,  -- 'rule_based' | 'ml' | 'hybrid'
    ml_confidence_score REAL,  -- 0-1 if ML-generated
    
    -- Metrics Results (JSON)
    metrics_before TEXT,
    metrics_after TEXT,
    
    -- ML Training Data
    used_for_ml_training BOOLEAN DEFAULT false,
    ml_feature_vector TEXT,  -- JSON array of features
    ml_prediction_accuracy REAL,  -- How accurate was ML prediction?
    
    -- Metadata
    notes TEXT,
    created_by TEXT DEFAULT 'metrics_recommendation_system'
);

CREATE INDEX idx_ml_training ON configuration_snapshots(used_for_ml_training);
CREATE INDEX idx_recommendation_source ON configuration_snapshots(recommendation_source);
```

### **ml_training_dataset**
```sql
CREATE TABLE ml_training_dataset (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER,
    
    -- Features
    feature_vector TEXT,  -- JSON array
    feature_names TEXT,  -- JSON array of feature names
    
    -- Target
    target_metric TEXT,  -- 'sharpe_ratio' | 'win_rate' | 'profit_factor'
    target_value REAL,
    
    -- Performance
    actual_improvement REAL,  -- Actual improvement achieved
    predicted_improvement REAL,  -- ML predicted improvement
    prediction_error REAL,  -- |actual - predicted|
    
    -- Metadata
    training_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    model_version TEXT,
    
    FOREIGN KEY (snapshot_id) REFERENCES configuration_snapshots(id)
);
```

---

## Implementation Phases (Updated)

### **Phase 0: Prerequisites (CRITICAL - 2-3 hours)**
- [ ] Task 0.1: Implement Starting Capital in backtest_config_panel.py
- [ ] Task 0.2: Add capital_changed signal
- [ ] Task 0.3: Update optimizer to receive starting_capital
- [ ] Task 0.4: Update all metric calculations to use starting_capital
- [ ] Task 0.5: Test Starting Capital across all features
- [ ] **Sign-off**: ☐ Developer ☐ Lead

### **Phase 1: Core Recommendation System (4-5 hours)**
- [ ] Task 1.1: Restructure Metrics UI (stacked layout)
- [ ] Task 1.2: Add checkbox column
- [ ] Task 1.3: Add control buttons
- [ ] Task 1.4: Implement rule-based recommendation logic
- [ ] Task 1.5: Test recommendation generation
- [ ] **Sign-off**: ☐ Developer ☐ Lead

### **Phase 2: Database & Version Control (3-4 hours)**
- [ ] Task 2.1: Create configuration_snapshots table
- [ ] Task 2.2: Create recommendation_actions table
- [ ] Task 2.3: Implement snapshot creation/loading
- [ ] Task 2.4: Test version control flow
- [ ] **Sign-off**: ☐ Developer ☐ Lead

### **Phase 3: Integration (5-6 hours)**
- [ ] Task 3.1: Strategy Builder connector
- [ ] Task 3.2: Backtest Config connector
- [ ] Task 3.3: Apply recommendations logic
- [ ] Task 3.4: Auto-retest after applying
- [ ] Task 3.5: Test end-to-end workflow
- [ ] **Sign-off**: ☐ Developer ☐ Lead

### **Phase 4: Comparison View (3-4 hours)**
- [ ] Task 4.1: Design comparison UI
- [ ] Task 4.2: Implement snapshot diff
- [ ] Task 4.3: Calculate improvements
- [ ] Task 4.4: Test A/B comparison
- [ ] **Sign-off**: ☐ Developer ☐ Lead

### **Phase 5: ML Integration (REQUIRES PHASE 2 COMPLETE)**
**⚠️ DEPENDENCY: Sprint 2.1, 2.2, 2.3, 2.4 MUST BE COMPLETE**

**Prerequisites:**
- Sprint 2.1: Automated Trainer ✅ (provides training infrastructure)
- Sprint 2.2: Signal Intelligence ✅ (provides signal_events table)
- Sprint 2.3: ML Generator ✅ (provides XGBoost framework)
- Sprint 2.4: Integration ✅ (validates Phase 2 systems)

**Duration:** 8-10 hours  
**Cannot Start Until:** All Phase 2 sprints signed off

**Tasks:**
- [ ] Task 5.1: Build ML dataset from Signal Intelligence (Sprint 2.2 data)
- [ ] Task 5.2: Train XGBoost recommendation model (Sprint 2.3 framework)
- [ ] Task 5.3: Implement ML recommendation engine
- [ ] Task 5.4: Integrate with hybrid system
- [ ] Task 5.5: Test ML vs rule-based accuracy
- [ ] Task 5.6: Validate ML confidence scores
- [ ] **Sign-off**: ☐ Developer ☐ Lead ☐ ML Engineer

### **Phase 6: Polish & Testing (2-3 hours)**
- [ ] Task 6.1: Error handling
- [ ] Task 6.2: User confirmations
- [ ] Task 6.3: Tooltips
- [ ] Task 6.4: Integration testing
- [ ] **Sign-off**: ☐ Developer ☐ Lead

**Total Estimated Time:** 
- **Phase 0-4:** 19-26 hours (can start immediately)
- **Phase 5:** 8-10 hours (⚠️ REQUIRES PHASE 2 COMPLETE)
- **Total:** 27-36 hours

---

## Success Criteria

✅ **Phase 0 (Prerequisites):**
- Starting Capital implemented in Backtest Config
- All metrics use starting_capital for calculations
- Properly integrated across system

✅ **Phase 1-4 (Core System):**
- User can view actionable recommendations
- User can select multiple recommendations
- System creates snapshots before applying
- System updates Strategy Builder & Backtest Config
- System runs new backtest automatically
- User can compare before/after metrics
- User can revert to previous configuration

✅ **Phase 5 (ML Integration - ⚠️ REQUIRES PHASE 2 COMPLETE):**
- **Dependency:** Sprints 2.1, 2.2, 2.3, 2.4 must be complete
- ML model trained on Signal Intelligence data (from Sprint 2.2)
- XGBoost framework (from Sprint 2.3) integrated
- ML recommendations generated with confidence scores
- Hybrid system (rule + ML) operational
- ML accuracy tracked and improving
- Dataset continuously updated from new backtests

---

## Future Enhancements (Aligned with Phase 2 Sprints)

1. **ML Strategy Generator Integration (Sprint 2.3)** ✅ DESIGNED ABOVE
   - XGBoost for parameter optimization
   - Signal filtering (weight ≥50, win rate ≥0.4)
   - Strategy scoring with NautilusTrader types
   - Automated parameter search

2. **Walk-Forward Validation (Sprint 2.4)**
   - Test recommendations on out-of-sample data
   - Validate ML predictions before applying
   - Track real-world vs predicted improvements

3. **Signal Intelligence Integration (Sprint 2.2)**
   - Use signal_events table for ML training
   - Track which signals correlate with improvements
   - Recommend signal additions/removals

4. **Automated Trainer Integration (Sprint 2.1)**
   - Auto-generate recommendations after training runs
   - Compare trained vs untrained performance
   - Suggest optimal training windows

5. **Portfolio-Level Optimization (Phase 3)**
   - Optimize across multiple strategies
   - Balance risk across portfolio
   - Correlation-aware recommendations

---

**READY FOR IMPLEMENTATION**

**CRITICAL PATH:**

**Immediate Implementation (No Dependencies):**
1. **Phase 0:** Implement Starting Capital (2-3 hours)
2. **Phases 1-4:** Core Recommendation System (15-19 hours)
   - Rule-based recommendations
   - Version control
   - Auto-apply functionality
   - A/B comparison

**Future Implementation (⚠️ REQUIRES PHASE 2):**
3. **Phase 5:** ML Integration (8-10 hours)
   - **CANNOT START UNTIL:** Sprints 2.1, 2.2, 2.3, 2.4 complete
   - **DEPENDENCY:** Signal Intelligence table + XGBoost framework
   - Adds ML-powered recommendations on top of rule-based system

**Timeline:**
- **Now → Phase 1 Complete:** Phases 0-4 (fully functional system)
- **After Phase 2 Complete:** Phase 5 (ML enhancement)

This design is complete, ML-ready, and clearly sequenced with Phase 2 dependencies.

# OPTIMIZER V3 - AUTOMATED TRAINING SYSTEM
**Forward-Looking Signal Analysis for Optimal Parameter Discovery**

**Date**: 2026-01-19  
**Status**: 🔬 CRITICAL ENHANCEMENT  
**Priority**: P0 - Foundation for learning optimal recheck delays and timing windows

---

## 🔍 CONCEPT: LEARN FROM MARKET BEHAVIOR

### **The Problem**
How do we know the optimal recheck delay or timing window for a signal?

**Current Approach**: Guess and test manually
- User sets recheck delay to 25 bars... why 25? Why not 50 or 65?
- No data-driven justification
- Optimal settings remain unknown

### **The Solution**
**Record what happens in the NEXT 200 candles after signal fires!**

**Example** (from user):
1. HOD rejection fires at candle 0
2. Trade doesn't reach TP
3. Price comes back to HOD at candle 80 and rejects again (successful trade!)
4. Across 100+ tests: price returns at candles 50-70 (median: 65)
5. **Optimal recheck delay = 65 candles** (data-driven!)

---

## 🚀 AUTOMATED TRAINING SYSTEM ARCHITECTURE

### **Core Workflow**

```
1. USER SELECTS TRAINING CONFIGURATION
   ├─ Select specific building blocks (checkboxes)
   │  └─ Example: ☑ HOD, ☑ Stochastic RSI, ☑ Order Block
   ├─ Choose training period
   │  ├─ Testing Mode: 7, 14, or 30 days (fast validation)
   │  └─ Production Mode: 90, 180, or 365 days (full training)
   ├─ Select timeframes (5m, 15m, 1h, 4h)
   └─ Click "Start Training"

2. SYSTEM ESTIMATES RESOURCE REQUIREMENTS
   ├─ Calculate expected duration
   │  └─ Example: "5 blocks × 15m timeframe × 30 days ≈ 12 minutes"
   ├─ Show CPU usage warning
   │  └─ "High CPU utilization expected (80-90%)"
   └─ User confirms or adjusts

3. SYSTEM LOADS HISTORICAL DATA
   ├─ Only selected period (7-365 days)
   ├─ Only selected timeframes
   └─ Only selected building blocks

4. FOR EACH SELECTED BUILDING BLOCK:
   FOR EACH SIGNAL:
     FOR EACH SELECTED TIMEFRAME:
       ├─ Scan through historical data candle by candle
       ├─ Detect when signal fires
       └─ For EVERY signal fire:
          ├─ Record signal context (price, volume, market condition)
          ├─ Analyze NEXT 200 candles (forward-looking)
          │  ├─ When does signal fire again? (recheck pattern)
          │  ├─ When do dependent signals fire? (timing window)
          │  ├─ What is price behavior? (max favorable/adverse)
          │  └─ Does trade reach TP/SL? (outcome)
          └─ Save to training database

5. CALCULATE OPTIMAL PARAMETERS
   ├─ Recheck delays: Median of successful recurrence times
   ├─ Timing windows: Percentiles of dependent signal delays
   └─ Confidence scores based on sample size

6. GENERATE RECOMMENDATIONS
   └─ "HOD_REJECTION: Use 65-candle recheck (85% confidence, 347 samples)"
```

### **Training Modes**

**Testing Mode** (Fast Validation)
- Purpose: Verify system works correctly
- Period: 7-30 days
- Duration: 2-15 minutes per block
- Use case: Development, debugging, quick tests

**Production Mode** (Full Training)
- Purpose: Discover optimal parameters
- Period: 90-365 days
- Duration: 20-60 minutes per block
- Use case: Real strategy optimization

### **Resource Estimates**

| Blocks | Timeframe | Period | Duration | CPU Usage |
|--------|-----------|--------|----------|-----------|
| 1 block | 15m | 7 days | ~2 min | 60-70% |
| 1 block | 15m | 30 days | ~8 min | 70-80% |
| 1 block | 15m | 365 days | ~45 min | 80-90% |
| 5 blocks | 15m | 30 days | ~40 min | 80-90% |
| 5 blocks | 15m | 365 days | ~4 hours | 90-95% |
| All (20+) | All | 365 days | ~24 hours | 95-100% |

---

## 💾 TRAINING DATABASE SCHEMA

```sql
CREATE TABLE signal_training_events (
    event_id UUID PRIMARY KEY,
    block_name TEXT,
    signal_name TEXT,
    timeframe TEXT,
    timestamp TIMESTAMP,
    candle_index INTEGER,
    
    -- Signal Context
    price_at_signal DECIMAL,
    volume_at_signal DECIMAL,
    volatility DECIMAL,
    market_condition TEXT,  -- 'trend', 'range', 'volatile'
    
    -- Forward-Looking Analysis (next 200 candles)
    recurrence_delays INTEGER[],  -- [50, 80, 120] - when signal fired again
    successful_recurrences INTEGER[],  -- [0, 2] - which led to profitable trades
    failed_recurrences INTEGER[],  -- [1] - which led to losses
    
    -- Price Behavior
    max_favorable_move DECIMAL,  -- Largest move in our direction
    max_adverse_move DECIMAL,    -- Largest move against us
    time_to_max_favorable INTEGER,  -- Bars until best price
    time_to_max_adverse INTEGER,    -- Bars until worst price
    
    -- Dependent Signal Analysis
    dependent_signals JSONB,  -- {"RSI_OVERBOUGHT": [15, 25, 40], "DIVERGENCE": [30]}
    optimal_windows JSONB,    -- Calculated optimal timing windows
    
    -- Outcome Analysis
    reached_tp BOOLEAN,
    bars_to_tp INTEGER,
    reached_sl BOOLEAN,
    bars_to_sl INTEGER,
    final_outcome TEXT,  -- 'TP', 'SL', 'timeout', 'none'
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast analysis
CREATE INDEX idx_training_signal ON signal_training_events(signal_name);
CREATE INDEX idx_training_timeframe ON signal_training_events(timeframe);
CREATE INDEX idx_training_outcome ON signal_training_events(final_outcome);
CREATE INDEX idx_training_recurrence ON signal_training_events USING GIN(recurrence_delays);
```

---

## 🧠 IMPLEMENTATION

### **1. AutomatedTrainingSystem Class**

```python
class AutomatedTrainingSystem:
    """Train on all building blocks to learn optimal parameters"""
    
    def __init__(self):
        self.signal_db = SignalDatabase()
        self.lookback_candles = 200  # Analyze next 200 candles
    
    def train_all_blocks(self, data_period: int = 365):
        """Run training on all available building blocks"""
        
        # Get all building blocks from registry
        all_blocks = BuildingBlockRegistry.get_all_blocks()
        
        total_blocks = len(all_blocks)
        for i, block in enumerate(all_blocks):
            print(f"Training block {i+1}/{total_blocks}: {block.name}")
            
            for signal in block.signals:
                # Train at multiple timeframes
                for timeframe in ["5m", "15m", "1h", "4h"]:
                    print(f"  Signal: {signal.name} @ {timeframe}")
                    
                    results = self._train_signal(
                        block_name=block.name,
                        signal_name=signal.name,
                        timeframe=timeframe,
                        period_days=data_period
                    )
                    
                    # Save results to database
                    self.signal_db.save_training_results(results)
                    print(f"    Saved {len(results)} events")
    
    def _train_signal(self, block_name, signal_name, timeframe, period_days):
        """Train on single signal - record forward-looking behavior"""
        
        training_events = []
        
        # Load historical market data
        data = load_market_data(timeframe=timeframe, days=period_days)
        
        print(f"    Scanning {len(data)} candles...")
        
        # Scan through all candles
        for i in range(len(data) - self.lookback_candles):
            candle = data[i]
            
            # Check if signal fires at this candle
            signal_fired = evaluate_signal(
                block_name=block_name,
                signal_name=signal_name,
                candle=candle,
                historical_data=data[:i+1]  # Only past data available
            )
            
            if signal_fired:
                # CRITICAL: Record what happens in next 200 candles
                forward_behavior = self._analyze_forward_behavior(
                    signal_candle=i,
                    signal_name=signal_name,
                    block_name=block_name,
                    data=data,
                    lookback=self.lookback_candles
                )
                
                training_events.append(forward_behavior)
        
        return training_events
    
    def _analyze_forward_behavior(self, signal_candle, signal_name, 
                                  block_name, data, lookback):
        """Analyze what happens in next X candles after signal fires"""
        
        current_candle = data[signal_candle]
        forward_data = data[signal_candle:signal_candle + lookback]
        
        analysis = {
            'signal_candle': signal_candle,
            'block_name': block_name,
            'signal_name': signal_name,
            'timestamp': current_candle['timestamp'],
            'price_at_signal': current_candle['close'],
            'volume_at_signal': current_candle['volume'],
            'volatility': calculate_volatility(data[signal_candle-20:signal_candle]),
            'market_condition': detect_market_condition(data[signal_candle-50:signal_candle]),
            
            # RECHECK ANALYSIS
            'recurrence_delays': [],
            'successful_recurrences': [],
            'failed_recurrences': [],
            
            # PRICE BEHAVIOR
            'max_favorable_move': 0,
            'max_adverse_move': 0,
            'time_to_max_favorable': 0,
            'time_to_max_adverse': 0,
            
            # DEPENDENT SIGNALS
            'dependent_signals': {},
            
            # OUTCOME
            'reached_tp': False,
            'bars_to_tp': None,
            'reached_sl': False,
            'bars_to_sl': None,
            'final_outcome': 'none'
        }
        
        # Analyze recurrence pattern
        analysis.update(self._find_signal_recurrence(
            signal_name, block_name, forward_data, current_candle
        ))
        
        # Analyze price behavior
        analysis.update(self._analyze_price_movement(
            current_candle, forward_data
        ))
        
        # Find dependent signals
        analysis['dependent_signals'] = self._find_dependent_signals(
            signal_name, forward_data
        )
        
        # Check trade outcome
        analysis.update(self._analyze_trade_outcome(
            current_candle, forward_data
        ))
        
        return analysis
    
    def _find_signal_recurrence(self, signal_name, block_name, 
                                forward_data, original_candle):
        """Find when the same signal fires again in next X candles"""
        
        recurrence_delays = []
        successful_recurrences = []
        failed_recurrences = []
        
        for i, candle in enumerate(forward_data[1:], 1):  # Start from candle 1
            # Check if signal fires again
            if evaluate_signal(signal_name, block_name, candle, forward_data[:i+1]):
                recurrence_delays.append(i)
                
                # Check if this recurrence would lead to profitable trade
                trade_success = self._would_trade_succeed(
                    candle, 
                    forward_data[i:]
                )
                
                if trade_success:
                    successful_recurrences.append(len(recurrence_delays) - 1)
                else:
                    failed_recurrences.append(len(recurrence_delays) - 1)
        
        return {
            'recurrence_delays': recurrence_delays,
            'successful_recurrences': successful_recurrences,
            'failed_recurrences': failed_recurrences
        }
    
    def _analyze_price_movement(self, entry_candle, forward_data):
        """Track maximum favorable and adverse price movement"""
        
        entry_price = entry_candle['close']
        direction = entry_candle.get('signal_direction', 'SHORT')  # Default SHORT for HOD rejection
        
        max_favorable = 0
        max_adverse = 0
        time_to_favorable = 0
        time_to_adverse = 0
        
        for i, candle in enumerate(forward_data):
            if direction == 'SHORT':
                # Favorable = price goes down
                move_favorable = entry_price - candle['low']
                move_adverse = candle['high'] - entry_price
            else:
                # Favorable = price goes up
                move_favorable = candle['high'] - entry_price
                move_adverse = entry_price - candle['low']
            
            if move_favorable > max_favorable:
                max_favorable = move_favorable
                time_to_favorable = i
            
            if move_adverse > max_adverse:
                max_adverse = move_adverse
                time_to_adverse = i
        
        return {
            'max_favorable_move': max_favorable,
            'max_adverse_move': max_adverse,
            'time_to_max_favorable': time_to_favorable,
            'time_to_max_adverse': time_to_adverse
        }
    
    def _find_dependent_signals(self, anchor_signal, forward_data):
        """Find when other signals fire after anchor signal"""
        
        dependent_signals = {}
        
        # Get all other signals that could depend on this one
        all_signals = get_all_building_block_signals()
        
        for other_signal in all_signals:
            if other_signal.name == anchor_signal:
                continue
            
            fire_delays = []
            for i, candle in enumerate(forward_data):
                if evaluate_signal(other_signal.name, other_signal.block, 
                                  candle, forward_data[:i+1]):
                    fire_delays.append(i)
            
            if fire_delays:
                dependent_signals[other_signal.name] = fire_delays
        
        return dependent_signals
    
    def _analyze_trade_outcome(self, entry_candle, forward_data):
        """Determine if trade would reach TP or SL"""
        
        entry_price = entry_candle['close']
        direction = entry_candle.get('signal_direction', 'SHORT')
        
        # Typical TP/SL ratios
        tp_pct = 0.02  # 2% TP
        sl_pct = 0.01  # 1% SL
        
        if direction == 'SHORT':
            tp_price = entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 + sl_pct)
        else:
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)
        
        for i, candle in enumerate(forward_data):
            # Check TP
            if direction == 'SHORT' and candle['low'] <= tp_price:
                return {
                    'reached_tp': True,
                    'bars_to_tp': i,
                    'reached_sl': False,
                    'bars_to_sl': None,
                    'final_outcome': 'TP'
                }
            elif direction == 'LONG' and candle['high'] >= tp_price:
                return {
                    'reached_tp': True,
                    'bars_to_tp': i,
                    'reached_sl': False,
                    'bars_to_sl': None,
                    'final_outcome': 'TP'
                }
            
            # Check SL
            if direction == 'SHORT' and candle['high'] >= sl_price:
                return {
                    'reached_tp': False,
                    'bars_to_tp': None,
                    'reached_sl': True,
                    'bars_to_sl': i,
                    'final_outcome': 'SL'
                }
            elif direction == 'LONG' and candle['low'] <= sl_price:
                return {
                    'reached_tp': False,
                    'bars_to_tp': None,
                    'reached_sl': True,
                    'bars_to_sl': i,
                    'final_outcome': 'SL'
                }
        
        # No TP/SL hit in lookback period
        return {
            'reached_tp': False,
            'bars_to_tp': None,
            'reached_sl': False,
            'bars_to_sl': None,
            'final_outcome': 'timeout'
        }
```

---

## 📊 OPTIMAL PARAMETER CALCULATOR

```python
class OptimalParameterCalculator:
    """Calculate optimal recheck delays and timing windows from training data"""
    
    def __init__(self):
        self.signal_db = SignalDatabase()
    
    def calculate_optimal_recheck_delay(self, signal_name: str, 
                                       timeframe: str = "15m") -> dict:
        """
        Calculate optimal recheck delay from training data
        
        Example Output:
        {
            'signal': 'HOD_REJECTION',
            'timeframe': '15m',
            'sample_size': 347,
            'optimal_delay': 65,  # Median
            'min_delay': 50,      # 10th percentile
            'max_delay': 85,      # 90th percentile
            'confidence': 0.85
        }
        """
        
        # Get all training events for this signal
        events = self.signal_db.query("""
            SELECT recurrence_delays, successful_recurrences
            FROM signal_training_events
            WHERE signal_name = %s
            AND timeframe = %s
            AND array_length(recurrence_delays, 1) > 0
        """, (signal_name, timeframe))
        
        if not events:
            return None
        
        # Extract successful recurrence delays only
        successful_delays = []
        for event in events:
            recurrence_delays = event['recurrence_delays']
            successful_indices = event['successful_recurrences']
            
            for idx in successful_indices:
                if idx < len(recurrence_delays):
                    successful_delays.append(recurrence_delays[idx])
        
        if len(successful_delays) < 10:  # Need minimum sample size
            return None
        
        # Statistical analysis
        delays_array = np.array(successful_delays)
        
        return {
            'signal': signal_name,
            'timeframe': timeframe,
            'sample_size': len(successful_delays),
            'optimal_delay': int(np.median(delays_array)),
            'min_delay': int(np.percentile(delays_array, 10)),
            'max_delay': int(np.percentile(delays_array, 90)),
            'mean': float(np.mean(delays_array)),
            'std': float(np.std(delays_array)),
            'confidence': min(1.0, len(successful_delays) / 100)  # 100+ samples = 100% confidence
        }
    
    def calculate_optimal_timing_window(self, anchor_signal: str,
                                       dependent_signal: str,
                                       timeframe: str = "15m") -> dict:
        """
        Calculate optimal timing constraint window
        
        Example Output:
        {
            'anchor_signal': 'HOD_REJECTION',
            'dependent_signal': 'RSI_OVERBOUGHT',
            'timeframe': '15m',
            'sample_size': 234,
            'optimal_window': 20,  # Median
            'tight_window': 10,    # Catches 75% of occurrences
            'loose_window': 35,    # Catches 90% of occurrences
            'recommendation': 20   # Balanced
        }
        """
        
        # Get training events where anchor signal fired
        events = self.signal_db.query("""
            SELECT dependent_signals
            FROM signal_training_events
            WHERE signal_name = %s
            AND timeframe = %s
            AND dependent_signals ? %s
        """, (anchor_signal, timeframe, dependent_signal))
        
        if not events:
            return None
        
        # Extract timing delays
        timing_delays = []
        for event in events:
            if dependent_signal in event['dependent_signals']:
                delays = event['dependent_signals'][dependent_signal]
                timing_delays.extend(delays)
        
        if len(timing_delays) < 10:
            return None
        
        delays_array = np.array(timing_delays)
        
        return {
            'anchor_signal': anchor_signal,
            'dependent_signal': dependent_signal,
            'timeframe': timeframe,
            'sample_size': len(timing_delays),
            'optimal_window': int(np.median(delays_array)),
            'tight_window': int(np.percentile(delays_array, 25)),  # Strict
            'loose_window': int(np.percentile(delays_array, 90)),  # Permissive
            'recommendation': int(np.percentile(delays_array, 75)),  # Balanced (catches 75%)
            'confidence': min(1.0, len(timing_delays) / 100)
        }
    
    def generate_recommendations_report(self) -> dict:
        """Generate comprehensive recommendations for all signals"""
        
        report = {
            'generated_at': datetime.now(),
            'recheck_recommendations': [],
            'timing_recommendations': [],
            'summary': {}
        }
        
        # Get all unique signals from training
        trained_signals = self.signal_db.query("""
            SELECT DISTINCT signal_name, timeframe
            FROM signal_training_events
        """)
        
        for signal in trained_signals:
            # Calculate recheck delay
            recheck = self.calculate_optimal_recheck_delay(
                signal['signal_name'],
                signal['timeframe']
            )
            
            if recheck and recheck['confidence'] >= 0.5:
                report['recheck_recommendations'].append(recheck)
        
        # Get all signal pairs for timing windows
        # (This would query which signals commonly appear together)
        
        report['summary'] = {
            'total_recheck': len(report['recheck_recommendations']),
            'total_timing': len(report['timing_recommendations']),
            'high_confidence': len([
                r for r in report['recheck_recommendations']
                if r['confidence'] >= 0.8
            ])
        }
        
        return report
```

---

## 🎯 TRAINING UI INTEGRATION

```python
class TrainingPanelUI(QWidget):
    """UI for automated training system"""
    
    def __init__(self):
        super().__init__()
        self.trainer = AutomatedTrainingSystem()
        self.calculator = OptimalParameterCalculator()
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("🎓 Automated Training System")
        title.setStyleSheet(get_panel_title_stylesheet())
        layout.addWidget(title)
        
        # Building Block Selection
        blocks_group = QGroupBox("1️⃣ Select Building Blocks to Train")
        blocks_layout = QVBoxLayout()
        
        # Add "Select All" / "Deselect All" buttons
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all_blocks)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self._deselect_all_blocks)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        blocks_layout.addLayout(btn_layout)
        
        # Building block checkboxes
        self.block_checkboxes = {}
        all_blocks = get_all_building_blocks()
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        for block in all_blocks:
            checkbox = QCheckBox(f"{block.name} ({len(block.signals)} signals)")
            checkbox.setToolTip(f"Train: {', '.join(s.name for s in block.signals)}")
            scroll_layout.addWidget(checkbox)
            self.block_checkboxes[block.name] = checkbox
        
        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setMaximumHeight(200)
        blocks_layout.addWidget(scroll_area)
        
        blocks_group.setLayout(blocks_layout)
        layout.addWidget(blocks_group)
        
        # Training Configuration
        config_group = QGroupBox("2️⃣ Training Configuration")
        config_layout = QFormLayout()
        
        # Training Mode Selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Testing Mode", "Production Mode"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        config_layout.addRow("Training Mode:", self.mode_combo)
        
        # Data Period (changes based on mode)
        self.data_period_combo = QComboBox()
        self._update_period_options()
        config_layout.addRow("Data Period:", self.data_period_combo)
        
        # Timeframe Selection
        timeframe_layout = QHBoxLayout()
        self.timeframe_checks = {
            "5m": QCheckBox("5m"),
            "15m": QCheckBox("15m"),
            "1h": QCheckBox("1h"),
            "4h": QCheckBox("4h")
        }
        self.timeframe_checks["15m"].setChecked(True)  # Default
        for cb in self.timeframe_checks.values():
            timeframe_layout.addWidget(cb)
        config_layout.addRow("Timeframes:", timeframe_layout)
        
        # Forward Lookback
        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(50, 500)
        self.lookback_spin.setValue(200)
        self.lookback_spin.setSuffix(" candles")
        config_layout.addRow("Forward Lookback:", self.lookback_spin)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Resource Estimate
        estimate_group = QGroupBox("3️⃣ Resource Estimate")
        estimate_layout = QVBoxLayout()
        
        self.estimate_label = QLabel()
        self.estimate_label.setWordWrap(True)
        estimate_layout.addWidget(self.estimate_label)
        
        calc_estimate_btn = QPushButton("Calculate Estimate")
        calc_estimate_btn.clicked.connect(self._calculate_estimate)
        estimate_layout.addWidget(calc_estimate_btn)
        
        estimate_group.setLayout(estimate_layout)
        layout.addWidget(estimate_group)
        
        # Control Buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🎓 Start Training")
        self.start_btn.clicked.connect(self._on_start_training)
        self.start_btn.setStyleSheet(get_primary_button_stylesheet())
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        self.results_btn = QPushButton("📊 View Results")
        self.results_btn.clicked.connect(self._on_view_results)
        btn_layout.addWidget(self.results_btn)
        
        layout.addLayout(btn_layout)
    
    def _select_all_blocks(self):
        """Select all building blocks"""
        for checkbox in self.block_checkboxes.values():
            checkbox.setChecked(True)
        self._calculate_estimate()
    
    def _deselect_all_blocks(self):
        """Deselect all building blocks"""
        for checkbox in self.block_checkboxes.values():
            checkbox.setChecked(False)
        self._calculate_estimate()
    
    def _on_mode_changed(self, mode: str):
        """Update period options when mode changes"""
        self._update_period_options()
        self._calculate_estimate()
    
    def _update_period_options(self):
        """Update data period options based on mode"""
        self.data_period_combo.clear()
        
        if self.mode_combo.currentText() == "Testing Mode":
            self.data_period_combo.addItems([
                "7 days (Quick Test)",
                "14 days (Standard Test)",
                "30 days (Extended Test)"
            ])
        else:  # Production Mode
            self.data_period_combo.addItems([
                "90 days (Minimal)",
                "180 days (Standard)",
                "365 days (Comprehensive)"
            ])
    
    def _calculate_estimate(self):
        """Calculate and display resource estimate"""
        
        # Count selected blocks
        selected_blocks = [
            name for name, cb in self.block_checkboxes.items()
            if cb.isChecked()
        ]
        
        if not selected_blocks:
            self.estimate_label.setText("⚠️ No blocks selected")
            return
        
        # Count selected timeframes
        selected_timeframes = [
            tf for tf, cb in self.timeframe_checks.items()
            if cb.isChecked()
        ]
        
        if not selected_timeframes:
            self.estimate_label.setText("⚠️ No timeframes selected")
            return
        
        # Extract period days
        period_text = self.data_period_combo.currentText()
        period_days = int(period_text.split()[0])
        
        # Estimate duration (rough formula)
        # Base: ~2 min per block per timeframe per 30 days
        base_time_per_block = 2  # minutes
        time_multiplier = period_days / 30
        
        total_configs = len(selected_blocks) * len(selected_timeframes)
        estimated_minutes = total_configs * base_time_per_block * time_multiplier
        
        # Format duration
        if estimated_minutes < 60:
            duration_str = f"{int(estimated_minutes)} minutes"
        else:
            hours = int(estimated_minutes // 60)
            mins = int(estimated_minutes % 60)
            duration_str = f"{hours}h {mins}m"
        
        # CPU usage estimate
        if len(selected_blocks) <= 2:
            cpu_usage = "60-70%"
        elif len(selected_blocks) <= 5:
            cpu_usage = "70-85%"
        else:
            cpu_usage = "85-95%"
        
        # Display estimate
        self.estimate_label.setText(
            f"📊 Estimated Resources:\n"
            f"  • Blocks: {len(selected_blocks)}\n"
            f"  • Timeframes: {len(selected_timeframes)}\n"
            f"  • Period: {period_days} days\n"
            f"  • Duration: ~{duration_str}\n"
            f"  • CPU Usage: {cpu_usage}\n"
            f"  • Configs: {total_configs}\n\n"
            f"⚠️ System will be under heavy load during training"
        )
        
        # Progress
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to train...")
        layout.addWidget(self.status_label)
        
        # Results Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Signal", "Timeframe", "Optimal Delay", 
            "Range", "Samples", "Confidence"
        ])
        layout.addWidget(self.results_table)
        
        self.setLayout(layout)
    
    def _on_start_training(self):
        """Start training process"""
        
        # Validate selection
        selected_blocks = [
            name for name, cb in self.block_checkboxes.items()
            if cb.isChecked()
        ]
        
        if not selected_blocks:
            QMessageBox.warning(
                self,
                "No Blocks Selected",
                "Please select at least one building block to train."
            )
            return
        
        selected_timeframes = [
            tf for tf, cb in self.timeframe_checks.items()
            if cb.isChecked()
        ]
        
        if not selected_timeframes:
            QMessageBox.warning(
                self,
                "No Timeframes Selected",
                "Please select at least one timeframe."
            )
            return
        
        # Confirm with user
        period_text = self.data_period_combo.currentText()
        period_days = int(period_text.split()[0])
        
        reply = QMessageBox.question(
            self,
            "Confirm Training",
            f"Start training on:\n"
            f"  • {len(selected_blocks)} blocks\n"
            f"  • {len(selected_timeframes)} timeframes\n"
            f"  • {period_days} days of data\n\n"
            f"This will take approximately {self._get_duration_estimate()} "
            f"and use significant CPU resources.\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Start training
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Run training in background thread
        self.training_thread = TrainingThread(
            trainer=self.trainer,
            selected_blocks=selected_blocks,
            selected_timeframes=selected_timeframes,
            period_days=period_days,
            lookback_candles=self.lookback_spin.value()
        )
        self.training_thread.progress_updated.connect(self._on_progress)
        self.training_thread.training_complete.connect(self._on_training_complete)
        self.training_thread.start()
    
    def _get_duration_estimate(self) -> str:
        """Get human-readable duration estimate"""
        # Extract from estimate label
        text = self.estimate_label.text()
        for line in text.split('\n'):
            if 'Duration:' in line:
                return line.split('Duration:')[1].strip()
        return "unknown duration"
    
    def _on_progress(self, message, percent):
        """Update progress display"""
        self.status_label.setText(message)
        self.progress_bar.setValue(percent)
    
    def _on_training_complete(self):
        """Training finished - calculate and display results"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Training complete! Calculating recommendations...")
        
        # Generate recommendations
        report = self.calculator.generate_recommendations_report()
        
        # Display in table
        self._display_results(report['recheck_recommendations'])
        
        self.status_label.setText(
            f"✅ Found {len(report['recheck_recommendations'])} recommendations "
            f"({report['summary']['high_confidence']} high confidence)"
        )
    
    def _display_results(self, recommendations):
        """Display recommendations in table"""
        self.results_table.setRowCount(len(recommendations))
        
        for i, rec in enumerate(recommendations):
            self.results_table.setItem(i, 0, QTableWidgetItem(rec['signal']))
            self.results_table.setItem(i, 1, QTableWidgetItem(rec['timeframe']))
            self.results_table.setItem(i, 2, QTableWidgetItem(str(rec['optimal_delay'])))
            self.results_table.setItem(i, 3, QTableWidgetItem(
                f"{rec['min_delay']}-{rec['max_delay']}"
            ))
            self.results_table.setItem(i, 4, QTableWidgetItem(str(rec['sample_size'])))
            self.results_table.setItem(i, 5, QTableWidgetItem(
                f"{rec['confidence']*100:.0f}%"
            ))
```

---

## 📈 EXAMPLE OUTPUT

```
Training Complete: HOD_REJECTION (15m timeframe)
═══════════════════════════════════════════════════

Sample Size: 347 signal occurrences
Data Period: 365 days
Forward Analysis: 200 candles per occurrence

RECHECK ANALYSIS:
├─ Total Recurrences: 1,247
├─ Successful Recurrences: 563 (45%)
├─ Failed Recurrences: 684 (55%)
└─ Recurrence Timing Distribution:
   ├─ 10th %ile: 50 candles
   ├─ 25th %ile: 58 candles
   ├─ Median: 65 candles ⭐ OPTIMAL
   ├─ 75th %ile: 72 candles
   └─ 90th %ile: 85 candles

RECOMMENDATION:
✅ Set recheck_delay = 65 candles
   Confidence: 85% (347 samples)
   Expected Win Rate: 45% on recheck trades
   
CURRENT VALUE: 25 candles
IMPROVEMENT: +40 candles (160% increase)
RATIONALE: Price typically returns to HOD after 65 candles
           Setting delay too short (25) misses optimal re-entry
```

---

## 🎯 SUCCESS METRICS

**Automated Trainer is successful if:**
1. ✅ Records forward-looking behavior for ALL signals
2. ✅ Analyzes 200 candles after each signal fire
3. ✅ Detects signal recurrence patterns accurately
4. ✅ Calculates statistically valid optimal delays
5. ✅ Provides high-confidence recommendations (>80%)
6. ✅ Reduces manual guesswork by 95%
7. ✅ Improves strategy performance by 20%+

---

**Status**: 🔬 DESIGN COMPLETE - Ready for implementation  
**Timeline**: 5 days (Sprint 6 in Phase 2)  
**Integration**: Feeds into Optimizer v3 + Signal Intelligence

**Quality**: 💎 **REVOLUTIONARY** - Data-driven parameter discovery!

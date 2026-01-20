# OPTIMIZER V3 - TESTING & DEBUG FRAMEWORK
**Institutional-Grade Quality Assurance for Data Accuracy**

**Date**: 2026-01-19  
**Status**: 🔬 CRITICAL INFRASTRUCTURE  
**Priority**: P0 - Foundation for reliable training data

---

## 🎯 TESTING PHILOSOPHY

### **Core Principle:** ZERO TOLERANCE FOR INACCURATE DATA

**Why This Matters:**
- Inaccurate training data → Bad ML models → Poor strategy recommendations → Lost money
- One bug in forward-looking analysis → Thousands of corrupted training records
- Silent failures → Database fills with garbage → System learns wrong patterns

**Solution:** Multi-layered testing + comprehensive debug logging + data validation

---

## 🏗️ TESTING PYRAMID

```
                    ┌─────────────┐
                    │   Manual    │  5%
                    │  Validation │
                  ┌─┴─────────────┴─┐
                  │   Integration   │  15%
                  │      Tests      │
                ┌─┴─────────────────┴─┐
                │   Component Tests   │  30%
              ┌─┴─────────────────────┴─┐
              │      Unit Tests         │  50%
              └─────────────────────────┘
```

### **Level 1: Unit Tests (50%)** - Verify individual functions
### **Level 2: Component Tests (30%)** - Verify modules work together
### **Level 3: Integration Tests (15%)** - Verify full system accuracy
### **Level 4: Manual Validation (5%)** - Human verification of critical paths

---

## 📊 MULTI-LEVEL TESTING STRATEGY

### **1. Unit Tests** (Function-Level Accuracy)

```python
class TestSignalRecurrence:
    """Test signal recurrence detection accuracy"""
    
    def test_detect_single_recurrence(self):
        """Verify we correctly detect when signal fires again"""
        
        # GIVEN: Known test data where HOD fires at candle 0 and 65
        test_data = generate_test_data_with_hod_at([0, 65])
        
        # WHEN: We analyze recurrence
        recurrence = find_signal_recurrence('HOD_REJECTION', test_data)
        
        # THEN: Should detect recurrence at candle 65
        assert recurrence['recurrence_delays'] == [65]
        assert len(recurrence['successful_recurrences']) >= 0
        
    def test_multiple_recurrences(self):
        """Test detection of multiple signal fires"""
        
        test_data = generate_test_data_with_hod_at([0, 50, 80, 120])
        recurrence = find_signal_recurrence('HOD_REJECTION', test_data)
        
        assert recurrence['recurrence_delays'] == [50, 80, 120]
        
    def test_no_recurrence(self):
        """Test handling when signal never fires again"""
        
        test_data = generate_test_data_with_hod_at([0])  # Only fires once
        recurrence = find_signal_recurrence('HOD_REJECTION', test_data)
        
        assert recurrence['recurrence_delays'] == []
        
    def test_recurrence_success_classification(self):
        """Verify we correctly classify successful vs failed recurrences"""
        
        # HOD fires at 0 (fails), recurs at 50 (succeeds), 80 (fails)
        test_data = generate_test_data_with_outcomes([
            (0, 'SL'),
            (50, 'TP'),
            (80, 'SL')
        ])
        
        recurrence = find_signal_recurrence('HOD_REJECTION', test_data)
        
        assert recurrence['successful_recurrences'] == [0]  # Index of 50-candle recurrence
        assert recurrence['failed_recurrences'] == [1]     # Index of 80-candle recurrence
```

### **2. Component Tests** (Module Integration)

```python
class TestForwardLookingAnalysis:
    """Test complete forward-looking analysis pipeline"""
    
    def test_200_candle_analysis_completeness(self):
        """Verify all 200 candles are analyzed"""
        
        # GIVEN: 300 candles of data (enough for 200 forward)
        test_data = generate_300_candles()
        
        # WHEN: Signal fires at candle 50
        analysis = analyze_forward_behavior(
            signal_candle=50,
            data=test_data,
            lookback=200
        )
        
        # THEN: Should analyze candles 50-250
        assert analysis['analyzed_candles'] == 200
        assert 'max_favorable_move' in analysis
        assert 'recurrence_delays' in analysis
        assert 'dependent_signals' in analysis
        
    def test_price_movement_accuracy(self):
        """Verify max favorable/adverse move calculations"""
        
        # GIVEN: Known price movement
        test_data = generate_test_data_with_known_moves(
            entry_price=50000,
            max_down=49000,  # 2% favorable for SHORT
            max_up=51000    # 2% adverse for SHORT
        )
        
        # WHEN: Analyze price movement
        analysis = analyze_price_movement(
            entry_candle={'close': 50000, 'signal_direction': 'SHORT'},
            forward_data=test_data
        )
        
        # THEN: Should accurately capture extremes
        assert analysis['max_favorable_move'] == 1000  # 50000 - 49000
        assert analysis['max_adverse_move'] == 1000   # 51000 - 50000
        
    def test_dependent_signal_timing(self):
        """Verify dependent signal timing detection"""
        
        # GIVEN: HOD fires at 0, RSI_OVERBOUGHT fires at [15, 25, 40]
        test_data = generate_test_data_with_signals({
            'HOD_REJECTION': [0],
            'RSI_OVERBOUGHT': [15, 25, 40]
        })
        
        # WHEN: Find dependent signals
        dependent = find_dependent_signals('HOD_REJECTION', test_data)
        
        # THEN: Should detect RSI timing correctly
        assert 'RSI_OVERBOUGHT' in dependent
        assert dependent['RSI_OVERBOUGHT'] == [15, 25, 40]
```

### **3. Integration Tests** (Full System Validation)

```python
class TestTrainingSystemIntegration:
    """Test complete training pipeline end-to-end"""
    
    @pytest.fixture
    def clean_database(self):
        """Ensure clean database before each test"""
        db = SignalDatabase()
        db.clear_all_training_data()
        yield db
        db.close()
    
    def test_complete_training_cycle(self, clean_database):
        """Test: Load data → Analyze → Store → Retrieve → Verify"""
        
        # GIVEN: Clean database and test data
        trainer = AutomatedTrainingSystem()
        test_period = 30  # 30 days for fast test
        
        # WHEN: Run complete training
        trainer.train_all_blocks(data_period=test_period)
        
        # THEN: Verify data was stored correctly
        events = clean_database.query("""
            SELECT * FROM signal_training_events
            WHERE signal_name = 'HOD_REJECTION'
        """)
        
        assert len(events) > 0, "No training events recorded!"
        
        # Verify each event has required fields
        for event in events:
            assert event['price_at_signal'] is not None
            assert event['recurrence_delays'] is not None
            assert event['max_favorable_move'] is not None
            assert event['final_outcome'] in ['TP', 'SL', 'timeout', 'none']
    
    def test_optimal_parameter_calculation_accuracy(self, clean_database):
        """Test: Training → Calculate optimal params → Verify accuracy"""
        
        # GIVEN: Pre-populated test data with known patterns
        # (HOD recurs at 60-70 candles most of the time)
        inject_test_training_data(
            signal='HOD_REJECTION',
            recurrence_pattern=[60, 62, 65, 65, 67, 70, 68, 63]
        )
        
        # WHEN: Calculate optimal parameters
        calculator = OptimalParameterCalculator()
        optimal = calculator.calculate_optimal_recheck_delay('HOD_REJECTION')
        
        # THEN: Should recommend ~65 candles (median of pattern)
        assert 63 <= optimal['optimal_delay'] <= 67
        assert optimal['confidence'] > 0.5
        assert optimal['sample_size'] == 8
    
    def test_data_accuracy_regression(self, clean_database):
        """Test: Verify training data matches known market behavior"""
        
        # GIVEN: Real historical data with known patterns
        # (E.g., we manually verified HOD rejection on 2025-01-15)
        real_data = load_historical_data('2025-01-15', '2025-01-16')
        
        # WHEN: Run trainer on this data
        trainer = AutomatedTrainingSystem()
        results = trainer._train_signal(
            block_name='hod',
            signal_name='HOD_REJECTION',
            timeframe='15m',
            period_days=1  # Just test one day
        )
        
        # THEN: Compare against manually verified ground truth
        ground_truth = load_ground_truth('HOD_REJECTION_2025-01-15.json')
        
        for i, event in enumerate(results):
            truth = ground_truth[i]
            assert event['timestamp'] == truth['timestamp']
            assert abs(event['price_at_signal'] - truth['price']) < 0.01
            assert event['final_outcome'] == truth['outcome']
```

### **4. Data Validation Tests** (Accuracy Verification)

```python
class TestDataValidation:
    """Verify all training data meets quality standards"""
    
    def test_no_null_required_fields(self):
        """Ensure no critical fields are NULL"""
        
        db = SignalDatabase()
        invalid = db.query("""
            SELECT * FROM signal_training_events
            WHERE price_at_signal IS NULL
               OR timestamp IS NULL
               OR final_outcome IS NULL
        """)
        
        assert len(invalid) == 0, f"Found {len(invalid)} events with NULL required fields!"
    
    def test_price_sanity_checks(self):
        """Verify prices are within reasonable ranges"""
        
        db = SignalDatabase()
        invalid_prices = db.query("""
            SELECT * FROM signal_training_events
            WHERE price_at_signal <= 0
               OR price_at_signal > 1000000  -- BTC shouldn't be > $1M
               OR max_favorable_move < 0
               OR max_adverse_move < 0
        """)
        
        assert len(invalid_prices) == 0
    
    def test_recurrence_delays_logical(self):
        """Verify recurrence delays are logical"""
        
        db = SignalDatabase()
        events = db.query("""
            SELECT recurrence_delays FROM signal_training_events
            WHERE array_length(recurrence_delays, 1) > 0
        """)
        
        for event in events:
            delays = event['recurrence_delays']
            # Should be sorted ascending
            assert delays == sorted(delays)
            # Should all be positive
            assert all(d > 0 for d in delays)
            # Should be within 200 candles (our lookback)
            assert all(d <= 200 for d in delays)
    
    def test_confidence_scores_valid(self):
        """Verify confidence scores are 0-1"""
        
        calculator = OptimalParameterCalculator()
        all_signals = get_all_trained_signals()
        
        for signal in all_signals:
            params = calculator.calculate_optimal_recheck_delay(signal)
            if params:
                assert 0 <= params['confidence'] <= 1
                assert params['sample_size'] >= 0
```

---

## 🔍 DEBUG LOGGING FRAMEWORK

### **Architecture: Multi-Level Structured Logging**

```python
class OptimizerLogger:
    """Sophisticated debug logger for Optimizer v3"""
    
    def __init__(self, component: str):
        self.component = component
        self.session_id = uuid.uuid4()
        self.start_time = datetime.now()
        
        # Configure multi-output logging
        self.logger = logging.getLogger(f"optimizer_v3.{component}")
        self.logger.setLevel(logging.DEBUG)
        
        # 1. File Handler - Detailed logs
        fh = logging.FileHandler(f'logs/optimizer_v3_{component}_{self.session_id}.log')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
        ))
        
        # 2. Console Handler - Important events only
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        
        # 3. Database Handler - Critical events for analysis
        dbh = DatabaseLogHandler()
        dbh.setLevel(logging.WARNING)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        self.logger.addHandler(dbh)
    
    def log_signal_analysis(self, signal_name: str, candle_index: int, 
                           fired: bool, context: dict):
        """Log signal analysis with full context"""
        
        self.logger.debug(
            f"Signal Analysis",
            extra={
                'signal_name': signal_name,
                'candle_index': candle_index,
                'fired': fired,
                'price': context.get('price'),
                'volume': context.get('volume'),
                'conditions_met': context.get('conditions_met', []),
                'fail_reasons': context.get('fail_reasons', [])
            }
        )
        
        # If signal fired, log important event
        if fired:
            self.logger.info(
                f"✓ Signal FIRED: {signal_name} @ candle {candle_index} "
                f"(price: {context.get('price')})"
            )
    
    def log_forward_analysis_start(self, signal_name: str, start_candle: int,
                                   lookback: int):
        """Log start of forward-looking analysis"""
        
        self.logger.info(
            f"▶ Forward Analysis: {signal_name} | "
            f"Candles {start_candle} → {start_candle + lookback}"
        )
    
    def log_recurrence_detected(self, signal_name: str, delay: int,
                               success: bool, context: dict):
        """Log signal recurrence with success indicator"""
        
        emoji = "✅" if success else "❌"
        self.logger.info(
            f"{emoji} Recurrence: {signal_name} +{delay} candles "
            f"({'SUCCESS' if success else 'FAILED'})"
        )
        
        self.logger.debug(
            f"Recurrence details",
            extra={
                'signal_name': signal_name,
                'delay': delay,
                'success': success,
                'price_at_recurrence': context.get('price'),
                'outcome': context.get('outcome')
            }
        )
    
    def log_data_validation_error(self, validation_type: str, error: str,
                                  data: dict):
        """Log data validation failures (CRITICAL)"""
        
        self.logger.error(
            f"🚨 DATA VALIDATION FAILED: {validation_type}",
            extra={
                'validation_type': validation_type,
                'error': error,
                'invalid_data': data,
                'session_id': self.session_id
            }
        )
        
        # Also raise exception to halt execution
        raise DataValidationError(f"{validation_type}: {error}")
    
    def log_training_summary(self, signal_name: str, stats: dict):
        """Log training completion summary"""
        
        self.logger.info(
            f"✓ Training Complete: {signal_name}\n"
            f"  └─ Events: {stats['total_events']}\n"
            f"  └─ Recurrences: {stats['total_recurrences']}\n"
            f"  └─ Success Rate: {stats['success_rate']:.1%}\n"
            f"  └─ Optimal Delay: {stats['optimal_delay']} candles"
        )
    
    def log_performance_metric(self, operation: str, duration_ms: float,
                              records_processed: int):
        """Log performance metrics"""
        
        rate = records_processed / (duration_ms / 1000) if duration_ms > 0 else 0
        
        self.logger.debug(
            f"⏱ Performance: {operation}",
            extra={
                'operation': operation,
                'duration_ms': duration_ms,
                'records': records_processed,
                'rate_per_sec': rate
            }
        )
```

### **Database Log Handler**

```sql
-- Store critical log events for analysis
CREATE TABLE optimizer_debug_logs (
    log_id UUID PRIMARY KEY,
    session_id UUID,
    timestamp TIMESTAMP DEFAULT NOW(),
    component TEXT,
    level TEXT,  -- 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    message TEXT,
    context JSONB,
    stack_trace TEXT
);

-- Index for querying errors
CREATE INDEX idx_debug_logs_level ON optimizer_debug_logs(level);
CREATE INDEX idx_debug_logs_session ON optimizer_debug_logs(session_id);
CREATE INDEX idx_debug_logs_timestamp ON optimizer_debug_logs(timestamp DESC);
```

### **Usage in Training System**

```python
class AutomatedTrainingSystem:
    """Enhanced with comprehensive logging"""
    
    def __init__(self):
        self.logger = OptimizerLogger('training_system')
        self.validator = DataValidator(self.logger)
    
    def _train_signal(self, block_name, signal_name, timeframe, period_days):
        """Training with full logging"""
        
        self.logger.info(f"🎓 Training: {block_name}::{signal_name} @ {timeframe}")
        
        training_events = []
        data = load_market_data(timeframe=timeframe, days=period_days)
        
        self.logger.debug(f"Loaded {len(data)} candles for analysis")
        
        start_time = time.time()
        signals_found = 0
        
        for i in range(len(data) - self.lookback_candles):
            candle = data[i]
            
            # Check if signal fires
            signal_context = evaluate_signal_with_context(
                block_name, signal_name, candle, data[:i+1]
            )
            
            self.logger.log_signal_analysis(
                signal_name, i, signal_context['fired'], signal_context
            )
            
            if signal_context['fired']:
                signals_found += 1
                
                # Forward analysis
                self.logger.log_forward_analysis_start(
                    signal_name, i, self.lookback_candles
                )
                
                forward_behavior = self._analyze_forward_behavior(
                    signal_candle=i,
                    signal_name=signal_name,
                    block_name=block_name,
                    data=data,
                    lookback=self.lookback_candles
                )
                
                # Validate data before storing
                self.validator.validate_training_event(forward_behavior)
                
                training_events.append(forward_behavior)
        
        # Log performance
        duration_ms = (time.time() - start_time) * 1000
        self.logger.log_performance_metric(
            'signal_training', duration_ms, signals_found
        )
        
        # Log summary
        self.logger.log_training_summary(signal_name, {
            'total_events': len(training_events),
            'total_recurrences': sum(
                len(e['recurrence_delays']) for e in training_events
            ),
            'success_rate': calculate_success_rate(training_events),
            'optimal_delay': calculate_median_delay(training_events)
        })
        
        return training_events
```

---

## ✅ DATA VALIDATION FRAMEWORK

```python
class DataValidator:
    """Validate all training data before storage"""
    
    def __init__(self, logger: OptimizerLogger):
        self.logger = logger
    
    def validate_training_event(self, event: dict) -> bool:
        """Comprehensive validation of training event"""
        
        # 1. Required fields present
        required_fields = [
            'signal_name', 'timestamp', 'price_at_signal',
            'recurrence_delays', 'max_favorable_move', 'final_outcome'
        ]
        
        for field in required_fields:
            if field not in event or event[field] is None:
                self.logger.log_data_validation_error(
                    'missing_required_field',
                    f"Field '{field}' is missing or NULL",
                    event
                )
        
        # 2. Price sanity checks
        price = event['price_at_signal']
        if not (1000 <= price <= 1000000):  # BTC price range
            self.logger.log_data_validation_error(
                'invalid_price',
                f"Price {price} outside valid range [1000, 1000000]",
                event
            )
        
        # 3. Recurrence delays logical
        delays = event['recurrence_delays']
        if delays:
            if delays != sorted(delays):
                self.logger.log_data_validation_error(
                    'invalid_recurrence_order',
                    f"Recurrence delays not sorted: {delays}",
                    event
                )
            
            if any(d <= 0 or d > 200 for d in delays):
                self.logger.log_data_validation_error(
                    'invalid_recurrence_range',
                    f"Recurrence delay outside [1, 200]: {delays}",
                    event
                )
        
        # 4. Price movements non-negative
        if event['max_favorable_move'] < 0:
            self.logger.log_data_validation_error(
                'negative_favorable_move',
                f"Max favorable move is negative: {event['max_favorable_move']}",
                event
            )
        
        # 5. Outcome valid
        valid_outcomes = ['TP', 'SL', 'timeout', 'none']
        if event['final_outcome'] not in valid_outcomes:
            self.logger.log_data_validation_error(
                'invalid_outcome',
                f"Outcome '{event['final_outcome']}' not in {valid_outcomes}",
                event
            )
        
        # 6. Timestamp reasonable
        if event['timestamp'] > datetime.now():
            self.logger.log_data_validation_error(
                'future_timestamp',
                f"Timestamp in future: {event['timestamp']}",
                event
            )
        
        return True  # All validations passed
```

---

## 📈 REGRESSION TESTING

```python
class RegressionTestSuite:
    """Prevent bugs from reappearing"""
    
    def test_known_bug_HOD_65_candle_pattern(self):
        """
        Regression: Issue #123
        Bug: HOD recurrence at 65 candles was being recorded as 64.5
        Fix: Proper integer rounding
        """
        
        test_data = generate_hod_at_exact_delay(65)
        recurrence = find_signal_recurrence('HOD_REJECTION', test_data)
        
        assert recurrence['recurrence_delays'][0] == 65  # Not 64.5!
    
    def test_known_bug_negative_price_movement(self):
        """
        Regression: Issue #145
        Bug: Negative price movements were recorded as 0
        Fix: Proper absolute value calculation
        """
        
        test_data = generate_price_drop_scenario(entry=50000, drop_to=49000)
        analysis = analyze_price_movement(
            {'close': 50000, 'signal_direction': 'SHORT'},
            test_data
        )
        
        assert analysis['max_favorable_move'] == 1000  # Not 0!
```

---

## 🎯 TEST EXECUTION STRATEGY

### **Continuous Integration Pipeline**

```yaml
# .github/workflows/optimizer_v3_tests.yml

name: Optimizer V3 Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Unit Tests
        run: pytest tests/unit/optimizer_v3/ -v --cov
      
  component-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - name: Run Component Tests
        run: pytest tests/component/optimizer_v3/ -v
      
  integration-tests:
    runs-on: ubuntu-latest
    needs: component-tests
    steps:
      - name: Run Integration Tests (30-day data)
        run: pytest tests/integration/optimizer_v3/ -v --slow
      
  data-validation:
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - name: Validate Training Data Accuracy
        run: python scripts/validate_training_data.py
      
  regression-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Regression Suite
        run: pytest tests/regression/optimizer_v3/ -v
```

---

## 📋 TEST COVERAGE REQUIREMENTS

### **Minimum Coverage Standards**

| Component | Coverage Required | Current | Status |
|-----------|------------------|---------|--------|
| Signal Detection | 95% | - | ⏳ TBD |
| Forward Analysis | 95% | - | ⏳ TBD |
| Recurrence Detection | 98% | - | ⏳ TBD |
| Price Movement | 90% | - | ⏳ TBD |
| Data Validation | 100% | - | ⏳ TBD |
| Database Operations | 85% | - | ⏳ TBD |
| Parameter Calculation | 95% | - | ⏳ TBD |

---

## 🎯 SUCCESS METRICS

**Testing Framework is successful if:**
1. ✅ 95%+ code coverage across critical components
2. ✅ ZERO data validation failures in production
3. ✅ All regression tests pass on every commit
4. ✅ Integration tests complete in <30 minutes
5. ✅ Debug logs enable bug diagnosis in <15 minutes
6. ✅ Data accuracy verified against manual ground truth
7. ✅ Performance metrics logged for optimization

---

**Status**: 🔬 DESIGN COMPLETE - Ready for implementation  
**Timeline**: Integrated into each sprint (ongoing)  
**Priority**: P0 - No code merged without passing all tests

**Quality**: 🏆 **INSTITUTIONAL GRADE** - Zero tolerance for inaccurate data!

# Phase 2 Week 5: Weis Wave Analysis (Layer 3) - PLAN

**Start Date:** December 16, 2025  
**Target Completion:** 1-2 days  
**Status:** Planning

## Overview

Implement Layer 3: Weis Wave Volume Analysis to detect institutional accumulation/distribution patterns and provide early warning signals 1-3 days before major moves.

## Objectives

### Primary Goals
1. Implement Weis Wave volume tracking
2. Detect accumulation/distribution patterns
3. Identify wave exhaustion signals
4. Multi-wave pattern recognition
5. Integration with Layer 2 divergences

### Expected Performance Impact
- **Win Rate:** +2-3% (to 63-65% cumulative)
- **Accumulation Detection Accuracy:** >70%
- **Distribution Warning Lead Time:** 1-3 days
- **False Signal Reduction:** Additional 10-15%

## Technical Specifications

### 1. Weis Wave Concepts

**Wave Definition:**
- Volume accumulation during price moves
- Waves end when price reverses direction
- Each wave has direction (up/down) and volume
- Wave exhaustion = declining volume with continued price movement

**Key Metrics:**
- Wave volume (total volume in wave)
- Wave duration (bars in wave)
- Wave price range (high - low)
- Volume efficiency (volume/price ratio)
- Climactic volume (spike detection)

### 2. Layer 3 Architecture

```python
@dataclass
class WeisWave:
    wave_id: int
    direction: str  # 'up' or 'down'
    start_idx: int
    end_idx: int
    start_price: float
    end_price: float
    total_volume: float
    bar_count: int
    price_range: float
    volume_efficiency: float
    is_climactic: bool
    
@dataclass
class AccumulationDistribution:
    pattern_type: str  # 'accumulation', 'distribution', 'neutral'
    confidence: float
    wave_sequence: List[WeisWave]
    volume_trend: str
    price_action: str
    expected_outcome: str

class Layer3WeisWave(BaseLayer):
    - calculate_waves()
    - detect_wave_exhaustion()
    - identify_accumulation()
    - identify_distribution()
    - analyze_wave_patterns()
    - calculate_layer_score()
    - generate_signal()
```

### 3. Wave Detection Algorithm

**Step 1: Identify Swing Points**
- Use pivot detection (similar to Layer 2)
- Find local highs and lows
- Minimum swing size filter

**Step 2: Calculate Wave Metrics**
- Sum volume between pivots
- Calculate price range
- Determine wave efficiency
- Detect climactic bars

**Step 3: Pattern Recognition**
- Accumulation: Declining wave volume on downswings
- Distribution: Declining wave volume on upswings
- Exhaustion: Large volume with small price movement
- Spring/Upthrust: Volume spike with price rejection

### 4. Integration with Layer 2

**Confirmation Signals:**
- Weis Wave accumulation + Layer 2 bullish divergence = Strong buy
- Weis Wave distribution + Layer 2 bearish divergence = Strong sell
- Wave exhaustion + CVD divergence = Early reversal signal

**Conflict Resolution:**
- Layer 3 distribution overrides Layer 2 bullish if confidence >0.7
- Layer 3 accumulation overrides Layer 2 bearish if confidence >0.7

## Implementation Plan

### Phase 1: Core Wave Tracking (~200 lines)

```python
class Layer3WeisWave(BaseLayer):
    def __init__(
        self,
        min_wave_bars: int = 3,
        climax_threshold: float = 2.0,
        efficiency_threshold: float = 0.5
    ):
        super().__init__(
            name="layer3_weis_wave",
            enabled=True,
            weight=1.0,
            confidence_threshold=0.3
        )
        self.min_wave_bars = min_wave_bars
        self.climax_threshold = climax_threshold
        self.efficiency_threshold = efficiency_threshold
    
    def calculate_waves(self, df: pd.DataFrame) -> List[WeisWave]:
        """
        Calculate Weis Waves from price data.
        
        Algorithm:
        1. Find swing points (pivots)
        2. Create waves between pivots
        3. Calculate wave metrics
        4. Identify climactic waves
        """
        pass
    
    def calculate_wave_efficiency(
        self, 
        volume: float, 
        price_range: float
    ) -> float:
        """
        Calculate volume efficiency ratio.
        
        High efficiency = Large price move with low volume
        Low efficiency = Small price move with high volume (accumulation/distribution)
        """
        pass
```

### Phase 2: Pattern Recognition (~150 lines)

```python
def identify_accumulation(
    self,
    waves: List[WeisWave],
    current_price: float
) -> AccumulationDistribution:
    """
    Detect accumulation patterns.
    
    Characteristics:
    - Price ranging or declining
    - Declining volume on down waves
    - Increasing volume on up waves
    - Wave efficiency improving
    - Spring pattern (false breakdown)
    """
    pass

def identify_distribution(
    self,
    waves: List[WeisWave],
    current_price: float
) -> AccumulationDistribution:
    """
    Detect distribution patterns.
    
    Characteristics:
    - Price ranging or rising
    - Declining volume on up waves
    - Increasing volume on down waves
    - Wave efficiency deteriorating
    - Upthrust pattern (false breakout)
    """
    pass

def detect_wave_exhaustion(
    self,
    waves: List[WeisWave]
) -> Dict:
    """
    Detect wave exhaustion signals.
    
    Exhaustion indicators:
    - Climactic volume spike
    - Declining subsequent waves
    - Price momentum slowing
    - Volume/price divergence
    """
    pass
```

### Phase 3: Scoring & Signal Generation (~100 lines)

```python
def calculate_layer_score(
    self,
    waves: List[WeisWave],
    accumulation: AccumulationDistribution,
    exhaustion: Dict
) -> float:
    """
    Calculate Layer 3 composite score (-10 to +10).
    
    Scoring components:
    - Accumulation: +5 to +8 (based on confidence)
    - Distribution: -5 to -8 (based on confidence)
    - Wave exhaustion: ±3 to ±5
    - Wave efficiency trend: ±1 to ±2
    - Climactic volume: ±2
    """
    pass

def generate_signal(
    self,
    data: pd.DataFrame,
    current_price: float,
    current_position: Optional[str] = None
) -> LayerSignal:
    """
    Generate Layer 3 trading signal.
    
    Returns:
        LayerSignal with:
        - direction: 'long', 'short', 'neutral'
        - confidence: 0.0 to 1.0
        - strength: 0.0 to 1.0
        - metadata: {
            'waves': [...],
            'accumulation': {...},
            'exhaustion': {...},
            'score': float
          }
    """
    pass
```

## Test Plan

### Test Coverage (~250 lines)

```python
def test_layer3_weis_wave():
    """Comprehensive Layer 3 tests."""
    
    # Test 1: Wave Calculation
    test_wave_calculation()
    
    # Test 2: Accumulation Detection
    test_accumulation_detection()
    
    # Test 3: Distribution Detection
    test_distribution_detection()
    
    # Test 4: Wave Exhaustion
    test_wave_exhaustion()
    
    # Test 5: Climactic Volume
    test_climactic_volume()
    
    # Test 6: Wave Efficiency
    test_wave_efficiency()
    
    # Test 7: Pattern Recognition
    test_pattern_recognition()
    
    # Test 8: Score Calculation
    test_score_calculation()
    
    # Test 9: Signal Generation
    test_signal_generation()
    
    # Test 10: Layer 2 Integration
    test_layer2_integration()
```

### Test Scenarios

**Scenario 1: Clear Accumulation**
- Price declining with smaller waves
- Volume declining on down moves
- Expected: Bullish signal with confidence >0.7

**Scenario 2: Clear Distribution**
- Price rising with smaller waves
- Volume declining on up moves
- Expected: Bearish signal with confidence >0.7

**Scenario 3: Climactic Exhaustion**
- Large volume spike with price rejection
- Subsequent waves declining
- Expected: Reversal signal with high confidence

**Scenario 4: Neutral/Ranging**
- Equal up/down wave volumes
- No clear pattern
- Expected: Neutral signal

## Development Checklist

### Core Implementation
- [ ] Create `src/layers/layer3_weis_wave.py`
- [ ] Implement `WeisWave` dataclass
- [ ] Implement `AccumulationDistribution` dataclass
- [ ] Implement `Layer3WeisWave` class
- [ ] Implement wave calculation
- [ ] Implement pivot detection (reuse from Layer 2)
- [ ] Implement wave efficiency calculation
- [ ] Implement climactic volume detection

### Pattern Recognition
- [ ] Implement accumulation detection
- [ ] Implement distribution detection
- [ ] Implement wave exhaustion detection
- [ ] Implement spring/upthrust patterns
- [ ] Implement multi-wave sequence analysis

### Scoring & Signals
- [ ] Implement layer score calculation
- [ ] Implement signal generation
- [ ] Add Layer 2 integration hooks
- [ ] Add rich metadata to signals

### Testing
- [ ] Create `tests/test_layer3_weis_wave.py`
- [ ] Test wave calculation
- [ ] Test accumulation detection
- [ ] Test distribution detection
- [ ] Test wave exhaustion
- [ ] Test climactic volume
- [ ] Test pattern recognition
- [ ] Test score calculation
- [ ] Test signal generation
- [ ] Test Layer 2 integration
- [ ] Run all tests (target: 100% pass)

### Documentation
- [ ] Add comprehensive docstrings
- [ ] Create usage examples
- [ ] Document integration with Layer 2
- [ ] Create `docs/PHASE_2_WEEK_5_COMPLETE.md`

## Expected Deliverables

### Code Files
1. **`src/layers/layer3_weis_wave.py`** (~450 lines)
   - Layer 3 implementation
   - Wave tracking and analysis
   - Pattern recognition
   - Signal generation

2. **`tests/test_layer3_weis_wave.py`** (~250 lines)
   - Comprehensive test suite
   - 10 test cases
   - Integration tests

3. **`docs/PHASE_2_WEEK_5_COMPLETE.md`**
   - Completion documentation
   - Performance metrics
   - Integration guide

### Performance Targets
- All tests passing (100%)
- Accumulation detection accuracy >70%
- Distribution detection accuracy >70%
- Early warning lead time: 1-3 days
- False signal reduction: 10-15%

## Integration Points

### Layer 2 Integration
```python
# Example: Combined signal
layer2_signal = layer2.generate_signal(data, current_price)
layer3_signal = layer3.generate_signal(data, current_price)

# Strong buy when both align
if (layer3_signal.metadata['accumulation']['confidence'] > 0.7 and
    layer2_signal.direction == 'long'):
    # High confidence long entry
    pass

# Distribution warning overrides bullish divergence
if (layer3_signal.metadata['distribution']['confidence'] > 0.7 and
    layer2_signal.direction == 'long'):
    # Cancel long entry, potential reversal
    pass
```

### Compositor Integration
```python
# In layer_compositor.py
def calculate_composite_score(self, layer_signals: Dict) -> float:
    """
    Composite score with Layer 3 integration.
    
    Layer 3 has 10% weight but can override other layers
    when accumulation/distribution confidence is high.
    """
    score = 0.0
    
    # Layer 3 can amplify or dampen other signals
    if layer3_signal['accumulation_confidence'] > 0.7:
        # Boost bullish signals
        score += layer1_score * 1.2 if layer1_score > 0 else layer1_score
    elif layer3_signal['distribution_confidence'] > 0.7:
        # Dampen bullish signals or boost bearish
        score += layer1_score * 0.5 if layer1_score > 0 else layer1_score * 1.2
    
    return score
```

## Risk Considerations

### False Positives
- **Issue:** Accumulation patterns in downtrends
- **Mitigation:** Require trend confirmation from Layer 1
- **Threshold:** Confidence <0.5 if trend conflicts

### Late Signals
- **Issue:** Wave patterns develop over time
- **Mitigation:** Early exhaustion detection
- **Target:** 1-3 day lead time

### Volume Data Quality
- **Issue:** Exchange volume reliability
- **Mitigation:** Volume spike filtering
- **Validation:** Cross-reference with Layer 2 CVD

## Success Criteria

### Must Have (MVP)
- ✅ Wave calculation working
- ✅ Accumulation detection functional
- ✅ Distribution detection functional
- ✅ Basic signal generation
- ✅ All tests passing

### Should Have
- ✅ Wave exhaustion detection
- ✅ Climactic volume identification
- ✅ Spring/upthrust patterns
- ✅ Layer 2 integration

### Nice to Have
- Multi-timeframe wave analysis
- Volume profile integration
- Historical wave database
- Wave pattern backtesting

## Timeline

### Day 1 (December 16, 2025)
- Morning: Core implementation (wave tracking)
- Afternoon: Pattern recognition
- Evening: Testing framework

### Day 2 (December 17, 2025)
- Morning: Signal generation & scoring
- Afternoon: Layer 2 integration
- Evening: Complete testing & documentation

## Next Phase Preview

**Phase 2 Week 6-7: XGBoost Ensemble (Layer 4)**
- Feature engineering for ML
- XGBoost model training
- Walk-forward validation
- Integration with Layers 1-3
- Target win rate: 65-68%

---

**Status:** Ready to Begin Implementation  
**Dependencies:** Layer 2 complete ✅  
**Estimated LOC:** ~700 lines (450 layer + 250 tests)

# Layer 0: Multi-Timeframe Trend Foundation Specification

## Overview

**Layer 0** is the foundational layer that establishes the **dominant market trend** across multiple timeframes and provides the **directional bias** for all subsequent layers. It acts as the gatekeeper, ensuring that all opportunity generation layers (Layer 1, Layer 6, etc.) only produce signals that align with the higher-timeframe trend.

## Core Philosophy

> "Trade with the trend on higher timeframes, time entries on lower timeframes."

- **4H timeframe has absolute precedence** - dictates long-only or short-only bias
- **2H and 1H confirm or conflict** with 4H trend
- **30m and 15m are for entry timing only**, not trend determination
- **No counter-trend trades** - if 4H is bullish, Layer 0 blocks all short signals

## Architecture Position

```
Layer 0 (Multi-TF Trend Foundation)
    ↓ Establishes: LONG-ONLY | SHORT-ONLY | NEUTRAL
    ↓
Layer 1 (Traditional Signals) + Layer 6 (TV Alerts)
    ↓ Generate opportunities in allowed direction only
    ↓
Layers 2-5 (Quality Filters)
    ↓ Filter bad opportunities
    ↓
Final Trades: High-quality, trend-aligned entries
```

## 1. Multi-Timeframe Trend Analysis

### 1.1 Timeframe Hierarchy

| Timeframe | Role | Purpose | Weight |
|-----------|------|---------|--------|
| **4H** | Primary Trend | Macro market context - ABSOLUTE AUTHORITY | 50% |
| **2H** | Intermediate Trend | Refines 4H direction | 25% |
| **1H** | Micro Trend | Entry confirmation | 15% |
| **30m** | Local Bias | Structure refinement | 7% |
| **15m** | Execution | Trade timing only | 3% |

### 1.2 Trend Components (Per Timeframe)

Each timeframe is analyzed using **4 pillars**:

#### Pillar 1: Market Structure (40% weight)
- **Bullish**: Higher Highs (HH) + Higher Lows (HL)
- **Bearish**: Lower Highs (LH) + Lower Lows (LL)
- **Ranging**: No clear pattern, price oscillating

**Implementation**:
```python
# Look back 50-100 bars
last_high = recent_highs[-1]
prev_high = recent_highs[-2]
last_low = recent_lows[-1]
prev_low = recent_lows[-2]

if last_high > prev_high and last_low > prev_low:
    structure = "bullish"
elif last_high < prev_high and last_low < prev_low:
    structure = "bearish"
else:
    structure = "ranging"
```

#### Pillar 2: Moving Average Alignment (30% weight)
Uses **EMA 9, 21, 50** stack:

**Bullish**:
- Price > EMA9 > EMA21 > EMA50
- All EMAs sloping upward
- EMAs fanning out (spacing increasing)

**Bearish**:
- Price < EMA9 < EMA21 < EMA50
- All EMAs sloping downward
- EMAs fanning out

**Implementation**:
```python
# Check alignment
bullish_alignment = (
    price > ema9 > ema21 > ema50
    and ema9_slope > 0 and ema21_slope > 0 and ema50_slope > 0
)

bearish_alignment = (
    price < ema9 < ema21 < ema50
    and ema9_slope < 0 and ema21_slope < 0 and ema50_slope < 0
)

# Check fanning
ema_spacing = abs(ema9 - ema21) + abs(ema21 - ema50)
prev_spacing = abs(prev_ema9 - prev_ema21) + abs(prev_ema21 - prev_ema50)
fanning = ema_spacing > prev_spacing
```

#### Pillar 3: MACD (20% weight)
Parameters: 12/26/9

**Bullish**:
- MACD line > Signal line
- Histogram > 0 and expanding
- MACD line rising

**Bearish**:
- MACD line < Signal line
- Histogram < 0 and expanding downward
- MACD line falling

#### Pillar 4: RSI Context (10% weight)
Period: 14

**Bullish Context**: RSI 50-80 and rising
**Bearish Context**: RSI 20-50 and falling
**Overextended**: RSI > 80 or < 20 (caution flag)

### 1.3 Timeframe Scoring

**For each timeframe**, combine the 4 pillars into a trend score:

```python
def score_timeframe_trend(data, timeframe):
    """
    Returns: -2 (strong bearish) to +2 (strong bullish)
    """
    score = 0.0
    
    # Pillar 1: Structure (40%)
    structure = analyze_market_structure(data)
    if structure == "bullish":
        score += 0.8
    elif structure == "bearish":
        score -= 0.8
    elif structure == "ranging":
        score += 0.0
    
    # Pillar 2: MA Alignment (30%)
    ma_state = analyze_ma_alignment(data)
    if ma_state == "bullish":
        score += 0.6
    elif ma_state == "bearish":
        score -= 0.6
    
    # Pillar 3: MACD (20%)
    macd_state = analyze_macd(data)
    if macd_state == "bullish":
        score += 0.4
    elif macd_state == "bearish":
        score -= 0.4
    
    # Pillar 4: RSI Context (10%)
    rsi_state = analyze_rsi_context(data)
    if rsi_state == "bullish":
        score += 0.2
    elif rsi_state == "bearish":
        score -= 0.2
    
    # Normalize to -2 to +2
    return np.clip(score, -2, 2)
```

**Trend Classification**:
- Score > 1.2: **Strong Bullish**
- Score 0.5 to 1.2: **Bullish**
- Score -0.5 to 0.5: **Neutral/Ranging**
- Score -1.2 to -0.5: **Bearish**
- Score < -1.2: **Strong Bearish**

## 2. Hierarchical Trend Resolution

### 2.1 Primary Trend (4H)

**4H trend has absolute authority:**

```python
tf_4h_score = score_timeframe_trend(data_4h, "4H")

if tf_4h_score > 1.2:
    primary_trend = "STRONG_BULLISH"
    allowed_direction = "LONG_ONLY"
elif tf_4h_score > 0.5:
    primary_trend = "BULLISH"
    allowed_direction = "LONG_ONLY"
elif tf_4h_score < -1.2:
    primary_trend = "STRONG_BEARISH"
    allowed_direction = "SHORT_ONLY"
elif tf_4h_score < -0.5:
    primary_trend = "BEARISH"
    allowed_direction = "SHORT_ONLY"
else:
    primary_trend = "NEUTRAL"
    allowed_direction = "NONE"  # No trading!
```

### 2.2 Trend Confirmation (2H, 1H)

**Check if lower timeframes align with 4H:**

```python
def check_trend_alignment(tf_4h_score, tf_2h_score, tf_1h_score):
    """
    Returns: alignment_status, confidence_multiplier
    """
    
    # 4H bullish
    if tf_4h_score > 0.5:
        if tf_2h_score > 0 and tf_1h_score > 0:
            return "ALIGNED_BULLISH", 1.0
        elif tf_2h_score < -0.5 or tf_1h_score < -0.5:
            return "CONFLICTED", 0.3  # Major conflict
        else:
            return "PARTIAL_BULLISH", 0.6  # Some agreement
    
    # 4H bearish
    elif tf_4h_score < -0.5:
        if tf_2h_score < 0 and tf_1h_score < 0:
            return "ALIGNED_BEARISH", 1.0
        elif tf_2h_score > 0.5 or tf_1h_score > 0.5:
            return "CONFLICTED", 0.3
        else:
            return "PARTIAL_BEARISH", 0.6
    
    # 4H neutral
    else:
        return "NEUTRAL", 0.0
```

### 2.3 Entry Timing (30m, 15m)

30m and 15m are **NOT** used for trend determination, only for:
- Entry refinement (pullbacks in direction of 4H trend)
- Local support/resistance
- Candle patterns

**Example**:
- 4H: Strong bullish
- 1H: Bullish
- 30m: Small bearish pullback ✅ (this is GOOD - pullback for entry)
- 15m: Bullish reversal candle ✅ (entry timing)

## 3. Exchange-Based Signal Enhancement

Once **directional bias is established** by multi-TF trend, enhance entry quality with exchange data:

### 3.1 Order Book Imbalance

**Bid/Ask Ratio** (top 5-10 levels):
```python
bid_volume = sum(order_book['bids'][:10]['volume'])
ask_volume = sum(order_book['asks'][:10]['volume'])
imbalance = bid_volume / (bid_volume + ask_volume)

if imbalance > 0.65:
    ob_signal = "BULLISH"  # Strong demand
elif imbalance < 0.35:
    ob_signal = "BEARISH"  # Strong supply
else:
    ob_signal = "NEUTRAL"
```

**Usage**:
- LONG_ONLY bias + bullish OB → **Strong long candidate**
- SHORT_ONLY bias + bearish OB → **Strong short candidate**
- Misalignment → **Reduce signal quality**

### 3.2 Taker Buy/Sell Ratio

**Aggressive flow**:
```python
taker_ratio = taker_buy_volume / taker_sell_volume

if taker_ratio > 1.2:
    taker_signal = "BULLISH"  # Buyers aggressive
elif taker_ratio < 0.83:
    taker_signal = "BEARISH"  # Sellers aggressive
else:
    taker_signal = "NEUTRAL"
```

### 3.3 Cumulative Volume Delta (CVD)

**Net buying/selling pressure**:

**Bullish Accumulation**:
- Price flat/down, CVD rising → Hidden buying
- Price makes lower low, CVD makes higher low → Bullish divergence

**Bearish Distribution**:
- Price flat/up, CVD falling → Hidden selling
- Price makes higher high, CVD makes lower high → Bearish divergence

### 3.4 Open Interest + Funding Rate

**Short Squeeze Setup** (long bias):
- High/rising OI
- Negative funding (shorts paying longs)
- In bullish trend → Explosive upside potential

**Long Squeeze Setup** (short bias):
- High/rising OI
- Positive funding (longs paying shorts)
- In bearish trend → Sharp downside potential

### 3.5 Volume Confirmation

**All signals require volume validation**:
```python
volume_ratio = current_volume / sma(volume, 20)

if volume_ratio > 1.5:
    volume_confirmed = True
    quality_multiplier = min(volume_ratio / 3, 1.5)
else:
    volume_confirmed = False
    quality_multiplier = 0.5
```

## 4. Layer 0 Output

### 4.1 Primary Output: Directional Bias

Layer 0 outputs a **global bias** for the trading system:

```python
@dataclass
class Layer0Signal:
    # Primary trend direction
    allowed_direction: str  # "LONG_ONLY", "SHORT_ONLY", "NONE"
    
    # Trend strength per timeframe
    tf_4h_trend: str  # "STRONG_BULLISH", "BULLISH", etc.
    tf_2h_trend: str
    tf_1h_trend: str
    tf_30m_trend: str
    tf_15m_trend: str
    
    # Trend scores
    tf_4h_score: float  # -2 to +2
    tf_2h_score: float
    tf_1h_score: float
    
    # Alignment
    alignment_status: str  # "ALIGNED_BULLISH", "CONFLICTED", etc.
    confidence_multiplier: float  # 0.0 to 1.0
    
    # Exchange context
    order_book_bias: str  # "BULLISH", "BEARISH", "NEUTRAL"
    taker_flow_bias: str
    cvd_state: str
    oi_funding_setup: str  # "SHORT_SQUEEZE", "LONG_SQUEEZE", "NEUTRAL"
    volume_confirmed: bool
    quality_score: float  # 0.0 to 1.0
    
    # Metadata
    timestamp: datetime
    current_price: float
    key_levels: Dict  # Support/resistance from higher TFs
```

### 4.2 Integration with Other Layers

**Layer 1 and Layer 6** check Layer 0 before generating signals:

```python
def generate_signal(self, data, current_price):
    # Get Layer 0 bias
    layer0_signal = get_layer0_signal()
    
    # Respect directional bias
    if layer0_signal.allowed_direction == "NONE":
        return LayerSignal(direction="neutral", confidence=0.0)
    
    # Generate signal
    signal = self._calculate_signal(data, current_price)
    
    # Block counter-trend signals
    if layer0_signal.allowed_direction == "LONG_ONLY" and signal.direction == "short":
        return LayerSignal(direction="neutral", confidence=0.0)
    
    if layer0_signal.allowed_direction == "SHORT_ONLY" and signal.direction == "long":
        return LayerSignal(direction="neutral", confidence=0.0)
    
    # Apply confidence multiplier
    signal.confidence *= layer0_signal.confidence_multiplier
    signal.metadata['layer0_alignment'] = layer0_signal.alignment_status
    
    return signal
```

## 5. Signal Quality Scoring

### 5.1 Quality Components

Each potential entry gets a **quality score** (0.0 to 1.0):

```python
def calculate_signal_quality(layer0_signal, price_action):
    score = 0.0
    
    # Multi-TF alignment (40%)
    if layer0_signal.alignment_status == "ALIGNED_BULLISH":
        score += 0.4
    elif layer0_signal.alignment_status == "ALIGNED_BEARISH":
        score += 0.4
    elif layer0_signal.alignment_status.startswith("PARTIAL"):
        score += 0.25
    else:  # CONFLICTED
        score += 0.1
    
    # Exchange confirmation (30%)
    exchange_score = 0.0
    if layer0_signal.order_book_bias == trend_direction:
        exchange_score += 0.1
    if layer0_signal.taker_flow_bias == trend_direction:
        exchange_score += 0.1
    if "ACCUMULATION" in layer0_signal.cvd_state and trend == "bull":
        exchange_score += 0.05
    if "DISTRIBUTION" in layer0_signal.cvd_state and trend == "bear":
        exchange_score += 0.05
    if layer0_signal.volume_confirmed:
        exchange_score += 0.05
    score += exchange_score
    
    # Price action (20%)
    if price_action.at_key_level and price_action.has_reversal_pattern:
        score += 0.2
    elif price_action.at_key_level or price_action.has_reversal_pattern:
        score += 0.1
    
    # Squeeze potential (10%)
    if layer0_signal.oi_funding_setup in ["SHORT_SQUEEZE", "LONG_SQUEEZE"]:
        if layer0_signal.oi_funding_setup == "SHORT_SQUEEZE" and trend == "bull":
            score += 0.1
        elif layer0_signal.oi_funding_setup == "LONG_SQUEEZE" and trend == "bear":
            score += 0.1
    
    return min(score, 1.0)
```

### 5.2 Minimum Quality Thresholds

**For Layer 0 to emit a signal**:
- Quality score > 0.4 (minimum)
- Quality score > 0.6 (good)
- Quality score > 0.8 (excellent)

**Layers 2-5 can use this** to filter further:
- Layer 2-3: Accept quality > 0.4
- Layer 4-5: Only accept quality > 0.6

## 6. Implementation Strategy

### Phase 1: Core Multi-TF Trend (Week 1)
1. Create `Layer0MultiTFTrend` class
2. Implement 4-pillar analysis per timeframe
3. Implement hierarchical trend resolution
4. Test: Verify 4H trend detection accuracy

### Phase 2: Exchange Integration (Week 2)
1. Add order book imbalance tracking
2. Add taker flow ratio
3. Add CVD calculation
4. Add OI/funding monitoring
5. Test: Verify exchange signals align with trend

### Phase 3: Quality Scoring (Week 3)
1. Implement signal quality scoring
2. Create `Layer0Signal` output structure
3. Test: Verify quality scores correlate with profitable trades

### Phase 4: Layer Integration (Week 4)
1. Update Layer 1 to respect Layer 0 bias
2. Update Layer 6 to respect Layer 0 bias
3. Update compositor to use Layer 0 confidence multiplier
4. Full system testing

## 7. Expected Improvements

### 7.1 Signal Quality
- **Current**: 20% win rate with Layer 1 alone
- **With Layer 0**: Target 40-50% win rate on raw opportunities
- **After filtering**: Target 60-70% win rate

### 7.2 Trade Frequency
- **Layer 1 alone**: 20 trades per 60 days
- **With Layer 0 blocking counter-trend**: 10-15 trades per 60 days
- **But with Layer 6 adding signals**: 20-30 trades per 60 days
- **After filtering**: 10-20 high-quality trades

### 7.3 Profitability
- **Eliminates counter-trend losses**: Major improvement
- **Trades only with 4H trend**: Higher win rate
- **Exchange confirmation**: Better entry timing
- **Result**: Expect positive returns even before Layers 2-5

## 8. Configuration

```yaml
layer0_config:
  # Timeframe weights
  tf_4h_weight: 0.50
  tf_2h_weight: 0.25
  tf_1h_weight: 0.15
  tf_30m_weight: 0.07
  tf_15m_weight: 0.03
  
  # Trend component weights (per TF)
  structure_weight: 0.40
  ma_weight: 0.30
  macd_weight: 0.20
  rsi_weight: 0.10
  
  # EMA periods
  ema_fast: 9
  ema_medium: 21
  ema_slow: 50
  
  # Thresholds
  strong_trend_threshold: 1.2
  weak_trend_threshold: 0.5
  
  # Exchange settings
  order_book_levels: 10
  ob_imbalance_threshold: 0.65  # >65% bids = bullish
  taker_ratio_bullish: 1.2
  taker_ratio_bearish: 0.83
  volume_multiplier_min: 1.5
  
  # Quality thresholds
  min_quality_score: 0.4
  good_quality_score: 0.6
  excellent_quality_score: 0.8
```

## 9. Testing Strategy

### 9.1 Backtesting
1. Run Layer 0 alone to verify trend detection
2. Compare Layer 1 signals WITH vs WITHOUT Layer 0 filtering
3. Measure improvement in win rate and profitability

### 9.2 Key Metrics
- **Trend accuracy**: % of time 4H trend correctly identifies profitable direction
- **Conflict periods**: How often TFs conflict (should be <20% of time)
- **Signal quality correlation**: Do higher quality scores → higher win rates?
- **Counter-trend blocking**: How many losing trades eliminated?

## 10. Future Enhancements

### Phase 5+:
- **Machine learning on trend patterns**: Train model to recognize complex multi-TF patterns
- **Dynamic timeframe selection**: Auto-adjust which TFs matter most based on market regime
- **Volatility regime detection**: Separate logic for ranging vs trending markets
- **Cross-asset correlation**: Use BTC correlation with ETH, stocks, DXY for confirmation
- **Sentiment integration**: Add funding rate extremes, social sentiment

---

## Summary

**Layer 0** transforms the system from generating random opportunities to **intelligently filtering opportunities based on multi-timeframe trend context and exchange-side confirmations**.

**Key Benefits**:
✅ Eliminates counter-trend trades
✅ Provides directional bias to all layers
✅ Adds exchange-based signal quality
✅ Creates foundation for 60%+ win rate
✅ Reduces drawdowns significantly

**This is the missing piece that will make the entire system institutional-grade.**

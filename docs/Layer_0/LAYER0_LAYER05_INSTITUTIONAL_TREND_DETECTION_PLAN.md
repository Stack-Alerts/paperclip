# Layer 0/0.5 Institutional-Grade Trend Detection Plan

## 🎯 Objective

**Achieve 80%+ trend detection accuracy with PROPER TIMEFRAME NESTING for 15-minute scalp entries.**

**Critical Constraint:** Trends must be actionable on 15m timeframe for Layers 1-6 to find entries/exits.

Based on validation showing current Layer 0/0.5 at ~50% accuracy (not the documented 60-70%), we need a fundamental rethinking using your unique advantage: **real orderbook and trade data** while ensuring timeframe compatibility.

---

## 📊 Current State Analysis

### What Validation Revealed:

| Horizon | Layer 0 | Layer 0.5 | Combined | When Agreed |
|---------|---------|-----------|----------|-------------|
| 6hr | 53.5% | 53.7% | 52.9% | 28.9% ❌ |
| 12hr | 52.0% | 51.3% | 51.4% | 26.9% ❌ |
| 24hr | 49.3% | 48.3% | 48.6% | 24.8% ❌ |

**Critical Issue:** When layers agree, accuracy is 25-29% (WORSE than disagreement!)
- This means they're systematically learning the wrong patterns together
- Both using same failed approach (EMAs + MACD + RSI)

### What Was Tried (All Failed):

1. ❌ **Rule-based Layer 0** (4-pillar: structure, MA, MACD, RSI) → 50%
2. ❌ **Rule-based Layer 0.5** (fast EMAs 5/13/34) → 50%
3. ❌ **ML on 15m** (triple barrier) → 28-47%
4. ❌ **ML on 30m** (couldn't get labels) → Blocked
5. ❌ **ML with enhanced features** → 47% (no improvement)

---

## 💡 Your Unique Advantage: Institutional Data

### What You Have That Others Don't:

**1. Orderbook Data (25 monthly files)**
```
data/raw/orderbook/
├── BTC-USDT_orderbook_2024-01.parquet
├── BTC-USDT_orderbook_2024-02.parquet
...
└── BTC-USDT_orderbook_2025-12.parquet
```

**2. Trade Data**
```
data/raw/trades/
```

**3. OHLCV at Multiple Timeframes**
- 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d

### Why This Matters:

**Traditional indicators (EMAs, MACD, RSI) use only OHLCV.**  
**Institutional traders use orderbook flow and trade data.**

**Key insight from your docs:**
> "To reach 65-85% accuracy, you must have stationary features AND market structure detection."

**Orderbook provides:**
- ✅ **Market structure** (support/resistance levels)
- ✅ **Smart money positioning** (large orders)
- ✅ **Supply/demand imbalance** (bid/ask pressure)
- ✅ **Absorption patterns** (whale accumulation)

---

## 🔬 Research-Backed Approach

### Academic Evidence (from your docs):

1. **"EMA crossovers achieve 70-80% win rates on 1H BTC"** ← But our validation shows 50%!
   - **Why?** Because everyone uses EMAs → no edge
   - **Solution:** Add institutional signals others don't have

2. **"Machine learning models using MACD achieve 86-92% accuracy"** ← But ours got 47%!
   - **Why?** Overfitting on public data
   - **Solution:** Train on orderbook features (proprietary edge)

3. **"RSI14 ranks in top 8 features"** ← But still only 50% accuracy!
   - **Why?** RSI alone insufficient
   - **Solution:** Combine with orderbook imbalance

### The Pattern:

**Public indicators (OHLCV-based)** → No edge → 50% accuracy  
**Private indicators (Orderbook-based)** → Potential edge → 70-80%+ possible

---

## 🚀 New Strategy: Institutional Flow-Based Trend Detection

### Core Hypothesis:

**Trends don't come from price alone. Trends come from ORDER FLOW.**

**When institutions accumulate:**
- Large bids appear deep in orderbook
- Price dips get absorbed (not sold)
- Volume profile shows buying at lows
- **THEN** price trends up (weeks later)

**When institutions distribute:**
- Large asks appear in orderbook
- Price pumps get sold into
- Volume shows selling at highs
- **THEN** price trends down

### The Advantage:

**Traditional traders:** React to price movement (lagging)  
**You:** Detect accumulation BEFORE trend (leading)

---

## 📋 Implementation Plan

### Phase 1: Extract Institutional Orderbook Features (Week 1)

**Goal:** Create features that detect smart money positioning

#### A. Order Book Imbalance (1-2 days)

**Features to extract:**
```python
# Bid-Ask Imbalance
bid_volume_top10 = sum(orderbook['bids'][:10]['size'])
ask_volume_top10 = sum(orderbook['asks'][:10]['size'])
imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)

# Large Order Detection
whale_bid_levels = count_orders_above(threshold=10_BTC)
whale_ask_levels = count_orders_above(threshold=10_BTC)

# Order Book Depth
support_strength = sum(bids_within_1pct_below_price)
resistance_strength = sum(asks_within_1pct_above_price)

# Absorption Rate
price_drops_absorbed = (bids_filled / bids_posted) when price drops
price_pumps_absorbed = (asks_filled / asks_posted) when price pumps
```

**Why this works:**
- Imbalance predicts short-term direction (5-15min)
- Large orders show institutional positioning
- Absorption shows conviction (weak hands vs strong hands)

#### B. Trade Flow Features (1-2 days)

**Features from trade data:**
```python
# Aggressor Classification
buy_volume = sum(trades where aggressor='buy')
sell_volume = sum(trades where aggressor='sell')
trade_flow_imbalance = (buy_vol - sell_vol) / total_vol

# Large Trade Detection  
institutional_buys = count(trades > 5_BTC and aggressor='buy')
institutional_sells = count(trades > 5_BTC and aggressor='sell')

# Trade Velocity
trades_per_minute = count(trades in 1min window)
volume_velocity = sum(volume in 1min window)
```

**Why this works:**
- Aggressive buying = urgent demand (bullish)
- Large trades = institutions moving (leading indicator)
- Velocity = momentum building

#### C. Volume Profile (1 day)

**Features:**
```python
# Point of Control (POC)
poc_level = price_level_with_most_volume
distance_from_poc = (current_price - poc) / poc

# Value Area
value_area_high = 70th_percentile_volume
value_area_low = 30th_percentile_volume
in_value_area = current_price within (VAL, VAH)

# Volume Delta
volume_delta = cumulative(buy_volume - sell_volume)
volume_delta_slope = delta_change_per_hour
```

**Why this works:**
- POC acts as magnet (price returns to it)
- Value area shows where institutions comfortable
- Volume delta shows accumulated positioning

**Total:** ~30-40 new institutional features

### Phase 2: Build Ground Truth Labels WITH TIMEFRAME NESTING (2-3 days)

**CRITICAL: Multi-tier trend detection for 15m scalping:**

```python
def label_nested_trends(current_price, future_prices_1h, future_prices_15m):
    """
    Label trends at MULTIPLE timeframes that nest properly
    
    Layer 0 (Macro): 4H/12H trend (use 4-12 hour horizon)
    Layer 0.5 (Micro): 1H/2H trend (use 1-3 hour horizon)  
    Layers 1-6 (Entry): 15m timing (entries within micro trend)
    """
    
    # LAYER 0: Macro Trend (4H+)
    # For 15m scalping, 24hr trend is TOO BIG - you were right!
    # Use 4-6 hour window for macro trend
    future_4hr = future_prices_1h[4]   # 4 hours ahead
    future_6hr = future_prices_1h[6]   # 6 hours ahead
    
    if (future_4hr > current_price * 1.02 and 
        future_6hr > current_price * 1.03):
        macro_trend = "BULLISH"      # 2-3% over 4-6hr
    elif (future_4hr < current_price * 0.98 and 
          future_6hr < current_price * 0.97):
        macro_trend = "BEARISH"      # -2-3% over 4-6hr
    else:
        macro_trend = "NEUTRAL"
    
    # LAYER 0.5: Micro Trend (1H-2H)  
    # This is what 15m entries actually trade within!
    future_1hr = future_prices_1h[1]   # 1 hour ahead
    future_2hr = future_prices_1h[2]   # 2 hours ahead
    
    if (future_1hr > current_price * 1.01 and 
        future_2hr > current_price * 1.015):
        micro_trend = "BULLISH"      # 1-1.5% over 1-2hr
    elif (future_1hr < current_price * 0.99 and 
          future_2hr < current_price * 0.985):
        micro_trend = "BEARISH"      # -1-1.5% over 1-2hr
    else:
        micro_trend = "NEUTRAL"
    
    # COMBINED: What should system do?
    if macro_trend == "BULLISH" and micro_trend == "BULLISH":
        return "STRONG_LONG"      # Both aligned - aggressive
    elif macro_trend == "BULLISH" and micro_trend == "NEUTRAL":
        return "LONG_PULLBACK"    # Wait for micro to turn bullish
    elif macro_trend == "BULLISH" and micro_trend == "BEARISH":
        return "NO_TRADE"         # Conflicted - stay out
    elif macro_trend == "BEARISH" and micro_trend == "BEARISH":
        return "STRONG_SHORT"     # Both aligned - aggressive
    elif macro_trend == "BEARISH" and micro_trend == "NEUTRAL":
        return "SHORT_PULLBACK"   # Wait for micro to turn bearish
    elif macro_trend == "BEARISH" and micro_trend == "BULLISH":
        return "NO_TRADE"         # Conflicted - stay out
    else:
        return "RANGE_BOUND"      # No clear trend either timeframe
```

**Why this nested approach works:**

**Layer 0 (4-6hr trend):**
- 2-3% movement = tradeable on 1H
- Provides macro direction
- 15m can get 5-10 entries within this

**Layer 0.5 (1-2hr trend):**
- 1-1.5% movement = perfect for 15m scalping!
- Each 15m entry targets 0.3-0.5% (multiple within 1hr trend)
- This is the ACTIONABLE timeframe you mentioned

**Example:**
```
Macro (Layer 0): Bullish 4hr trend (+2.5%)
  └─ Micro (Layer 0.5): Bullish 1hr swing (+1.2%)
      └─ 15m Entry #1: Long at support (+0.4% target)
      └─ 15m Entry #2: Long at pullback (+0.3% target)
      └─ 15m Entry #3: Long at breakout (+0.5% target)
```

**Expected label distribution:**
- 20-30% STRONG_LONG/SHORT (both aligned)
- 15-25% PULLBACK (waiting for micro confirmation)
- 10-15% NO_TRADE (conflicted)
- 30-40% RANGE_BOUND (no clear trend)

### Phase 3: Train Hybrid Model (3-4 days)

**Combine traditional + institutional features:**

#### Feature Sets:

**A. Traditional (OHLCV-based) - 30 features**
- EMAs (12/26/50/200)
- MACD histogram
- RSI (14)
- Bollinger Bands
- ADX / DMI
- Volume MA
- etc.

**B. Institutional (Orderbook/Trade-based) - 40 features**
- Bid/ask imbalance
- Whale order levels
- Absorption rates
- Trade flow
- Volume profile
- Large trade counts
- etc.

**Total:** ~70 features

#### Model Architecture:

**Option 1: Ensemble (Recommended)**
```python
# Train 2 models:
model_traditional = XGBoost(features_traditional)
model_institutional = XGBoost(features_institutional)

# Combine predictions:
final_prediction = 0.4 * model_traditional + 0.6 * model_institutional
```

**Why ensemble:**
- Traditional captures price momentum
- Institutional captures positioning
- Together = complete picture

**Option 2: Single Model**
```python
# All 70 features together
model = XGBoost(features_all)
```

**Option 3: Sequential**
```python
# First check institutional positioning
if institutional_model predicts BULLISH:
    # Then check if price confirms
    if traditional_model predicts BULLISH:
        final = "STRONG_BULLISH"
    else:
        final = "WEAK_BULLISH" (wait for confirmation)
```

#### Training Strategy:

```python
# Walk-forward validation
for year in [2024, 2025]:
    train_data = data[year - 1]  # Previous year
    test_data = data[year]        # Current year
    
    model.fit(train_data)
    accuracy = model.evaluate(test_data)
    
    print(f"{year}: {accuracy:.1%}")
```

**Target:** 70-80% accuracy on test set

### Phase 4: Validation Against Ground Truth (1-2 days)

**Use your existing validation framework:**

```python
# Generate predictions on full dataset
predictions = model.predict(features_2019_to_2025)

# Compare against actual outcomes
results = validate_predictions(
    predictions=predictions,
    actual_outcomes=ground_truth_labels,
    horizons=[6, 12, 24]  # hours
)

# Analyze by timeframe
print("6hr horizon:", results[6]['accuracy'])
print("12hr horizon:", results[12]['accuracy'])
print("24hr horizon:", results[24]['accuracy'])
```

**Success criteria:**
- ✅ 70%+ accuracy on all horizons
- ✅ When model confident (>0.7 probability), 80%+ accuracy
- ✅ No negative correlation (agreement paradox resolved)

### Phase 5: Integration & Deployment (2-3 days)

**Replace existing Layer 0/0.5:**

```python
class Layer0InstitutionalTrend:
    def __init__(self):
        self.model_traditional = load_model('traditional.pkl')
        self.model_institutional = load_model('institutional.pkl')
    
    def generate_signal(self, data, orderbook, trades):
        # Extract features
        features_trad = extract_traditional_features(data)
        features_inst = extract_institutional_features(orderbook, trades)
        
        # Get predictions
        pred_trad = self.model_traditional.predict(features_trad)
        pred_inst = self.model_institutional.predict(features_inst)
        
        # Ensemble
        final_pred = 0.4 * pred_trad + 0.6 * pred_inst
        
        # Convert to signal
        if final_pred > 0.7:
            return "STRONG_BULLISH"
        elif final_pred > 0.5:
            return "BULLISH"
        elif final_pred < -0.7:
            return "STRONG_BEARISH"
        elif final_pred < -0.5:
            return "BEARISH"
        else:
            return "NEUTRAL"
```

---

## 📊 Why This Will Work

### Your Unique Advantages:

1. ✅ **Institutional Data** (orderbook/trades) - others don't have
2. ✅ **Long History** (6+ years) - enough for ML
3. ✅ **Multiple Timeframes** (5m to 1d) - multi-TF validation
4. ✅ **Validation Framework** - proper ground truth testing

### The Edge:

**Everyone uses EMAs → No edge → 50% accuracy**  
**You use orderbook flow → Edge → 70-80% possible**

### Academic Support:

- Orderbook imbalance predicts short-term returns (proven)
- Large orders predict institutional positioning (proven)
- Volume profile identifies support/resistance (proven)
- **Combined with traditional:** Captures complete picture

---

## ⏰ Timeline

| Phase | Task | Duration | Outcome |
|-------|------|----------|---------|
| 1A | **TEST: Extract 2024-2025 features** | **1-2 hours** | **Validate extraction works** |
| 1B | Full extraction (2022-2025) | 3-4 hours | 40 institutional features (full) |
| 2 | Generate nested trend labels | 2-3 days | Layer 0 (4-6hr) + Layer 0.5 (1-2hr) |
| 3 | Train TWO models (macro + micro) | 3-4 days | 70% accuracy each |
| 4 | Validate timeframe nesting | 1-2 days | Confirm 15m entries work |
| 5 | Integration & deployment | 2-3 days | Replace Layer 0/0.5 |

**Testing Phase:** 1-2 hours (2024-2025 data only)  
**Full Implementation:** 2-3 weeks to 70-80% accuracy with proper nesting

---

## 🎯 Success Metrics

### Minimum Viable:
- ✅ **Layer 0:** 65% accuracy on 4-6hr macro trend
- ✅ **Layer 0.5:** 70% accuracy on 1-2hr micro trend
- ✅ **Nested:** When both aligned, 75%+ accuracy
- ✅ **Actionable:** 1-2hr trends allow 5-10 x 15m entries

### Target:
- ✅ **Layer 0:** 75% accuracy on 4-6hr trend
- ✅ **Layer 0.5:** 80% accuracy on 1-2hr trend
- ✅ **Nested:** When aligned, 85%+ accuracy
- ✅ **Entry count:** Average 7-8 scalp opportunities per 2hr trend

### Stretch:
- ✅ 80%+ accuracy on both layers
- ✅ Detect micro-trend 30-60min BEFORE price confirms
- ✅ Layer 0.5 catches 80% of 1hr swings within Layer 0 trend

---

## 🚨 Risk Mitigation

### If Orderbook Features Don't Help (unlikely):
- Still have 30 traditional features
- Should achieve at least 60-65% (baseline)
- Better than current 50%

### If ML Overfits Again:
- Use walk-forward validation (prevents this)
- Ensemble multiple models
- Simplify to rules-based on best features

### If Can't Reach 70%:
- 65% is still improvement over 50%
- Combine with other layers for higher confidence
- Use for filtering, not primary signal

---

## 💡 Key Insights

### Why Current Approach Failed:

1. **Used only public data** (OHLCV) → No edge
2. **Everyone uses same indicators** (EMAs, MACD) → Crowded trade
3. **Tested wrong timeframe** (15m too noisy)
4. **Wrong validation** (resampled data vs real)

### Why New Approach Will Work:

1. **Use institutional data** (orderbook/trades) → Unique edge
2. **Indicators others don't have** (imbalance, flow) → Less crowded
3. **Right timeframe** (1H stable enough)
4. **Proper validation** (ground truth outcomes)

---

## 📋 Immediate Next Steps

### TODAY (Phase 1A - Testing, 1-2 hours):
1. ✅ Review and approve plan
2. ✅ Update extraction script for 2024-2025 only
3. ⏳ **RUN: Extract institutional features from 2024-2025 data**
4. ⏳ Validate feature quality and structure
5. ⏳ Inspect sample output

### TOMORROW (If Phase 1A successful):
1. Run full extraction with all data (2022-2025)
2. Begin Phase 2: Generate nested trend labels
3. Validate label distribution

### THIS WEEK:
1. Complete Phase 2: Nested labels (Layer 0 + 0.5)
2. Begin Phase 3: Train baseline model
3. Add institutional features
4. Compare performance

### NEXT WEEK:
1. Validate on full dataset
2. Compare traditional vs institutional vs hybrid
3. If hitting 70%+, proceed to integration
4. If not, analyze which features matter most

---

## 🎯 Bottom Line

**You were right to focus on trend detection as the foundation.**

**You were right that current 50% accuracy isn't good enough.**

**The solution:** Use your unique advantage (institutional data) that others don't have.

**Traditional indicators** (EMAs, MACD, RSI) → Public → No edge → 50%  
**Institutional signals** (orderbook, flow, absorption) → Private → Edge → 70-80%

**This is the path to 80%+ accuracy.**

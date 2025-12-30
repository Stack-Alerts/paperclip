# Layer 0.5 Feature Gap Analysis

## 🔍 Current Features vs XGBoost Guide Requirements

### What We Already Have ✅ (72 features)

**From `generate_market_invariant_features.py`:**

1. **Relative Price Position (10 features)** ✅
   - price_vs_ema9/21/50/100/200
   - All normalized as ratios

2. **Momentum (15 features)** ✅
   - ROC 1/3/5/10/20
   - Momentum acceleration
   - Momentum strength
   - Price velocity
   - Momentum divergence

3. **Volatility (12 features)** ✅
   - Volatility 5/10/20/50
   - Z-score normalized
   - Volatility regime (expanding/contracting/high/low)

4. **Volume (9 features)** ✅
   - Volume ratios (10/20/50)
   - Volume z-score
   - Volume acceleration
   - Volume spikes/dried up
   - Volume percentile

5. **Price Structure (12 features)** ✅
   - Higher highs/lower lows
   - Making HH/LL
   - Bullish/bearish structure
   - Consolidation/range expansion
   - Range position
   - Near high/low
   - Breakout/breakdown

6. **EMA Alignment (8 features)** ✅
   - 9/21/50/200 alignment checks
   - All EMAs bullish/bearish
   - EMA slopes

7. **Time-Based (6 features)** ✅
   - Hour, day of week
   - Session flags (Asian/London/NY)
   - Weekend flag

---

## 🎯 What XGBoost Guide Requires (vs What We Have)

### 1. Moving Average Alignment ✅ HAVE IT
**Guide says:**
- Price > 50 EMA
- 50 EMA > 200 EMA
- EMA slopes

**We have:**
- ✅ price_vs_ema50, price_vs_ema200
- ✅ ema_50_200_aligned
- ✅ ema_50_slope, ema_200_slope

### 2. Market Structure (HH/HL, LH/LL) ✅ HAVE IT
**Guide says:**
- Higher Highs / Higher Lows
- Lower Highs / Lower Lows

**We have:**
- ✅ higher_high, lower_low
- ✅ making_hh, making_ll
- ✅ bullish_structure, bearish_structure

### 3. RSI Regime ❌ MISSING
**Guide says:**
- RSI > 45 (bullish regime)
- RSI < 55 (bearish regime)
- RSI 45-55 (choppy)

**We have:**
- ❌ No RSI features at all!

### 4. Ichimoku Cloud ❌ MISSING
**Guide says:**
- Price > Cloud (bullish)
- Price < Cloud (bearish)
- Price in Cloud (neutral)

**We have:**
- ❌ No Ichimoku features

### 5. ADX (Trend Strength) ❌ MISSING
**Guide says:**
- ADX > 25 (strong trend)
- ADX < 25 (weak trend)

**We have:**
- ❌ No ADX feature

### 6. Stationary Features ⚠️ PARTIAL
**Guide says:**
- Log returns (not raw prices)
- All features as ratios

**We have:**
- ✅ All price features as ratios (good!)
- ✅ ROC features are % changes (good!)
- ⚠️ But using `.pct_change()` not `log returns`

### 7. 5-Point Scoring System ❌ MISSING
**Guide says:**
- Pre-compute trend score
- 3/5 checks required for trend

**We have:**
- ❌ No scoring system

---

## 📊 Summary: What's Missing

### Critical Missing Features:

1. **RSI (3 features needed)**
   - rsi_14
   - rsi_bull_regime (RSI > 45)
   - rsi_bear_regime (RSI < 55)
   - rsi_neutral (45 <= RSI <= 55)

2. **Ichimoku Cloud (4 features needed)**
   - tenkan_sen
   - kijun_sen
   - senkou_span_a
   - senkou_span_b
   - above_cloud
   - below_cloud
   - in_cloud

3. **ADX (2 features needed)**
   - adx_14
   - strong_trend (ADX > 25)

4. **5-Point Trend Score (3 features needed)**
   - trend_score_bull (0-5)
   - trend_score_bear (0-5)
   - trend_confirmed (score >= 3)

**Total missing: ~12 critical features**

---

## 🎯 Proposed Modification

### Create New Script: `add_xgboost_recommended_features.py`

**What it will do:**
1. Load existing 72 features from `layer05_features_market_invariant.parquet`
2. Calculate missing 12 features (RSI, Ichimoku, ADX, scoring)
3. Merge with existing features → 84 total features
4. Save to NEW file: `layer05_features_enhanced.parquet`
5. Keep original file intact (no breaking changes)

**Why this approach:**
- ✅ Doesn't modify existing feature generator
- ✅ Doesn't break existing system
- ✅ Original 72 features remain unchanged
- ✅ Can easily compare 72-feature vs 84-feature models
- ✅ Additive only (no deletions)

### Code Structure:

```python
# Load existing features
features_df = pd.read_parquet('data/processed/layer05_features_market_invariant.parquet')

# Add RSI features (3 new)
df['rsi_14'] = calculate_rsi(df['close'], 14)
df['rsi_bull_regime'] = (df['rsi_14'] > 45).astype(int)
df['rsi_bear_regime'] = (df['rsi_14'] < 55).astype(int)

# Add Ichimoku features (3 new)
# ... calculate cloud components
df['above_cloud'] = (price > senkou_a) & (price > senkou_b)
df['below_cloud'] = (price < senkou_a) & (price < senkou_b)
df['in_cloud'] = ~above_cloud & ~below_cloud

# Add ADX features (2 new)
df['adx_14'] = calculate_adx(df, 14)
df['strong_trend'] = (df['adx_14'] > 25).astype(int)

# Add 5-point scoring (3 new)
df['trend_score_bull'] = calculate_bull_score(df)  # uses existing features
df['trend_score_bear'] = calculate_bear_score(df)
df['trend_confirmed'] = (df['trend_score_bull'] >= 3) | (df['trend_score_bear'] >= 3)

# Merge with existing features
enhanced_features = features_df.join(new_features)

# Save to NEW file
enhanced_features.to_parquet('data/processed/layer05_features_enhanced.parquet')
```

### Impact:
- Original system: **UNCHANGED**
- New enhanced features: **AVAILABLE**
- Can test both versions
- If enhanced works better → use it
- If not → keep original

---

## 🚀 Proposal for Your Approval

### What I want to create:

**File:** `scripts/ml_training/add_xgboost_recommended_features.py`

**Purpose:** Add 12 missing features from XGBoost guide

**Input:** 
- `data/processed/layer05_features_market_invariant.parquet` (existing 72 features)
- `data/raw/BTC_USDT_PERP_15m.csv` (for OHLC data)

**Output:**
- `data/processed/layer05_features_enhanced.parquet` (84 features = 72 existing + 12 new)

**Changes to existing files:** 
- ❌ NONE (purely additive)

**New features to add:**
1. RSI (3 features)
2. Ichimoku Cloud (3 features)
3. ADX (2 features)
4. 5-Point Scoring (4 features)

**Then:**
- Retrain model with 84 features
- Compare vs 72-feature model
- Expected: 47% → 65-75% precision

---

## ✅ Approval Needed

**Question:** May I create `add_xgboost_recommended_features.py` to add the 12 missing features?

**Guarantees:**
- Won't modify existing `generate_market_invariant_features.py`
- Won't change existing feature files
- Purely additive (new file, new features)
- Can easily rollback if it doesn't work

**Your approval?**

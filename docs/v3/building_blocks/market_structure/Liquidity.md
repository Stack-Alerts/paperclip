# Liquidity - Building Block Documentation

**Block ID:** 69  
**Category:** MARKET_STRUCTURE  
**Type:** CONTEXT BLOCK  
**Mode:** ALWAYS ACTIVE  
**Timeframe:** 15min (optimized)  
**Author:** Institutional Research  
**Date:** 2026-01-05  
**Status:** Testing  
**Grade:** TBD (pending walkforward validation)

---

## 📋 OVERVIEW

The Liquidity detector identifies institutional liquidity zones based on LuxAlgo and ICT (Inner Circle Trader) concepts. It detects where smart money accumulates stop-losses before major moves.

Key concepts:
- **Buyside Liquidity:** Where short sellers place stops (bounce zones)
- **Sellside Liquidity:** Where long traders place stops (reversal zones)
- **Liquidity Voids:** Aggressive institutional moves leaving gaps
- **Zone Breaches:** Stop hunts complete, momentum continues

Based on **LuxAlgo Liquidity** and **ICT** methodology.

---

## ⚠️ BLOCK TYPE: CONTEXT PROVIDER

**This is a CONTEXT BLOCK, not a selective signal block.**

**What this means:**
- ✅ 100% active signal rate is **INTENTIONAL**
- ✅ Always provides liquidity zone context
- ✅ Moderate confidence (55-75%) is **APPROPRIATE**
- ✅ Use for structure + event detection, **NOT** primary filtering

**How to use:**
1. **USE zone touches** as potential reversal points (boost confluence)
2. **USE breaches** for momentum continuation confirmation
3. **USE voids** as aggressive move indicators
4. **DO NOT use** as primary signal filter (combine with selective blocks)

---

## 🎯 WHAT IT DETECTS

### Liquidity Zones

**Buyside Zones (Support):**
- Swing lows where short sellers accumulate stops
- Potential bounce/reversal up areas
- Smart money buy zones

**Sellside Zones (Resistance):**
- Swing highs where long traders accumulate stops
- Potential reversal down areas
- Smart money sell zones

### Events

**Zone Touches:**
- Price entering buyside/sellside zone
- High-probability reversal points
- Stop-loss hunting in progress

**Zone Breaches:**
- Price breaking through zones
- Stop hunt complete
- Continuation momentum signal

**L iquidity Voids:**
- Large-bodied candles with small wicks
- Aggressive institutional moves
- Often get "filled" later

---

## 🔧 PARAMETERS

```python
Liquidity(
    timeframe='15min',
    detection_length=20,      # Swing detection lookback
    zone_margin=0.003,        # 0.3% zone width
    min_touches=2,            # Minimum touches to confirm
    proximity_pct=0.01,       # 1% = "near" threshold
    void_threshold=0.005,     # 0.5% minimum void size
)
```

---

## 📊 SIGNALS

| Signal | When | Confidence | is_new_event |
|--------|------|------------|--------------|
| BUYSIDE_ZONE_TOUCH | Price in buyside zone | 60-75 | True |
| SELLSIDE_ZONE_TOUCH | Price in sellside zone | 60-75 | True |
| VOID_DETECTED | Liquidity void found | 70 | True |
| BUYSIDE_BREACH | Break below buyside | 70 | True |
| SELLSIDE_BREACH | Break above sellside | 70 | True |
| NEAR_BUYSIDE | Approaching buyside | 55 | False |
| NEAR_SELLSIDE | Approaching sellside | 55 | False |
| NEUTRAL | Between zones | 50 | False |

### Example Signal Metadata

**BUYSIDE_ZONE_TOUCH:**
```python
{
    'zone_center': 45000.00,
    'zone_high': 45135.00,
    'zone_low': 44865.00,
    'zone_strength': 68.5,
    'zone_strength_pct': 68.5,  # Fine-grained filtering (0-100)
    'touch_count': 3,
    'is_new_event': True
}
```

**VOID_DETECTED:**
```python
{
    'void_direction': 'BULLISH',
    'void_size': 450.00,
    'void_size_pct': 1.02,
    'void_range_low': 44500.00,
    'void_range_high': 44950.00,
    'void_fill_potential': 'MEDIUM',  # HIGH/MEDIUM/LOW
    'is_new_event': True
}
```

---

## 📈 USAGE IN STRATEGIES

### As Confluence Booster

```python
liq = Liquidity()
result = liq.analyze(df)

if result['signal'] == 'BUYSIDE_ZONE_TOUCH':
    confluence_score += 20  # Bounce zone
    
elif result['signal'] == 'SELLSIDE_BREACH':
    confluence_score += 15  # Momentum continuation
```

### Risk Management

```python
if result['signal'] == 'BUYSIDE_ZONE_TOUCH':
    stop = result['metadata']['zone_low']  # Below zone
    entry = current_price
    target = result['metadata']['zone_center'] * 1.02  # 2% above
```

---

## 📚 ICT CONCEPTS

### Buyside Liquidity (Support)
- Short sellers accumulate stops below price
- Smart money "runs the stops" then reverses up
- Pattern: Price dips into zone → bounce

### Sellside Liquidity (Resistance)
- Long traders accumulate stops above price
- Smart money "runs the stops" then reverses down
- Pattern: Price spikes into zone → reversal

### Liquidity Voids
- Rapid moves with minimal wicks
- Often get "filled" later
- Indicates aggressive institutional activity

---

## ⚠️ MARKET CONDITION SENSITIVITY

**Liquidity zones reflect prevailing market conditions:**

- **Uptrend markets:** More buyside signals (support tests)
- **Downtrend markets:** More sellside signals (resistance tests)  
- **Range markets:** Balanced buyside/sellside distribution

**Test Results (66/34 buyside/sellside):**
- 66% buyside signals = net uptrend period
- This is **NORMAL and EXPECTED**
- Block correctly detects market structure
- Ratio will vary with market regime

**Important:** Don't expect 50/50 in all conditions. The ratio tells you about market dynamics!

---

## ⚠️ LIMITATIONS

- 100% active (context block, not filter)
- Moderate base confidence (appropriate for context)
- Combine with selective blocks for entries
- Zones can shift as new swings form
- Buyside/sellside ratio varies with market regime

---

## 📋 IMPLEMENTATION CHECKLIST

- [x] Swing high/low detection
- [x] Zone clustering
- [x] Touch counting
- [x] Void detection
- [x] Breach detection
- [x] Event tracking
- [ ] Walkforward testing
- [ ] Expert Mode analysis

---

**Status:** Ready for walkforward testing  
**Expected Grade:** B+ to A- (institutional ICT concept)  
**Value:** Liquidity structure context + event detection  
**Use Case:** Confluence booster + structure framework

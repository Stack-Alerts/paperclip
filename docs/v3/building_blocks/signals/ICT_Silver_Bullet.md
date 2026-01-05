# ICT Silver Bullet - Building Block Documentation

**Block ID:** 74  
**Category:** SIGNALS  
**Type:** SIGNAL BLOCK  
**Mode:** SELECTIVE (only on FVG retest setups)  
**Timeframe:** 3-15min (intraday only)  
**Author:** Institutional Research  
**Date:** 2026-01-05  
**Status:** Testing  
**Grade:** TBD (pending walkforward validation)

---

## 📋 OVERVIEW

ICT Silver Bullet detects Fair Value Gaps (FVGs) during three institutional trading windows and generates signals when price retests these gaps.

**Key Features:**
- Three Silver Bullet sessions (London, AM, PM)
- Fair Value Gap detection (bullish/bearish)
- FVG retest confirmation
- Trend alignment filtering
- Risk/reward calculation

Based on **Inner Circle Trader (ICT) Silver Bullet** methodology.

---

## ⚠️ BLOCK TYPE: SIGNAL BLOCK

**This is a SIGNAL BLOCK - selective, high-quality signals only.**

**What this means:**
- ✅ Only triggers on FVG retest setups
- ✅ Three institutional windows analyzed
- ✅ Trend-aligned FVGs preferred
- ✅ Clear entry/stop/target levels
- ✅ Use as primary or confirmation signal

**How it works:**
1. **Identify session** - Determine Silver Bullet window
2. **Detect FVGs** - Find gaps in recent price action
3. **Check alignment** - Verify trend alignment
4. **Detect retest** - Price returns to FVG zone
5. **Generate signal** - Confirm setup with targets

---

## 🎯 WHAT IT DETECTS

### Silver Bullet Sessions

**LONDON_OPEN (3-4 AM NY time):**
- Asian/European market transition
- Clean price moves, low noise
- Good for overnight setups

**AM_SESSION (10-11 AM NY time):**
- US market open + 30 minutes
- High volatility, strong directional moves
- Best session for main trend

**PM_SESSION (2-3 PM NY time):**
- Pre-close institutional rebalancing
- European market close overlap
- Good for continuation moves

### Signals

**BULLISH_FVG_RETEST:**
- Bullish FVG detected (gap up)
- Price retests FVG support
- Entry at FVG zone
- Confidence: 70-90%

**BEARISH_FVG_RETEST:**
- Bearish FVG detected (gap down)
- Price retests FVG resistance
- Short entry at FVG zone
- Confidence: 70-90%

**BULLISH_FVG_IN_ZONE:**
- Price in bullish FVG zone
- Not yet a confirmed retest
- Monitor for entry
- Confidence: 60-75%

**BEARISH_FVG_IN_ZONE:**
- Price in bearish FVG zone
- Not yet a confirmed retest
- Monitor for short entry
- Confidence: 60-75%

**FVG_PRESENT:**
- FVGs detected but no retest
- Awaiting price action
- Confidence: 50%

**NEUTRAL:**
- No FVGs detected
- No setup present

---

## 🔧 PARAMETERS

```python
ICTSilverBullet(
    timeframe='15min',
    min_gap_pct=0.1,             # Minimum gap size (%)
    trend_aligned_only=True,     # Only trend-aligned FVGs
)
```

### Critical Parameters:

**min_gap_pct (0.1):**
- Minimum gap size as % of price
- 0.1%: More FVGs (noisier)
- 0.2%: Balanced (recommended for BTC)
- 0.3%+: Fewer, larger institutional gaps

**trend_aligned_only (True):**
- True: Only show FVGs aligned with trend
- False: Show all FVGs
- Recommended: True for higher win rate

**Timeframe requirements:**
- 3-5 min: Very active, many signals
- 15 min: Balanced (recommended)
- 30 min+: Too few FVGs for intraday

---

## 📊 SIGNALS & METADATA

### Example: BULLISH_FVG_RETEST

```python
{
    'signal': 'BULLISH_FVG_RETEST',
    'confidence': 85,
    'metadata': {
        'fvg_type': 'bullish',
        'fvg_size': 125.50,
        'fvg_size_pct': 0.28,
        'fvg_high': 45125.50,
        'fvg_low': 45000.00,
        'current_price': 45050.00,
        'session': 'am_session',
        'trend': 'bullish',
        'trend_aligned': True,
        'is_retest': True,
        'support_resistance': 45000.00,
        'stop_loss': 44910.00,
        'target': 45802.50,
        'risk_reward_ratio': 5.4,
        'is_new_event': True
    }
}
```

---

## 📈 USAGE IN STRATEGIES

### As Primary Entry Signal

```python
silver_bullet = ICTSilverBullet()
result = silver_bullet.analyze(df)

# Entry on FVG retest
if result['signal'] == 'BULLISH_FVG_RETEST':
    if result['confidence'] >= 80:
        # High-quality setup
        entry_price = result['metadata']['current_price']
        stop_loss = result['metadata']['stop_loss']
        target = result['metadata']['target']
        
        enter_long(entry_price, stop_loss, target)

# Or for shorts
elif result['signal'] == 'BEARISH_FVG_RETEST':
    if result['confidence'] >= 80:
        enter_short(...)
```

### As Confluence Signal

```python
# Combine with other blocks
if other_signal == 'BULLISH':
    if result['signal'] in ['BULLISH_FVG_RETEST', 'BULLISH_FVG_IN_ZONE']:
        if result['metadata']['trend_aligned']:
            confluence_score += 25  # Strong confluence
```

### Session-Specific Trading

```python
# Focus on AM session (highest probability)
if result['metadata']['session'] == 'am_session':
    if result['signal'] == 'BULLISH_FVG_RETEST':
        # Premium setup
        position_size *= 1.5  # Increase size
```

---

## 💡 PARAMETER TUNING GUIDE

**For Crypto (Volatile):**
```python
min_gap_pct=0.2,          # Larger gaps for BTC
trend_aligned_only=True   # Filter noise
```

**For Stocks (Less Volatile):**
```python
min_gap_pct=0.1,          # Smaller gaps OK
trend_aligned_only=True
```

**For Aggressive Trading:**
```python
min_gap_pct=0.1,
trend_aligned_only=False  # More signals
```

---

## 🎯 CONFIDENCE SCORING

Confidence is calculated based on:

1. **Base:** 65

2. **Retest Confirmation:** +15
   - True retest (price was outside, now in)

3. **Trend Alignment:** +10
   - FVG matches trend direction

4. **Premium Session:** +5
   - AM or PM session

5. **Institutional Size:** +5
   - Gap > 0.3% of price

**Final Range:** 50-90%

---

## 📊 SIGNAL INTERPRETATION

**Fair Value Gap (FVG):**
- Price gap where no trading occurred
- Institutional order flow zone
- Acts as support (bullish) or resistance (bearish)
- 70-80% probability of retest

**Bullish FVG:**
- Bar2 low > Bar1 high (gap up)
- Support level = Bar1 high
- Buy when retested

**Bearish FVG:**
- Bar2 high < Bar1 low (gap down)
- Resistance level = Bar1 low
- Sell when retested

**Retest:**
- Price returns to FVG zone
- Confirms institutional interest
- Best entry opportunity

---

## ⚠️ LIMITATIONS

- Requires intraday data (3-15 min bars)
- Only works during specific sessions
- NY timezone required for session detection
- FVGs may not always retest (20-30% never fill)
- Crypto markets don't follow traditional sessions
- Requires trend for alignment filtering

---

## 💡 BEST PRACTICES

**✅ DO:**
- Use on 3-15 minute timeframes
- Wait for retest confirmation
- Respect the FVG zone boundaries
- Use provided stop loss levels
- Focus on AM session for best setups
- Combine with volume confirmation
- Trade trend-aligned FVGs only
- Monitor risk/reward ratio (>2:1)

**❌ DON'T:**
- Trade on hourly or daily charts
- Enter before retest confirmation
- Move stops or adjust FVG zones
- Ignore trend alignment
- Trade during off-hours
- Over-leverage on single setup
- Trade counter-trend FVGs as primary
- Ignore session context

---

## 📋 IMPLEMENTATION CHECKLIST

- [x] Session detection (3 windows)
- [x] FVG detection (bullish/bearish)
- [x] Trend detection
- [x] FVG retest detection
- [x] Trend alignment filtering
- [x] Confidence scoring
- [x] Stop/target calculation
- [ ] Walkforward testing
- [ ] Expert Mode analysis

---

**Status:** Ready for testing  
**Expected Grade:** B to A- (institutional FVG methodology)  
**Value:** ICT Silver Bullet retest setups  
**Use Case:** Primary entry signals + confluence + institutional zones

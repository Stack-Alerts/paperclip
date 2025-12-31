# Master Building Block Document - EXPANDED v3.1
## Optimized for Cline/Claude Sonnet 4.5 & Bitcoin Crypto Trading

**Version:** v3.1 (Expanded with ICT, SMC, Elliott Wave, and Wyckoff Methodology)  
**Document Path:** docs/v3/building_blocks/0_Building_Blocks_Master_Expanded.md  
**Purpose:** Comprehensive tracker for all building blocks (concept blocks, status, documentation) specifically optimized for Bitcoin cryptocurrency market analysis, incorporating advanced methodologies from ICT (Inner Circle Trader), Smart Money Concepts (SMC), Elliott Wave Theory, and Wyckoff Method.

---

## Overview

This master document tracks all building blocks used in systematic trading strategy development. Each building block is a standardized, testable component that can be combined with others in permutation backtests to discover profitable trading patterns.

### Building Block Requirements

- **Backtesting:** Each block requires backtest results on 15min and 30min timeframes
- **Walk-forward Testing:** Must pass walk-forward validation
- **Standardization:** All blocks must follow the same structure and return format
- **Multi-timeframe:** Must work across different timeframes
- **Bitcoin-Specific:** Optimized for Bitcoin 24/7 crypto market characteristics
- **Institutional Focus:** Identify smart money footprints and institutional order flow

### Strategy Development Process

Building blocks are combined in systematic permutation tests to discover profitable patterns. For example:
- **Complex Setup:** 15min liquidity sweep + MACD bullish divergence + Breaker block retest + OTE 70.5% Fibonacci + New York Kill Zone + Fair Value Gap = High-probability long entry
- **If confirmed successful:** Becomes a tradable pattern or confluence for existing patterns

---

## BUILDING BLOCKS CATEGORIES

### 1. Moving Average Indicators
### 2. Oscillator Indicators
### 3. Price Level Indicators (HOD, LOD, HOW, LOW)
### 4. Session & Time-Based Indicators
### 5. Volatility Indicators
### 6. Advanced Price Action Indicators (Order Blocks, FVG)
### 7. Smart Money Concepts (SMC) & ICT Indicators [NEW]
### 8. Elliott Wave Pattern Recognition [NEW]
### 9. Wyckoff Method Phases [NEW]
### 10. Market Structure Indicators [NEW]

---

## 1. MOVING AVERAGE INDICATORS

### Block Name: 50 EMA Vector Break
**Description:** Identifies when price breaks the 50 EMA with a high-volume candle (vector candle).

**Criteria:**
- Break 50 EMA with Vector Candle (volume > 1.5x average volume)
- Determine direction: Bullish break (price crosses above from below) or Bearish break (price crosses below from above)
- Must work on any timeframe (15min, 30min, 1hr, 4hr, 1D)
- Track number of breaks before candle close (for walk-forward/live trading)
- Confirm break with candle close beyond EMA

**Function:** Returns "Bullish Break" or "Bearish Break" with confidence score (0-100)

**BTC-Specific Notes:**
- Bitcoin tends to respect 50 EMA on 4hr and daily timeframes
- During bull markets, 50 EMA acts as dynamic support
- Vector breaks with 2x volume have 65%+ follow-through rate

**Document:** docs/v3/building_blocks/50_EMA_Vector_Break.md  
**File:** src/detectors/building_blocks/50_ema_vector_break.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: 200 EMA Vector Break
**Description:** Breaks the 200 EMA with a vector candle (high volume candle).

**Criteria:**
- Break 200 EMA with Vector Candle
- Must know if the break is breaking bullish or bearish
- Must be able to work on any timeframe
- Track how many breaks of the EMA before the candle close

**Function:** Returns "Bullish Break" or "Bearish Break"

**BTC-Specific Notes:**
- 200 EMA is a critical long-term trend indicator for Bitcoin
- Major bull/bear market divider on daily timeframe
- Price above 200 EMA = bull market bias, below = bear market bias
- Breaks often lead to multi-week trends

**Document:** docs/v3/building_blocks/200_EMA_Vector_Break.md  
**File:** src/detectors/building_blocks/200_ema_vector_break.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## 2. OSCILLATOR INDICATORS

### Block Name: MACD Signal
**Description:** Identifies MACD crossovers and divergences for trend momentum detection.

**Criteria:**
- Standard MACD settings: 12, 26, 9 (market standard)
- **Bullish Signal:** MACD line crosses above Signal line
- **Bearish Signal:** MACD line crosses below Signal line
- **Bullish Divergence:** Price makes lower low, MACD makes higher low
- **Bearish Divergence:** Price makes higher high, MACD makes lower high
- **Histogram Analysis:** Increasing bars = momentum building
- Zero line cross: MACD above 0 = bullish trend, below 0 = bearish trend

**Function:** Returns signal type with histogram momentum indicator

**BTC-Specific Notes:**
- MACD effective on 4hr and daily Bitcoin charts
- During Bitcoin bull runs, MACD crossovers showed 77%+ CAGR vs 61% buy-and-hold
- Combine with volume confirmation to avoid false signals

**Document:** docs/v3/building_blocks/MACD_Signal.md  
**File:** src/detectors/building_blocks/macd_signal.py  
**Backtest Result:** 77% CAGR (historical)  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: RSI Divergence
**Description:** Identifies bullish and bearish divergence between price action and RSI indicator.

**Criteria:**
- Standard RSI period: 14
- **Bullish Divergence:** Price makes lower lows, RSI makes higher lows
- **Bearish Divergence:** Price makes higher highs, RSI makes lower highs
- **Hidden Bullish Divergence:** Price makes higher lows, RSI makes lower lows (continuation)
- **Hidden Bearish Divergence:** Price makes lower highs, RSI makes higher highs (continuation)
- Must identify at least 2 pivot points for valid divergence

**Function:** Returns divergence type with strength score (0-100)

**BTC-Specific Notes:**
- RSI divergence often precedes major Bitcoin trend reversals
- Most effective on daily and 4hr charts
- Failed divergences can occur - always confirm with price action

**Document:** docs/v3/building_blocks/RSI_Divergence.md  
**File:** src/detectors/building_blocks/rsi_divergence.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## 3. PRICE LEVEL INDICATORS

### Block Name: HOD (High of Day)
**Description:** Identifies and tracks the highest price reached during the current trading day.

**Criteria:**
- Calculate highest price from 00:00 UTC to current time
- Update in real-time as new highs are made
- Track number of times HOD has been tested/touched
- Identify breaks above HOD (breakout) vs rejection at HOD (resistance)
- Reset at daily open (00:00 UTC)

**Function:** Returns HOD price level, current distance from HOD, breakout status, number of tests

**BTC-Specific Notes:**
- HOD acts as intraday resistance in Bitcoin markets
- Breakouts above HOD with volume often lead to continuation
- During US trading session (13:00-21:00 UTC), HOD breaks are more significant

**Document:** docs/v3/building_blocks/HOD.md  
**File:** src/detectors/building_blocks/hod.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: LOD (Low of Day)
**Description:** Identifies and tracks the lowest price reached during the current trading day.

**Criteria:**
- Calculate lowest price from 00:00 UTC to current time
- Update in real-time as new lows are made
- Track number of times LOD has been tested/touched
- Identify breaks below LOD (breakdown) vs bounce at LOD (support)

**Function:** Returns LOD price level, current distance from LOD, breakdown status, number of tests

**BTC-Specific Notes:**
- LOD acts as intraday support in Bitcoin markets
- Multiple tests of LOD without breaking often lead to reversal
- Liquidity sweeps below LOD followed by quick recovery are common traps

**Document:** docs/v3/building_blocks/LOD.md  
**File:** src/detectors/building_blocks/lod.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: HOW (High of Week)
**Description:** Identifies and tracks the highest price reached during the current trading week.

**Criteria:**
- Calculate highest price from Monday 00:00 UTC to current time
- Week starts Monday 00:00 UTC, ends Sunday 23:59 UTC
- Monday's high and low often set the weekly range (Weekly Opening Range - WOR)

**Function:** Returns HOW price level, current distance from HOW, breakout status, WOR status

**BTC-Specific Notes:**
- Weekly highs/lows more significant than daily for swing trading
- Monday's range (WOR) often determines weekly directional bias
- Clear break above HOW on Monday signals strong weekly bullish trend

**Document:** docs/v3/building_blocks/HOW.md  
**File:** src/detectors/building_blocks/how.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: LOW (Low of Week)
**Description:** Identifies and tracks the lowest price reached during the current trading week.

**Criteria:**
- Calculate lowest price from Monday 00:00 UTC to current time
- Week starts Monday 00:00 UTC, ends Sunday 23:59 UTC
- Monday's range establishes weekly support/resistance framework

**Function:** Returns LOW price level, current distance from LOW, breakdown status, WOR status

**BTC-Specific Notes:**
- Weekly lows provide strong support zones for swing entries
- Breakdown below LOW often signals weekly bearish trend
- Multiple tests without breaking = strong support

**Document:** docs/v3/building_blocks/LOW.md  
**File:** src/detectors/building_blocks/low.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: US Settlement Price
**Description:** Tracks the price level at US market close (4:00 PM EST) which sets daily candle close.

**Criteria:**
- Capture Bitcoin price at 16:00 EST (21:00 UTC)
- Track settlement price range (16:00-17:00 EST)
- Identify if current price is above/below settlement price
- Settlement price becomes reference point for next day

**Function:** Returns settlement price, current position, distance, next settlement time

**BTC-Specific Notes:**
- Bitcoin often shows increased volatility around US market close
- CME Bitcoin futures settle at 16:00 EST, impacting spot price
- Bitcoin ETF NAV calculated based on 16:00 EST prices
- Post-settlement (17:00-18:00 EST) often shows low liquidity "dead zone"

**Document:** docs/v3/building_blocks/US_Settlement.md  
**File:** src/detectors/building_blocks/us_settlement.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Asia Session 50% Price
**Description:** Calculates the 50% equilibrium level of the Asian trading session range.

**Criteria:**
- Asia session time: 18:00 UTC - 00:00 UTC
- Calculation: Asia 50% = (Asia High + Asia Low) / 2
- Track current price position relative to 50% level
- 50% level often acts as equilibrium/mean reversion point

**Function:** Returns Asia 50% price level, Asia High, Asia Low, current position, range size

**BTC-Specific Notes:**
- Asia session characterized by low volume and tight ranges
- Creates daily liquidity pools for later sessions to sweep
- Price often reverts to 50% during US session after UK manipulation
- Asia 50% retest during US session = high-probability mean reversion setup

**Document:** docs/v3/building_blocks/Asia_Session_50_Percent.md  
**File:** src/detectors/building_blocks/asia_session_50_percent.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## 4. SESSION & TIME-BASED INDICATORS

### Block Name: Session Time
**Description:** Determines current Forex/Crypto trading session and expected market characteristics.

**Criteria:**

**Asia Session (18:00-00:00 UTC)**
- Low volume, tight ranges, accumulation phase
- Creates "Asian Range" for later manipulation

**UK/London Session (02:00-05:00 UTC)**
- Manipulation / "Judas Swing" phase
- Often sweeps Asia high or low to trap traders
- Tends to set the daily trend direction

**US Session (13:00-21:00 UTC)**
- Highest volume (UK/US overlap early)
- Distribution / Continuation or Reversal phase
- "50% Rule": Often reverses to 50% of daily range
- 16:00 EST: US Settlement

**Session Gap (21:00-18:00 UTC)**
- Lowest liquidity period, avoid trading

**Function:** Returns current session, expected volume, bias, weight factor (0.0-1.0), time remaining

**BTC-Specific Notes:**
- Bitcoin trades 24/7 but still influenced by traditional market sessions
- Highest Bitcoin volatility during UK/US overlap (13:00-16:00 UTC)
- US market hours show recent pattern of Bitcoin sell-offs

**Document:** docs/v3/building_blocks/Session_Time.md  
**File:** src/detectors/building_blocks/session_time.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Kill Zones [NEW - ICT]
**Description:** Identifies specific high-probability trading windows when institutional activity is highest.

**Criteria:**

**London Kill Zone (02:00-05:00 AM EST / 07:00-10:00 UTC)**
- Highest volume session
- Creates daily low in bullish markets, daily high in bearish markets
- EUR and GBP pairs most active
- London open offers 25-50 pip opportunities

**New York AM Kill Zone (08:00-11:00 AM EST / 13:00-16:00 UTC)**
- Overlap with London session = maximum liquidity
- USD pairs most active
- Optimal Trade Entry patterns form
- 30-40 pip directional moves common
- Best for breakout strategies

**New York PM Kill Zone (13:00-16:00 PM EST / 18:00-21:00 UTC)**
- Lower volatility than AM session
- End-of-day position squaring
- Useful for next-day trade planning
- US Settlement at 16:00 EST critical

**London Close Kill Zone (10:00-12:00 EST / 15:00-17:00 UTC)**
- Position squaring before European close
- Price often peaks (bullish day) or bottoms (bearish day)
- Good for scalp trades and reversal setups

**Function:** Returns current kill zone status ("Active", "Inactive"), time to next kill zone, expected volatility level, recommended pairs/assets

**BTC-Specific Notes:**
- Bitcoin respects kill zone timing despite 24/7 trading
- New York AM Kill Zone shows highest Bitcoin volatility
- Combine with Fair Value Gaps and Order Blocks during kill zones
- Kill zones increase probability of OTE patterns by 30-40%
- Avoid trading during session gaps (17:00-18:00 EST)

**Document:** docs/v3/building_blocks/Kill_Zones.md  
**File:** src/detectors/building_blocks/kill_zones.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## 5. VOLATILITY INDICATORS

### Block Name: ATR (Average True Range)
**Description:** Measures market volatility by calculating the average range of price movement.

**Criteria:**
- Standard period: 14
- True Range = Max of: (High-Low), |High-PrevClose|, |Low-PrevClose|
- ATR = 14-period moving average of True Range
- Use for stop-loss placement and position sizing

**Function:** Returns ATR value, change direction, volatility level, suggested stop distance

**BTC-Specific Notes:**
- Bitcoin ATR: $500-1000 calm, $3000+ volatile periods
- Use ATR for adaptive stop-losses: Stop = Entry - (2 × ATR) for longs
- Combine with Bollinger Bands for comprehensive volatility analysis

**Document:** docs/v3/building_blocks/ATR.md  
**File:** src/detectors/building_blocks/atr.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: ADR (Average Daily Range)
**Description:** Measures the average price movement from daily high to low.

**Criteria:**
- Standard period: 14 days
- Calculation: ADR = Average of (Daily High - Daily Low) over 14 periods
- Track current day's range vs ADR percentage
- ~57% chance price stays within 100% ADR

**Function:** Returns ADR value, current day range, percentage completed, reversal probability

**BTC-Specific Notes:**
- Bitcoin ADR: $800-1500 typical, $3000+ during high volatility
- When BTC moves >100% of ADR, look for reversal setups
- ADR typically filled during UK/US sessions, not Asia

**Document:** docs/v3/building_blocks/ADR.md  
**File:** src/detectors/building_blocks/adr.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Bollinger Bands
**Description:** Volatility indicator using standard deviations around moving average.

**Criteria:**
- Standard settings: 20-period SMA, 2 standard deviations
- Upper Band = SMA + (2 × SD), Lower Band = SMA - (2 × SD)
- **Bollinger Squeeze:** Narrow bands = major move imminent
- **Overbought:** Price touches/exceeds upper band
- **Oversold:** Price touches/exceeds lower band

**Function:** Returns band values, current position, band width status, pattern detected

**BTC-Specific Notes:**
- Bollinger Bands capture ~90% of Bitcoin price action
- Squeeze often precedes major Bitcoin breakouts
- Price above upper band = overbought, below lower = oversold

**Document:** docs/v3/building_blocks/Bollinger_Bands.md  
**File:** src/detectors/building_blocks/bollinger_bands.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## 6. ADVANCED PRICE ACTION INDICATORS

### Block Name: Order Block
**Description:** Identifies consolidation zones where institutions placed large orders before major moves.

**Criteria:**
- **Bullish Order Block:** Last bearish candle before bullish impulse move
- **Bearish Order Block:** Last bullish candle before bearish impulse move
- Represents area of accumulation/distribution
- Price often returns to order block for retest
- Combine with volume analysis

**Function:** Returns order block type, price range, age, number of retests, validity status

**BTC-Specific Notes:**
- Order blocks particularly effective on Bitcoin 15min-4hr timeframes
- Valid order blocks provide high-probability entry zones
- Priority: Order blocks take precedence over Fair Value Gaps
- Order blocks near swing highs/lows have 70%+ reaction rate

**Document:** docs/v3/building_blocks/Order_Block.md  
**File:** src/detectors/building_blocks/order_block.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Fair Value Gap (FVG)
**Description:** Identifies price imbalances where three-candle patterns create gaps.

**Criteria:**
- **Bullish FVG:** Gap between candle 1 high and candle 3 low
- **Bearish FVG:** Gap between candle 1 low and candle 3 high
- FVG represents price inefficiency - market wants to fill the gap
- **Valid FVG:** Larger gaps (>0.5% of price) more reliable

**Function:** Returns FVG type, gap price range, gap size, mitigation status, age

**BTC-Specific Notes:**
- FVGs extremely common during Bitcoin volatility spikes
- Large FVGs (>1% price) almost always get filled eventually
- Combine with order blocks: FVG + OB = highest probability setup
- FVG at session boundaries especially significant

**Document:** docs/v3/building_blocks/Fair_Value_Gap.md  
**File:** src/detectors/building_blocks/fair_value_gap.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Volume Profile
**Description:** Analyzes volume distribution across price levels to identify HVN and LVN.

**Criteria:**
- **Point of Control (POC):** Price level with highest traded volume
- **Value Area (VA):** Price range containing 70-80% of total volume
- **High Volume Nodes (HVN):** Significant trading activity = support/resistance
- **Low Volume Nodes (LVN):** Minimal trading = price moves through quickly

**Function:** Returns POC price, VAH/VAL prices, current position, HVN/LVN locations

**BTC-Specific Notes:**
- Volume profile critical for Bitcoin support/resistance identification
- Use session-based volume profile for 24/7 crypto markets
- POC often acts as magnet - price returns to test POC multiple times

**Document:** docs/v3/building_blocks/Volume_Profile.md  
**File:** src/detectors/building_blocks/volume_profile.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Pivot Points
**Description:** Calculates support and resistance levels based on previous period's price.

**Criteria:**
- **Pivot Point (PP):** (Prev High + Prev Low + Prev Close) / 3
- **Resistance:** R1 = (2 × PP) - Prev Low, R2 = PP + (High - Low), R3 = High + 2×(PP - Low)
- **Support:** S1 = (2 × PP) - Prev High, S2 = PP - (High - Low), S3 = Low - 2×(High - PP)
- Price above PP = bullish bias, below = bearish bias

**Function:** Returns PP value, R1/R2/R3, S1/S2/S3, current position, nearest pivot, trend bias

**BTC-Specific Notes:**
- Daily pivot points useful for Bitcoin intraday trading
- Weekly pivots provide swing trading reference levels
- Bitcoin often respects pivot levels during consolidation

**Document:** docs/v3/building_blocks/Pivot_Points.md  
**File:** src/detectors/building_blocks/pivot_points.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## 7. SMART MONEY CONCEPTS (SMC) & ICT INDICATORS [NEW]

### Block Name: Liquidity Sweep / Stop Hunt [NEW]
**Description:** Identifies when smart money deliberately triggers stop-loss clusters to create liquidity for large positions.

**Criteria:**
- **Bullish Liquidity Sweep:** Price spikes below support/swing low, triggers stops, then quickly reverses upward
- **Bearish Liquidity Sweep:** Price spikes above resistance/swing high, triggers stops, then quickly reverses downward
- Characteristics: Sharp move beyond key level, low volume on break, high volume on reversal, 1-2 candle reversal
- **Liquidity Zones:** Below swing lows and above swing highs where retail stop-losses cluster
- **Equal Highs/Lows:** Multiple touches at same level = high liquidity pool
- Different from genuine breakout: Sweep shows immediate rejection and return inside level
- Often occurs at obvious technical levels: Round numbers, pivot points, Order Blocks, POC

**Function:** Returns sweep type ("Bullish Sweep", "Bearish Sweep", "None"), swept price level, reversal confirmation status, volume characteristics, liquidity pool size estimate

**BTC-Specific Notes:**
- Bitcoin liquidity sweeps extremely common due to 24/7 market and retail trader concentration
- Most frequent during low liquidity periods: Session gaps, weekends, Asian session
- Stop clusters typically 5-10 pips below support or above resistance
- Institutions often sweep liquidity before major directional moves
- Sweeps at HOD/LOD levels particularly significant
- Wait for sweep + reversal confirmation before entering (don't fade the sweep)
- Place stops beyond obvious clusters, never at round numbers or exact support/resistance

**Trading Strategy:**
- Don't enter before sweep - let it happen first
- Wait for price to close back inside the key level
- Enter on confirmation (engulfing candle or retest)
- Stop-loss beyond the sweep extreme with buffer
- Target: Opposite liquidity pool or next structure level

**Document:** docs/v3/building_blocks/Liquidity_Sweep.md  
**File:** src/detectors/building_blocks/liquidity_sweep.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Breaker Block [NEW - ICT]
**Description:** A failed order block that marks pivotal shift in market structure and liquidity, transforming into support/resistance.

**Criteria:**
- **Bullish Breaker Block:** Forms when price breaks below a bullish order block (closes below OB low), triggers buy-side stops, then reverses upward creating lower low. Failed bullish OB becomes bearish breaker block (resistance).
- **Bearish Breaker Block:** Forms when price breaks above a bearish order block (closes above OB high), triggers sell-side stops, then reverses downward creating higher high. Failed bearish OB becomes bullish breaker block (support).
- **Formation Process:**
  1. Identify established order block (last opposite-colored candle before swing)
  2. Watch for liquidity sweep through the order block
  3. Confirm market structure shift (MSS) - new high/low established
  4. Price reverses, failed OB becomes breaker block
- Breaker blocks exploit liquidity dynamics - institutions break OBs to trap retail traders
- The failed block becomes a magnet for price retest
- Stronger than regular order blocks due to failed expectations

**Function:** Returns breaker block type ("Bullish BB", "Bearish BB"), original OB zone, breaker zone, liquidity sweep level, MSS confirmation, age, retest count, validity status

**BTC-Specific Notes:**
- Breaker blocks extremely powerful in Bitcoin due to high retail participation
- Most effective on 15min to 4hr timeframes for intraday/swing trading
- Breaker blocks near session boundaries (London open, NY open) have highest win rate
- After liquidity sweep, breaker block retest offers ideal entry
- Combine with FVG for "unicorn model" - highest probability setup
- Stop-loss: Just beyond breaker block zone (above for bearish, below for bullish)
- Take profit: Minimum 2:1 RR, target next liquidity pool or structure level
- Failed breaker blocks (price doesn't return) indicate strong directional momentum

**Trading Strategy:**
- Wait for order block to fail (liquidity sweep + MSS)
- Mark the breaker block zone (consecutive candles before swing that was swept)
- Enter on retest of breaker block, not immediately after sweep
- Confirm with price action (rejection wick, engulfing candle)
- Best confluence: Breaker block + FVG + OTE level + Kill zone timing

**Document:** docs/v3/building_blocks/Breaker_Block.md  
**File:** src/detectors/building_blocks/breaker_block.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Optimal Trade Entry (OTE) [NEW - ICT]
**Description:** Uses Fibonacci retracement levels to identify the highest probability entry zone during price pullbacks within trending markets.

**Criteria:**
- **OTE Zone:** Fibonacci 62% to 79% retracement levels of recent swing
- **Precise OTE Level:** 70.5% (equilibrium between 62% and 79%)
- **ICT Fibonacci Settings:**
  - 0 = First profit scale
  - 0.5 = Equilibrium
  - 0.618 = Golden zone (OTE zone)
  - 0.705 = Precise OTE level
  - 0.786 = Golden zone (OTE zone)
  - 1 = Starting position
  - -0.5 = Target 1
  - -1 = Target 2
  - -2 = Symmetrical price
- **Application Process:**
  1. Identify trend direction and market structure (BOS or CHoCH)
  2. Define ICT Dealing Range (most recent swing high to swing low)
  3. Apply Fibonacci from swing high to swing low (downtrend) or low to high (uptrend)
  4. Enter at 62-79% retracement zone, ideally at 70.5%
  5. Confirm with price action, Order Block, or FVG at OTE level
- **Entry Confirmation:** Requires additional confluence - don't enter solely on Fibonacci level
- **Best Timing:** During Kill Zones, especially New York AM (08:00-11:00 EST)
- **Stop Loss:** Beyond 100% Fibonacci level (below for long, above for short)
- **Take Profit:** Previous high/low, liquidity pool, or Fibonacci extension

**Function:** Returns OTE zone range (62-79% levels), precise OTE level (70.5%), current price position relative to OTE, dealing range boundaries, confluence factors (OB/FVG present), entry readiness score (0-100)

**BTC-Specific Notes:**
- OTE particularly effective during Bitcoin trending phases
- Combine OTE with Kill Zone timing for 30-40% higher win rate
- Best entries occur when OTE aligns with Order Block or FVG
- Bitcoin often respects 70.5% level precisely during strong trends
- In ranging markets, OTE less reliable - wait for clear trend
- Higher timeframe trend + lower timeframe OTE = optimal setup
- Entry at OTE provides best risk-to-reward ratio (typically 1:3 or better)

**Trading Strategy - Bullish OTE:**
1. Confirm uptrend on higher timeframe (daily/4hr)
2. Wait for pullback after Break of Structure (BOS)
3. Apply Fib from swing low to swing high
4. Enter buy limit at 70.5% or within 62-79% zone
5. Confirm with bullish Order Block, FVG fill, or price rejection
6. Stop below 100% Fib level
7. Target previous high or -0.5 extension level

**Trading Strategy - Bearish OTE:**
1. Confirm downtrend on higher timeframe
2. Wait for pullback after BOS
3. Apply Fib from swing high to swing low
4. Enter sell limit at 70.5% or within 62-79% zone
5. Confirm with bearish Order Block, FVG fill, or price rejection
6. Stop above 100% Fib level
7. Target previous low or -0.5 extension level

**Document:** docs/v3/building_blocks/Optimal_Trade_Entry.md  
**File:** src/detectors/building_blocks/optimal_trade_entry.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Market Structure Shift (MSS) [NEW - ICT/SMC]
**Description:** Identifies significant changes in market structure that signal potential trend reversals or strong continuation moves.

**Criteria:**
- **MSS Definition:** A decisive break of a key market structure level (swing high in downtrend or swing low in uptrend) that indicates institutional repositioning
- **Bullish MSS:** In a downtrend (series of lower highs and lower lows), price breaks above the most recent lower high, confirming potential trend reversal
- **Bearish MSS:** In an uptrend (series of higher highs and higher lows), price breaks below the most recent higher low, confirming potential trend reversal
- **Difference from BOS:** MSS signals potential reversal, BOS signals continuation
- **Confirmation Requirements:**
  - Clear break of structure with strong momentum
  - Close beyond the structure level (not just a wick)
  - Preferably with increased volume
  - Often accompanied by liquidity sweep before the break
- **Higher Timeframe MSS:** More significant than lower timeframe MSS
- **Multiple Timeframe Analysis:** HTF MSS + LTF confirmation = highest probability

**Function:** Returns MSS status ("Bullish MSS", "Bearish MSS", "No MSS"), broken structure level price, break strength (0-100), volume confirmation, timeframe, confluence factors

**BTC-Specific Notes:**
- MSS on Bitcoin daily chart signals major trend changes (weeks to months)
- 4hr MSS useful for swing trading (days to weeks)
- 15min/1hr MSS for intraday trading
- Bitcoin MSS often occurs during Kill Zones (London/NY open)
- False MSS can occur - wait for retest confirmation
- Combine MSS with Order Block or FVG retest for entries
- MSS preceded by liquidity sweep = higher probability
- After MSS, previous resistance becomes support (and vice versa)

**Trading Strategy:**
1. Identify prevailing market structure (trend direction)
2. Mark key swing highs/lows
3. Wait for decisive break of structure
4. Confirm with volume and momentum
5. Enter on retest of broken structure (now support/resistance)
6. Use Order Block or Breaker Block at retest level
7. Stop-loss beyond the swing that was broken
8. Target: Next major structure level or liquidity pool

**Document:** docs/v3/building_blocks/Market_Structure_Shift.md  
**File:** src/detectors/building_blocks/market_structure_shift.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Break of Structure (BOS) [NEW - SMC]
**Description:** Identifies when price breaks through recent swing highs/lows, confirming trend continuation.

**Criteria:**
- **Bullish BOS:** In an uptrend, price breaks above the most recent higher high, confirming bullish continuation
- **Bearish BOS:** In a downtrend, price breaks below the most recent lower low, confirming bearish continuation
- **Difference from CHoCH/MSS:** BOS confirms continuation, CHoCH/MSS signal reversal
- **Significance:** BOS validates the current trend strength
- **Multiple BOS:** Series of BOS in same direction = very strong trend
- **Confirmation:** Close beyond the swing high/low, preferably with volume

**Function:** Returns BOS type ("Bullish BOS", "Bearish BOS"), broken level price, trend strength score (0-100), volume confirmation

**BTC-Specific Notes:**
- Bitcoin BOS on 4hr/daily charts signals strong trending conditions
- Multiple BOS without CHoCH = ride the trend
- After BOS, pullbacks to Order Blocks provide re-entry opportunities
- BOS during Kill Zones more reliable

**Document:** docs/v3/building_blocks/Break_Of_Structure.md  
**File:** src/detectors/building_blocks/break_of_structure.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Change of Character (CHoCH) [NEW - SMC]
**Description:** Signals potential trend reversal by identifying when market fails to maintain momentum.

**Criteria:**
- **Bullish CHoCH:** In downtrend, price breaks above most recent lower high, signaling potential bullish reversal
- **Bearish CHoCH:** In uptrend, price breaks below most recent higher low, signaling potential bearish reversal
- **Similar to Quasimodo pattern:** Same concept, different name
- **Confirmation:** After CHoCH, wait for retest of supply/demand zone before entering
- **Supply/Demand Zones:** Use with CHoCH to determine entry and stop levels

**Function:** Returns CHoCH type, broken level, reversal probability score (0-100), supply/demand zone

**BTC-Specific Notes:**
- CHoCH on Bitcoin daily chart signals major reversals
- Early warning system for trend changes
- Wait for CHoCH + Order Block/FVG retest for entries
- False CHoCH possible - use confluence for confirmation

**Trading Strategy:**
1. Identify CHoCH pattern formation
2. Mark supply/demand zone based on recent wave
3. Wait for price retracement to the zone
4. Enter in direction of CHoCH
5. Stop-loss few pips beyond zone
6. Close when counter-trend CHoCH forms

**Document:** docs/v3/building_blocks/Change_Of_Character.md  
**File:** src/detectors/building_blocks/change_of_character.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Displacement [NEW - ICT/SMC]
**Description:** Identifies rapid, decisive price movements that signal strong institutional activity and create Fair Value Gaps.

**Criteria:**
- **Definition:** Aggressive candle(s) moving price quickly with minimal retracement
- **Characteristics:**
  - Large candle bodies relative to recent price action (2-3x average candle size)
  - Minimal wicks (strong directional conviction)
  - Often gaps between candles (FVG formation)
  - High volume relative to recent bars
  - Moves through multiple price levels without pullback
- **Bullish Displacement:** Strong upward move breaking through resistance
- **Bearish Displacement:** Strong downward move breaking through support
- **Significance:** Indicates institutional order flow and smart money positioning
- **Creates:** Fair Value Gaps that price likely returns to fill
- **Follow-Through:** Displacement typically continues in same direction after minor retracement

**Function:** Returns displacement status ("Bullish Displacement", "Bearish Displacement", "None"), displacement size (points/percentage), created FVGs, volume confirmation, momentum strength (0-100)

**BTC-Specific Notes:**
- Bitcoin displacement often occurs during Kill Zones (NY AM especially)
- News-driven displacement (FOMC, major economic data) shows strongest follow-through
- Displacement of >3% on 15min Bitcoin chart = highly significant
- After displacement, first pullback to FVG or Order Block = ideal entry
- Displacement without FVG less reliable for retracement entries
- Weekend gaps in Bitcoin can create false displacement signals
- Strongest displacement occurs on Break of Structure (BOS) or MSS

**Trading Strategy:**
1. Identify displacement candle(s) with FVG formation
2. Wait for initial momentum to exhaust
3. Enter on retracement to FVG within the displacement
4. Stop-loss beyond FVG or displacement low/high
5. Target: Continuation of displacement direction to next structure
6. Expect displacement to continue after FVG fill

**Document:** docs/v3/building_blocks/Displacement.md  
**File:** src/detectors/building_blocks/displacement.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Liquidity Pool Identification [NEW - SMC]
**Description:** Identifies areas where stop-loss orders cluster, representing liquidity targets for institutional traders.

**Criteria:**
- **Equal Highs:** Multiple swing highs at same price level = sell-side liquidity pool above
- **Equal Lows:** Multiple swing lows at same price level = buy-side liquidity pool below
- **Round Numbers:** Psychological levels (e.g., $100,000, $50,000 for BTC) attract stops
- **Trendline Liquidity:** Stops placed along trendlines
- **Support/Resistance Liquidity:** Stops cluster just beyond S/R levels
- **Liquidity Grab:** When price spikes to liquidity pool then reverses
- **Size Estimation:** More touches = larger liquidity pool

**Function:** Returns liquidity pool locations, pool size estimate, type (buy-side/sell-side), proximity to current price

**BTC-Specific Notes:**
- Bitcoin round number liquidity pools: $100k, $90k, $80k, $75k, $70k, $50k
- Equal lows during accumulation often swept before upward move
- Institutions target liquidity before significant moves
- Identify liquidity pools, wait for sweep, enter on reversal

**Document:** docs/v3/building_blocks/Liquidity_Pool.md  
**File:** src/detectors/building_blocks/liquidity_pool.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## 8. ELLIOTT WAVE PATTERN RECOGNITION [NEW]

### Block Name: Elliott Wave Count [NEW]
**Description:** Identifies and tracks 5-wave impulse patterns and 3-wave corrective patterns based on Elliott Wave Theory.

**Criteria:**

**Impulse Wave Structure (5 waves in trend direction):**
- **Wave 1:** Initial movement, modest with limited participation
- **Wave 2:** Retracement typically 50-61.8% of Wave 1, doesn't exceed Wave 1 start
- **Wave 3:** Usually longest and strongest wave, increased volume, extends to 161.8% of Wave 1, never shortest wave
- **Wave 4:** Corrective wave, typically 38.2% retracement of Wave 3, doesn't overlap Wave 1
- **Wave 5:** Final trend wave, diminishing momentum, often shows divergence with indicators

**Corrective Wave Structure (3 waves against trend - ABC):**
- **Wave A:** Initial counter-trend move
- **Wave B:** Retracement of Wave A, often 50-61.8%
- **Wave C:** Final corrective move, often extends to 100% or 161.8% of Wave A

**Fibonacci Relationships:**
- Wave 2: typically 50-61.8% retracement of Wave 1
- Wave 3: often 161.8% extension of Wave 1 (golden ratio)
- Wave 4: typically 38.2% retracement of Wave 3
- Wave 5: often 61.8-100% of Wave 1

**Wave Rules (Invalidation Points):**
- Wave 2 never retraces more than 100% of Wave 1
- Wave 3 is never the shortest wave
- Wave 4 never overlaps with price territory of Wave 1

**Function:** Returns current wave count, wave degree, confidence level (0-100), Fibonacci projections for next waves, invalidation levels, expected completion zones

**BTC-Specific Notes:**
- Elliott Waves particularly visible during Bitcoin trending phases
- 2017 Bitcoin bull run showed textbook 5-wave impulse to $20k
- 2020-2021 rally demonstrated clear Elliott structure to $64k
- Wave 3 in Bitcoin often shows 200%+ extensions due to high volatility
- Altcoins display even more pronounced Elliott Wave patterns
- Combine Elliott Waves with RSI/MACD divergence for Wave 5 identification
- Multi-timeframe wave analysis: Daily waves contain hourly sub-waves
- Wave 5 exhaustion often shows bearish divergence on RSI
- Corrective ABC waves provide accumulation opportunities

**Trading Strategy:**
- **Wave 1:** Difficult to identify early, often missed
- **Wave 2:** Accumulation zone, wait for reversal confirmation
- **Wave 3:** Primary target, highest profit potential, enter on Wave 2 completion
- **Wave 4:** Profit-taking opportunity, reduce positions
- **Wave 5:** Final exit, watch for divergence signals
- **Wave A:** Initial short opportunity or stay flat
- **Wave B:** False hope rally, distribution zone
- **Wave C:** Final capitulation, accumulation opportunity

**Document:** docs/v3/building_blocks/Elliott_Wave_Count.md  
**File:** src/detectors/building_blocks/elliott_wave_count.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Elliott Wave Oscillator [NEW]
**Description:** Momentum indicator measuring difference between two moving averages to confirm wave patterns.

**Criteria:**
- **Calculation:** EWO = 5-period SMA - 35-period SMA
- **Wave Confirmation:**
  - Wave 3: Sharp spike in oscillator (highest momentum)
  - Wave 4: Oscillator decline but stays above zero
  - Wave 5: Lower oscillator high than Wave 3 (divergence warning)
- **Zero Line:** Above = bullish momentum, Below = bearish momentum
- **Divergence:** Price makes new high but oscillator doesn't = Wave 5 exhaustion

**Function:** Returns EWO value, wave momentum confirmation, divergence detection, zero-line position

**BTC-Specific Notes:**
- Use EWO to confirm Wave 3 identification (momentum spike)
- EWO divergence at Wave 5 warned of Bitcoin tops in 2017 ($20k) and 2021 ($64k)
- Combine with standard MACD for additional confirmation

**Document:** docs/v3/building_blocks/Elliott_Wave_Oscillator.md  
**File:** src/detectors/building_blocks/elliott_wave_oscillator.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## 9. WYCKOFF METHOD PHASES [NEW]

### Block Name: Wyckoff Accumulation Phase [NEW]
**Description:** Identifies the accumulation phase where smart money quietly builds positions after downtrends.

**Criteria:**

**Phase A: Downtrend Slows**
- **Preliminary Support (PS):** Buying emerges, higher volume, slowing declines
- **Selling Climax (SC):** Panic selling, very high volume, ultimate low point
- **Automatic Rally (AR):** Bounce from SC due to bargain hunting
- **Secondary Test (ST):** Retest of SC area on lower volume, confirms selling exhausted

**Phase B: Building Positions (Cause)**
- Smart money accumulates within trading range
- Price swings test support and demand
- Volume drops on down moves (weak selling pressure)
- Can last weeks or months
- Creates "cause" for future "effect" (markup)

**Phase C: The Spring**
- False breakdown below support shakes out weak holders
- **Spring:** Price quickly recovers below support, indicating strong demand
- Springs not always present but highly significant when they occur
- **Upthrust After Distribution (UTAD) alternative:** False breakout above resistance

**Phase D: Breakout Preparation**
- **Sign of Strength (SOS):** Price breaks above resistance with volume
- **Last Point of Support (LPS):** Retest of breakout level, reduced volume
- Higher lows forming, selling pressure exhausted

**Phase E: Markup**
- Price breaks above trading range with strong volume
- Sustained uptrend begins
- Rallies to new resistance become support

**Function:** Returns current Wyckoff phase (A, B, C, D, E), phase characteristics, volume profile, key price levels (PS, SC, AR, ST, Spring), accumulation progress percentage, estimated markup target

**BTC-Specific Notes:**
- Bitcoin accumulation phases often last 3-12 months
- 2018-2020 Bitcoin showed classic Wyckoff accumulation ($3k-$10k range)
- Phase C spring in Bitcoin often wicks below support by 5-10%
- High volume on SC and SOS confirms institutional activity
- Phase D breakout (SOS) with volume >2x average = strong accumulation
- Accumulation ranges often form after -70% to -85% drawdowns
- Multiple springs possible (complex accumulation)
- Use weekly/daily charts for identifying full accumulation structure

**Trading Strategy:**
- **Phase A:** Observe, don't trade yet
- **Phase B:** Small accumulation positions on support tests
- **Phase C Spring:** Major buying opportunity if confirmed
- **Phase D LPS:** Add to positions on successful retest
- **Phase E:** Ride markup trend, scale out at Fibonacci extensions

**Document:** docs/v3/building_blocks/Wyckoff_Accumulation.md  
**File:** src/detectors/building_blocks/wyckoff_accumulation.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Wyckoff Distribution Phase [NEW]
**Description:** Identifies distribution phase where smart money sells positions to retail at peak prices before markdown.

**Criteria:**

**Phase A: Uptrend Peaks**
- **Preliminary Supply (PSY):** Selling increases with higher volume after rally
- **Buying Climax (BC):** Retail buying frenzy pushes price higher, smart money sells at premium
- **Automatic Reaction (AR):** Sharp drop from BC as buying exhausted
- **Secondary Test (ST):** Rally back toward BC on lower volume, confirms demand weakening

**Phase B: Distribution Range**
- Trading range forms at elevated prices
- Smart money distributes positions to retail
- Volume declining overall
- Multiple tests of support and resistance
- Can last weeks or months

**Phase C: Upthrust After Distribution (UTAD)**
- False breakout above resistance traps late buyers
- Price reverses quickly, confirming weak demand
- UTAD optional but significant when present
- **Spring alternative:** False breakdown (rare in distribution)

**Phase D: Weakness Emerges**
- **Sign of Weakness (SOW):** Sharp drop with high volume signals seller dominance
- **Last Point of Supply (LPSY):** Weak rally fails to reach prior highs
- Lower highs forming, buying pressure exhausted

**Phase E: Markdown**
- Price breaks below support with high volume
- Sustained downtrend begins
- Rallies to new resistance offer short opportunities

**Function:** Returns current Wyckoff phase (A, B, C, D, E), phase characteristics, volume profile, key price levels (PSY, BC, AR, ST, UTAD, SOW, LPSY), distribution progress percentage, estimated markdown target

**BTC-Specific Notes:**
- Bitcoin distribution phases often form at cycle tops
- 2021 Bitcoin $60k-$65k range showed distribution characteristics
- 2017 Bitcoin $17k-$20k exhibited classic distribution before crash
- Phase C UTAD in Bitcoin often exceeds resistance by 3-7%
- SOW (Sign of Weakness) shows >3x average volume on selling
- Distribution ranges can last 2-6 months at major tops
- Multiple UTAD events possible (complex distribution)
- Use daily/weekly charts for full distribution structure identification

**Trading Strategy:**
- **Phase A:** Take profits, reduce long exposure
- **Phase B:** Trade range, short near resistance
- **Phase C UTAD:** Major shorting opportunity if confirmed
- **Phase D LPSY:** Add to short positions on failed rally
- **Phase E:** Ride markdown trend, cover shorts at support levels

**Document:** docs/v3/building_blocks/Wyckoff_Distribution.md  
**File:** src/detectors/building_blocks/wyckoff_distribution.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Wyckoff Re-Accumulation [NEW]
**Description:** Identifies consolidation phase within existing uptrend where smart money adds to positions before continuation.

**Criteria:**
- Occurs after initial markup phase
- Similar structure to accumulation but within uptrend
- Shorter duration than base accumulation (days to weeks vs months)
- Trading range forms at elevated prices
- **Key Difference:** Acts as continuation pattern, not reversal
- Spring or shakeout common before breakout continuation
- Lower volume during range, spike on breakout

**Function:** Returns re-accumulation status, phase progress, range boundaries, breakout probability

**BTC-Specific Notes:**
- Bitcoin re-accumulation ranges common during bull markets
- Often forms at previous resistance turned support
- Provides additional entry opportunities in established trends
- Breakout continuation often matches or exceeds initial markup

**Document:** docs/v3/building_blocks/Wyckoff_Reaccumulation.md  
**File:** src/detectors/building_blocks/wyckoff_reaccumulation.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## 10. MARKET STRUCTURE INDICATORS [NEW]

### Block Name: Swing Point Identification [NEW - ICT]
**Description:** Identifies significant swing highs and swing lows where market structure shifts occur.

**Criteria:**
- **Swing High:** High with lower highs on both sides (minimum 2 candles each side)
- **Swing Low:** Low with higher lows on both sides (minimum 2 candles each side)
- **Higher Timeframe Swing Points:** More significant than lower timeframe
- **Strong Swing:** 5+ candles on each side
- **Weak Swing:** 2-3 candles on each side
- Used to define market structure, identify BOS/CHoCH/MSS

**Function:** Returns swing high/low locations, strength rating, timeframe significance

**BTC-Specific Notes:**
- Daily swing points critical for Bitcoin trend analysis
- 4hr swings useful for swing trading
- Breaking swing points signals structure shifts

**Document:** docs/v3/building_blocks/Swing_Points.md  
**File:** src/detectors/building_blocks/swing_points.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Premium and Discount Zones [NEW - ICT]
**Description:** Divides price range into premium (expensive) and discount (cheap) areas for institutional perspective.

**Criteria:**
- **Calculation:** Use Fibonacci 50% of dealing range as equilibrium
- **Discount Zone:** Below 50% level (0.5 to 1.0 on Fib) - "cheap" prices
- **Premium Zone:** Above 50% level (0 to 0.5 on Fib) - "expensive" prices
- **Equilibrium:** 50% level itself
- **Trading Logic:**
  - Look for longs in discount zone
  - Look for shorts in premium zone
  - Equilibrium acts as decision point

**Function:** Returns current zone (Premium, Equilibrium, Discount), distance from equilibrium, dealing range boundaries

**BTC-Specific Notes:**
- Bitcoin often oscillates between premium and discount zones
- Best entries: Discount zone + bullish confluence (OB, FVG)
- Best shorts: Premium zone + bearish confluence
- Equilibrium often acts as support/resistance

**Document:** docs/v3/building_blocks/Premium_Discount_Zones.md  
**File:** src/detectors/building_blocks/premium_discount_zones.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Internal/External Range Liquidity [NEW - ICT]
**Description:** Identifies liquidity pools inside (internal) and outside (external) of current trading ranges.

**Criteria:**
- **Internal Liquidity:** Stops within current range (equal highs/lows inside range)
- **External Liquidity:** Stops beyond range boundaries (swing highs/lows outside range)
- **Buy-Side Liquidity:** Above swing highs (sell stops)
- **Sell-Side Liquidity:** Below swing lows (buy stops)
- Institutions target external liquidity before major moves

**Function:** Returns internal/external liquidity locations, size estimates, priority targets

**BTC-Specific Notes:**
- Bitcoin often sweeps external liquidity before trend continuation
- During consolidation, internal liquidity grabbed first
- External liquidity sweep = high-probability reversal/continuation setup

**Document:** docs/v3/building_blocks/Range_Liquidity.md  
**File:** src/detectors/building_blocks/range_liquidity.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## IMPLEMENTATION NOTES FOR CLINE (CLAUDE SONNET 4.5)

### Code Structure Requirements

1. **Standardized Return Format:**
```python
{
    "signal": str,  # Main signal output
    "confidence": float,  # 0-100 confidence score
    "metadata": dict,  # Additional context data
    "timestamp": datetime,
    "timeframe": str,
    "confluence_factors": list  # Other aligned signals
}
```

2. **Multi-Timeframe Support:**
- Each building block must accept timeframe parameter
- Support for: 1min, 5min, 15min, 30min, 1hr, 4hr, 1D, 1W
- Higher timeframe alignment increases signal reliability

3. **Bitcoin-Specific Optimizations:**
- Handle 24/7 market (no gaps like stocks)
- Account for high volatility characteristics
- Session-aware processing (Asia, UK, US sessions)
- CME futures settlement impact (16:00 EST)
- Weekend liquidity adjustments

4. **Backtesting Requirements:**
- Walk-forward optimization
- Out-of-sample testing
- Transaction cost modeling (0.1% fees minimum)
- Slippage modeling (0.05-0.1% on volatile moves)
- Maximum drawdown tracking
- Risk-adjusted returns (Sharpe ratio)

5. **Permutation Testing Framework:**
- Systematic combination of multiple building blocks
- Example: [Liquidity Sweep + Breaker Block + OTE 70.5% + NY AM Kill Zone + MACD Bullish Div]
- Automated discovery of profitable pattern combinations
- Statistical significance testing (minimum 100 trades)
- Win rate analysis by market condition

6. **Confluence Scoring System:**
- Weight each building block signal (0-100)
- Combine multiple signals for total confluence score
- Threshold for trade execution: >70 confluence score
- Example scoring:
  - Liquidity Sweep Confirmed: +25 points
  - Breaker Block Retest: +20 points
  - OTE 70.5% Level: +15 points
  - NY Kill Zone Active: +10 points
  - MACD Bullish Divergence: +15 points
  - FVG Present: +15 points
  - **Total: 100 points = Maximum Confluence Trade**

### Performance Targets

- **Minimum Win Rate:** 55%+ (for 1:2 R:R), 65%+ (for 1:1 R:R)
- **Sharpe Ratio:** >1.5
- **Maximum Drawdown:** <20%
- **Profit Factor:** >1.8
- **Minimum Trades:** 100+ for statistical validity
- **Risk-Reward:** Minimum 1:2, optimal 1:3

---

## ADVANCED STRATEGY EXAMPLES

### High-Probability Long Entry Setup (90+ Confluence Score)

**Conditions:**
1. **Market Structure:** Bullish MSS confirmed on 4hr chart (+15 points)
2. **Liquidity:** Sell-side liquidity sweep below recent low (+25 points)
3. **Price Action:** Breaker block retest at swept level (+20 points)
4. **Fibonacci:** OTE 70.5% retracement of recent impulse (+15 points)
5. **Timing:** New York AM Kill Zone (08:00-11:00 EST) (+10 points)
6. **Confluence:** Fair Value Gap present at entry level (+10 points)
7. **Momentum:** MACD showing bullish divergence (+10 points)
8. **Volume:** Volume spike on liquidity sweep reversal (+5 points)

**Total Confluence Score: 110 points (Maximum Quality Setup)**

**Entry:** Buy limit at breaker block / FVG / OTE confluence zone  
**Stop Loss:** Below liquidity sweep low + buffer (2 x ATR)  
**Take Profit:** 
- TP1: 1:2 R:R (take 50% profit)
- TP2: Previous swing high (take 30% profit)
- TP3: Buy-side liquidity pool above (take 20% profit)

**Expected Win Rate:** 75-85%  
**Expected R:R:** 1:3 to 1:5

---

### High-Probability Short Entry Setup

**Conditions:**
1. **Market Structure:** Bearish MSS on daily chart
2. **Wyckoff:** Distribution Phase D - Sign of Weakness detected
3. **Price Action:** Failed bullish order block (now bearish breaker block)
4. **Fibonacci:** Price at premium zone (above 50% of range)
5. **Elliott Wave:** Potential Wave 5 completion with RSI bearish divergence
6. **Timing:** London Kill Zone (02:00-05:00 EST)
7. **Liquidity:** Buy-side liquidity swept above recent high

**Entry:** Sell limit at breaker block retest  
**Stop Loss:** Above liquidity sweep high + buffer  
**Take Profit:** Discount zone, previous swing low, or Wyckoff markdown target

---

## DOCUMENT MAINTENANCE

**Last Updated:** 2025-12-31  
**Next Review:** Quarterly  
**Maintained By:** Trading System Development Team  
**Version Control:** Git repository with detailed commit history

**Version History:**
- v3.0 (2025-12-31): Initial building blocks (MA, Oscillators, Price Levels, Sessions, Volatility, Advanced PA)
- v3.1 (2025-12-31): Expanded with ICT, SMC, Elliott Wave, Wyckoff methodology (27 additional blocks)

---

**Total Building Blocks: 45+**

**Categories:**
1. Moving Averages: 5 blocks
2. Oscillators: 3 blocks
3. Price Levels: 6 blocks
4. Sessions & Time: 2 blocks
5. Volatility: 3 blocks
6. Advanced Price Action: 4 blocks
7. Smart Money Concepts (ICT/SMC): 10 blocks [NEW]
8. Elliott Wave: 2 blocks [NEW]
9. Wyckoff Method: 3 blocks [NEW]
10. Market Structure: 3 blocks [NEW]

**End of Expanded Master Building Blocks Document**
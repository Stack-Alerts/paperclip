# Master Building Block Document 

**Version:** v1
**Document Path:** docs/v3/building_blocks/0_Building_Blocks_Master_Complete.md  
**Purpose:** Comprehensive tracker for all building blocks (concept blocks, status, documentation) specifically optimized for Bitcoin cryptocurrency market analysis, incorporating advanced methodologies from ICT (Inner Circle Trader), Smart Money Concepts (SMC), Elliott Wave Theory, and Wyckoff Method.

---

## Overview

This master document tracks all building blocks used in systematic trading strategy development. Each building block is a standardized, testable component that can be combined with others in permutation backtests to discover profitable trading patterns.

### Building Block Requirements

- **Backtesting:** Each block requires backtest results on 15min and 30min timeframes
- **Walk-forward Testing:** Must pass walk-forward validation
- **Standardization:** All blocks must follow the same structure and return format
- **Multi-timeframe:** Must work across different timeframes (1min to 1W)
- **Bitcoin-Specific:** Optimized for Bitcoin 24/7 crypto market characteristics
- **Institutional Focus:** Identify smart money footprints and institutional order flow

### Strategy Development Process

Building blocks are combined in systematic permutation tests to discover profitable patterns. 

Example 1:
- 15min break of 50 EMA + Stochastic RSI Oversold + 1hr retest of LOD + Order Book liquidity above price = Bullish strategy test
- If confirmed successful, it becomes a tradable pattern or confluence for existing patterns

Example 2
- UK trend was up and continued Asia trend, price is near HOW, US session starts, Price breaks HOW but closes below, RSI overbought, RSI crossing down, Double Top Pattern = Bearish
- If confirmed, US will take price down to near 50% Asia, if breaks through 50% Asia, price will visit near US settlement from previous day.  It is a Short trade

Example 3:
- **Complex Setup:** Liquidity sweep + MACD bullish divergence + Breaker block retest + OTE 70.5% Fibonacci + New York Kill Zone + Fair Value Gap = High-probability long entry
- **Multi-timeframe Alignment:** Daily trend bias + 4hr setup development + 1hr entry confirmation = Optimal confluent setup
- **If confirmed successful:** Becomes a tradable pattern or confluence for existing patterns

### Multi-Timeframe Analysis Framework

Effective building block combination requires multi-timeframe confluence:
- **Higher Timeframe (Daily/Weekly):** Trend direction and macro bias
- **Medium Timeframe (4hr/1hr):** Setup recognition and structure analysis  
- **Lower Timeframe (15min/30min):** Entry execution and micro timing
- **Confluence Multiplier:** Each aligned timeframe increases probability 15-25%
- **Optimal Combinations:** 
  - Day Trading: 15min/1hr/4hr or 5min/15min/1hr
  - Swing Trading: 1hr/4hr/Daily or 4hr/Daily/Weekly
  - Position Trading: Daily/Weekly/Monthly

---

## BUILDING BLOCKS CATEGORIES

### 1. Moving Average Indicators (5 blocks)
### 2. Oscillator Indicators (3 blocks)
### 3. Price Level Indicators (6 blocks)
### 4. Session & Time-Based Indicators (2 blocks)
### 5. Volatility Indicators (3 blocks)
### 6. Advanced Price Action Indicators (4 blocks)
### 7. Smart Money Concepts (SMC) & ICT Indicators (10 blocks)
### 8. Elliott Wave Pattern Recognition (2 blocks)
### 9. Wyckoff Method Phases (3 blocks)
### 10. Market Structure Indicators (3 blocks)
### 11. Pattern-Based Building Blocks (15 blocks)
### 12. Institutional & Volume Indicators: (5 blocks)
### 13. Supply/Demand & Fibonacci: (2 blocks)
### 14. Harmonic Patterns: 1 block (4 patterns) 
### 15. Trend Strength & Momentum: (2 blocks)

**Total: 56 Building Blocks**

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
- Combine with higher timeframe 200 EMA for directional bias

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

### Block Name: 55 EMA Vector Break
**Description:** Breaks the 55 EMA with a vector candle (high volume candle).

**Criteria:**
- Break 55 EMA with Vector Candle
- Must know if the break is breaking bullish or bearish
- Must be able to work on any timeframe
- Track how many breaks of the EMA before the candle close

**Function:** Returns "Bullish Break" or "Bearish Break"

**BTC-Specific Notes:**
- Less commonly used than 50 EMA, but provides slight lag advantage
- Useful for reducing false signals in choppy markets
- Middle ground between 50 EMA and 200 EMA

**Document:** docs/v3/building_blocks/55_EMA_Vector_Break.md  
**File:** src/detectors/building_blocks/55_ema_vector_break.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: 255 EMA Vector Break
**Description:** Breaks the 255 EMA with a vector candle (high volume candle).

**Criteria:**
- Break 255 EMA with Vector Candle
- Must know if the break is breaking bullish or bearish
- Must be able to work on any timeframe
- Track how many breaks of the EMA before the candle close

**Function:** Returns "Bullish Break" or "Bearish Break"

**BTC-Specific Notes:**
- Approximately 1-year moving average on daily charts
- Identifies very long-term trend shifts
- Less noise than 200 EMA but slower to react

**Document:** docs/v3/building_blocks/255_EMA_Vector_Break.md  
**File:** src/detectors/building_blocks/255_ema_vector_break.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: 800 EMA Vector Break
**Description:** Breaks the 800 EMA with a vector candle (high volume candle).

**Criteria:**
- Break 800 EMA with Vector Candle
- Must know if the break is breaking bullish or bearish
- Must be able to work on any timeframe
- Track how many breaks of the EMA before the candle close

**Function:** Returns "Bullish Break" or "Bearish Break"

**BTC-Specific Notes:**
- Extremely long-term trend indicator (~3-year equivalent on daily charts)
- Rarely broken on intraday timeframes
- On weekly/monthly charts, signals major market regime changes
- Used for macro Bitcoin cycle analysis

**Document:** docs/v3/building_blocks/800_EMA_Vector_Break.md  
**File:** src/detectors/building_blocks/800_ema_vector_break.py  
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
- Reduces maximum drawdown from -83% to -62% compared to buy-and-hold

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
- Elliott Wave 5 exhaustion often shows bearish RSI divergence

**Document:** docs/v3/building_blocks/RSI_Divergence.md  
**File:** src/detectors/building_blocks/rsi_divergence.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Stochastic RSI Cross
**Description:** Detects when Stochastic RSI signal lines cross to identify overbought/oversold conditions.

**Criteria:**
- Stochastic RSI consists of two lines: %K line (fast) and %D line (slow, 3-period MA of %K)
- **Bullish Signal (Buy):** %K crosses above %D, especially below 20 level (oversold zone)
- **Bearish Signal (Sell):** %K crosses below %D, especially above 80 level (overbought zone)
- Must work on any timeframe
- Most significant signals occur in oversold (<20) or overbought (>80) regions
- Neutral zone (20-80) signals are less reliable

**Function:** Returns signal type with zone indicator (Oversold, Neutral, Overbought)

**BTC-Specific Notes:**
- Highly effective for Bitcoin swing trading on 4hr/daily timeframes
- In strong trends, can remain overbought/oversold for extended periods
- Best used with trend confirmation from EMAs
- Extreme oversold readings during Buy the Dip opportunities

**Document:** docs/v3/building_blocks/Stochastic_RSI_Cross.md  
**File:** src/detectors/building_blocks/stochastic_rsi_cross.py  
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
- Must work on intraday timeframes (1min, 5min, 15min, 30min, 1hr)

**Function:** Returns HOD price level, current distance from HOD, breakout status, number of tests

**BTC-Specific Notes:**
- HOD acts as intraday resistance in Bitcoin markets
- Breakouts above HOD with volume often lead to continuation
- During US trading session (13:00-21:00 UTC), HOD breaks are more significant
- False breakouts common during low liquidity periods (Asian session gaps)

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
- Reset at daily open (00:00 UTC)
- Must work on intraday timeframes (1min, 5min, 15min, 30min, 1hr)

**Function:** Returns LOD price level, current distance from LOD, breakdown status, number of tests

**BTC-Specific Notes:**
- LOD acts as intraday support in Bitcoin markets
- Multiple tests of LOD without breaking often lead to reversal
- Liquidity sweeps below LOD followed by quick recovery are common traps
- Use with order flow analysis for high-probability entries

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
- Track number of times HOW has been tested

**Function:** Returns HOW price level, current distance from HOW, breakout status, WOR status, number of tests

**BTC-Specific Notes:**
- Weekly highs/lows more significant than daily for swing trading
- Monday's range (WOR) often determines weekly directional bias
- Clear break above HOW on Monday signals strong weekly bullish trend
- Weekend gaps can significantly impact Monday opening and WOR formation

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
- Track number of times LOW has been tested

**Function:** Returns LOW price level, current distance from LOW, breakdown status, WOR status, number of tests

**BTC-Specific Notes:**
- Weekly lows provide strong support zones for swing entries
- Breakdown below LOW often signals weekly bearish trend
- Multiple tests without breaking = strong support
- Weekend price action can create artificial lows during thin liquidity

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
- Settlement price becomes reference point for next day's trading
- US settlement affects Bitcoin ETF pricing and CME futures settlement

**Function:** Returns settlement price, current position, distance, next settlement time

**BTC-Specific Notes:**
- Bitcoin often shows increased volatility around US market close
- CME Bitcoin futures settle at 16:00 EST, impacting spot price
- Bitcoin ETF NAV calculated based on 16:00 EST prices
- Institutional flows often concentrate near settlement time
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
- Asian range creates accumulation zone - price builds liquidity pools at highs and lows

**Function:** Returns Asia 50% price level, Asia High, Asia Low, current position, range size, volume profile

**BTC-Specific Notes:**
- Asia session characterized by low volume and tight ranges
- Creates daily liquidity pools for later sessions to sweep
- Price often reverts to 50% during US session after UK manipulation
- Narrow Asia range often precedes high volatility in UK/US sessions
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

**Weekend**
- Low volume, no Market Maker Activity

**Function:** Returns current session, expected volume, bias, weight factor (0.0-1.0), time remaining, confluence multiplier

**BTC-Specific Notes:**
- Bitcoin trades 24/7 but still influenced by traditional market sessions
- Highest Bitcoin volatility during UK/US overlap (13:00-16:00 UTC)
- US market hours show recent pattern of Bitcoin sell-offs
- Session gaps show stop-hunting behavior before new day starts

**Document:** docs/v3/building_blocks/Session_Time.md  
**File:** src/detectors/building_blocks/session_time.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Kill Zones
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

**Function:** Returns current kill zone status ("Active", "Inactive"), time to next kill zone, expected volatility level, confluence boost factor

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
- Higher ATR = higher volatility, Lower ATR = lower volatility

**Function:** Returns ATR value, change direction, volatility level, suggested stop distance

**BTC-Specific Notes:**
- Bitcoin ATR: $500-1000 calm, $3000+ volatile periods
- Use ATR for adaptive stop-losses: Stop = Entry - (2 × ATR) for longs
- Combine with Bollinger Bands for comprehensive volatility analysis
- ATR helps determine position sizing based on current volatility

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
- ~57% chance price stays within 100% ADR, only ~23% exceed 125% ADR

**Function:** Returns ADR value, current day range, percentage completed, reversal probability, suggested targets

**BTC-Specific Notes:**
- Bitcoin ADR: $800-1500 typical, $3000+ during high volatility
- When BTC moves >100% of ADR, look for reversal setups
- ADR typically filled during UK/US sessions, not Asia
- Useful for identifying when daily move is "exhausted"

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
- **W-Bottom:** Double bottom with second low inside bands = bullish reversal
- **M-Top:** Double top with second high inside bands = bearish reversal

**Function:** Returns band values, current position, band width status, pattern detected

**BTC-Specific Notes:**
- Bollinger Bands capture ~90% of Bitcoin price action
- In trending markets, Bitcoin can "walk the band" (stay near upper/lower band)
- Squeeze often precedes major Bitcoin breakouts
- For Bitcoin: Use 20-period SMA with 2 SD on 4hr and daily charts
- Combine with ATR for confirmation: BB squeeze + rising ATR = breakout

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
- Typically occurs at swing lows (bullish) or swing highs (bearish)
- Price often returns to order block for retest
- Combine with volume analysis

**Function:** Returns order block type, price range, age, number of retests, validity status

**BTC-Specific Notes:**
- Order blocks particularly effective on Bitcoin 15min-4hr timeframes
- Valid order blocks provide high-probability entry zones
- Priority: Order blocks take precedence over Fair Value Gaps
- Order blocks near swing highs/lows have 70%+ reaction rate
- Combine with Fair Value Gaps for "unicorn model" setup

**Document:** docs/v3/building_blocks/Order_Block.md  
**File:** src/detectors/building_blocks/order_block.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Fair Value Gap (FVG)
**Description:** Identifies price imbalances where three-candle patterns create gaps.

**Criteria:**
- **Bullish FVG:** Gap between candle 1 high and candle 3 low (unfilled buy orders)
- **Bearish FVG:** Gap between candle 1 low and candle 3 high (unfilled sell orders)
- FVG represents price inefficiency - market wants to fill the gap
- **Valid FVG:** Larger gaps (>0.5% of price) more reliable
- **Mitigation:** When price returns and fills the FVG

**Function:** Returns FVG type, gap price range, gap size, mitigation status, age, position relative to current price

**BTC-Specific Notes:**
- FVGs extremely common during Bitcoin volatility spikes
- Large FVGs (>1% price) almost always get filled eventually
- Combine with order blocks: FVG + OB = highest probability setup
- FVG at session boundaries especially significant
- Failed FVG fills can signal strong trend continuation

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
- Price gravitates toward POC and VAH/VAL levels

**Function:** Returns POC price, VAH/VAL prices, current position, HVN/LVN locations, volume cluster zones

**BTC-Specific Notes:**
- Volume profile critical for Bitcoin support/resistance identification
- Use session-based volume profile for 24/7 crypto markets
- POC often acts as magnet - price returns to test POC multiple times
- Bitcoin respects HVNs during retracements in trending markets
- LVNs provide low-resistance breakout targets

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
- Breakouts above R1 or below S1 signal strong directional moves

**Document:** docs/v3/building_blocks/Pivot_Points.md  
**File:** src/detectors/building_blocks/pivot_points.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## 7. SMART MONEY CONCEPTS (SMC) & ICT INDICATORS

### Block Name: Liquidity Sweep / Stop Hunt
**Description:** Identifies when smart money deliberately triggers stop-loss clusters to create liquidity for large positions.

**Criteria:**
- **Bullish Liquidity Sweep:** Price spikes below support/swing low, triggers stops, then quickly reverses upward
- **Bearish Liquidity Sweep:** Price spikes above resistance/swing high, triggers stops, then quickly reverses downward
- Characteristics: Sharp move beyond key level, low volume on break, high volume on reversal, 1-2 candle reversal
- **Liquidity Zones:** Below swing lows and above swing highs where retail stop-losses cluster
- **Equal Highs/Lows:** Multiple touches at same level = high liquidity pool
- Often occurs at obvious technical levels: Round numbers, pivot points, Order Blocks, POC

**Function:** Returns sweep type, swept price level, reversal confirmation status, volume characteristics, liquidity pool size estimate

**BTC-Specific Notes:**
- Bitcoin liquidity sweeps extremely common due to 24/7 market and retail trader concentration
- Most frequent during low liquidity periods: Session gaps, weekends, Asian session
- Stop clusters typically 5-10 pips below support or above resistance
- Institutions often sweep liquidity before major directional moves
- Sweeps at HOD/LOD levels particularly significant
- Wait for sweep + reversal confirmation before entering (don't fade the sweep)

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

### Block Name: Breaker Block
**Description:** A failed order block that marks pivotal shift in market structure and liquidity, transforming into support/resistance.

**Criteria:**
- **Bullish Breaker Block:** Failed bullish OB becomes bearish breaker block (resistance)
- **Bearish Breaker Block:** Failed bearish OB becomes bullish breaker block (support)
- **Formation Process:**
  1. Identify established order block
  2. Watch for liquidity sweep through the order block
  3. Confirm market structure shift (MSS) - new high/low established
  4. Price reverses, failed OB becomes breaker block
- Breaker blocks exploit liquidity dynamics - institutions break OBs to trap retail traders
- The failed block becomes a magnet for price retest

**Function:** Returns breaker block type, original OB zone, breaker zone, liquidity sweep level, MSS confirmation, age, retest count, validity status

**BTC-Specific Notes:**
- Breaker blocks extremely powerful in Bitcoin due to high retail participation
- Most effective on 15min to 4hr timeframes for intraday/swing trading
- Breaker blocks near session boundaries (London open, NY open) have highest win rate
- After liquidity sweep, breaker block retest offers ideal entry
- Combine with FVG for "unicorn model" - highest probability setup
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

### Block Name: Optimal Trade Entry (OTE)
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
- **Best Timing:** During Kill Zones, especially New York AM (08:00-11:00 EST)

**Function:** Returns OTE zone range, precise OTE level (70.5%), current position relative to OTE, dealing range boundaries, confluence factors, entry readiness score (0-100)

**BTC-Specific Notes:**
- OTE particularly effective during Bitcoin trending phases
- Combine OTE with Kill Zone timing for 30-40% higher win rate
- Best entries occur when OTE aligns with Order Block or FVG
- Bitcoin often respects 70.5% level precisely during strong trends
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

**Document:** docs/v3/building_blocks/Optimal_Trade_Entry.md  
**File:** src/detectors/building_blocks/optimal_trade_entry.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Market Structure Shift (MSS)
**Description:** Identifies significant changes in market structure that signal potential trend reversals or strong continuation moves.

**Criteria:**
- **MSS Definition:** A decisive break of a key market structure level that indicates institutional repositioning
- **Bullish MSS:** In a downtrend, price breaks above the most recent lower high, confirming potential trend reversal
- **Bearish MSS:** In an uptrend, price breaks below the most recent higher low, confirming potential trend reversal
- **Difference from BOS:** MSS signals potential reversal, BOS signals continuation
- **Confirmation Requirements:**
  - Clear break of structure with strong momentum
  - Close beyond the structure level (not just a wick)
  - Preferably with increased volume
  - Often accompanied by liquidity sweep before the break
- **Higher Timeframe MSS:** More significant than lower timeframe MSS
- **Multiple Timeframe Analysis:** HTF MSS + LTF confirmation = highest probability

**Function:** Returns MSS status, broken structure level price, break strength (0-100), volume confirmation, timeframe, confluence factors

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

### Block Name: Break of Structure (BOS)
**Description:** Identifies when price breaks through recent swing highs/lows, confirming trend continuation.

**Criteria:**
- **Bullish BOS:** In an uptrend, price breaks above the most recent higher high, confirming bullish continuation
- **Bearish BOS:** In a downtrend, price breaks below the most recent lower low, confirming bearish continuation
- **Difference from CHoCH/MSS:** BOS confirms continuation, CHoCH/MSS signal reversal
- **Significance:** BOS validates the current trend strength
- **Multiple BOS:** Series of BOS in same direction = very strong trend
- **Confirmation:** Close beyond the swing high/low, preferably with volume

**Function:** Returns BOS type, broken level price, trend strength score (0-100), volume confirmation

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

### Block Name: Change of Character (CHoCH)
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

### Block Name: Displacement
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

**Function:** Returns displacement status, displacement size (points/percentage), created FVGs, volume confirmation, momentum strength (0-100)

**BTC-Specific Notes:**
- Bitcoin displacement often occurs during Kill Zones (NY AM especially)
- News-driven displacement shows strongest follow-through
- Displacement of >3% on 15min Bitcoin chart = highly significant
- After displacement, first pullback to FVG or Order Block = ideal entry
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

### Block Name: Liquidity Pool Identification
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

## 8. ELLIOTT WAVE PATTERN RECOGNITION

### Block Name: Elliott Wave Count
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
- Combine Elliott Waves with RSI/MACD divergence for Wave 5 identification
- Wave 5 exhaustion often shows bearish divergence on RSI
- Corrective ABC waves provide accumulation opportunities

**Trading Strategy:**
- **Wave 1:** Difficult to identify early, often missed
- **Wave 2:** Accumulation zone, wait for reversal confirmation
- **Wave 3:** Primary target, highest profit potential, enter on Wave 2 completion
- **Wave 4:** Profit-taking opportunity, reduce positions
- **Wave 5:** Final exit, watch for divergence signals

**Document:** docs/v3/building_blocks/Elliott_Wave_Count.md  
**File:** src/detectors/building_blocks/elliott_wave_count.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Elliott Wave Oscillator
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

## 9. WYCKOFF METHOD PHASES

### Block Name: Wyckoff Accumulation Phase
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

**Phase D: Breakout Preparation**
- **Sign of Strength (SOS):** Price breaks above resistance with volume
- **Last Point of Support (LPS):** Retest of breakout level, reduced volume
- Higher lows forming, selling pressure exhausted

**Phase E: Markup**
- Price breaks above trading range with strong volume
- Sustained uptrend begins
- Rallies to new resistance become support

**Function:** Returns current Wyckoff phase (A, B, C, D, E), phase characteristics, volume profile, key price levels, accumulation progress percentage, estimated markup target

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

### Block Name: Wyckoff Distribution Phase
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

**Phase D: Weakness Emerges**
- **Sign of Weakness (SOW):** Sharp drop with high volume signals seller dominance
- **Last Point of Supply (LPSY):** Weak rally fails to reach prior highs
- Lower highs forming, buying pressure exhausted

**Phase E: Markdown**
- Price breaks below support with high volume
- Sustained downtrend begins
- Rallies to new resistance offer short opportunities

**Function:** Returns current Wyckoff phase (A, B, C, D, E), phase characteristics, volume profile, key price levels, distribution progress percentage, estimated markdown target

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

### Block Name: Wyckoff Re-Accumulation
**Description:** Identifies consolidation phase within existing uptrend where smart money adds to positions before continuation.

**Criteria:**
- Occurs after initial markup phase
- Similar structure to accumulation but within uptrend
- Shorter duration than base accumulation (days to weeks vs months)
- Trading range forms at elevated prices
- Acts as continuation pattern, not reversal
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

## 10. MARKET STRUCTURE INDICATORS

### Block Name: Swing Point Identification
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
- Multiple timeframe swing alignment increases significance

**Document:** docs/v3/building_blocks/Swing_Points.md  
**File:** src/detectors/building_blocks/swing_points.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Premium and Discount Zones
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
- Combine with Asia Session 50% for additional confluence

**Document:** docs/v3/building_blocks/Premium_Discount_Zones.md  
**File:** src/detectors/building_blocks/premium_discount_zones.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Internal/External Range Liquidity
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
- Combine with session analysis for timing

**Document:** docs/v3/building_blocks/Range_Liquidity.md  
**File:** src/detectors/building_blocks/range_liquidity.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built


## 11. PATTERN-BASED BUILDING BLOCKS

### Block Name: Head and Shoulders Pattern
**Description:** Identifies bearish reversal pattern characterized by three peaks: left shoulder, head (highest), and right shoulder, with neckline support.

**Criteria:**
- **Formation Components:**
  - Left Shoulder: Initial peak with high volume during end of uptrend
  - Head: Highest peak surpassing both shoulders, often on normal/heavy volume
  - Right Shoulder: Third peak similar to left shoulder but lower than head, on reduced volume
  - Neckline: Support line connecting the two troughs between peaks
- **Confirmation:** Pattern confirmed when price breaks below neckline with increased volume
- **Volume Pattern:** High at left shoulder, diminished at head, lower at right shoulder, surge on break
- **Time Consideration:** Shoulders need not be perfectly symmetrical in time or exact price
- **Pullback Possibility:** Price may retest neckline from below before continuing downward

**Function:** Returns pattern status ("Detected", "Confirmed", "Invalid"), neckline price, shoulder/head coordinates, volume confirmation, completion percentage (0-100), price target projection

**Signal:** SHORT on neckline break with volume confirmation

**BTC-Specific Notes:**
- One of most reliable reversal patterns in Bitcoin with 75-82% success rate
- Pattern formation typically takes 3-8 weeks on daily charts for Bitcoin
- Bitcoin head and shoulders often forms at cycle tops ($20k 2017, $64k 2021)
- Volume confirmation critical - false breaks common without volume spike
- Neckline becomes resistance after break - failed retests = continuation signal
- Common at end of parabolic bull runs when retail FOMO exhausts
- Price target: Measure head-to-neckline distance, project downward from break point

**Trading Strategy:**
- Entry: Short position on neckline break with volume >1.5x average
- Stop-Loss: Above right shoulder high (conservative) or above head (aggressive)
- Take Profit 1: Measured move (head-to-neckline distance)
- Take Profit 2: Next major support level or previous swing low
- Risk-Reward: Typically 1:2 to 1:3
- Combine with RSI bearish divergence at head for higher confidence

**Document:** docs/v3/building_blocks/patterns/Head_And_Shoulders.md  
**File:** src/detectors/building_blocks/patterns/head_and_shoulders.py  
**Backtest Result:** 75-82% success rate (historical studies)  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Inverse Head and Shoulders Pattern
**Description:** Identifies bullish reversal pattern (mirror of H&S) with three troughs: left shoulder, head (lowest), right shoulder, with neckline resistance.

**Criteria:**
- **Formation Components:**
  - Left Shoulder: Initial trough in downtrend, followed by rally
  - Head: Deepest trough (lowest point), creates new low
  - Right Shoulder: Third trough higher than head, approximately equal to left shoulder
  - Neckline: Resistance line connecting peaks between troughs
- **Confirmation:** Pattern confirmed when price breaks above neckline with strong volume
- **Volume Pattern:** Decreases during formation, significant spike on neckline breakout
- **Structure:** Three troughs at similar timeframes showing weakening selling pressure
- **Breakout Validation:** Close above neckline, not just a wick

**Function:** Returns pattern status, neckline price, trough coordinates, volume confirmation, strength score (0-100), target price projection

**Signal:** LONG on neckline breakout with volume confirmation

**BTC-Specific Notes:**
- Extremely reliable bullish reversal - 86% success rate per altFINS backtests
- Forms after significant Bitcoin downtrends (accumulation bottoms)
- Pattern duration: 2-6 months on daily charts during bear markets
- Volume spike on breakout essential - minimum 2x average volume
- Best entries: breakout or pullback retest of neckline (now support)
- Common at Bitcoin cycle bottoms ($3k 2018, $29k 2021)
- Head often forms with capitulation selling (panic volume spike)
- Neckline retest provides safer entry with better R:R

**Trading Strategy:**
- Entry 1: Aggressive - buy on neckline breakout
- Entry 2: Conservative - wait for neckline retest as support
- Stop-Loss: Below right shoulder low (safe) or below head (wider)
- Take Profit: Measure head-to-neckline distance, add to breakout point
- Expected Move: Often equals or exceeds measured target in Bitcoin
- Combine with bullish divergence on RSI/MACD for confirmation
- Risk-Reward: Minimum 1:2, often achieves 1:4 in crypto

**Document:** docs/v3/building_blocks/patterns/Inverse_Head_And_Shoulders.md  
**File:** src/detectors/building_blocks/patterns/inverse_head_and_shoulders.py  
**Backtest Result:** 86% success rate (altFINS study)  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Double Top Pattern
**Description:** Identifies bearish reversal pattern with two peaks at approximately same price level separated by trough (M-shaped).

**Criteria:**
- **Two Peaks:** Approximately equal height (within 1-3% tolerance), resistance level tested twice
- **Trough/Valley:** Price decline between peaks forming support (neckline)
- **Time Between Peaks:** Sufficient separation (not consolidation) - typically days to weeks
- **Volume Confirmation:** First peak higher volume, second peak lower volume, break below neckline with volume spike
- **Neckline:** Horizontal support at valley low
- **Confirmation:** Price closes below neckline support
- **Failed Pattern:** If price breaks above second peak, pattern invalidated

**Function:** Returns pattern status, peak prices, neckline level, volume analysis, confirmation status, price target, reliability score (0-100)

**Signal:** SHORT on neckline break after second peak rejection

**BTC-Specific Notes:**
- Common Bitcoin reversal pattern at resistance zones
- Forms at psychological levels ($10k, $20k, $50k, $100k)
- Second peak often forms 2-5% below first peak (not exact)
- Declining volume at second peak = distribution signal
- Bitcoin double tops can take 1-4 weeks to form
- Neckline break with <2x volume often fails - wait for confirmation
- Target achievement rate: ~65-70% in crypto markets

**Trading Strategy:**
- Wait for second peak formation with clear rejection
- Enter short after neckline break and close below
- Stop-Loss: Above second peak high + 1-2%
- Take Profit: Measure peak-to-neckline distance, project downward
- Partial profits at 50% of target distance
- Watch for neckline retest as resistance (failed retest = stronger signal)

**Document:** docs/v3/building_blocks/patterns/Double_Top.md  
**File:** src/detectors/building_blocks/patterns/double_top.py  
**Backtest Result:** 65-70% success rate  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Double Bottom Pattern
**Description:** Identifies bullish reversal pattern with two troughs at approximately same price level separated by peak (W-shaped).

**Criteria:**
- **Two Troughs:** Approximately equal depth (within 1-3% tolerance), support level tested twice
- **Peak:** Price rally between troughs forming resistance (neckline)
- **Time Between Troughs:** Adequate separation - typically days to weeks
- **Volume Confirmation:** Higher volume at first trough, lower at second, spike on neckline break
- **Neckline:** Horizontal resistance at peak high
- **Confirmation:** Price closes above neckline resistance
- **Pattern Invalidation:** Break below second trough negates pattern

**Function:** Returns pattern status, trough prices, neckline level, volume profile, breakout confirmation, price target, strength score (0-100)

**Signal:** LONG on neckline breakout after second trough bounce

**BTC-Specific Notes:**
- Strong bullish reversal signal in Bitcoin markets
- Forms at major support levels during corrections
- Second bottom often slightly higher than first (shows buying strength)
- Volume declining into second bottom = sellers exhausted
- Common at Fibonacci retracement levels (61.8%, 50%, 38.2%)
- Breakout volume >2x average increases success to 75-80%
- Bitcoin double bottoms reliable on 4hr and daily timeframes

**Trading Strategy:**
- Identify potential pattern after first trough forms
- Confirm second trough holds support (doesn't break lower)
- Entry: Buy on neckline breakout or pullback retest
- Stop-Loss: Below second trough - 1-2% buffer
- Take Profit: Measured move = trough-to-neckline height added to breakout
- Scale out: 50% at measured target, 50% at next resistance
- Combine with RSI bullish divergence between troughs

**Document:** docs/v3/building_blocks/patterns/Double_Bottom.md  
**File:** src/detectors/building_blocks/patterns/double_bottom.py  
**Backtest Result:** 75-80% success rate with volume  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Triple Top Pattern
**Description:** Identifies strong bearish reversal pattern with three peaks at approximately same resistance level - extension of double top.

**Criteria:**
- **Three Peaks:** All near same price level (within 2-3% range), creates strong resistance zone
- **Two Valleys:** Pullbacks between peaks forming neckline support
- **Volume Pattern:** Typically decreasing at each successive peak (second lowest, third lowest)
- **Peak Spacing:** Need not be evenly spaced - irregular timing acceptable
- **Neckline:** Horizontal support connecting valley lows
- **Confirmation:** Price breaks and closes below neckline with volume
- **Rare Formation:** Less common than double top, thus more significant
- **Failed Breakout:** If fourth attempt succeeds breaking resistance, pattern fails

**Function:** Returns pattern status, three peak coordinates, neckline level, volume trend analysis, confirmation status, target projection, reliability score (0-100)

**Signal:** SHORT after third rejection at resistance level

**BTC-Specific Notes:**
- Rarer than double top, making it more reliable when forms
- Often appears at major Bitcoin resistance zones ($60k, $70k regions)
- Third peak rejection particularly significant - three failed attempts = strong seller control
- Pattern formation can span 4-8 weeks on daily charts
- Triple tops preceded by parabolic moves show highest reliability
- Volume declining at each peak confirms distribution
- Similar to "Bart pattern" in crypto (triple top with sharp moves)
- Target hit rate: 75-79% according to technical analysis studies

**Trading Strategy:**
- Observe first two peaks establish resistance
- Wait for third peak rejection confirmation
- Entry: Short on neckline break with volume confirmation
- Stop-Loss: Above highest peak + 2-3% buffer
- Take Profit 1: Measured move (peak height to neckline)
- Take Profit 2: Next major support level
- High-confidence short when combined with bearish divergence on all three peaks
- Avoid if volume increases at third peak (buyers may overwhelm)

**Document:** docs/v3/building_blocks/patterns/Triple_Top.md  
**File:** src/detectors/building_blocks/patterns/triple_top.py  
**Backtest Result:** 75-79% success rate  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Triple Bottom Pattern
**Description:** Identifies strong bullish reversal pattern with three troughs at approximately same support level - extension of double bottom.

**Criteria:**
- **Three Troughs:** All near same price level (within 2-3% range), strong support zone
- **Two Peaks:** Rallies between troughs forming neckline resistance
- **Volume Pattern:** High at first trough, decreasing at second/third, rising on breakout
- **Trough Spacing:** Can be irregular timing - focus on price level consistency
- **Neckline:** Horizontal resistance connecting peak highs
- **Confirmation:** Price breaks and closes above neckline with strong volume
- **Accumulation Phase:** Three tests without breaking shows buyer strength
- **False Breakdown:** If price breaks below third trough, pattern invalidated

**Function:** Returns pattern status, three trough coordinates, neckline level, volume analysis, breakout confirmation, price target, strength rating (0-100)

**Signal:** LONG after third bounce from support level

**BTC-Specific Notes:**
- Powerful bullish reversal - three successful support defenses very bullish
- Common at Bitcoin major support zones after corrections
- Pattern often spans 6-12 weeks during bear market bottoms
- Third trough typically shows lowest volume = selling exhausted
- Accumulation occurs between troughs - smart money building positions
- Neckline breakout with >2x volume critical for confirmation
- Target achievement rate improves with each successful support test
- Often forms at previous cycle highs turned support

**Trading Strategy:**
- Monitor first two troughs establishing support
- Third trough bounce provides highest-confidence entry signal
- Entry 1: Buy on neckline breakout
- Entry 2: Buy on pullback retest of neckline (now support)
- Stop-Loss: Below lowest trough - 2-3%
- Take Profit: Measure trough-to-neckline height, add to breakout point
- Expect strong momentum after triple test - often exceeds target
- Combine with bullish candlestick patterns at third trough
- Scale in: 50% at breakout, 50% on successful retest

**Document:** docs/v3/building_blocks/patterns/Triple_Bottom.md  
**File:** src/detectors/building_blocks/patterns/triple_bottom.py  
**Backtest Result:** 78-82% success rate  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Ascending Triangle
**Description:** Identifies bullish continuation pattern with horizontal resistance and rising support (higher lows), signaling accumulation before upward breakout.

**Criteria:**
- **Horizontal Resistance:** Flat upper trendline connecting equal highs (minimum 2-3 touches)
- **Rising Support:** Upward-sloping lower trendline connecting higher lows (minimum 2-3 touches)
- **Preceding Trend:** Typically forms during uptrend (continuation), rarely in downtrend (reversal)
- **Volume Pattern:** Declining during formation, surge on breakout above resistance
- **Triangle Convergence:** Lines meet at apex - breakout typically occurs at 50-75% completion
- **Accumulation Signal:** Higher lows show increasing buying pressure
- **Confirmation:** Close above resistance with volume >1.5x average

**Function:** Returns pattern status, resistance level, support trendline, apex location, completion percentage, volume confirmation, breakout probability (0-100), price target

**Signal:** LONG on breakout above resistance level

**BTC-Specific Notes:**
- High-reliability bullish continuation in Bitcoin - 70-75% success rate
- Common during Bitcoin bull market corrections and consolidations
- Pattern duration: 3-8 weeks on daily charts, 1-3 weeks on 4hr charts
- Each resistance test absorbs sellers - breakout occurs when sellers exhausted
- Ascending triangles near previous all-time highs particularly powerful
- Volume declining into apex = coiling energy for breakout
- False breakouts occur ~25% of time - wait for volume confirmation
- Measured move: Widest part of triangle height added to breakout point

**Trading Strategy:**
- Identify pattern after 2-3 resistance tests and rising lows
- Wait for apex approach (50-75% complete)
- Entry: Buy on breakout above resistance with volume
- Aggressive Entry: Buy at rising support with tight stop below
- Stop-Loss: Below most recent higher low on support line
- Take Profit: Add triangle height to breakout point
- Partial profit taking: 50% at measured target, trail stop for remainder
- Combine with bullish indicators (MACD, RSI) for confirmation

**Document:** docs/v3/building_blocks/patterns/Ascending_Triangle.md  
**File:** src/detectors/building_blocks/patterns/ascending_triangle.py  
**Backtest Result:** 70-75% success rate  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Descending Triangle
**Description:** Identifies bearish continuation pattern with horizontal support and falling resistance (lower highs), signaling distribution before downward breakdown.

**Criteria:**
- **Horizontal Support:** Flat lower trendline connecting equal lows (minimum 2-3 touches)
- **Falling Resistance:** Downward-sloping upper trendline connecting lower highs (minimum 2-3 touches)
- **Preceding Trend:** Typically forms during downtrend (continuation), rarely in uptrend (reversal)
- **Volume Pattern:** Declining during formation, spike on breakdown below support
- **Triangle Convergence:** Lines converge toward apex - breakdown usually at 50-75% completion
- **Distribution Signal:** Lower highs indicate increasing selling pressure
- **Confirmation:** Close below support with volume surge

**Function:** Returns pattern status, support level, resistance trendline, apex point, formation progress, volume analysis, breakdown probability (0-100), target projection

**Signal:** SHORT on breakdown below support level

**BTC-Specific Notes:**
- Reliable bearish continuation in Bitcoin bear markets
- Forms during downtrends as consolidation before further decline
- Pattern takes 2-6 weeks to develop on daily charts
- Each support test finds fewer buyers - breakdown when buyers exhausted
- Common in Bitcoin corrections after parabolic rallies
- Volume increase on breakdown essential - weak volume breakdowns often fail
- False breakdowns ~20-25% of time - require volume confirmation
- Target: Triangle height subtracted from breakdown point

**Trading Strategy:**
- Identify after 2-3 support tests and descending highs
- Monitor volume - should decline during formation
- Entry: Short on breakdown below support with volume
- Conservative: Wait for retest of broken support (now resistance)
- Stop-Loss: Above most recent lower high on resistance line
- Take Profit: Subtract triangle height from breakdown point
- Risk Management: 50% profit at target, trail stop for rest
- Avoid shorting if volume increases on support bounces (buyers stepping in)

**Document:** docs/v3/building_blocks/patterns/Descending_Triangle.md  
**File:** src/detectors/building_blocks/patterns/descending_triangle.py  
**Backtest Result:** 68-72% success rate  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Symmetrical Triangle
**Description:** Identifies neutral continuation pattern with converging trendlines (higher lows and lower highs), breakout direction determines trade.

**Criteria:**
- **Converging Trendlines:** Lower trendline rising (higher lows), upper trendline falling (lower highs)
- **Symmetrical Convergence:** Both lines converge at similar angles toward apex
- **Volume Pattern:** Steadily declining as pattern progresses, explosion on breakout
- **Neutral Bias:** Can break either direction - follows prevailing trend ~75% of time
- **Breakout Timing:** Typically occurs at 50-75% of pattern completion (before apex)
- **Consolidation:** Represents equilibrium between buyers and sellers
- **Confirmation:** Decisive close beyond trendline with volume >2x average

**Function:** Returns pattern status, upper/lower trendlines, apex location, completion percentage, volume trend, breakout direction when occurs, strength score (0-100), target price

**Signal:** Trade breakout direction - LONG on upward break, SHORT on downward break

**BTC-Specific Notes:**
- Common Bitcoin consolidation pattern during trends
- Direction-neutral until breakout - trade the break
- Pattern duration: 2-6 weeks on daily Bitcoin charts
- ~75% break in direction of prior trend (continuation pattern)
- Volume must confirm breakout - weak volume = likely false break
- Bitcoin symmetrical triangles on lower timeframes less reliable
- Best on 4hr+ timeframes with clear preceding trend
- Failed breakout (reversal back into triangle) = trade opposite direction

**Trading Strategy:**
- Identify pattern with minimum 4 touches (2 upper, 2 lower)
- Monitor volume decline - confirms consolidation
- Await breakout at 50-75% completion
- Entry: Trade direction of breakout with volume confirmation
- Stop-Loss: Opposite side of triangle or just inside triangle
- Take Profit: Widest part of triangle added to breakout (up) or subtracted (down)
- False Breakout Protection: Wait for daily/4hr close beyond trendline
- Higher timeframe trend alignment increases success rate to 80%+

**Document:** docs/v3/building_blocks/patterns/Symmetrical_Triangle.md  
**File:** src/detectors/building_blocks/patterns/symmetrical_triangle.py  
**Backtest Result:** 75% continuation rate  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Flag Pattern (Bullish/Bearish)
**Description:** Identifies short-term continuation pattern with sharp "flagpole" move followed by parallel channel consolidation (the "flag").

**Criteria:**
- **Flagpole:** Strong, near-vertical price move (bullish or bearish impulse)
- **Flagpole Formation:** High volume explosive move of 10-30%+ in Bitcoin
- **Flag Formation:** Parallel channel consolidation counter to flagpole direction
  - Bullish Flag: Downward-sloping or sideways channel after up-move
  - Bearish Flag: Upward-sloping or sideways channel after down-move
- **Parallel Lines:** Both channel lines roughly parallel (not converging)
- **Volume:** High on flagpole, declining in flag, surge on breakout
- **Duration:** Flag typically lasts 1-3 weeks (shorter than pole)
- **Breakout:** Continues in flagpole direction with volume

**Function:** Returns pattern type (Bullish/Bearish Flag), flagpole size, flag boundaries, duration, volume confirmation, breakout status, continuation probability (0-100), price target

**Signal:** LONG on bullish flag breakout, SHORT on bearish flag breakout

**BTC-Specific Notes:**
- Extremely reliable short-term continuation pattern in Bitcoin
- Success rate: 70-80% in trending markets
- Common in parabolic Bitcoin rallies (bullish flags) and crashes (bearish flags)
- Flagpole forms during FOMO buying or panic selling
- Flag represents pause as traders take profits/shorts cover
- Bitcoin flags often complete in 5-15 days on daily charts
- Target: Flagpole height added to (bullish) or subtracted from (bearish) breakout
- Best during strong trends - avoid in choppy/ranging markets

**Trading Strategy - Bullish Flag:**
- Identify strong upward move (flagpole) with high volume
- Wait for downward/sideways consolidation (flag) on declining volume
- Entry: Buy on breakout above flag upper boundary
- Stop-Loss: Below flag lower boundary
- Take Profit: Add flagpole height to breakout point
- Expected target hit: 70-80% of time

**Trading Strategy - Bearish Flag:**
- Identify strong downward move (flagpole) with panic volume
- Wait for upward/sideways bounce (flag) on declining volume
- Entry: Short on breakdown below flag lower boundary
- Stop-Loss: Above flag upper boundary
- Take Profit: Subtract flagpole height from breakdown
- Watch for failed bearish flags in strong uptrends (reversal signal)

**Document:** docs/v3/building_blocks/patterns/Flag_Pattern.md  
**File:** src/detectors/building_blocks/patterns/flag_pattern.py  
**Backtest Result:** 70-80% success rate  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Pennant Pattern
**Description:** Identifies short-term continuation pattern with strong "flagpole" followed by small symmetrical triangle consolidation.

**Criteria:**
- **Flagpole:** Sharp directional move (bullish or bearish) with high volume
- **Pennant Body:** Small symmetrical triangle (converging trendlines)
- **Converging Lines:** Both trendlines slope toward each other
- **Size:** Pennant much smaller than flagpole - compact triangle shape
- **Duration:** Very short - typically 1-3 weeks maximum
- **Volume Pattern:** High on pole, declining in pennant, explosion on breakout
- **Breakout Direction:** Continues in direction of flagpole
- **Similarity to Symmetrical Triangle:** If >12-13 weeks, it's a triangle, not pennant

**Function:** Returns pattern type (Bullish/Bearish Pennant), flagpole metrics, pennant boundaries, convergence point, completion status, volume analysis, breakout confirmation, target projection

**Signal:** Trade in flagpole direction - LONG for bullish, SHORT for bearish

**BTC-Specific Notes:**
- High-probability continuation pattern during Bitcoin momentum moves
- Forms after strong impulse moves (15-40% in short time)
- Pennant duration in Bitcoin: typically 1-2 weeks on daily charts
- Volume signature critical - declining in pennant, spike on break
- Common mid-trend during Bitcoin parabolic rallies or capitulations
- Target equals flagpole length added/subtracted from breakout
- Success rate: 65-75% in trending Bitcoin markets
- Failed pennants (breakout opposite direction) signal potential reversal

**Trading Strategy:**
- Confirm strong flagpole with high volume (>2x average)
- Identify pennant formation (small converging triangle)
- Wait for breakout at 50-80% of pennant completion
- Entry: Trade breakout direction with volume confirmation
- Stop-Loss: Opposite side of pennant
- Take Profit: Flagpole height projected from breakout
- Quick Pattern: Pennants resolve faster than flags/triangles
- Best during established trends - avoid in consolidation zones

**Document:** docs/v3/building_blocks/patterns/Pennant_Pattern.md  
**File:** src/detectors/building_blocks/patterns/pennant_pattern.py  
**Backtest Result:** 65-75% success rate  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Wedge Patterns (Rising/Falling)
**Description:** Identifies reversal patterns with converging trendlines - Rising Wedge (bearish), Falling Wedge (bullish).

**Criteria:**

**Rising Wedge (Bearish Reversal):**
- **Both Lines Rising:** Support and resistance both slope upward
- **Converging:** Support rises faster than resistance (wedge narrows)
- **Volume Declining:** Decreasing volume as pattern progresses
- **Context:** Usually bearish - forms at tops or during uptrends
- **Breakout:** Downward through support line
- **Signal:** Buying momentum weakening despite higher prices

**Falling Wedge (Bullish Reversal):**
- **Both Lines Falling:** Support and resistance both slope downward  
- **Converging:** Resistance falls faster than support (wedge narrows)
- **Volume Declining:** Diminishing volume throughout formation
- **Context:** Usually bullish - forms at bottoms or during downtrends
- **Breakout:** Upward through resistance line
- **Signal:** Selling pressure weakening

**Common Elements:**
- **Duration:** Typically 3-6 months for reliability
- **Minimum 10-50 periods:** On daily charts
- **Three Touches:** Minimum 3 touches each trendline

**Function:** Returns wedge type (Rising/Falling), trendline coordinates, volume trend, convergence angle, completion percentage, breakout probability, target projection, reliability score (0-100)

**Signal:** Rising Wedge = BEARISH (short on support break), Falling Wedge = BULLISH (long on resistance break)

**BTC-Specific Notes:**
- Rising Wedge: 81% success rate in bull markets (bearish reversal)
- Falling Wedge: 74% success rate in bull markets (bullish reversal)  
- Bitcoin rising wedges common before corrections in uptrends
- Falling wedges form during Bitcoin bear market bottoms
- Volume decline critical - spike on breakout confirms pattern
- Rising wedge breakdowns can be violent (5-15% quick drops)
- Falling wedge breakouts often explosive (15-30%+ rallies)
- Best on 4hr and daily timeframes for Bitcoin

**Trading Strategy - Rising Wedge:**
- Identify upward-sloping converging trendlines
- Wait for declining volume confirmation
- Entry: Short on break below support with volume
- Stop-Loss: Above recent high within wedge
- Take Profit: Measure widest part, subtract from breakdown
- Watch for failed breakdowns (bullish trap)

**Trading Strategy - Falling Wedge:**
- Identify downward-sloping converging trendlines
- Confirm volume declining (selling exhaustion)
- Entry: Long on break above resistance with volume spike
- Stop-Loss: Below recent low within wedge
- Take Profit: Measure widest part, add to breakout
- High-confidence when forms after significant decline

**Document:** docs/v3/building_blocks/patterns/Wedge_Patterns.md  
**File:** src/detectors/building_blocks/patterns/wedge_patterns.py  
**Backtest Result:** Rising 81%, Falling 74% in bull markets  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Cup and Handle Pattern
**Description:** Identifies bullish continuation pattern shaped like tea cup with handle, signaling consolidation before upward breakout.

**Criteria:**
- **Preceding Uptrend:** Must have prior bullish trend
- **Cup Formation:** U-shaped rounded bottom (not V-shaped)
  - Initial decline: 30-50% retracement of prior uptrend
  - Bottom: Rounded, gradual - not sharp spike
  - Recovery: Rally back near prior high (within 10%)
  - Duration: Weeks to months (3-6 months typical)
- **Handle Formation:**
  - Slight downward drift or sideways consolidation
  - Forms in upper half of cup (above 50% level)
  - Smaller than cup - typically 1/5 to 1/3 cup's time
  - Parallel channel or slight downward slope
- **Volume Pattern:**
  - High at start of cup
  - Declining into cup bottom (sellers exhausting)
  - Increases on cup right side rally
  - Declines in handle (shakes out weak hands)
  - Explodes on handle breakout
- **Confirmation:** Break above handle's high/resistance with volume

**Function:** Returns pattern status, cup boundaries (high/low), handle boundaries, volume profile, completion stage, breakout readiness, price target projection, reliability (0-100)

**Signal:** LONG on breakout above handle resistance

**BTC-Specific Notes:**
- Powerful bullish continuation in Bitcoin bull markets
- Forms during corrections within larger uptrends
- Cup represents accumulation after profit-taking
- Handle shakes out late buyers and weak hands before breakout
- Target: Cup depth added to breakout point (conservative)
- Measured move often exceeded in Bitcoin due to momentum
- Best on daily/weekly timeframes - less reliable on intraday
- Failed patterns (breakdown below cup) suggest deeper correction
- Stop loss: Below handle low (conservative) or cup bottom (wide)

**Trading Strategy:**
- Identify U-shaped cup after uptrend
- Wait for handle formation in upper half of cup
- Monitor handle for downward drift on declining volume
- Entry: Buy on breakout above handle resistance with volume >2x average
- Aggressive Entry: Buy in handle at support with stop below handle
- Stop-Loss: Below handle low (tight) or cup 50% level
- Take Profit 1: Cup depth added to breakout (measured move)
- Take Profit 2: Previous all-time high or next major resistance
- Scale out: 50% at measured target, trail stop remainder
- Best win rate when combined with other bullish signals

**Document:** docs/v3/building_blocks/patterns/Cup_And_Handle.md  
**File:** src/detectors/building_blocks/patterns/cup_and_handle.py  
**Backtest Result:** 70-75% success rate  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Rounding Bottom/Top
**Description:** Identifies gradual reversal patterns - Rounding Bottom (bullish), Rounding Top (bearish) - characterized by smooth curved formations.

**Criteria:**

**Rounding Bottom (Saucer Bottom/Cup):**
- **Formation:** U-shaped, gradual curve from downtrend to uptrend
- **Left Side:** Declining price with high volume
- **Bottom:** Rounded, extended consolidation with low volume
- **Right Side:** Rising price with increasing volume
- **Neckline:** Resistance drawn at start of pattern
- **Confirmation:** Break above neckline with volume surge
- **Duration:** Weeks to months - longer = more reliable
- **Characteristic:** Smooth, gradual - not sharp angles

**Rounding Top (Dome Pattern/Inverted Saucer):**
- **Formation:** Inverted U-shape, gradual curve from uptrend to downtrend
- **Left Side:** Rising price with high volume
- **Peak:** Rounded top with small fluctuations, diminishing volume
- **Right Side:** Declining price with increasing volume
- **Neckline:** Support drawn at start of pattern
- **Confirmation:** Break below neckline with volume
- **Duration:** Weeks to months
- **Characteristic:** Dome-like, smooth curve

**Common Elements:**
- **Volume:** High at ends, low in middle (consolidation)
- **Not Perfect:** Rarely perfect semicircle - some irregularities normal
- **Gradual Shift:** Represents slow change in market sentiment

**Function:** Returns pattern type (Rounding Bottom/Top), curve coordinates, neckline level, volume profile, formation stage, completion percentage, breakout status, price target, strength score (0-100)

**Signal:** Rounding Bottom = LONG on neckline break, Rounding Top = SHORT on neckline break

**BTC-Specific Notes:**
- Rounding bottoms common at Bitcoin bear market cycle lows
- Rounding tops appear at extended bull market peaks
- Bottom patterns often span 3-12 months at major Bitcoin lows
- Top patterns typically 2-6 months at cycle peaks
- Volume U-shape in rounding bottom = strong reversal signal
- Irregularities and fluctuations normal in Bitcoin (high volatility)
- Target: Pattern height projected from neckline break
- Best identified on daily and weekly Bitcoin charts
- Failed patterns (no neckline break) suggest continued consolidation

**Trading Strategy - Rounding Bottom:**
- Identify after extended downtrend
- Monitor for U-shaped formation with declining volume at bottom
- Look for volume increasing on right side recovery
- Entry: Long on neckline breakout with volume confirmation
- Stop-Loss: Below bottom of pattern or recent support
- Take Profit: Measure pattern depth, add to breakout point
- Patience required - slow-forming pattern

**Trading Strategy - Rounding Top:**
- Identify after significant uptrend
- Watch for dome formation with declining volume at top
- Monitor for volume increase on right-side decline
- Entry: Short on neckline breakdown with volume
- Stop-Loss: Above top of dome
- Take Profit: Measure pattern height, subtract from breakdown
- Early warning: Distribution visible in volume pattern

**Document:** docs/v3/building_blocks/patterns/Rounding_Bottom_Top.md  
**File:** src/detectors/building_blocks/patterns/rounding_bottom_top.py  
**Backtest Result:** 68-75% success rate (longer duration = higher)  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Diamond Pattern
**Description:** Identifies rare reversal pattern with expanding then contracting price action forming diamond shape.

**Criteria:**

**Diamond Top (Bearish Reversal):**
- **Formation:** At market top after uptrend
- **Left Side Expansion:** 
  - Higher highs and lower lows (broadening)
  - Upper resistance line rising
  - Lower support line declining
- **Right Side Contraction:**
  - Lower highs and higher lows (narrowing)
  - Upper resistance line declining
  - Lower support line rising
- **Diamond Shape:** Four trendlines form diamond/rhombus
- **Volume:** High and erratic during formation, spike on breakdown
- **Confirmation:** Break below lower right support with volume

**Diamond Bottom (Bullish Reversal):**
- **Formation:** At market bottom after downtrend
- **Left Side Expansion:** Widening price swings
- **Right Side Contraction:** Narrowing range
- **Diamond Shape:** Inverted diamond formation
- **Confirmation:** Break above upper right resistance with volume

**Common Elements:**
- **Rarity:** Uncommon pattern - significant when forms
- **Complexity:** Requires clear identification of four trendlines
- **Duration:** Typically 3-6 months
- **Volatility:** Increasing then decreasing
- **Consolidation:** Represents indecision before major move

**Function:** Returns pattern type (Diamond Top/Bottom), four trendline coordinates, expansion/contraction metrics, volume analysis, completion status, breakout direction, target projection, reliability (0-100)

**Signal:** Diamond Top = SHORT on breakdown, Diamond Bottom = LONG on breakout

**BTC-Specific Notes:**
- Rare in Bitcoin but highly significant when properly formed
- Diamond tops occasionally appear at Bitcoin cycle peaks
- Pattern reflects extreme volatility followed by consolidation
- Requires manual identification - difficult to automate
- Volume erratic during formation confirms indecision
- Target: Widest part of diamond projected from break
- High failure rate if volume doesn't confirm breakout
- Best on weekly/monthly Bitcoin charts at major turning points

**Trading Strategy - Diamond Top:**
- Identify broadening formation (left side of diamond)
- Confirm contraction phase (right side forming)
- Wait for breakdown below lower support
- Entry: Short on confirmed breakdown with volume spike
- Stop-Loss: Above highest point of diamond
- Take Profit: Measure diamond width, subtract from breakdown
- Risk-Reward: Wide stops require careful position sizing

**Trading Strategy - Diamond Bottom:**
- Identify expanding then contracting volatility
- Wait for diamond shape completion
- Entry: Long on breakout above upper resistance with volume
- Stop-Loss: Below lowest point of diamond
- Take Profit: Diamond width added to breakout
- Rare pattern requires patience - don't force identification

**Document:** docs/v3/building_blocks/patterns/Diamond_Pattern.md  
**File:** src/detectors/building_blocks/patterns/diamond_pattern.py  
**Backtest Result:** 70-75% when properly identified  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## PATTERN DETECTION REQUIREMENTS

### Implementation Standards for Pattern Building Blocks:

1. **Pivot Point Detection:**
   - Implement swing high/low identification algorithm
   - Configurable lookback periods (default: 5-10 candles each side)
   - Higher timeframe pivots have more weight

2. **Neckline Detection:**
   - Automatic horizontal line drawing connecting relevant pivots
   - Tolerance for "approximately equal" levels (1-3% range)
   - Sloped necklines for complex patterns

3. **Volume Confirmation:**
   - Volume ratio analysis (current vs. average)
   - Volume profile during pattern formation
   - Breakout volume surge detection (>1.5-2x average)

4. **Pattern Completion:**
   - Progressive scoring as pattern develops
   - Percentage complete calculation
   - Early warning when pattern ~70-80% formed

5. **Validation Rules:**
   - Minimum time requirements (avoid micro-patterns)
   - Maximum time limits (pattern decay)
   - Trend context validation (preceding trend required)

6. **Price Target Calculation:**
   - Measured move methodology (pattern height projection)
   - Alternative target: Next significant support/resistance
   - Fibonacci extension targets for aggressive traders

7. **False Pattern Filtering:**
   - Volume divergence detection
   - Context validation (trend alignment)
   - Multi-timeframe confirmation

---

## PATTERN CONFLUENCE SCORING

### Pattern Building Block Weights:

- **Head & Shoulders / Inverse H&S:** 25 points (highest reliability)
- **Triple Top/Bottom:** 20 points
- **Double Top/Bottom:** 15 points
- **Ascending/Descending Triangle:** 18 points
- **Cup & Handle:** 18 points
- **Wedge Patterns:** 15 points
- **Flag/Pennant:** 15 points
- **Symmetrical Triangle:** 12 points
- **Rounding Top/Bottom:** 12 points
- **Diamond Pattern:** 20 points (rare but powerful)

### Combined Pattern + Indicator Setup Example:

**Extremely High-Probability Short (125+ Confluence Points):**
1. Head & Shoulders Pattern Confirmed: +25
2. MACD Bearish Divergence at Head: +15
3. RSI Overbought >70 at Right Shoulder: +10
4. Volume Declining at Right Shoulder: +10
5. Neckline at Key Resistance (HOW/previous high): +15
6. Pattern Forms During Distribution Phase (Wyckoff): +15
7. Break Occurs During Kill Zone: +10
8. 4hr Bearish MSS Confirmed: +15
9. Pattern Near Premium Zone (above 50% range): +10

**Total: 125 Points = Exceptional Short Setup**

---

---

## IMPLEMENTATION NOTES

### Pattern-Specific Optimizations:

**Bitcoin 24/7 Market Considerations:**
- Patterns span weekends - adjust time calculations
- Weekend gaps can distort pattern formations
- Lower volume weekends may delay breakouts
- Session awareness (Asia/UK/US) for breakout timing

**Backtesting Requirements:**
- Minimum 200 pattern occurrences for statistical validity
- Walk-forward testing on out-of-sample data
- Test across different market conditions (bull/bear/sideways)
- Separate statistics for each timeframe (15min, 1hr, 4hr, daily)

**Performance Metrics:**
- Pattern Success Rate (% achieving target)
- Average R:R ratio achieved
- Time to target (days/weeks)
- Failure rate and average loss
- Breakout fakeout percentage
---

## IMPLEMENTATION NOTES

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
- Higher timeframe alignment increases signal reliability by 15-25% per timeframe

3. **Bitcoin-Specific Optimizations:**
- Handle 24/7 market (no gaps like stocks)
- Account for high volatility characteristics
- Session-aware processing (Asia, UK, US sessions)
- CME futures settlement impact (16:00 EST)
- Weekend liquidity adjustments
- Crypto-specific volume analysis (exchange volume vs aggregated)

4. **Backtesting Requirements:**
- Walk-forward optimization (train on first 70%, test on next 30%, repeat)
- Out-of-sample testing (minimum 100 trades required)
- Transaction cost modeling (0.1% fees minimum)
- Slippage modeling (0.05-0.1% on volatile moves)
- Maximum drawdown tracking
- Risk-adjusted returns (Sharpe ratio)
- Monte Carlo analysis for robustness testing

5. **Permutation Testing Framework:**
- Systematic combination of multiple building blocks
- Example: [Liquidity Sweep + Breaker Block + OTE 70.5% + NY AM Kill Zone + MACD Bullish Div]
- Automated discovery of profitable pattern combinations
- Statistical significance testing (minimum 100 trades)
- Win rate analysis by market condition
- Track correlation between blocks (avoid over-correlation)

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
  - Multi-timeframe alignment: +5-10 points per aligned timeframe
  - **Total: 100+ points = Maximum Confluence Trade**

### Performance Targets

- **Minimum Win Rate:** 55%+ (for 1:2 R:R), 65%+ (for 1:1 R:R)
- **Sharpe Ratio:** >1.5
- **Maximum Drawdown:** <20%
- **Profit Factor:** >1.8
- **Minimum Trades:** 100+ for statistical validity
- **Risk-Reward:** Minimum 1:2, optimal 1:3
- **Multi-timeframe Win Rate:** 75-85% (with 3+ timeframe alignment)

---

## ADVANCED STRATEGY EXAMPLES

### High-Probability Long Entry Setup (110+ Confluence Score)

**Conditions:**
1. **Higher Timeframe Trend (Daily):** Bullish bias, price above 200 EMA (+10 points)
2. **Market Structure (4hr):** Bullish MSS confirmed on 4hr chart (+15 points)
3. **Liquidity (30min):** Sell-side liquidity sweep below recent low (+25 points)
4. **Price Action (15min):** Breaker block retest at swept level (+20 points)
5. **Fibonacci (4hr):** OTE 70.5% retracement of recent impulse (+15 points)
6. **Timing (Sessions):** New York AM Kill Zone (08:00-11:00 EST) (+10 points)
7. **Confluence (15min):** Fair Value Gap present at entry level (+10 points)
8. **Momentum (4hr):** MACD showing bullish divergence (+10 points)
9. **Volume (30min):** Volume spike on liquidity sweep reversal (+5 points)

**Total Confluence Score: 120 points (Maximum Quality Setup)**

**Entry:** Buy limit at breaker block / FVG / OTE confluence zone  
**Stop Loss:** Below liquidity sweep low + buffer (2 x ATR)  
**Take Profit:** 
- TP1: 1:2 R:R (take 50% profit)
- TP2: Previous swing high (take 30% profit)
- TP3: Buy-side liquidity pool above (take 20% profit)

**Expected Win Rate:** 75-85%  
**Expected R:R:** 1:3 to 1:5

## INSTITUTIONAL & VOLUME INDICATORS

### Block Name: VWAP (Volume Weighted Average Price)
**Description:** Calculates average price weighted by volume, providing institutional benchmark for fair value.

**Criteria:**
- **Calculation:** VWAP = Σ(Price × Volume) / Σ(Volume)
- **Daily Reset:** Resets at market open (00:00 UTC for Bitcoin)
- **Cumulative Intraday:** Calculation accumulates throughout trading session
- **Fair Value Line:** Represents institutional average execution price
- **Above VWAP:** Price trading at premium (bullish sentiment)
- **Below VWAP:** Price trading at discount (bearish sentiment)
- **Mean Reversion:** Price tends to gravitate toward VWAP

**Function:** Returns VWAP price, current position (premium/discount), distance from VWAP, standard deviation bands, volume-weighted trend

**BTC-Specific Notes:**
- VWAP widely used by Bitcoin institutions (Citadel handles ~35% US retail volume with VWAP algos)
- Bitcoin spot price often gravitates to VWAP during consolidation
- CME futures traders use VWAP for benchmark execution
- Price above VWAP with high volume = institutional accumulation
- Price below VWAP with high volume = institutional distribution
- VWAP acts as dynamic support in uptrends, resistance in downtrends
- Most effective on 5min to 1hr charts for Bitcoin day trading
- Bitcoin ETF institutions use VWAP for trade execution quality measurement

**Trading Strategy:**
- **Pullback Entry (Uptrend):** Buy when price pulls back to VWAP
- **Breakout Entry:** Enter long on break above VWAP with volume
- **Mean Reversion:** Fade extremes >2 standard deviations from VWAP
- Stop-Loss: Below VWAP for longs, above for shorts
- Target: Previous swing high/low or next resistance/support
- Combine with RSI: VWAP pullback + RSI <50 = high probability long

**Document:** docs/v3/building_blocks/institutional/VWAP.md  
**File:** src/detectors/building_blocks/institutional/vwap.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Anchored VWAP
**Description:** VWAP calculated from user-defined anchor point (specific event, pivot, breakout) rather than daily reset.

**Criteria:**
- **Anchor Points:** Significant highs/lows, earnings, breakouts, news events, cycle tops/bottoms
- **Persistent Calculation:** Continues from anchor until new anchor set
- **Institutional Cost Basis:** Reveals where institutions entered positions
- **Multi-Anchor:** Can plot multiple anchored VWAPs simultaneously
- **Dynamic S/R:** Acts as institutional support/resistance levels
- **Timeframe Flexibility:** Works on any timeframe from minutes to months

**Function:** Returns anchored VWAP value, anchor date/price, age since anchor, deviation bands, support/resistance status

**BTC-Specific Notes:**
- Extremely powerful for Bitcoin swing trading (weeks to months)
- Anchor to major Bitcoin events: Halving, ETF approval, major breakouts
- Citadel and institutional traders use anchored VWAP extensively
- Common anchors: Bitcoin cycle low ($15.5k 2022), cycle high ($69k 2021)
- Anchored VWAP from significant low acts as trailing support in bull market
- Multiple timeframe anchors provide confluence zones
- Weekly anchor + daily anchor alignment = high-probability setup
- Failed breaks of anchored VWAP = strong reversal signal

**Trading Strategy:**
- Anchor VWAP to significant swing low after downtrend
- Enter longs on pullbacks to anchored VWAP
- Stop-loss below anchored VWAP
- Anchor provides dynamic trend-following entry system
- Break below = trend change, reanchor to new swing
- Common practice: Anchor to quarterly/yearly opens for position trading

**Document:** docs/v3/building_blocks/institutional/Anchored_VWAP.md  
**File:** src/detectors/building_blocks/institutional/anchored_vwap.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: EMA Crossover Systems
**Description:** Standard Exponential Moving Averages (20, 50, 200) without vector break requirement, used for trend identification and crossover signals.

**Criteria:**

**20 EMA:**
- **Purpose:** Short-term trend and dynamic support/resistance
- **Weight:** More recent prices (α = 2/(20+1) = 9.5%)
- **Use:** Scalping and day trading
- **Signal:** Price above 20 EMA = short-term bullish

**50 EMA:**
- **Purpose:** Medium-term trend, swing trading reference
- **Weight:** α = 2/(50+1) = 3.9%
- **Use:** Most popular among swing traders
- **Signal:** Golden cross (50 above 200) = major uptrend

**200 EMA:**
- **Purpose:** Long-term trend, major bull/bear divider
- **Weight:** α = 2/(200+1) = 1%
- **Use:** Position trading and macro trend identification
- **Signal:** Price above 200 EMA = bull market bias

**Crossover Signals:**
- **Golden Cross:** 50 EMA crosses above 200 EMA (bullish)
- **Death Cross:** 50 EMA crosses below 200 EMA (bearish)
- **9/21 EMA:** Fast crossovers for aggressive day trading

**Function:** Returns 20/50/200 EMA values, crossover signals, current price position, trend direction, dynamic S/R levels

**BTC-Specific Notes:**
- Bitcoin respects 50 EMA and 200 EMA on 4hr and daily charts
- During bull markets, 50 EMA provides dynamic support with 65%+ bounce rate
- 200 EMA on weekly Bitcoin chart = major trend divider
- Golden cross on Bitcoin daily chart preceded major rallies (2019, 2020)
- Death cross signaled 2018 and 2022 bear markets
- Bitcoin above 200 daily EMA = bull market bias, below = bear
- EMA pullbacks in trending Bitcoin markets offer 1:3+ R:R entries
- Combine with RSI: 50 EMA pullback + RSI 40-50 = optimal entry

**Trading Strategy - EMA + RSI:**
1. Confirm trend: Price above 50 EMA
2. Wait for pullback to 50 EMA
3. Enter when RSI moves up from <50 (but not oversold)
4. Stop-loss below EMA
5. Target: Previous high or next resistance

**Trading Strategy - Golden/Death Cross:**
1. Identify crossover on 4hr or daily chart
2. Wait for retest of EMAs after cross
3. Enter in direction of cross
4. Hold position for weeks to months
5. Exit on opposite crossover signal

**Document:** docs/v3/building_blocks/moving_averages/EMA_Crossover_Systems.md  
**File:** src/detectors/building_blocks/moving_averages/ema_crossover.py  
**Backtest Result:** Golden Cross 77% CAGR historical  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Order Flow Imbalance (OFI)
**Description:** Measures imbalance between aggressive buy and sell orders at each price level, revealing institutional order flow.

**Criteria:**
- **Calculation:** OFI = (Buy Volume - Sell Volume) at each price level
- **Market Orders:** Only aggressive takers (market orders), not limit orders
- **Positive OFI:** Buy orders > Sell orders (bullish pressure)
- **Negative OFI:** Sell orders > Buy orders (bearish pressure)
- **Threshold Levels:** Typical 300% (3:1), 400% (4:1), or 900% (9:1) imbalance
- **Consecutive Imbalances:** Multiple bars at same price = strong S/R forming
- **Volume Delta:** Cumulative OFI shows net buying/selling pressure
- **Requires Level 2 Data:** Order book / market depth access

**Function:** Returns OFI value, imbalance direction, threshold level, volume delta, consecutive imbalance count, support/resistance zones

**BTC-Specific Notes:**
- Research shows 60% forecast improvement for price direction (ScienceDirect study)
- Bitcoin order flow particularly useful on major exchanges (Binance, Coinbase)
- Large OFI imbalances (>5:1) often precede Bitcoin breakouts
- Consecutive buy imbalances at same level = institutional accumulation
- Consecutive sell imbalances = distribution phase
- OFI works best on 1min to 15min Bitcoin charts for scalping
- Spoofing detection: Large orders appearing/disappearing quickly
- Combine with volume profile POC for confirmation

**Trading Strategy - Scalping:**
1. Monitor order book for significant imbalance (>4:1)
2. Enter in direction of imbalance
3. Place tight stop-loss (opposite side of imbalance)
4. Target small profits (0.3-0.5% on Bitcoin)
5. Exit when imbalance reverses

**Trading Strategy - Accumulation Detection:**
1. Identify consecutive buy imbalances at same price level
2. Recognize institutional accumulation phase
3. Enter long position on next pullback to that level
4. Stop below accumulation zone
5. Target next resistance or measured move

**Document:** docs/v3/building_blocks/institutional/Order_Flow_Imbalance.md  
**File:** src/detectors/building_blocks/institutional/order_flow_imbalance.py  
**Backtest Result:** 60% forecast improvement (research study)  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Market Depth Analysis
**Description:** Analyzes bid/ask depth at multiple price levels to gauge liquidity and predict support/resistance.

**Criteria:**
- **Order Book Structure:** Displays pending limit orders at each price
- **Bid Depth:** Total buy orders at various prices below current
- **Ask Depth:** Total sell orders at various prices above current
- **Depth Ratio:** Bid/Ask volume ratio (>1.5 = bullish, <0.67 = bearish)
- **Liquidity Zones:** Price levels with concentrated orders
- **Support Levels:** Large bid clusters indicate strong support
- **Resistance Levels:** Large ask clusters indicate resistance
- **Spread Analysis:** Tight spread = high liquidity, wide = low liquidity
- **Spoofing Detection:** Large orders that disappear before execution

**Function:** Returns bid/ask depth ratio, support/resistance clusters, spread size, liquidity assessment, spoofing alerts, depth chart visualization

**BTC-Specific Notes:**
- Research shows 60% price impact prediction accuracy
- Bitcoin market depth critical during high volatility (leverage liquidations)
- Large bid walls at round numbers ($90k, $95k, $100k) often psychological
- Disappearing sell walls can trigger Bitcoin breakouts
- Depth ratio <0.5 indicates elevated downside risk
- Thin order books lead to increased Bitcoin volatility and slippage
- Best exchanges for depth analysis: Binance, Coinbase Pro, Kraken
- Weekend Bitcoin depth typically 30-50% lower (higher manipulation risk)

**Trading Strategy - Support/Resistance:**
1. Identify large bid clusters (>5x average size)
2. Mark as potential support level
3. Enter long on approach to support with price rejection
4. Stop-loss below support cluster
5. Target next ask cluster (resistance)

**Trading Strategy - Breakout Confirmation:**
1. Monitor large ask wall above resistance
2. Watch for wall disappearing or getting consumed
3. Enter long on breakout above resistance
4. Volume confirmation required
5. Target measured move or next resistance

**Document:** docs/v3/building_blocks/institutional/Market_Depth_Analysis.md  
**File:** src/detectors/building_blocks/institutional/market_depth.py  
**Backtest Result:** 60% price impact prediction  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## NEW CATEGORY 13: SUPPLY/DEMAND & FIBONACCI INDICATORS

### Block Name: Supply & Demand Zones
**Description:** Identifies consolidation zones where institutions accumulated or distributed, creating future support/resistance.

**Criteria:**

**Demand Zone (Bullish):**
- **Base Formation:** Price consolidates with small candles, low volatility
- **Aggressive Departure:** Strong bullish move leaving the base (high volume, large candles)
- **Imbalance/FVG:** Often creates Fair Value Gap above zone
- **Reaction:** Price returns to zone, bounces (retest of demand)

**Supply Zone (Bearish):**
- **Base Formation:** Price consolidates before drop
- **Aggressive Departure:** Strong bearish move from the base (high volume)
- **Imbalance/FVG:** Creates Fair Value Gap below zone
- **Reaction:** Price returns to zone, rejects (retest of supply)

**Zone Characteristics:**
- **Fresh Zones:** Untouched zones most reliable
- **Strong Departure:** Steeper departure = stronger zone
- **Volume Spike:** High volume on departure confirms institutional activity
- **Consolidation Size:** Larger base = more significant zone
- **Multiple Touches:** Each touch weakens zone reliability

**Function:** Returns zone type (Supply/Demand), zone boundaries, departure strength, age, touch count, volume profile, validity score (0-100)

**BTC-Specific Notes:**
- Research shows 68% success rate for supply/demand zones (2024 study)
- Extremely effective for Bitcoin swing trading (days to weeks)
- Fresh demand zones in Bitcoin uptrends provide 1:4+ R:R entries
- Supply zones form at Bitcoin resistance during distribution phases
- Zone identification works best on 4hr and daily Bitcoin charts
- Combine with Smart Money Concepts: Demand zone + FVG = optimal
- Failed zones (break without reaction) signal strong trend
- Bitcoin respects institutional S/D zones more than retail S/R levels

**Trading Strategy - Demand Zone:**
1. Identify consolidation before strong upward move
2. Mark demand zone at consolidation area
3. Wait for price to return to zone
4. Enter long on bullish confirmation (engulfing, pin bar)
5. Stop-loss below zone
6. Target: Previous high or opposite supply zone
7. First touch highest probability (fresh zone)

**Trading Strategy - Supply Zone:**
1. Identify consolidation before strong downward move
2. Mark supply zone at consolidation area
3. Wait for price rally back to zone
4. Enter short on bearish confirmation
5. Stop-loss above zone
6. Target: Previous low or opposite demand zone

**Document:** docs/v3/building_blocks/supply_demand/Supply_Demand_Zones.md  
**File:** src/detectors/building_blocks/supply_demand/supply_demand_zones.py  
**Backtest Result:** 68% success rate (2024 study)  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Fibonacci Retracements
**Description:** Identifies potential reversal levels based on Fibonacci ratios (23.6%, 38.2%, 50%, 61.8%, 78.6%) within trends.

**Criteria:**

**Fibonacci Levels:**
- **23.6%:** Shallow retracement, weak pullback
- **38.2%:** Common retracement in strong trends
- **50%:** Psychological midpoint (not true Fibonacci but widely used)
- **61.8%:** Golden Ratio - strongest reversal level
- **78.6%:** Deep retracement, trend weakening signal
- **100%:** Full retracement (trend failure)

**Application:**
- **Uptrend:** Draw from swing low to swing high
- **Downtrend:** Draw from swing high to swing low
- **Retracement Entry:** Enter at Fibonacci levels in direction of main trend
- **Extension Targets:** 161.8%, 261.8% for profit targets

**Function:** Returns all Fibonacci levels, current price position, nearest level, support/resistance status, historical reaction data

**BTC-Specific Notes:**
- Research shows 60% success rate (UPV 2021 study)
- Profitable in energy and crypto markets specifically
- Bitcoin respects 61.8% retracement with remarkable consistency
- Most price reversals occur at 38.2-61.8% zone
- Fibonacci works best on Bitcoin 4hr and daily charts
- Combine with EMAs: 61.8% Fib + 50 EMA confluence = high probability
- OTE (Optimal Trade Entry) uses 62-79% zone for ICT methodology
- Bitcoin extensions often reach 161.8% and 261.8% in strong trends

**Trading Strategy - Retracement Entry:**
1. Identify clear trend (uptrend/downtrend)
2. Wait for pullback after impulse move
3. Draw Fibonacci from swing low to high (uptrend)
4. Watch for reversal at 38.2%, 50%, or 61.8%
5. Enter with confirmation (candlestick pattern, volume)
6. Stop-loss below 78.6% level
7. Target: Previous high or 161.8% extension

**Trading Strategy - Extension Targets:**
1. Identify completed retracement and reversal
2. Draw Fibonacci extension from initial swing
3. Set take profit at 161.8% extension (conservative)
4. Set TP2 at 261.8% extension (aggressive)
5. Trail stop-loss as price advances

**Document:** docs/v3/building_blocks/fibonacci/Fibonacci_Retracements.md  
**File:** src/detectors/building_blocks/fibonacci/fibonacci_retracements.py  
**Backtest Result:** 60% success rate (UPV study)  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## NEW CATEGORY 14: HARMONIC PATTERNS

### Block Name: Harmonic Patterns (Gartley, Butterfly, Bat, Crab)
**Description:** Advanced 5-point patterns (X, A, B, C, D) based on specific Fibonacci ratios, signaling high-probability reversals.

**Criteria:**

**Pattern Structure (5 Points):**
- **X:** Pattern origin
- **A:** First impulse move
- **B:** First retracement (creates the "eye")
- **C:** Second impulse
- **D:** Pattern completion zone (PCZ) - reversal point

**Gartley Pattern:**
- B retracement: 61.8% of XA
- C retracement: 38.2-88.6% of AB
- D: 78.6% retracement of XA
- CD: 127-161.8% extension of AB
- Most common harmonic pattern

**Butterfly Pattern:**
- B retracement: 78.6% of XA
- C retracement: 38.2-88.6% of AB
- D: 127% or 161.8% extension of XA (beyond X)
- CD: 161.8-261.8% extension of BC
- D point extends past X point

**Bat Pattern:**
- B retracement: 38.2-50% of XA
- C retracement: 38.2-88.6% of AB
- D: 88.6% retracement of XA
- CD: 161.8-261.8% extension of BC
- Tighter pattern with shallow B

**Crab Pattern:**
- B retracement: 38.2-61.8% of XA
- C retracement: 38.2-88.6% of AB
- D: 161.8% extension of XA (deep extension)
- CD: 224-361.8% extension of BC
- Deepest extension pattern

**Function:** Returns pattern type, X/A/B/C/D coordinates, Fibonacci validation, completion percentage, PCZ (Pattern Completion Zone), entry/stop/target levels

**BTC-Specific Notes:**
- Research shows 80-90% accuracy (LiteFinance, FxGroundworks)
- Harmonic patterns highly effective on Bitcoin 4hr and daily charts
- Butterfly pattern common at Bitcoin cycle tops (reversal signal)
- Gartley most frequent pattern in Bitcoin trending markets
- D point (PCZ) provides precise entry with tight stops
- Combine with RSI divergence at D point for confirmation
- Bitcoin volatility creates clear harmonic patterns
- Target zones: A to C retracement (conservative), measured extensions (aggressive)

**Trading Strategy - Gartley Bullish:**
1. Identify X, A, B points forming
2. Validate B is 61.8% of XA
3. Wait for C and D to complete pattern
4. Enter long at D point (78.6% of XA)
5. Stop-loss below D (X point for conservative)
6. TP1: A point level
7. TP2: 61.8% retracement of AD

**Trading Strategy - Butterfly Bearish:**
1. Pattern forms at resistance/top
2. D point extends beyond X (127-161.8%)
3. Enter short at D completion
4. Stop above D point extension
5. Target C level (first target)
6. Target A level (second target)
7. Risk-Reward typically 1:2 to 1:4

**Document:** docs/v3/building_blocks/harmonic/Harmonic_Patterns.md  
**File:** src/detectors/building_blocks/harmonic/harmonic_patterns.py  
**Backtest Result:** 80-90% accuracy (research studies)  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## NEW CATEGORY 15: TREND STRENGTH & MOMENTUM

### Block Name: ADX (Average Directional Index)
**Description:** Measures trend strength (not direction) using +DI and -DI indicators, helping traders distinguish trending vs ranging markets.

**Criteria:**

**ADX Components:**
- **ADX Line:** Trend strength (0-100 scale)
- **+DI (Positive Directional Indicator):** Upward movement strength
- **-DI (Negative Directional Indicator):** Downward movement strength

**ADX Interpretation:**
- **0-25:** Weak or no trend, ranging/choppy market (avoid trend-following)
- **25-50:** Moderate trend, developing strength
- **50-75:** Strong trend, trend-following strategies optimal
- **75-100:** Very strong trend, rare but extremely powerful

**Directional Signals:**
- **+DI > -DI:** Uptrend in effect (bulls in control)
- **-DI > +DI:** Downtrend in effect (bears in control)
- **+DI crosses above -DI + ADX >25:** Strong buy signal
- **-DI crosses above +DI + ADX >25:** Strong sell signal

**ADX Rising:** Existing trend strengthening (follow trend)
**ADX Falling:** Trend weakening (prepare for reversal or consolidation)

**Function:** Returns ADX value, +DI, -DI, trend strength category, directional bias, crossover signals, rising/falling status

**BTC-Specific Notes:**
- ADX extremely effective for filtering Bitcoin trend vs chop
- ADX >25 on Bitcoin 4hr/daily indicates tradeable trend
- During Bitcoin bull runs, ADX often stays 40-60 for weeks
- ADX <20 signals ranging Bitcoin market (avoid breakout trades)
- Combine with EMAs: ADX >25 + price above 50 EMA = strong trend-following signal
- Bitcoin ADX spike above 50 often precedes parabolic moves
- Falling ADX after strong trend warns of upcoming consolidation
- Best for position sizing: Larger positions when ADX >40

**Trading Strategy - Trend Following:**
1. Wait for ADX to rise above 25
2. Identify direction: +DI above -DI = uptrend
3. Enter long on pullback to EMA
4. Hold position while ADX stays above 25 and rising
5. Exit when ADX starts falling or drops below 25
6. Switch to range-trading strategies when ADX <20

**Trading Strategy - Directional Crossover:**
1. Monitor +DI and -DI for crossover
2. Wait for ADX >25 (confirms trend strength)
3. Entry: +DI crosses above -DI = Long signal
4. Entry: -DI crosses above +DI = Short signal
5. Stop-loss: Recent swing low/high
6. Hold until opposite crossover or ADX falls below 20

**Document:** docs/v3/building_blocks/trend/ADX.md  
**File:** src/detectors/building_blocks/trend/adx.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Block Name: Ichimoku Cloud
**Description:** Comprehensive indicator system showing trend direction, momentum, support/resistance using 5 components forming a "cloud."

**Criteria:**

**Ichimoku Components:**

**1. Tenkan-sen (Conversion Line):**
- Formula: (9-period high + 9-period low) / 2
- Shows short-term momentum
- Price above = bullish momentum

**2. Kijun-sen (Base Line):**
- Formula: (26-period high + 26-period low) / 2
- Shows medium-term trend
- Acts as stronger support/resistance than Tenkan

**3. Senkou Span A (Leading Span A):**
- Formula: (Tenkan + Kijun) / 2, plotted 26 periods ahead
- Forms cloud top/bottom edge
- Faster reacting cloud boundary

**4. Senkou Span B (Leading Span B):**
- Formula: (52-period high + 52-period low) / 2, plotted 26 periods ahead
- Forms cloud opposite edge
- Slower reacting boundary

**5. Chikou Span (Lagging Span):**
- Current close plotted 26 periods back
- Confirms momentum and trend

**The Cloud (Kumo):**
- Area between Senkou Span A and B
- Green cloud: Span A > Span B (bullish)
- Red cloud: Span B > Span A (bearish)
- Thick cloud: Strong support/resistance
- Thin cloud: Weak support/resistance

**Function:** Returns all 5 component values, cloud color, cloud thickness, current position (above/below/in cloud), trend strength, support/resistance levels

**BTC-Specific Notes:**
- Ichimoku highly effective on Bitcoin 4hr and daily charts
- Research shows profitable application in Vietnam market (11 citations)
- Bitcoin price above green cloud = strong bullish signal
- Price below red cloud = strong bearish signal
- Cloud twist (color change) signals potential trend reversal
- Thick Bitcoin cloud provides reliable support/resistance
- Breakout above cloud with volume = high-probability long entry
- Tenkan/Kijun crossover above cloud = bullish confirmation
- Bitcoin bull runs often show price walking along cloud top

**Trading Strategy - Ichimoku Cloud Breakout:**
1. Identify trend: Price position relative to cloud
2. Wait for price to break above cloud (bullish) or below (bearish)
3. Confirm: Tenkan above Kijun, Chikou above price from 26 periods ago
4. Entry: Buy on close above cloud
5. Stop-loss: Below cloud or below Kijun
6. Target: Measured move or next major resistance
7. Trail stop using Kijun line

**Trading Strategy - Ichimoku Pullback (Uptrend):**
1. Confirm uptrend: Price above cloud, cloud is green
2. Wait for pullback to Kijun or cloud top
3. Enter long on bounce from Kijun/cloud
4. Stop below cloud
5. Target: Previous high
6. Strong signal when all components align bullish

**Document:** docs/v3/building_blocks/trend/Ichimoku_Cloud.md  
**File:** src/detectors/building_blocks/trend/ichimoku_cloud.py  
**Backtest Result:** Profitable (Vietnam market study)  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### Multi-Timeframe Confirmation Checklist

**For maximum confluence, verify alignment across:**

1. **Daily Timeframe:**
   - Trend direction (EMA 200 position)
   - Market structure (swing points)
   - Wyckoff phase (accumulation/distribution)
   - Elliott Wave count

2. **4-Hour Timeframe:**
   - Setup development (OTE formation)
   - Order blocks (building positions)
   - MACD momentum (divergence confirmation)
   - Break of Structure signals

3. **1-Hour Timeframe:**
   - Entry confirmation (candle patterns)
   - Fibonacci retracement completion
   - Volatility assessment (ATR/Bollinger Bands)
   - Session timing validation

4. **15-Minute Timeframe:**
   - Precise entry execution
   - Volume spike confirmation
   - Micr-trend alignment
   - Rejection wick patterns

**Scoring:** Each aligned timeframe adds 5-10 confluence points

---
## TECHNICAL COMPONENTS (Indicators & Systems)

### Currently Implemented ✅

**1. Zigzag Pivot Detector**
- **File:** `src/detectors/zigzag_detector.py`
- **Function:** Finds pivot highs and lows
- **Parameters:** Length (bars each side for pivot)
- **Output:** List of Pivot objects with price, index, type, oscillator value
- **Use Cases:** All pattern detection, trend analysis, support/resistance

**2. RSI Oscillator**
- **File:** `src/detectors/oscillators.py` (calculate_rsi)
- **Function:** Relative Strength Index calculation
- **Parameters:** Length (default 14)
- **Output:** RSI values (0-100)
- **Use Cases:** Divergences, overbought/oversold, statistical patterns

**3. Pattern Encoder (48 patterns)**
- **File:** `src/detectors/pattern_encoder.py`
- **Function:** Encodes 3-pivot sequences into pattern index
- **Components:** Trend + Price momentum + RSI divergence
- **Output:** Pattern index 0-47 with metadata
- **Use Cases:** Statistical prediction, divergence detection

**4. Pattern Statistics System**
- **File:** `src/detectors/pattern_statistics.py`
- **Function:** Tracks historical outcomes for each pattern
- **Metrics:** Win rate, Fibonacci ratios, bar counts
- **Output:** Predictions with probabilities
- **Use Cases:** Probability-based entries, confluence validation

**5. Volume Analyzer (needs revision)**
- **File:** `src/detectors/volume_analyzer.py`
- **Function:** Volume state classification (CLIMAX/HIGH/NORMAL/LOW)
- **Note:** Current logic needs crypto-specific adjustments
- **Use Cases:** Volume confirmation, institutional activity detection

**6. Divergence Detector**
- **File:** `src/detectors/divergence_detector.py`
- **Function:** Detects price/oscillator divergences
- **Types:** Regular, Hidden, Bullish, Bearish
- **Use Cases:** Pattern filtering, entry confirmation
---

## DOCUMENT MAINTENANCE

**Last Updated:** 2025-12-31  
**Next Review:** Quarterly  
**Maintained By:** Trading System Development Team  
**Version Control:** Git repository with detailed commit history


---

## TOTAL BUILDING BLOCKS: 66

**Categories:**
1. Moving Averages: 5 blocks
2. Oscillators: 3 blocks
3. Price Levels: 6 blocks
4. Sessions & Time: 2 blocks
5. Volatility: 3 blocks
6. Advanced Price Action: 4 blocks
7. Smart Money Concepts (ICT/SMC): 10 blocks
8. Elliott Wave: 2 blocks
9. Wyckoff Method: 3 blocks
10. Market Structure: 3 blocks
11. Pattern-Based Building Blocks: 15 blocks
12. Institutional & Volume Indicators: 5 blocks
13. Supply/Demand & Fibonacci: 2 blocks
14. Harmonic Patterns: 1 block (4 patterns) 
15. Trend Strength & Momentum: 2 blocks 
---

**End of Master Building Blocks Document v1**
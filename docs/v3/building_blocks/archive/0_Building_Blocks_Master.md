# Master Building Block Document (Optimized for Cline/Claude Sonnet 4.5)

**Version:** v3 (Optimized for Bitcoin Crypto Trading)  
**Document Path:** docs/v3/building_blocks/0_Building_Blocks_Master.md  
**Purpose:** This is the central tracker for all building blocks (concept blocks, status, documentation) specifically optimized for Bitcoin cryptocurrency market analysis.

---

## Overview

This master document tracks all building blocks used in systematic trading strategy development. Each building block is a standardized, testable component that can be combined with others in permutation backtests to discover profitable trading patterns.

### Building Block Requirements

- **Backtesting:** Each block requires backtest results on 15min and 30min timeframes
- **Walk-forward Testing:** Must pass walk-forward validation
- **Standardization:** All blocks must follow the same structure and return format
- **Multi-timeframe:** Must work across different timeframes
- **Bitcoin-Specific:** Optimized for Bitcoin 24/7 crypto market characteristics

### Strategy Development Process

Building blocks are combined in systematic permutation tests to discover profitable patterns. 

Example 1:
- 15min break of 50 EMA + Stochastic RSI Oversold + 1hr retest of LOD + Order Book liquidity above price = Bullish strategy test
- If confirmed successful, it becomes a tradable pattern or confluence for existing patterns

Example 2
- UK trend was up and continued Asia trend, price is near HOW, US session starts, Price breaks HOW but closes below, RSI overbought, RSI crossing down, Double Top Pattern = Bearish
- If confirmed, US will take price down to near 50% Asia, if breaks through 50% Asia, price will visit near US settlement from previous day.  It is a Short trade
---

## BUILDING BLOCKS

### 1. Moving Average Indicators

#### Block Name: 50 EMA Vector Break
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

#### Block Name: 55 EMA Vector Break
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

**Document:** docs/v3/building_blocks/55_EMA_Vector_Break.md  
**File:** src/detectors/building_blocks/55_ema_vector_break.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: 200 EMA Vector Break
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

#### Block Name: 255 EMA Vector Break
**Description:** Breaks the 255 EMA with a vector candle (high volume candle).

**Criteria:**
- Break 255 EMA with Vector Candle
- Must know if the break is breaking bullish or bearish
- Must be able to work on any timeframe
- Track how many breaks of the EMA before the candle close

**Function:** Returns "Bullish Break" or "Bearish Break"

**Document:** docs/v3/building_blocks/255_EMA_Vector_Break.md  
**File:** src/detectors/building_blocks/255_ema_vector_break.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: 800 EMA Vector Break
**Description:** Breaks the 800 EMA with a vector candle (high volume candle).

**Criteria:**
- Break 800 EMA with Vector Candle
- Must know if the break is breaking bullish or bearish
- Must be able to work on any timeframe
- Track how many breaks of the EMA before the candle close

**Function:** Returns "Bullish Break" or "Bearish Break"

**BTC-Specific Notes:**
- Extremely long-term trend indicator
- Rarely broken on intraday timeframes
- On weekly/monthly charts, signals major market regime changes

**Document:** docs/v3/building_blocks/800_EMA_Vector_Break.md  
**File:** src/detectors/building_blocks/800_ema_vector_break.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### 2. Oscillator Indicators

#### Block Name: MACD Signal
**Description:** Identifies MACD crossovers and divergences for trend momentum detection.

**Criteria:**
- Standard MACD settings: 12, 26, 9 (do not change - market standard)
- **Bullish Signal:** MACD line crosses above Signal line
- **Bearish Signal:** MACD line crosses below Signal line
- **Bullish Divergence:** Price makes lower low, MACD makes higher low
- **Bearish Divergence:** Price makes higher high, MACD makes lower high
- **Histogram Analysis:** Increasing bars = momentum building, Decreasing bars = momentum weakening
- Must work on any timeframe
- Zero line cross: MACD above 0 = bullish trend, below 0 = bearish trend

**Function:** Returns signal type ("Bullish Crossover", "Bearish Crossover", "Bullish Divergence", "Bearish Divergence", "Neutral") with histogram momentum indicator

**BTC-Specific Notes:**
- MACD effective on 4hr and daily Bitcoin charts
- Crossovers work best in trending markets, not sideways
- Combine with volume confirmation to avoid false signals
- During Bitcoin bull runs, MACD crossovers showed 77%+ CAGR vs 61% buy-and-hold
- Reduces maximum drawdown significantly (from -83% to -62%)

**Document:** docs/v3/building_blocks/MACD_Signal.md  
**File:** src/detectors/building_blocks/macd_signal.py  
**Backtest Result:** 77% CAGR (historical data)  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: Stochastic RSI Cross
**Description:** Detects when Stochastic RSI signal lines cross to identify overbought/oversold conditions.

**Criteria:**
- Stochastic RSI consists of two lines: %K line (fast) and %D line (slow, 3-period MA of %K)
- **Bullish Signal (Buy):** %K crosses above %D, especially below 20 level (oversold zone)
- **Bearish Signal (Sell):** %K crosses below %D, especially above 80 level (overbought zone)
- Must work on any timeframe
- Most significant signals occur in oversold (<20) or overbought (>80) regions
- Neutral zone (20-80) signals are less reliable

**Function:** Returns signal type ("Bullish Cross", "Bearish Cross", "Oversold Bullish", "Overbought Bearish", "Neutral") with zone indicator

**BTC-Specific Notes:**
- Highly effective for Bitcoin swing trading on 4hr/daily timeframes
- In strong trends, can remain overbought/oversold for extended periods
- Best used with trend confirmation from EMAs

**Document:** docs/v3/building_blocks/Stochastic_RSI_Cross.md  
**File:** src/detectors/building_blocks/stochastic_rsi_cross.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: RSI Divergence
**Description:** Identifies bullish and bearish divergence between price action and RSI indicator.

**Criteria:**
- Standard RSI period: 14
- **Bullish Divergence:** Price makes lower lows, RSI makes higher lows (weakening downtrend)
- **Bearish Divergence:** Price makes higher highs, RSI makes lower highs (weakening uptrend)
- **Hidden Bullish Divergence:** Price makes higher lows, RSI makes lower lows (continuation signal in uptrend)
- **Hidden Bearish Divergence:** Price makes lower highs, RSI makes higher highs (continuation signal in downtrend)
- Must identify at least 2 pivot points for valid divergence
- More reliable on higher timeframes (1hr+)
- Confirm with volume and support/resistance levels

**Function:** Returns divergence type ("Bullish Divergence", "Bearish Divergence", "Hidden Bullish", "Hidden Bearish", "None") with strength score (0-100)

**BTC-Specific Notes:**
- RSI divergence often precedes major Bitcoin trend reversals
- Most effective on daily and 4hr charts
- During 2017 bull run, RSI divergences marked key accumulation phases
- Failed divergences can occur - always confirm with price action
- Combine with MACD and Bollinger Bands for higher probability setups

**Document:** docs/v3/building_blocks/RSI_Divergence.md  
**File:** src/detectors/building_blocks/rsi_divergence.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### 3. Price Level Indicators

#### Block Name: HOD (High of Day)
**Description:** Identifies and tracks the highest price reached during the current trading day.

**Criteria:**
- Calculate highest price from 00:00 UTC to current time (or 00:00 local exchange time)
- Update in real-time as new highs are made
- Track number of times HOD has been tested/touched
- Identify breaks above HOD (breakout) vs rejection at HOD (resistance)
- Reset at daily open (00:00 UTC)
- Must work on intraday timeframes (1min, 5min, 15min, 30min, 1hr)

**Function:** Returns HOD price level, current distance from HOD, breakout status ("Above HOD", "At HOD", "Below HOD"), number of tests

**BTC-Specific Notes:**
- HOD acts as intraday resistance in Bitcoin markets
- Breakouts above HOD with volume often lead to continuation
- During US trading session (13:00-21:00 UTC), HOD breaks are more significant
- False breakouts common during low liquidity periods (Asian session gaps)
- Use with volume confirmation and session time awareness

**Document:** docs/v3/building_blocks/HOD.md  
**File:** src/detectors/building_blocks/hod.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: LOD (Low of Day)
**Description:** Identifies and tracks the lowest price reached during the current trading day.

**Criteria:**
- Calculate lowest price from 00:00 UTC to current time
- Update in real-time as new lows are made
- Track number of times LOD has been tested/touched
- Identify breaks below LOD (breakdown) vs bounce at LOD (support)
- Reset at daily open (00:00 UTC)
- Must work on intraday timeframes (1min, 5min, 15min, 30min, 1hr)

**Function:** Returns LOD price level, current distance from LOD, breakdown status ("Below LOD", "At LOD", "Above LOD"), number of tests

**BTC-Specific Notes:**
- LOD acts as intraday support in Bitcoin markets
- Multiple tests of LOD without breaking often lead to reversal
- Liquidity sweeps below LOD followed by quick recovery are common traps
- Combined with order flow analysis for high-probability entries

**Document:** docs/v3/building_blocks/LOD.md  
**File:** src/detectors/building_blocks/lod.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: HOW (High of Week)
**Description:** Identifies and tracks the highest price reached during the current trading week.

**Criteria:**
- Calculate highest price from Monday 00:00 UTC to current time
- Week starts Monday 00:00 UTC, ends Sunday 23:59 UTC
- Update in real-time as new weekly highs are made
- Track number of times HOW has been tested
- Identify breakout above HOW vs rejection
- Monday's high and low often set the weekly range (Weekly Opening Range - WOR)

**Function:** Returns HOW price level, current distance from HOW, breakout status, WOR status, number of tests

**BTC-Specific Notes:**
- Weekly highs/lows more significant than daily for swing trading
- Monday's range (WOR) often determines weekly directional bias
- Clear break above HOW on Monday signals strong weekly bullish trend
- Weekend gaps can significantly impact Monday opening and WOR formation
- Use for position trading and longer-term trend identification

**Document:** docs/v3/building_blocks/HOW.md  
**File:** src/detectors/building_blocks/how.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: LOW (Low of Week)
**Description:** Identifies and tracks the lowest price reached during the current trading week.

**Criteria:**
- Calculate lowest price from Monday 00:00 UTC to current time
- Week starts Monday 00:00 UTC, ends Sunday 23:59 UTC
- Update in real-time as new weekly lows are made
- Track number of times LOW has been tested
- Identify breakdown below LOW vs bounce
- Monday's range establishes weekly support/resistance framework

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

#### Block Name: US Settlement Price (16:00-17:00 EST / 21:00-22:00 UTC)
**Description:** Tracks the price level at US market close (4:00 PM EST) which sets the daily candle close for many traditional markets.

**Criteria:**
- Capture Bitcoin price at 16:00 EST (21:00 UTC) - official US equity market close
- Track settlement price range (16:00-17:00 EST / 21:00-22:00 UTC)
- Identify if current price is above/below settlement price
- Calculate distance from settlement level
- Settlement price becomes reference point for next day's trading
- US settlement affects Bitcoin ETF pricing and CME futures settlement

**Function:** Returns settlement price, current price position relative to settlement ("Above", "At", "Below"), distance in dollars and percentage, next settlement time

**BTC-Specific Notes:**
- Bitcoin often shows increased volatility around US market close (16:00 EST)
- CME Bitcoin futures settle at 16:00 EST, impacting spot price
- Bitcoin ETF NAV calculated based on 16:00 EST prices
- Institutional flows often concentrate near settlement time
- Price action 15:30-16:30 EST critical for daily bias
- Post-settlement (17:00-18:00 EST) often shows low liquidity "dead zone"

**Document:** docs/v3/building_blocks/US_Settlement.md  
**File:** src/detectors/building_blocks/us_settlement.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: Asia Session 50% Price
**Description:** Calculates the 50% equilibrium level of the Asian trading session range.

**Criteria:**
- Asia session time: 18:00 UTC - 00:00 UTC (6:00 PM - 12:00 AM EST)
- Calculate: Asia 50% = (Asia High + Asia Low) / 2
- Track current price position relative to 50% level
- Asian range creates accumulation zone - price builds liquidity pools at highs and lows
- 50% level often acts as equilibrium/mean reversion point
- Session acts as "box" that UK/US sessions later manipulate

**Function:** Returns Asia 50% price level, Asia High, Asia Low, current position relative to 50% ("Above", "At", "Below"), range size, volume profile

**BTC-Specific Notes:**
- Asia session characterized by low volume and tight ranges
- Creates the daily liquidity pools (highs/lows) for later sessions to sweep
- Price often reverts to 50% during US session after UK manipulation
- Narrow Asia range often precedes high volatility in UK/US sessions
- Bitcoin historically shows accumulation during Asia, distribution during US/UK
- Asia 50% retest during US session = high-probability mean reversion setup
- Recent data shows Bitcoin gains during Asian session vs losses during US session

**Document:** docs/v3/building_blocks/Asia_Session_50_Percent.md  
**File:** src/detectors/building_blocks/asia_session_50_percent.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### 4. Session & Time-Based Indicators

#### Block Name: Session Time
**Description:** Determines current Forex/Crypto trading session and expected market characteristics.

**Criteria:**

**Asia Session (18:00 - 00:00 UTC / 00:00 - 06:00 JST/HKT)**
- Low volume, tight ranges
- Accumulation phase - builds liquidity pools (highs/lows)
- Creates "Asian Range" - box for later manipulation
- Typically does not set trends, establishes the range
- Support/resistance levels form session highs/lows
- Bitcoin often shows buy accumulation during this period

**UK/London Session (02:00 - 05:00 UTC / 08:00 - 11:00 GMT / Pre-US overlap)**
- Manipulation / "Judas Swing" phase
- Often sweeps Asia high or low to trap traders (liquidity grab)
- Tends to set the daily trend direction
- After sweeping Asia liquidity, reverses to establish true Daily Trend
- False moves common - "stop hunt" before true directional move

**US Session (13:00 - 21:00 UTC / 08:00 - 16:00 EST / NY Trading Hours)**
- Highest volume (UK/US overlap early, then US-only)
- Distribution / Continuation or Reversal phase
- "50% Rule": Often reverses to 50% of daily range or Asia range equilibrium
- If UK set strong trend, US often retraces to discount (50% level) before continuing or reversing
- 16:00 EST: US Settlement (CME futures, ETF NAV pricing)
- Recent patterns show Bitcoin declining during US trading hours

**Session Gap (21:00 - 18:00 UTC / 17:00 EST - 18:00 EST / Dead Zone)**
- Lowest liquidity period
- No major market maker activity
- Spreads widen significantly
- Erratic, meaningless price action
- Often used to stop out positions before new day
- Avoid trading during this period

**Weekend (Saturday/Sunday)**
- Reduced volume (crypto still trades 24/7 but traditional markets closed)
- Lower institutional participation
- Can create artificial price levels
- Monday gap risk when traditional markets reopen

**Function:** Returns current session name, expected volume level ("High", "Medium", "Low"), session bias ("Accumulation", "Manipulation", "Distribution", "Dead Zone"), weight factor (0.0-1.0) for strategy application, time remaining in session

**BTC-Specific Notes:**
- Bitcoin trades 24/7 but still influenced by traditional market sessions
- Highest Bitcoin volatility during UK/US overlap (13:00-16:00 UTC)
- US market hours show recent pattern of Bitcoin sell-offs (possibly Jane Street accumulation)
- Weekend price action less reliable due to thin liquidity
- Session gaps (17:00-18:00 EST) show stop-hunting behavior
- Use session awareness as weight factor: High volume sessions (US) = higher signal reliability
- Asia session lows often swept during London open

**Document:** docs/v3/building_blocks/Session_Time.md  
**File:** src/detectors/building_blocks/session_time.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### 5. Volatility Indicators

#### Block Name: ATR (Average True Range)
**Description:** Measures market volatility by calculating the average range of price movement over a specified period.

**Criteria:**
- Standard period: 14 (can be adjusted for different timeframes)
- True Range = Maximum of:
  - Current High - Current Low
  - |Current High - Previous Close|
  - |Current Low - Previous Close|
- ATR = 14-period moving average of True Range
- Higher ATR = higher volatility, Lower ATR = lower volatility
- Use for stop-loss placement: Stop = Entry ± (ATR × multiplier)
- Use for position sizing: Higher ATR = smaller position size
- Identify trend strength: Rising ATR = increasing momentum

**Function:** Returns current ATR value, ATR change direction ("Rising", "Falling", "Stable"), volatility level ("High", "Medium", "Low"), suggested stop-loss distance

**BTC-Specific Notes:**
- Bitcoin ATR varies significantly based on market phase
- During calm markets: ATR ≈ $500-1000 on daily chart
- During volatile markets: ATR can exceed $3000+ on daily chart
- Use ATR for adaptive stop-losses: Stop = Entry - (2 × ATR) for longs
- ATR helps determine position sizing based on current volatility
- Combine with Bollinger Bands for comprehensive volatility analysis
- Useful for identifying breakout potential: Low ATR → High ATR = breakout imminent

**Document:** docs/v3/building_blocks/ATR.md  
**File:** src/detectors/building_blocks/atr.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: ADR (Average Daily Range)
**Description:** Measures the average price movement from daily high to low over a specified period.

**Criteria:**
- Standard period: 14 days (can be adjusted 5-20 days)
- Calculation: ADR = Average of (Daily High - Daily Low) over N periods
- Focuses specifically on daily range, unlike ATR which includes gaps
- Track current day's range vs ADR percentage
- Signals when price has moved X% of ADR (e.g., 80%, 100%, 125%)
- Probabilities: ~57% chance price stays within 100% ADR, only ~23% exceed 125% ADR
- When daily range exceeds ADR, expect consolidation or reversal

**Function:** Returns ADR value, current day range, percentage of ADR completed, reversal probability, suggested profit targets

**BTC-Specific Notes:**
- Bitcoin ADR highly variable: $800-1500 typical, $3000+ during high volatility
- Use for setting realistic daily profit targets
- When BTC moves >100% of ADR, look for reversal setups
- Particularly useful for day trading Bitcoin on 15min-1hr timeframes
- Combine with session time: ADR typically filled during UK/US sessions, not Asia
- Useful for identifying when daily move is "exhausted"

**Document:** docs/v3/building_blocks/ADR.md  
**File:** src/detectors/building_blocks/adr.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: Bollinger Bands
**Description:** Volatility indicator using standard deviations around a moving average to identify overbought/oversold conditions and volatility changes.

**Criteria:**
- Standard settings: 20-period SMA, 2 standard deviations (can adjust to EMA)
- Upper Band = SMA + (2 × Standard Deviation)
- Lower Band = SMA - (2 × Standard Deviation)
- Middle Band = 20-period SMA
- **Band Width:** Wide bands = high volatility, Narrow bands = low volatility (squeeze)
- **Bollinger Squeeze:** When bands contract, major move imminent
- **Overbought:** Price touches/exceeds upper band
- **Oversold:** Price touches/exceeds lower band
- **Bollinger Bounce:** Buy at lower band, sell at upper band (range-bound markets)
- **Bollinger Breakout:** Price breaks and closes outside bands = trend continuation
- **W-Bottom:** Double bottom with second low inside bands = bullish reversal
- **M-Top:** Double top with second high inside bands = bearish reversal

**Function:** Returns band values (upper, middle, lower), current position ("Above Upper", "Between", "Below Lower"), band width status ("Expanding", "Contracting", "Squeeze"), pattern detected ("W-Bottom", "M-Top", "None")

**BTC-Specific Notes:**
- Bollinger Bands capture ~90% of Bitcoin price action
- In trending markets, Bitcoin can "walk the band" (stay near upper/lower band)
- Squeeze (narrow bands) often precedes major Bitcoin breakouts
- For Bitcoin: Use 20-period SMA with 2 SD on 4hr and daily charts
- Combine with ATR for confirmation: BB squeeze + rising ATR = breakout
- Price above upper band = overbought (reversal likely), below lower = oversold
- Works for multiple crypto assets, adjust to asset volatility

**Document:** docs/v3/building_blocks/Bollinger_Bands.md  
**File:** src/detectors/building_blocks/bollinger_bands.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

### 6. Advanced Price Action Indicators

#### Block Name: Order Block
**Description:** Identifies significant consolidation zones where institutions placed large orders before major price movements.

**Criteria:**
- **Bullish Order Block:** Last bearish candle before bullish impulse move
- **Bearish Order Block:** Last bullish candle before bearish impulse move
- Order block represents area of accumulation/distribution before strong directional move
- Typically occurs at swing lows (bullish) or swing highs (bearish)
- Characterized by consolidation or indecision candles before explosive move
- Price often returns to order block for retest before continuing trend
- Combine with volume analysis: High volume order blocks more significant
- Multiple retests reduce reliability of order block
- Order blocks aligned with support/resistance levels have higher probability

**Function:** Returns order block type ("Bullish OB", "Bearish OB"), price range (high/low), age of block, number of retests, validity status ("Valid", "Invalidated", "Weakened")

**BTC-Specific Notes:**
- Order blocks particularly effective on Bitcoin 15min-4hr timeframes
- Institutional order blocks often align with session boundaries
- Valid order blocks provide high-probability entry zones
- Price typically respects order blocks in trending markets
- Priority: Order blocks take precedence over Fair Value Gaps when both present
- Combine with Fair Value Gaps for confluence setups
- Order blocks near swing highs/lows have 70%+ reaction rate

**Document:** docs/v3/building_blocks/Order_Block.md  
**File:** src/detectors/building_blocks/order_block.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: Fair Value Gap (FVG)
**Description:** Identifies price imbalances where three-candle patterns create gaps due to rapid directional moves.

**Criteria:**
- **FVG Formation:** Gap between candle 1 high/low and candle 3 low/high with candle 2 showing strong directional move
- **Bullish FVG:** Gap between candle 1 high and candle 3 low (unfilled buy orders)
- **Bearish FVG:** Gap between candle 1 low and candle 3 high (unfilled sell orders)
- FVG represents price inefficiency - market "wants" to fill the gap
- Market makers and exchanges incentivized to fill gaps (unfilled orders = lost fees)
- **Mitigation:** When price returns and fills the FVG
- **Valid FVG:** Larger gaps (>0.5% of price) more reliable than small gaps
- **FVG Priority:** Prefer larger gaps, more recent gaps, gaps at key levels
- Price acts as magnet to FVG - often returns to fill before continuing

**Function:** Returns FVG type ("Bullish FVG", "Bearish FVG"), gap price range, gap size, mitigation status ("Unmitigated", "Partially Filled", "Filled"), age, position relative to current price

**BTC-Specific Notes:**
- FVGs extremely common during Bitcoin volatility spikes
- Large FVGs (>1% price) almost always get filled eventually
- Combine with order blocks: FVG + Order Block = highest probability setup
- In trending markets, FVG fills provide pullback entry opportunities
- Multiple FVGs: Trade the largest or most recent first
- FVG at session boundaries (Asia → London) especially significant
- Failed FVG fills can signal strong trend continuation

**Document:** docs/v3/building_blocks/Fair_Value_Gap.md  
**File:** src/detectors/building_blocks/fair_value_gap.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: Volume Profile
**Description:** Analyzes volume distribution across price levels to identify high-volume nodes (HVN) and low-volume nodes (LVN).

**Criteria:**
- Display volume traded at each price level over specified period
- **Point of Control (POC):** Price level with highest traded volume
- **Value Area (VA):** Price range containing 70-80% of total volume
- **Value Area High (VAH):** Upper boundary of value area
- **Value Area Low (VAL):** Lower boundary of value area
- **High Volume Nodes (HVN):** Areas with significant trading activity = support/resistance
- **Low Volume Nodes (LVN):** Areas with minimal trading = price moves through quickly
- Price gravitates toward POC and VAH/VAL levels
- Price above POC = bullish sentiment, below = bearish sentiment
- LVN breakouts signal strong directional moves

**Function:** Returns POC price, VAH/VAL prices, current position relative to value area, HVN/LVN locations, volume cluster zones

**BTC-Specific Notes:**
- Volume profile critical for Bitcoin support/resistance identification
- Use session-based volume profile for 24/7 crypto markets (not just daily)
- POC often acts as magnet - price returns to test POC multiple times
- Bitcoin respects HVNs during retracements in trending markets
- LVNs provide low-resistance breakout targets
- Combine with order flow and market structure for optimal entries
- High volume at current price = potential consolidation zone

**Document:** docs/v3/building_blocks/Volume_Profile.md  
**File:** src/detectors/building_blocks/volume_profile.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

#### Block Name: Pivot Points
**Description:** Calculates support and resistance levels based on previous period's high, low, and close prices.

**Criteria:**
- **Standard Pivot Point (PP):** (Previous High + Previous Low + Previous Close) / 3
- **Resistance Levels:**
  - R1 = (2 × PP) - Previous Low
  - R2 = PP + (Previous High - Previous Low)
  - R3 = Previous High + 2 × (PP - Previous Low)
- **Support Levels:**
  - S1 = (2 × PP) - Previous High
  - S2 = PP - (Previous High - Previous Low)
  - S3 = Previous Low - 2 × (Previous High - PP)
- Price above PP = bullish bias, below PP = bearish bias
- Pivot levels act as potential reversal points
- Breaking through resistance/support levels signals trend strength
- Can be calculated for different timeframes (daily, weekly, monthly)

**Function:** Returns PP value, R1/R2/R3 levels, S1/S2/S3 levels, current position relative to PP, nearest pivot level, trend bias

**BTC-Specific Notes:**
- Daily pivot points useful for Bitcoin intraday trading
- Weekly pivots provide swing trading reference levels
- Bitcoin often respects pivot levels during consolidation
- Breakouts above R1 or below S1 signal strong directional moves
- Combine with volume: High volume at pivot levels = increased significance
- Pivot points objective and consistent across traders
- Particularly effective for short-term Bitcoin trading strategies

**Document:** docs/v3/building_blocks/Pivot_Points.md  
**File:** src/detectors/building_blocks/pivot_points.py  
**Backtest Result:** Pending  
**Walk-forward Result:** Pending  
**Status:** Research / To be Built

---

## Implementation Notes for Cline (Claude Sonnet 4.5)

### Code Structure Requirements

1. **Standardized Return Format:**
```python
{
    "signal": str,  # Main signal output
    "confidence": float,  # 0-100 confidence score
    "metadata": dict,  # Additional context data
    "timestamp": datetime,
    "timeframe": str
}
```

2. **Multi-Timeframe Support:**
- Each building block must accept timeframe parameter
- Support for: 1min, 5min, 15min, 30min, 1hr, 4hr, 1D, 1W

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
- Example: [50 EMA Break + Stochastic RSI + LOD Retest + Volume Profile]
- Automated discovery of profitable pattern combinations
- Statistical significance testing (minimum 100 trades)
- Win rate analysis by market condition

### Performance Targets

- **Minimum Win Rate:** 55%+ (for 1:2 R:R)
- **Sharpe Ratio:** >1.5
- **Maximum Drawdown:** <20%
- **Profit Factor:** >1.8
- **Minimum Trades:** 100+ for statistical validity

---

## Usage Example

**Strategy Permutation Test:**

```
Combine:
- MACD Bullish Crossover (4hr timeframe)
- RSI Oversold (<30)
- Price retest of Asia Session 50%
- Volume spike >1.5x average
- US Session (high liquidity)

If all conditions met → Enter Long
Stop Loss: 2x ATR below entry
Take Profit: HOD or previous swing high
```

---

## Document Maintenance

**Last Updated:** 2025-12-31  
**Next Review:** Quarterly  
**Maintained By:** Trading System Development Team  
**Version Control:** Git repository with detailed commit history

---

**End of Master Building Blocks Document**
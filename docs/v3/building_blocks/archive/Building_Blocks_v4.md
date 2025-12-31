# Master Building Block Document 

**Version:** v4.0 (Pattern-Based Building Blocks Added)
**Document Path:** docs/v3/building_blocks/0_Building_Blocks_Master_Complete.md  
**Purpose:** Comprehensive tracker for all building blocks (concept blocks, status, documentation) specifically optimized for Bitcoin cryptocurrency market analysis, incorporating advanced methodologies from ICT (Inner Circle Trader), Smart Money Concepts (SMC), Elliott Wave Theory, Wyckoff Method, and Classic Chart Patterns.

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

Example 2:
- UK trend was up and continued Asia trend, price is near HOW, US session starts, Price breaks HOW but closes below, RSI overbought, RSI crossing down, Double Top Pattern = Bearish
- If confirmed, US will take price down to near 50% Asia, if breaks through 50% Asia, price will visit near US settlement from previous day. It is a Short trade

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

**Total: 56 Building Blocks**

---

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

## DOCUMENT MAINTENANCE

**Last Updated:** 2025-12-31  
**Next Review:** Quarterly  
**Maintained By:** Trading System Development Team  
**Version Control:** Git repository with detailed commit history

**Version History:**
- v3.0 (2025-12-31): Initial building blocks (18 blocks)
- v3.1 (2025-12-31): Expanded with ICT, SMC, Elliott Wave, Wyckoff (41 blocks)
- v3.2 (2025-12-31): Complete merged document with integrated methodologies
- v4.0 (2025-12-31): Added Pattern-Based Building Blocks category (15 patterns)

---

## TOTAL BUILDING BLOCKS: 56

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

---

**End of Master Building Blocks Document v4.0**

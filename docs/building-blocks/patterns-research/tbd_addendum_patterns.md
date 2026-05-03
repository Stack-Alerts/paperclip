# Layer TBD – Addendum: Additional Pattern Methodologies

## Overview

Beyond the original 7 TBD patterns, the following institutional trading patterns have been proven effective and align with the market maker methodology. These patterns complement the core TBD framework and can be integrated with configuration switches.

---

## File: `layer_TBD_OB.py`

### Pattern 8 – Order Block (Institutional Accumulation/Distribution Zone)

#### Entry Conditions (CONFLUENCE SETUP)

1. **Order Block Identification**
   - Bullish OB:
     - Large bearish candle (institutional selling/distribution)
     - Followed by aggressive uptrend breakout
     - OB = body of bearish candle + 5-candle consolidation zone before breakout
   - Bearish OB:
     - Large bullish candle (institutional buying/accumulation)
     - Followed by aggressive downtrend breakdown
     - OB = body of bullish candle + 5-candle consolidation zone before breakdown

2. **Price Return to OB Zone**
   - Price must break away from OB and move in trend direction.
   - Price then retraces back into OB zone (retest).
   - OB now acts as support (bullish) or resistance (bearish).

3. **Entry Confirmation Options**
   - **Aggressive Entry**:
     - Buy stop above high of bearish candles within bullish OB.
     - Sell stop below low of bullish candles within bearish OB.
   - **Conservative Entry**:
     - Buy limit at upper edge of OB (waits for price to prove direction).
     - Sell limit at lower edge of OB.
   - **High-Probability Entry** (Confluence):
     - OB + Fair Value Gap fill
     - OB + Liquidity sweep
     - OB + Break of Structure alignment

4. **Action**
   - For bullish OB retest → **ENTER LONG**
   - For bearish OB retest → **ENTER SHORT**

#### Exit Conditions

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | OB high/low ± (OB height × 1.0) | 30% | Quick profit |
| **TP2** | OB high/low ± (OB height × 2.0) | 40% | Main target |
| **TP3** | OB high/low ± (OB height × 3.0) | 30% | Extended move |
| **Stop Loss** | Beyond OB boundary ± ATR × 1.0 | All if hit | Protective exit |

#### Configuration Parameters

```python
enable_order_block: bool = True
ob_lookback_candles: int = 5           # Candles to define OB zone
ob_retest_tolerance: float = 0.02      # 2% retest proximity
ob_volume_confirmation: float = 1.2    # Volume on retest
ob_confluence_weight: float = 0.25     # Weight for FVG+OB combos
```

#### Example Trade

```
Bullish OB Setup:
Bearish Candle (institution selling): $100,000 – $94,000
Consolidation (5 candles): $95,000 – $96,000
Breakout: Price closes $96,500 (above consolidation)
Trend Move: Price rallies to $102,000
Retest: Price retraces into OB zone ($95,500 – $96,200)
Entry (LONG): $95,800 (conservative limit)
TP1: $99,200 | TP2: $102,600 | TP3: $106,000
Stop: $95,000 (below OB) | Risk:Reward = 1:3
```

---

## File: `layer_TBD_FVG.py`

### Pattern 9 – Fair Value Gap (Imbalance Zone)

#### Entry Conditions (TREND CONTINUATION)

1. **FVG Formation**
   - Three consecutive candles where the middle candle's range is NOT touched by candles 1 and 3.
   - **Bullish FVG**:
     - Candle 3 low > Candle 1 high (gap created upward)
     - Indicates rapid upward price move without consolidation
   - **Bearish FVG**:
     - Candle 3 high < Candle 1 low (gap created downward)
     - Indicates rapid downward price move without consolidation

2. **FVG Characteristics**
   - Forms during high-volume moves (institutional entry with conviction)
   - Gap size typically 0.5%–2% of price
   - Most reliable on higher timeframes (1H, 4H, Daily)
   - Recent FVGs more significant than old ones

3. **Entry Strategy – Price Return to FVG**
   - Price moves away from FVG
   - Price retraces back into gap zone
   - Entry on retest with confirmation
   - **Bullish FVG (LONG)**:
     - Price retraces into bullish FVG from above
     - Enter on bullish reversal pattern (pin bar, engulfing, BOS)
   - **Bearish FVG (SHORT)**:
     - Price retraces into bearish FVG from below
     - Enter on bearish reversal pattern

4. **Action**
   - Bullish FVG retest with bullish confirmation → **ENTER LONG**
   - Bearish FVG retest with bearish confirmation → **ENTER SHORT**

#### Exit Conditions

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | Gap edge + (Gap Size × 1.0) | 30% | Momentum continuation |
| **TP2** | Next resistance/support | 40% | Structural target |
| **TP3** | Gap edge + (Gap Size × 2.0) | 30% | Extended move |
| **Stop Loss** | Opposite gap edge ± ATR × 0.8 | All if hit | Tight protective exit |

#### Configuration Parameters

```python
enable_fair_value_gap: bool = True
fvg_min_gap_size: float = 0.005         # Min 0.5% gap
fvg_max_gap_size: float = 0.05          # Max 5% gap
fvg_confirmation_required: bool = True  # Wait for pin/engulfing
fvg_fill_target: float = 0.5            # Partial fill acceptable
fvg_timeframe_min: str = "1H"          # Minimum timeframe
```

#### Example Trade

```
Bullish FVG Setup:
Candle 1 (green): $95,000 – $96,000
Candle 2 (green): $96,000 – $97,500
Candle 3 (green): $97,500 – $98,500
Gap Created: $96,000 – $97,500 (untouched range)
Price Move: Rallies to $99,500
Retracement: Price dips into gap ($96,500)
Pin Bar Confirmation: Lower wick into gap, close above gap edge
Entry (LONG): $96,800 (pin bar close)
TP1: $97,800 | TP2: $98,500 | TP3: $99,200
Stop: $96,200 (below gap) | Risk:Reward = 1:2.5
```

---

## File: `layer_TBD_BOS.py`

### Pattern 10 – Break of Structure (Trend Continuation Signal)

#### Entry Conditions (TREND CONFIRMATION)

1. **Structure Definition**
   - **Bullish Structure** (Uptrend):
     - Series of higher highs (HH) and higher lows (HL)
     - Previous swing high = resistance to break
   - **Bearish Structure** (Downtrend):
     - Series of lower lows (LL) and lower highs (LH)
     - Previous swing low = support to break

2. **Break of Structure Identification**
   - **Bullish BOS** (Continuation):
     - Price breaks above previous swing high
     - Confirms uptrend continues
     - New higher high established
   - **Bearish BOS** (Continuation):
     - Price breaks below previous swing low
     - Confirms downtrend continues
     - New lower low established

3. **Confirmation Requirements**
   - Break on increasing volume (institutional confirmation)
   - Close beyond previous swing level (not just a wick)
   - Follow-through candle(s) continuing in direction
   - No immediate reversal back inside structure

4. **Action**
   - Bullish BOS (break above swing high) → **ENTER LONG** (continuation)
   - Bearish BOS (break below swing low) → **ENTER SHORT** (continuation)
   - NOT used for reversals; used for trend confirmation

#### Exit Conditions

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | BOS point ± (swing range × 1.0) | 30% | Measured move |
| **TP2** | BOS point ± (swing range × 2.0) | 40% | Extended move |
| **TP3** | Trail by ATR × 1.0 | 30% | Trend following |
| **Stop Loss** | Previous swing level ± ATR × 0.5 | All if hit | Tight confirmation stop |

#### Configuration Parameters

```python
enable_break_of_structure: bool = True
bos_confirmation_volume: float = 1.3    # Volume multiplier
bos_follow_through_candles: int = 2     # Min candles after break
bos_swing_lookback: int = 20            # Bars to find swing
bos_use_trailing_stop: bool = True      # Trail on continuation
```

#### Example Trade

```
Bullish BOS Setup:
Previous Swing High: $98,000
Previous Swing Low: $95,000 (range = $3,000)
Current Uptrend: Series of HH & HL
BOS Event: Price breaks above $98,000 to $98,500
Volume: 1.5x average (confirmed)
Follow-through: Next 2 candles close above $98,200
Entry (LONG): $98,500 (on BOS close)
TP1: $99,500 | TP2: $100,500 | TP3: Trail
Stop: $97,700 (below previous swing low) | Risk:Reward = 1:1.5
Duration: Hours to days (continuation trade)
```

#### Why BOS Works

- Break of structure = smart money conviction
- Higher timeframe BOS = very high probability
- Combined with ChoCH = complete market structure shift
- Confirms institutional commitment to trend

---

## File: `layer_TBD_CHOCH.py`

### Pattern 11 – Change of Character (Trend Reversal Signal)

#### Entry Conditions (TREND REVERSAL)

1. **Change of Character (ChoCH) Formation**
   - **Bullish ChoCH** (reversal from downtrend):
     - Market in downtrend (lower lows, lower highs)
     - Price breaks above most recent lower high
     - Signals shift from bearish to bullish
   - **Bearish ChoCH** (reversal from uptrend):
     - Market in uptrend (higher highs, higher lows)
     - Price breaks below most recent higher low
     - Signals shift from bullish to bearish

2. **Structure of ChoCH**
   - **Phase 1**: Establish trend (HH/HL for uptrend, LL/LH for downtrend)
   - **Phase 2**: Final swing in trend direction
   - **Phase 3**: Break opposite to trend = ChoCH
   - **Phase 4**: New structure formation in new direction

3. **Confirmation Signals**
   - Volume surge on break (institutional participation)
   - Clean close beyond broken level (no wick pullback)
   - Follow-through candles in new direction
   - Retest of broken level often occurs (confirmation)

4. **Action**
   - Bullish ChoCH (break above lower high in downtrend) → **ENTER LONG** (reversal)
   - Bearish ChoCH (break below higher low in uptrend) → **ENTER SHORT** (reversal)

#### Exit Conditions

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | ChoCH point ± (prior range × 1.0) | 30% | Initial reversal target |
| **TP2** | ChoCH point ± (prior range × 2.0) | 40% | Extended reversal |
| **TP3** | Trail by ATR × 1.0 | 30% | Trend following |
| **Stop Loss** | Beyond prior swing ± ATR × 1.5 | All if hit | Protective exit |

#### Configuration Parameters

```python
enable_change_of_character: bool = True
choch_confirmation_volume: float = 1.4   # Volume multiplier
choch_follow_through_candles: int = 2    # Min candles after break
choch_swing_lookback: int = 25           # Bars to find swing
choch_retest_expected: bool = True       # Plan for retest
choch_entry_aggressive: float = 0.3      # 30% in on first break
choch_entry_conservative: float = 0.7    # 70% in on retest
```

#### Example Trade

```
Bearish ChoCH Setup (Uptrend Reversal):
Uptrend Structure: Series of HH ($102k, $104k) and HL ($99k, $101k)
Most Recent Higher Low: $101,000
ChoCH Event: Price breaks below $101,000 to $100,500
Volume: 1.5x average (confirmed)
Follow-through: Next 2 candles close below $100,800
Entry (SHORT): $100,500 (aggressive on break)
Alternative Entry: $100,700 (on retest of broken level)
TP1: $99,500 | TP2: $98,500 | TP3: Trail
Stop: $102,000 (above prior swing high) | Risk:Reward = 1:2
Duration: Hours to days (reversal trade)
```

#### ChoCH vs BOS Distinction

- **BOS**: Confirms CONTINUATION of existing trend (higher high → more up)
- **ChoCH**: Signals REVERSAL of existing trend (breaks opposite direction)
- **Together**: BOS + ChoCH = Complete market structure shift confirmation

---

## File: `layer_TBD_LS.py`

### Pattern 12 – Liquidity Sweep / Stop Hunt (Institutional Manipulation)

#### Entry Conditions (SCALP REVERSAL)

1. **Liquidity Pool Identification**
   - **At Support** (Bullish trap):
     - Identify where retail stop losses cluster (below support)
     - Multiple traders place stops below obvious support
   - **At Resistance** (Bearish trap):
     - Identify where retail stop losses cluster (above resistance)
     - Multiple traders place stops above obvious resistance

2. **Sweep Setup**
   - Price approaches support/resistance level
   - Consolidation volume DECLINES (coiling)
   - Weak rejection candles (indecision)
   - Price setup for sweep downside (if at support) or upside (if at resistance)

3. **The Sweep Execution**
   - **Bearish Sweep** (at support, go LONG):
     - Price breaks below support with spike volume
     - Triggers stop losses below support
     - Retail sellers market-sell into institutional buyers
   - **Bullish Sweep** (at resistance, go SHORT):
     - Price breaks above resistance with spike volume
     - Triggers stop losses above resistance
     - Retail buyers market-buy into institutional sellers

4. **Sweep Confirmation**
   - Extreme wick extended beyond level (stop-hunt evidence)
   - Immediate reversal candle (rejection of sweep direction)
   - High volume on sweep candle, higher volume on reversal
   - Price rapidly returns into original range

5. **Action**
   - Bearish sweep at support with bullish reversal → **ENTER LONG**
   - Bullish sweep at resistance with bearish reversal → **ENTER SHORT**

#### Exit Conditions

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | Entry ± (sweep wick size × 0.5) | 40% | Quick scalp |
| **TP2** | Entry ± (sweep wick size × 1.0) | 40% | Main scalp |
| **TP3** | Entry ± (sweep wick size × 1.5) | 20% | Extended scalp |
| **Stop Loss** | Beyond wick ± ATR × 0.3 | All if hit | **VERY TIGHT** |

#### Configuration Parameters

```python
enable_liquidity_sweep: bool = True
sweep_wick_threshold: float = 0.01       # Min 1% wick
sweep_volume_spike: float = 2.0          # 2x volume on sweep
sweep_reversal_speed: int = 1            # 1 candle max for reversal
sweep_min_distance_level: float = 0.02   # Level must be 2%+ away
sweep_trading_window_minutes: int = 15   # Only trade first 15 min
```

#### Example Trade

```
Bearish Sweep at Support (Go LONG):
Support Level: $95,000
Multiple Bounces: $95,200, $95,100, $95,050 (confirmations)
Consolidation: 6 candles with declining volume
Sweep Down: Price breaks to $94,500 (wick 500 pips below support)
Volume Spike: 2.5x average on sweep candle
Reversal Immediately: Next candle closes at $95,200 with higher volume
Entry (LONG): $95,100 (on reversal candle)
TP1: $95,350 | TP2: $95,600 | TP3: $95,850
Stop: $94,300 (below wick) | Risk:Reward = 1:1.5
Duration: 5-15 minutes (scalp only)
```

#### Why Sweeps Work

- Retail traders place obvious stops (textbook locations)
- Institutions know exactly where stops are clustered
- Institutions have size to trigger stops
- Triggered stops provide liquidity for institutional fills
- After fill, price reverses to break retail traders' positions

---

## File: `layer_TBD_SD.py`

### Pattern 13 – Supply and Demand Zones (Institutional Imbalance Areas)

#### Entry Conditions (REVERSAL/BREAKOUT)

1. **Supply Zone Identification** (Bearish Pressure)
   - Large bullish candle with rapid upward move
   - Significant volume on the upward move
   - Zone = body of candle that created the move
   - Represents excess supply (institutional sellers waiting)
   - Acts as future resistance

2. **Demand Zone Identification** (Bullish Pressure)
   - Large bearish candle with rapid downward move
   - Significant volume on the downward move
   - Zone = body of candle that created the move
   - Represents excess demand (institutional buyers waiting)
   - Acts as future support

3. **Zone Characteristics**
   - Multiple tests of zone increase validity
   - Zones on higher timeframes (4H, Daily) most reliable
   - Fresh (recent) zones more effective than old ones
   - Zones with 3+ touches show high institutional activity

4. **Entry Strategy – Reversal at Zone**
   - **At Demand Zone (LONG)**:
     - Price retraces into demand zone
     - Wait for bullish reversal pattern (pin bar, engulfing, BOS)
     - Enter on confirmation
   - **At Supply Zone (SHORT)**:
     - Price rallies into supply zone
     - Wait for bearish reversal pattern (pin bar, engulfing, BOS)
     - Enter on confirmation

5. **Entry Strategy – Breakout Through Zone**
   - **Above Supply Zone (LONG)**:
     - Price breaks cleanly above supply zone with volume
     - Supply exhausted, continuation upward
   - **Below Demand Zone (SHORT)**:
     - Price breaks cleanly below demand zone with volume
     - Demand exhausted, continuation downward

6. **Action**
   - Demand zone retest with bullish confirmation → **ENTER LONG**
   - Supply zone retest with bearish confirmation → **ENTER SHORT**
   - Breakout above supply with volume → **ENTER LONG**
   - Breakdown below demand with volume → **ENTER SHORT**

#### Exit Conditions

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | Zone edge ± (zone height × 1.0) | 30% | Initial target |
| **TP2** | Opposite zone level | 40% | Next institutional level |
| **TP3** | Zone edge ± (zone height × 2.0) | 30% | Extended target |
| **Stop Loss** | Opposite zone ± ATR × 1.0 | All if hit | Protective exit |

#### Configuration Parameters

```python
enable_supply_demand: bool = True
sd_zone_lookback_bars: int = 40         # Bars to scan for zones
sd_min_volume_confirmation: float = 1.3 # Volume on zone-creating move
sd_zone_width: float = 0.02             # Zone is 2% width
sd_multiple_touches: int = 2            # Min touches for validity
sd_confluence_weight: float = 0.20      # Weight in composite score
```

#### Example Trade

```
Demand Zone Setup (LONG):
Large Bearish Candle: $98,000 – $92,000 (rapid 6% drop)
Volume: 2x average (institutional buying signal)
Demand Zone: $92,000 – $93,000 (body of candle)
Price Action: Rallies to $97,000
Retracement: Price dips back into demand zone ($92,500)
Pin Bar Confirmation: Lower wick into zone, close above zone
Entry (LONG): $92,800 (pin bar close)
TP1: $94,000 | TP2: $96,500 | TP3: $98,500
Stop: $91,500 (below demand zone) | Risk:Reward = 1:3
```

---

## File: `layer_TBD_WA.py`

### Pattern 14 – Wyckoff Accumulation (Five-Phase Institutional Positioning)

#### Entry Conditions (MULTI-PHASE SETUP)

1. **Phase A – Stopping the Downtrend**
   - Market in clear downtrend
   - Events:
     - **PS** (Preliminary Support): Buying emerges, bounces form
     - **SC** (Selling Climax): Final capitulation selling, major low
     - **AR** (Automatic Rally): Swift rebound after SC (20-50% of drop)
     - **ST** (Secondary Test): Mild pullback to test SC level

2. **Phase B – Accumulation**
   - Price consolidates in range (no new lows, contained rallies)
   - Volume pattern:
     - Declining volume during range (smart money coiling)
     - Occasional volume spikes on dips (accumulation)
   - Characteristics:
     - Multiple failed breakouts downside (no new lows)
     - Price oscillating in tight range
     - Duration: Several weeks typical

3. **Phase C – Sign of Strength (SOS)**
   - Price breaks above consolidation range
   - High volume on breakout (conviction)
   - Closes well above range
   - Marks end of accumulation, start of markup

4. **Phase D – Markup / Uptrend**
   - Sustained uptrend with consistent higher highs/lows
   - Volume remains solid
   - Minor pullbacks quickly bought
   - This is the profitable trend for longs

5. **Phase E – Distribution**
   - Institutional sellers begin exiting
   - Volume stays high but sentiment weakens
   - Price rallies slow
   - Preparation for reversal (out of scope for long entries)

#### Entry Condition – At Phase C Breakout

1. **Prerequisites**
   - Clear Phase A–B structure on chart
   - Range (Phase B) lasted 4+ weeks minimum
   - Volume profile shows declining volume in range
   - Price formed new low during ST (tested SC zone)

2. **Breakout Signal**
   - Price closes above resistance of range
   - Volume surge (>1.5x average minimum)
   - No immediate false breakdown back into range
   - Next 1–2 candles confirm above-range trading

3. **Action**
   - Phase C breakout with volume confirmation → **ENTER LONG**
   - Treat as continuation of strong trend

#### Exit Conditions

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | Range high ± (range height × 1.0) | 30% | Initial trend target |
| **TP2** | Range high ± (range height × 2.0) | 40% | Extended markup |
| **TP3** | Trail by ATR × 1.0 | 30% | Trend following |
| **Stop Loss** | Range low ± ATR × 1.0 | All if hit | Accumulation zone support |

#### Configuration Parameters

```python
enable_wyckoff: bool = True
wyckoff_phase_b_min_weeks: int = 4      # Min accumulation duration
wyckoff_volume_decline_pct: float = 0.3 # Vol should drop 30%+ in range
wyckoff_sos_volume_mult: float = 1.5    # SOS breakout volume
wyckoff_use_markup_targets: bool = True # Use measured move targets
```

#### Example Trade

```
Wyckoff Accumulation (LONG):
Phase A-B History:
  - Downtrend: $120k to $80k (capitulation)
  - SC (Selling Climax): $80k (panic selling)
  - AR (Auto Rally): $95k (20% bounce)
  - ST (Secondary Test): $85k (confirms buying)
  
Phase B (Accumulation):
  - 8-week consolidation: $83k – $96k range
  - Volume: Declining throughout range
  - Pattern: Multiple bounces, failed breakdowns
  
Phase C (Sign of Strength):
  - Breakout: Price closes $98k (above $96k range high)
  - Volume: 2x average on breakout
  - Follow-through: Next 2 candles close $97.5k, $99k
  
Entry (LONG): $98,000 (on SOS breakout)
Range Height: $13,000 ($96k – $83k)
TP1: $109,000 | TP2: $120,000 | TP3: Trail
Stop: $82,000 (below range low) | Risk:Reward = 1:2.5
Duration: Weeks to months (strong trend)
```

#### Why Wyckoff Works

- Reflects actual institutional positioning over time
- Phase transitions are predictable
- Distribution of smart money clearly defined
- Multi-week structure = high-probability setup
- Works on all timeframes

---

## File: `layer_TBD_PB.py`

### Pattern 15 – Pin Bar Reversal (High-Wick Rejection)

#### Entry Conditions (REVERSAL AT LEVELS)

1. **Pin Bar Structure**
   - **Bullish Pin Bar** (reversal from downside):
     - Candle with small body (narrow range between open/close)
     - Very long lower wick (penetrates below level)
     - Small upper wick (if any)
     - Appearance: "T" shape or inverted hammer
   - **Bearish Pin Bar** (reversal from upside):
     - Candle with small body
     - Very long upper wick (penetrates above level)
     - Small lower wick (if any)
     - Appearance: upside-down "T" shape

2. **Pin Bar Metrics**
   - Wick size: ≥ 50% of candle's high-low range
   - Body size: < 30% of candle's high-low range
   - Close location:
     - Bullish: Close near candle high (rejection of downside)
     - Bearish: Close near candle low (rejection of upside)

3. **Location Requirements**
   - Forms at key support/resistance level
   - Forms at end of trending move (exhaustion)
   - Forms at demand/supply zone
   - Forms at order block
   - Multiple confluence = higher probability

4. **Action**
   - Bullish pin bar at support with buyers → **ENTER LONG**
   - Bearish pin bar at resistance with sellers → **ENTER SHORT**

#### Exit Conditions

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | Entry ± (wick size × 1.0) | 30% | Measured move from wick |
| **TP2** | Entry ± (wick size × 2.0) | 40% | Extended move |
| **TP3** | Entry ± (wick size × 3.0) | 30% | Max reversal target |
| **Stop Loss** | Beyond wick ± ATR × 0.5 | All if hit | Protective exit |

#### Configuration Parameters

```python
enable_pin_bar: bool = True
pb_wick_threshold: float = 0.50         # Wick ≥ 50% of range
pb_body_max_pct: float = 0.30           # Body ≤ 30% of range
pb_close_proximity: float = 0.10        # Close near wick end
pb_confluence_required: bool = True     # Use with level zones
pb_entry_aggressive: float = 0.5        # Enter on bar close
pb_entry_conservative: float = 1.0      # Enter on next bar
```

#### Example Trade

```
Bullish Pin Bar at Support:
Support Level: $94,500 (previous bounce, demand zone)
Pin Bar Setup:
  - High: $95,000
  - Low: $93,500 (wick 1,000 pips below support)
  - Open: $94,800
  - Close: $94,950 (near high = rejection of downside)
  - Range: $1,500 | Wick: $1,000 (67% of range ✓)
  - Body: $150 (10% of range ✓)

Volume: 1.2x average on pin bar candle
Entry (LONG): $94,950 (on close, conservative on next open)
TP1: $95,950 | TP2: $96,950 | TP3: $97,950
Stop: $93,200 (below wick) | Risk:Reward = 1:3.5
Duration: 30 minutes – 4 hours (scalp to swing)
```

#### Pin Bar Psychology

- Wick = institutions testing for trapped liquidity
- Small body = rejection of tested direction
- Close near opposite wick = conviction against test
- High volume on pin bar = institutional participation

---

## File: `layer_TBD_ENG.py`

### Pattern 16 – Engulfing Pattern (Two-Candle Reversal)

#### Entry Conditions (TWO-CANDLE REVERSAL)

1. **Bullish Engulfing**
   - **Candle 1** (Bearish):
     - Downward move from open to close
     - Establishes bearish sentiment
   - **Candle 2** (Bullish):
     - Opens BELOW candle 1's low
     - Closes ABOVE candle 1's high
     - Completely engulfs candle 1's body
     - Green candle with large range
   - **Signal**: Buyers overwhelm sellers, reversal from down

2. **Bearish Engulfing**
   - **Candle 1** (Bullish):
     - Upward move from open to close
     - Establishes bullish sentiment
   - **Candle 2** (Bearish):
     - Opens ABOVE candle 1's high
     - Closes BELOW candle 1's low
     - Completely engulfs candle 1's body
     - Red candle with large range
   - **Signal**: Sellers overwhelm buyers, reversal from up

3. **Confirmation Metrics**
   - Candle 2 body completely > Candle 1 body (no partial)
   - Candle 2 has strong volume (>1.2x average)
   - Candle 2 closes near extremes (no wick rejection)
   - Location: At support (bullish) or resistance (bearish)

4. **Action**
   - Bullish engulfing at support → **ENTER LONG**
   - Bearish engulfing at resistance → **ENTER SHORT**

#### Exit Conditions

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | Entry ± (engulfing range × 1.0) | 30% | Measured move |
| **TP2** | Entry ± (engulfing range × 2.0) | 40% | Extended move |
| **TP3** | Entry ± (engulfing range × 3.0) | 30% | Maximum reversal |
| **Stop Loss** | Beyond candle 1 extreme ± ATR × 0.5 | All if hit | Tight stop |

#### Configuration Parameters

```python
enable_engulfing: bool = True
eng_volume_confirmation: float = 1.2    # Min volume on candle 2
eng_location_required: bool = True      # Must be at support/resistance
eng_confluence_weight: float = 0.15     # Weight in composite
eng_entry_aggressive: float = 0.5       # On candle 2 close
eng_entry_conservative: float = 1.0     # On next candle
```

#### Example Trade

```
Bullish Engulfing at Support:
Support Zone: $94,000 – $94,500
Candle 1 (Bearish):
  - Open: $94,800
  - Close: $94,200
  - Range: $600

Candle 2 (Bullish Engulfing):
  - Open: $93,900 (below candle 1 low ✓)
  - Close: $95,100 (above candle 1 high ✓)
  - Range: $1,200 (engulfs candle 1 ✓)
  - Volume: 1.5x average ✓
  - Close near high (strong ✓)

Entry (LONG): $95,100 (on candle 2 close)
TP1: $96,300 | TP2: $97,500 | TP3: $98,700
Stop: $93,500 (below candle 1 low) | Risk:Reward = 1:2.5
Duration: 1-6 hours (swing trade)
```

#### Engulfing Psychology

- Candle 1 = Weak directional momentum
- Candle 2 = Strong counter-move with volume
- Complete engulfment = No hesitation in reversal
- Location at support/resistance = High confluence
- Often followed by strong continuation move

---

## File: `layer_TBD_AMD.py`

### Pattern 17 – Accumulation, Manipulation & Distribution (Three-Phase Cycle)

#### Entry Conditions (PHASE-BASED ENTRIES)

1. **Phase 1 – Accumulation** (Smart Money Building)
   - **Characteristics**:
     - Price consolidation in narrow range (2%–3% width)
     - Volume declining as price range tightens
     - No directional bias (balanced trading)
     - Duration: 2–8 weeks typical
   - **Institutional Activity**:
     - Large orders being placed gradually
     - Bid-ask spreads widen (hidden orders)
     - Volume-weighted average price (VWAP) stable
   - **Entry**: NOT YET – wait for next phase

2. **Phase 2 – Manipulation** (False Moves to Trap Retail)
   - **Characteristics**:
     - Initial breakout above/below consolidation
     - Volume spike on initial move (looks real)
     - Quick reversal back into consolidation range
     - False breakouts repeated 2–3 times
   - **Retail Behavior**:
     - Enters on breakout signal
     - Gets stopped out by quick reversal
     - Generates liquidity for institutions
   - **Entry**: BUY DIP INTO RANGE (fake break down)
           SHORT RALLY INTO RANGE (fake break up)

3. **Phase 3 – Distribution** (Smart Money Exiting)
   - **Characteristics**:
     - Final breakout with sustained volume
     - No return to consolidation range
     - Price moving decisively in direction
     - Higher highs/lows establishing (if bullish)
   - **Institutional Activity**:
     - Large orders feeding market
     - Providing liquidity on rallies
     - Taking profits gradually
   - **Entry**: ENTER WITH BREAKOUT (this time it's real)
           ENTER ON MINOR PULLBACK IN TREND

#### Detection Rules

| Phase | Volume | Price Action | Entry Signal |
|-------|--------|---|---|
| **Accumulation** | Declining | Range-bound | Wait – no trade |
| **Manipulation** | Spike then decline | False breaks | Counter-trend scalps |
| **Distribution** | Sustained | Trending | Breakout continuation |

#### Exit Conditions

**Phase 1 Entries**: Not traded

**Phase 2 Entries** (Counter-Trend Scalps):

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | Entry ± (range × 0.25) | 50% | Quick scalp |
| **TP2** | Entry ± (range × 0.50) | 50% | Back to range |
| **Stop Loss** | Beyond false break extreme ± ATR × 0.3 | All | Tight scalp stop |

**Phase 3 Entries** (Trend Continuation):

| Level | Exit Point | Position Size | Logic |
|-------|-----------|---|-------|
| **TP1** | Breakout ± (range × 1.0) | 30% | Measured move |
| **TP2** | Breakout ± (range × 2.0) | 40% | Extended move |
| **TP3** | Trail by ATR × 1.0 | 30% | Trend following |
| **Stop Loss** | Inside range level ± ATR × 0.5 | All if hit | Accumulation zone support |

#### Configuration Parameters

```python
enable_amd_pattern: bool = True
amd_accumulation_min_weeks: int = 2     # Min accumulation duration
amd_range_width_pct: float = 0.03       # Range width max 3%
amd_volume_decline_pct: float = 0.40    # Vol should drop 40% in range
amd_manipulation_count: int = 2         # Min false breaks
amd_distribution_volume_mult: float = 1.5  # Final breakout volume
amd_entry_phase_2: bool = True          # Trade manipulation phase
amd_entry_phase_3: bool = True          # Trade distribution phase
```

#### Example Trade

```
AMD Cycle (Bullish):
Price: $95,000

Phase 1 – Accumulation (6 weeks):
Range: $93,000 – $97,000 (4.3% width)
Volume: 500 BTC average, declining to 250 BTC by end
Action: Consolidation continues, institutions accumulating
Entry: NONE – wait for phase 2

Phase 2 – Manipulation (Days 1-7):
False Breakout Up:
  - Price breaks above $97,000 to $98,000
  - Volume: 1,200 BTC (2.4x average)
  - Then reverses back into $94,000
  
Retail Entry: Longs stop out
Retail Action: Frustrated sellers dump, creating liquidity
  
Institutions Counter-Trade (GO SHORT fake break):
Entry (SHORT): $97,500 (on failed breakout)
TP1: $96,000 | TP2: $94,500
Stop: $98,500 | Quick scalp

Phase 3 – Distribution (Final breakout):
Final Breakout Up:
  - Price breaks above $97,000 to $98,500, $99,500, $100,000+
  - Volume: 1,500 BTC sustained (3x average)
  - No return to range, clean uptrend
  
Entry (LONG): $97,500 (on sustained breakout)
TP1: $99,500 | TP2: $101,500 | TP3: Trail
Stop: $96,000 (inside range)
Risk:Reward = 1:2+
```

---

## Quick Pattern Reference Matrix

| Pattern # | File Name | Type | Entry | Exit | Best TF | Duration | Complexity |
|-----------|-----------|------|-------|------|---------|----------|------------|
| **8** | layer_TBD_OB.py | Institutional | Retest | Measured | 1H–4H | 4–12h | Medium |
| **9** | layer_TBD_FVG.py | Imbalance | Return & fill | Gap fill | 1H–Daily | 1–8h | High |
| **10** | layer_TBD_BOS.py | Continuation | Break up/down | Measured | 4H–Daily | 6h–3d | Medium |
| **11** | layer_TBD_CHOCH.py | Reversal | Opposite break | Measured | 4H–Daily | 4h–2d | Medium |
| **12** | layer_TBD_LS.py | Manipulation | Reversal after sweep | Quick scalp | 15m–1H | 5–30m | High |
| **13** | layer_TBD_SD.py | Reversal | Zone retest | Opposite zone | 1H–4H | 2–12h | Medium |
| **14** | layer_TBD_WA.py | Multi-phase | Phase C breakout | Trend trail | Daily–Weekly | Weeks–months | High |
| **15** | layer_TBD_PB.py | Reversal | Wick rejection | Measured | 15m–1H | 30m–4h | Low |
| **16** | layer_TBD_ENG.py | Reversal | Engulfing close | Measured | 15m–4H | 30m–4h | Low |
| **17** | layer_TBD_AMD.py | Cyclical | Phase 2 & 3 | Phase-based | 1H–Daily | Hours–weeks | Very High |

---

## Integration with Master Config

To enable additional patterns in `layer_TBD_Master_Config.py`:

```python
# Additional pattern switches (Patterns 8-17)
enable_order_block: bool = True
enable_fair_value_gap: bool = True
enable_break_of_structure: bool = True
enable_change_of_character: bool = True
enable_liquidity_sweep: bool = True
enable_supply_demand: bool = True
enable_wyckoff_accumulation: bool = True
enable_pin_bar: bool = True
enable_engulfing: bool = True
enable_amd_cycle: bool = True

# Weights for composite scoring
weight_order_block: float = 0.12
weight_fvg: float = 0.12
weight_bos: float = 0.10
weight_choch: float = 0.10
weight_liquidity_sweep: float = 0.08
weight_supply_demand: float = 0.12
weight_wyckoff: float = 0.08
weight_pin_bar: float = 0.08
weight_engulfing: float = 0.08
weight_amd: float = 0.12
```

---

## Recommended Subset for Implementation

For traders starting with expanded patterns, prioritize in this order:

1. **Order Blocks (OB)** – Highest probability, clear zones
2. **Fair Value Gaps (FVG)** – Excellent momentum reversal signals
3. **Supply & Demand Zones (SD)** – Reliable support/resistance
4. **Break of Structure (BOS)** – Trend confirmation (use with existing patterns)
5. **Pin Bars (PB)** – Easy to spot, low-risk reversal plays
6. **Liquidity Sweeps (LS)** – Advanced scalp pattern (requires discipline)
7. **Change of Character (ChoCH)** – Reversal signal (combine with BOS)
8. **Engulfing (ENG)** – Classic pattern, good confirmation
9. **Wyckoff (WA)** – Multi-week setups (for swing traders)
10. **AMD Cycle (AMD)** – Advanced, full-cycle analysis (expert level)

---

## Conclusion

These 10 additional patterns (8–17) complement the original 7 TBD patterns and create a comprehensive institutional trading framework. All patterns are:

- **Evidence-based**: Documented in professional trading literature
- **Market-tested**: Successful across crypto, forex, stocks, futures
- **Institutional-aligned**: Reflect how smart money actually trades
- **Configurable**: Can be enabled/disabled per trader preference
- **Combinable**: Work together for higher-probability confluence setups

Select patterns that align with your trading style, timeframe, and risk tolerance. Start with 3–4 and master them before adding more.

---

*"The more you understand how institutions move price, the more profitable your trading becomes."*

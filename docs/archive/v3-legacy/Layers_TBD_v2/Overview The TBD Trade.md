Overview
The TBD (Trade By Design) system operates on 7 distinct trade patterns, each with specific entry triggers and exit protocols. All rules are built on the market maker model and require multi-confirmation to trigger.

-------------


## File: `layer_TBD_M.py`  
### Pattern 1 – M-Pattern (Double Top / Bearish Reversal)

#### Entry Conditions (SHORT)

1. **Pattern Structure**
   - Two peaks at similar price levels:
     - `abs(peak2 - peak1) / peak1 <= 0.10–0.20`
   - Valley between peaks defines the **neckline**.
   - Pattern length:
     - `10 <= candles_in_pattern <= 50`
   - Second peak volume ≤ first peak volume (distribution).

2. **Breakdown Confirmation**
   - Neckline break:
     - `price <= neckline * (1 - 0.003)`  (≥ 0.3% below neckline)
   - Volume filter:
     - `volume_breakout >= 1.3 * avg_volume`
   - Global confirmations:
     - `require_volume_confirmation == False` OR volume condition above.
     - `minimum_confirmations` and other global filters satisfied.

3. **Action**
   - On confirmed neckline break: **ENTER SHORT** at market or close of breakout candle.

#### Exit Conditions

Let:
- `pattern_height = higher_peak - neckline`

1. **Take Profits**
   - `TP1 = neckline - pattern_height * 0.5`  (exit 30% of position)
   - `TP2 = neckline - pattern_height * 1.0`  (exit 40% of position)
   - `TP3 = neckline - pattern_height * 1.5`  (exit 30% of position)

2. **Stop Loss**
   - `SL = highest_peak + ATR * 1.5`

3. **Time/Fail-Safe Exit**
   - If max hold time exceeds configured hours for this timeframe or price structurally invalidates pattern (new higher high above SL zone), close remaining.

---

## File: `layer_TBD_W.py`  
### Pattern 2 – W-Pattern (Double Bottom / Bullish Reversal)

#### Entry Conditions (LONG)

1. **Pattern Structure**
   - Two troughs at similar price levels:
     - `abs(trough2 - trough1) / trough1 <= 0.10–0.20`
   - Peak between troughs defines the **neckline**.
   - Pattern length:
     - `10 <= candles_in_pattern <= 50`
   - Second trough volume ≤ first trough volume (absorption).

2. **Breakout Confirmation**
   - Neckline break:
     - `price >= neckline * (1 + 0.003)`  (≥ 0.3% above neckline)
   - Volume filter:
     - `volume_breakout >= 1.3 * avg_volume`
   - Global confirmations:
     - Respect `minimum_confirmations`, MTF alignment (if enabled), etc.

3. **Action**
   - On confirmed neckline break: **ENTER LONG** at market or close of breakout candle.

#### Exit Conditions

Let:
- `pattern_height = neckline - lower_trough`

1. **Take Profits**
   - `TP1 = neckline + pattern_height * 0.5`  (exit 30%)
   - `TP2 = neckline + pattern_height * 1.0`  (exit 40%)
   - `TP3 = neckline + pattern_height * 1.5`  (exit 30%)

2. **Stop Loss**
   - `SL = lowest_trough - ATR * 1.5`

3. **Time/Fail-Safe Exit**
   - Exit remaining if pattern is invalidated structurally (new lower low beyond SL zone) or max hold time exceeded.

---

## File: `layer_TBD_WT.py`  
### Pattern 3 – Weekend Trap (Monday Reversion)

#### Entry Conditions (MEAN REVERSION)

1. **Weekend Move Detection**
   - Compute `friday_close`.
   - Compute weekend extreme (`weekend_high`, `weekend_low`).
   - Weekend move (absolute):
     - `weekend_move_pct = abs(weekend_extreme - friday_close) / friday_close`
   - Condition:
     - `weekend_move_pct >= weekend_trap_threshold` (default `0.02`, i.e. 2%).

2. **Timing Filter**
   - Current bar is **Monday**.
   - Bar time within first `weekend_trap_reversal_hours` of Monday (default `4` hours).

3. **Direction Logic**
   - **Bullish Trap → LONG**:
     - If `weekend_low < friday_close` and `weekend_move_pct >= threshold` → price gapped/moved down.
     - On Monday: look to **LONG** (fade downside).
   - **Bearish Trap → SHORT**:
     - If `weekend_high > friday_close` and `weekend_move_pct >= threshold` → price gapped/moved up.
     - On Monday: look to **SHORT** (fade upside).

4. **Action**
   - Within the first `weekend_trap_reversal_hours` on Monday:
     - If weekend move down: **ENTER LONG**.
     - If weekend move up: **ENTER SHORT**.

#### Exit Conditions

1. **Take Profits**
   - Target reference: `friday_close`
   - For **LONG** (fading down move):
     - `TP1 = entry_price + (friday_close - entry_price) * 0.5` (50% retrace, exit 40%)
     - `TP2 = friday_close` (exit 40%)
     - `TP3 = friday_close * 1.01` (1% overshoot, exit 20%)
   - For **SHORT** (fading up move) – symmetric around `friday_close`.

2. **Stop Loss**
   - For LONG:
     - `SL = weekend_low - ATR`
   - For SHORT:
     - `SL = weekend_high + ATR`

3. **Time Stop**
   - Close position if trade still open after `weekend_trap_reversal_hours` expiry or end of Monday session.

---

## File: `layer_TBD_BM.py`  
### Pattern 4 – Board Meeting (Consolidation Breakout)

#### Entry Conditions (BREAKOUT CONTINUATION)

1. **Consolidation Detection**
   - Define consolidation segment:
     - `board_min_candles <= candles_in_range <= board_max_candles`
       - Defaults: `6 <= candles <= 24`.
   - Range constraint:
     - `range_pct = (high_range - low_range) / mid_price`
     - `range_pct <= board_range_threshold` (default `0.02`, i.e. 2%).
   - Volume profile:
     - Average volume of last third of consolidation ≤ average volume of first third (declining/flat volume).

2. **Breakout Candle**
   - Breakout above high_range (bullish) or below low_range (bearish).
   - Breakout magnitude:
     - `break_distance >= 0.5 * (high_range - low_range)` (≥ 50% of range height).
   - Volume filter:
     - `volume_breakout >= board_breakout_volume * avg_volume` (default: `1.5x`).
   - Avoid first hour of session (if configured, i.e. `avoid_first_30min_london`, etc).

3. **Action**
   - If price breaks **above** consolidation high with conditions satisfied → **ENTER LONG**.
   - If price breaks **below** consolidation low with conditions satisfied → **ENTER SHORT**.

#### Exit Conditions

Let:
- `range_height = high_range - low_range`
- `breakout_level = breakout_price` (entry).

1. **Take Profits**
   - For LONG:
     - `TP1 = breakout_level + range_height * 1.0` (exit 30%)
     - `TP2 = breakout_level + range_height * 2.0` (exit 40%)
     - `TP3 = breakout_level + range_height * 3.0` (exit 30%)
   - For SHORT: mirror below breakout_level.

2. **Stop Loss**
   - LONG:
     - `SL = low_range - ATR`
   - SHORT:
     - `SL = high_range + ATR`

3. **Time Stop**
   - If price fails to hit TP1 within configured max hold hours for this timeframe, consider early exit or tighter stop.

---

## File: `layer_TBD_TH.py`  
### Pattern 5 – Three Hits Rule (Exhaustion Reversal)

#### Entry Conditions (REVERSAL)

1. **Weekly Level Detection**
   - Compute `weekly_high` and `weekly_low` over `weekly_hl_lookback` weeks.
   - Track touches of these levels:
     - A touch occurs when:
       - At high: `abs(candle_high - weekly_high) / weekly_high <= three_hits_touch_tolerance`
       - At low:  `abs(candle_low - weekly_low) / weekly_low <= three_hits_touch_tolerance`
       - Default: `three_hits_touch_tolerance = 0.005` (0.5%).
   - Ensure spacing:
     - At least `three_hits_min_candles_between` candles between successive touches (default `4`).

2. **Rejection Candle at 3rd+ Touch**
   - For **weekly high** (SHORT):
     - Touch count ≥ 3.
     - Current candle high within tolerance to `weekly_high`.
     - Upper rejection wick:
       - `candle_close < candle_high` and upper wick is significant.
   - For **weekly low** (LONG):
     - Touch count ≥ 3.
     - Current candle low within tolerance to `weekly_low`.
     - Lower rejection wick:
       - `candle_close > candle_low` and lower wick is significant.

3. **Action**
   - At weekly high (3rd+ touch with rejection) → **ENTER SHORT**.
   - At weekly low (3rd+ touch with rejection) → **ENTER LONG**.

#### Exit Conditions

Let:
- `weekly_range = weekly_high - weekly_low`.

1. **Take Profits**
   - For SHORT from `entry` near weekly_high:
     - `TP1 = entry - weekly_range * 0.3` (exit 30%)
     - `TP2 = entry - weekly_range * 0.5` (exit 40%)
     - `TP3 = weekly_low` (exit 30%)
   - For LONG from `entry` near weekly_low: mirror upwards.

2. **Stop Loss**
   - SHORT:
     - `SL = weekly_high + ATR * 1.5`
   - LONG:
     - `SL = weekly_low - ATR * 1.5`

3. **Notes**
   - Never open on 1st or 2nd touch.
   - Priority given when combined with other confluence (e.g., pattern + liquidation cluster if enabled).

---

## File: `layer_TBD_TV.py`  
*(Assuming the intended name is `layer_TBD_TV.py`; using your exact label in this section title as requested.)*  
### Pattern 6 – Trapping Volume (False Breakout Reversal)

#### Entry Conditions (SCALP REVERSAL)

1. **Trap Candle Identification**
   - Candle range: `candle_range = high - low`.
   - Wick percentage:
     - Upper wick = `high - max(open, close)`
     - Lower wick = `min(open, close) - low`
   - For bullish trap (SHORT):
     - Upper wick ≥ `trap_wick_threshold * candle_range` (default `0.5` → 50%).
     - `close` near low (strong rejection).
   - For bearish trap (LONG):
     - Lower wick ≥ `trap_wick_threshold * candle_range`.
     - `close` near high.

2. **Volume Confirmation**
   - `volume_candle >= trap_volume_multiplier * avg_volume`
     - Default: `trap_volume_multiplier = 1.5`.

3. **Session Preference**
   - Prefer:
     - London open (first 30 minutes).
     - New York open (first 30 minutes).
   - Optionally avoid overlap if configured (real breakouts more frequent).

4. **Action**
   - Bullish trap (upper wick rejection) → **ENTER SHORT**.
   - Bearish trap (lower wick rejection) → **ENTER LONG**.
   - Entry typically at or just after trap candle close.

#### Exit Conditions

Let:
- `trap_range = wick_size` (size of dominant wick).

1. **Take Profits**
   - For LONG:
     - `TP1 = entry + trap_range * 0.5` (exit 40%)
     - `TP2 = entry + trap_range * 1.0` (exit 40%)
     - `TP3 = entry + trap_range * 1.5` (exit 20%)
   - For SHORT: mirror opposite direction.

2. **Stop Loss (Tight)**
   - LONG:
     - `SL = wick_low - ATR * 0.5`
   - SHORT:
     - `SL = wick_high + ATR * 0.5`

3. **Time Stop (Scalp Only)**
   - Close entire position if:
     - TP1 not reached within a short window (e.g., 3–6 candles on the active timeframe or 5–30 minutes on scalp TFs).

---

## File: `layer_TBD_OF.py`  
### Pattern 7 – One Formation (Decisive Breakout)

#### Entry Conditions (TREND INITIATION)

1. **Pre-Breakout Consolidation**
   - Consolidation window:
     - `one_consolidation_min_candles <= candles_in_consolidation <= 40`
       - Default: `one_consolidation_min_candles = 20`.
   - Consolidation range:
     - `range_pct = (high_consol - low_consol) / mid_price <= one_consolidation_max_range_pct`
       - Default: `one_consolidation_max_range_pct = 0.03` (3%).
   - Volume:
     - Average volume of consolidation is stable or declining versus prior regime.

2. **The One – Breakout Candle**
   - Candle range:
     - `breakout_range >= one_breakout_size_multiplier * avg_candle_range`
       - Default: `one_breakout_size_multiplier = 2.0` (≥ 2× average).
   - Volume:
     - `volume_breakout >= one_breakout_volume_multiplier * avg_volume`
       - Default: `one_breakout_volume_multiplier = 2.0` (≥ 2× average).
   - Location:
     - Candle closes **beyond** consolidation boundary:
       - Bullish: `close > high_consol`
       - Bearish: `close < low_consol`.

3. **Action**
   - Bullish One: close above consolidation high → **ENTER LONG** on close or next open.
   - Bearish One: close below consolidation low → **ENTER SHORT** similarly.

#### Exit Conditions

Let:
- `measured_move = high_consol - low_consol`
- `breakout_level = entry_price`.

1. **Take Profits**
   - For LONG:
     - `TP1 = breakout_level + measured_move * 1.0` (exit 30%)
     - `TP2 = breakout_level + measured_move * 2.0` (exit 40%)
     - `TP3 = breakout_level + measured_move * 3.0` (exit 30%)
   - For SHORT: mirror below breakout_level.

2. **Stop Loss**
   - LONG:
     - `SL = low_consol - ATR * 1.5`
   - SHORT:
     - `SL = high_consol + ATR * 1.5`

3. **Trailing Logic (Trend)**
   - Once TP1 hit:
     - Move SL to breakeven.
   - Once TP2 hit:
     - Begin trailing by `ATR * 1.0` (or config-defined multiplier).
   - Optionally, let TP3 act as hard final target or keep trailing for extended trend as per configured regime.

4. **Time Stop**
   - Because this is a trend pattern, max hold times are higher (e.g., 24–48h+ on intraday TFs); close position if no progress and structure breaks back into consolidation zone.

---

## Quick Pattern–File Mapping

| Pattern # | Description                                   | File Name                   |
|-----------|-----------------------------------------------|-----------------------------|
| Config    | Configuration switches for entry/exit         | `layer_TBD_Master_Config.py`|
| 1         | M-Pattern (Double Top – Bearish Reversal)     | `layer_TBD_M.py`           |
| 2         | W-Pattern (Double Bottom – Bullish Reversal)  | `layer_TBD_W.py`           |
| 3         | Weekend Trap (Monday Reversion)               | `layer_TBD_WT.py`          |
| 4         | Board Meeting (Consolidation Breakout)        | `layer_TBD_BM.py`          |
| 5         | Three Hits Rule (Exhaustion Reversal)         | `layer_TBD_TH.py`          |
| 6         | Trapping Volume (False Breakout Reversal)     | `ayer_TBD_TV.py`           |
| 7         | One Formation (Decisive Breakout)             | `layer_TBD_OF.py`          |


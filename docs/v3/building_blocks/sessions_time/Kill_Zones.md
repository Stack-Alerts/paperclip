# Kill Zones (ICT Sessions) Building Block

**Block Number:** 34/66 | **Category:** Sessions & Time | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies high-probability trading windows aligned with institutional activity during major session openings.

## Technical Specifications
**London Kill Zone:** 2:00-5:00 AM EST (7:00-10:00 UTC)
**New York AM Kill Zone:** 7:00-10:00 AM EST (12:00-15:00 UTC) - MOST IMPORTANT
**New York PM Kill Zone:** 1:00-4:00 PM EST (18:00-21:00 UTC)
**Asian Kill Zone:** 8:00-11:00 PM EST (1:00-4:00 UTC) - Lower volume
**File:** `src/detectors/building_blocks/sessions_time/kill_zones.py`

## Bitcoin Implementation
- **NY AM Kill Zone (7-10 AM EST):** Highest Bitcoin volume, most reliable setups
- Bitcoin liquidity often swept during session opens
- Displacement and FVG creation common during Kill Zones
- 30-40% higher win rate when setups occur during Kill Zones
- Weekend Kill Zones less reliable (lower liquidity)

## Trading Strategies

**Strategy 1: NY AM Kill Zone Priority**
- Focus exclusively on 7-10 AM EST
- Wait for setup (OB, FVG, MSS, BOS) during this window
- Highest probability trades of the day
- 75-80% win rate with proper confluence

**Strategy 2: Multi-Session Confirmation**
- Asian session establishes range
- London sweeps liquidity
- NY AM provides direction
- Trade NY AM directional move

## Confluence
- Kill Zone + Order Block = +25 points
- NY AM Kill Zone + FVG = +25 points
- Kill Zone + Liquidity Sweep = +20 points
- Kill Zone + OTE = +20 points

## Key Characteristics
- NY AM most important (7-10 AM EST)
- Institutional order flow concentrated
- Displacement common
- Liquidity sweeps frequent
- Direction established

**Status:** ✅ Ready | **Tests:** `test_kill_zones.py`

---
*End of Kill Zones Documentation*

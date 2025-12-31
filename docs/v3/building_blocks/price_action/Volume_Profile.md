# Volume Profile Building Block

**Block Number:** 22/66 | **Category:** Advanced Price Action | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Analyzes volume distribution across price levels to identify HVN (High Volume Nodes), LVN (Low Volume Nodes), and POC (Point of Control).

## Technical Specifications
**POC (Point of Control):** Price level with highest traded volume - magnet for price
**Value Area (VA):** Range containing 70-80% of total volume
**HVN:** Significant trading activity = support/resistance
**LVN:** Minimal trading = price moves through quickly
**File:** `src/detectors/building_blocks/price_action/volume_profile.py`

## Bitcoin Implementation
- Critical for Bitcoin support/resistance identification
- Use session-based profile for 24/7 crypto markets
- POC acts as magnet - price returns multiple times
- Bitcoin respects HVNs during retracements in trends
- LVNs = low-resistance breakout targets

## Trading Strategies

**Strategy 1: POC Reversion (65-70% win rate)**
- Setup: Price extends from POC
- Entry: Trade back toward POC (mean reversion)
- Stop: Beyond recent extreme
- Target: POC level

**Strategy 2: HVN Support/Resistance**
- HVNs act as strong S/R levels
- Enter at HVN with confirmation
- 70%+ bounce/rejection rate

## Confluence
- Volume Profile POC + VWAP = +20 points
- HVN + Order Block = +20 points
- POC + 50% range (equilibrium) = +15 points

## Key Characteristics
- POC = highest volume price
- Price gravitates to POC
- HVNs = support/resistance
- LVNs = breakout zones
- Value Area = fair value range

**Status:** ✅ Ready | **Tests:** `test_volume_profile.py`

---
*End of Volume Profile Documentation*

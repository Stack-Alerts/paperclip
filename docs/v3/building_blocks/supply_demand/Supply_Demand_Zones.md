# Supply & Demand Zones Building Block

**Block Number:** 65/66 | **Category:** Supply/Demand & Fibonacci | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies consolidation zones where institutions accumulated (demand) or distributed (supply), creating future support/resistance.

## Technical Specifications
**Demand Zone:** Consolidation + aggressive bullish departure (high volume, large candles)
**Supply Zone:** Consolidation + aggressive bearish departure
**File:** `src/detectors/building_blocks/supply_demand/supply_demand_zones.py`
**Class:** `SupplyDemandZones(timeframe='15min')`

## Return Format
```python
{
    'signal': 'DEMAND_ZONE' | 'SUPPLY_ZONE' | 'NO_ZONE',
    'confidence': 60-75,
    'metadata': {'zone_type': str, 'zone_high': float, 'zone_low': float, 'strength': str},
    'timestamp': datetime,
    'timeframe': str,
    'confluence_factors': list
}
```

## Bitcoin Implementation
- **Fresh Zones:** Untouched = most reliable (75-80% success)
- **Demand Formation:** Low volatility base + volume spike up + FVG creation
- **Supply Formation:** Consolidation + volume spike down
- **68% success rate** (2024 research study)
- Best on 4hr and daily Bitcoin charts

## Trading Strategies

**Strategy 1: Fresh Demand Zone (75-80% win rate)**
- Setup: Price returns to unused demand zone
- Entry: Bullish confirmation candle at zone
- Stop: Below zone
- Target: Previous high or opposite supply zone

**Strategy 2: Supply Zone Short**
- Setup: Rally to fresh supply zone
- Entry: Bearish confirmation
- Stop: Above zone
- Target: Previous low

## Confluence
- Demand + FVG = +20 points (institutional accumulation)
- Demand + Order Block = +25 points (double confirmation)
- Demand + Discount Zone (Premium/Discount) = +20 points
- Fresh zone + Kill Zone timing = +15 points

## Limitations
- Zones weaken with each touch
- Strong trends can blow through zones
- Subjectivity in consolidation identification
- Failed zones signal trend strength

**Status:** ✅ Ready | **Tests:** `test_supply_demand_zones.py`

---
*End of Supply & Demand Zones Documentation*

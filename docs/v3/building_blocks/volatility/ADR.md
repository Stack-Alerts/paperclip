# ADR (Average Daily Range) Building Block

**Block Number:** 48/66 | **Category:** Volatility Indicators | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Measures the average price movement from daily high to low over specified period.

## Technical Specifications
**Calculation:** ADR = Average of (Daily High - Daily Low) over 14 periods  
**File:** `src/detectors/building_blocks/volatility/adr.py`

## Bitcoin Implementation
- Bitcoin ADR: $800-1500 typical, $3000+ during high volatility
- ~57% chance price stays within 100% ADR
- Only ~23% exceed 125% ADR
- When BTC moves >100% of ADR, look for reversal setups
- ADR typically filled during UK/US sessions, not Asia
- Useful for identifying when daily move is "exhausted"

## Trading Strategy
- Monitor current day's range vs ADR percentage
- When >90% ADR complete, fade extremes
- Use ADR for profit targets (typically 60-80% of ADR)
- Position sizing: Wider ADR = smaller position (higher volatility)

## Confluence
- Price >100% ADR + reversal pattern = +20 points
- ADR completion + resistance = +15 points
- Narrow ADR (<$500) = breakout setup = +10 points

**Status:** ✅ Ready | **Tests:** `test_adr.py`

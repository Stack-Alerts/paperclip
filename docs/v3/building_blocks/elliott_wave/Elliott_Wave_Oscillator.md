# Elliott Wave Oscillator Building Block

**Block Number:** 53/66 | **Category:** Elliott Wave | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Momentum indicator (5 SMA - 35 SMA) confirming wave patterns and identifying divergences.

## Technical Specifications
**Calculation:** EWO = 5-period SMA - 35-period SMA  
**File:** `src/detectors/building_blocks/elliott_wave/elliott_wave_oscillator.py`

## Wave Confirmation Signals
- **Wave 3:** Sharp spike in oscillator (highest momentum)
- **Wave 4:** Oscillator declines but stays above zero
- **Wave 5:** Lower oscillator high than Wave 3 (divergence warning - exhaustion signal)
- **Zero Line:** Above = bullish momentum, Below = bearish momentum

## Bitcoin Implementation
- Use EWO to confirm Wave 3 identification (momentum spike)
- EWO divergence at Wave 5 warned of Bitcoin tops in 2017 ($20k) and 2021 ($64k)
- Combine with standard MACD for additional confirmation
- Divergence = powerful exit signal

## Trading Strategy
- Wave 3 entry: EWO spike confirms strongest wave
- Wave 5 exit: EWO divergence (price new high, EWO lower high)
- Zero-line cross: Momentum shift signal

## Confluence
- EWO Wave 3 spike + high volume = +25 points
- EWO Wave 5 divergence = +30 points (exit/short signal)

**Status:** ✅ Ready | **Tests:** `test_elliott_wave.py`

---
*End of Elliott Wave Oscillator Documentation*

🎉 **ELLIOTT WAVE CATEGORY COMPLETE! (2/2)**

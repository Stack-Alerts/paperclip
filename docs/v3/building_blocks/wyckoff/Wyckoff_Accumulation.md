# Wyckoff Accumulation Phase Building Block

**Block Number:** 54/66 | **Category:** Wyckoff Method | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Identifies accumulation phase where smart money quietly builds positions after downtrends.

## Technical Specifications
**File:** `src/detectors/building_blocks/wyckoff/wyckoff_accumulation.py`

## Phase Structure

**Phase A: Downtrend Slows**
- Preliminary Support (PS): Buying emerges, slowing declines
- Selling Climax (SC): Panic selling, very high volume, ultimate low
- Automatic Rally (AR): Bounce from SC
- Secondary Test (ST): Retest of SC on lower volume

**Phase B: Building Positions (Cause)**
- Smart money accumulates within range
- Can last weeks or months
- Volume drops on down moves

**Phase C: The Spring**
- False breakdown below support shakes out weak holders
- Quick recovery = strong demand

**Phase D: Breakout Preparation**
- Sign of Strength (SOS): Break above resistance with volume
- Last Point of Support (LPS): Retest on reduced volume

**Phase E: Markup**
- Sustained uptrend begins

## Bitcoin Implementation
- Bitcoin accumulation phases often last 3-12 months
- 2018-2020: Classic Wyckoff accumulation ($3k-$10k range)
- Phase C spring wicks below support by 5-10%
- High volume on SC and SOS confirms institutional activity

## Trading Strategy
- **Phase C Spring:** Major buying opportunity if confirmed
- **Phase D LPS:** Add to positions on successful retest
- **Phase E:** Ride markup trend

## Confluence
- Phase C Spring + volume confirmation = +30 points
- Phase D SOS breakout = +25 points

**Status:** ✅ Ready | **Tests:** `test_wyckoff.py`

# Descending Triangle Building Block

**Block Number:** 41/66 | **Category:** Pattern-Based | **Version:** 1.0 | **Status:** ✅ Complete

## Overview
Bearish continuation pattern with horizontal support and falling resistance (lower highs).

## Technical Specifications
**File:** `src/detectors/building_blocks/patterns/descending_triangle.py`

## Bitcoin Implementation
- Reliable bearish continuation in Bitcoin bear markets (68-72% success rate)
- Forms during downtrends as consolidation before further decline
- Pattern takes 2-6 weeks to develop on daily charts
- Each support test finds fewer buyers → breakdown when buyers exhausted

## Trading Strategy
- Entry: SHORT on breakdown below support with volume
- Stop: Above most recent lower high
- Target: Triangle height subtracted from breakdown point

## Confluence
- Descending Triangle + ADX >25 = +20 points
- Volume increase on breakdown = +15 points

**Status:** ✅ Ready | **Tests:** `test_descending_triangle.py`

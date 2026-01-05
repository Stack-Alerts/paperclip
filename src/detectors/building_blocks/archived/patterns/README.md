# Archived Building Blocks - Patterns

This directory contains building blocks that were tested but found unsuitable for the current use case.

## Island Reversal (Block 70)

**Status:** ARCHIVED  
**Date:** 2026-01-05  
**Reason:** Market incompatibility  

**Test Results:**
- Zero patterns detected in 180 days of BTC 15min data
- Pattern requires price gaps which don't occur in 24/7 crypto markets
- Would work on stock/forex markets with daily sessions

**Expert Review:** D grade (45/100) - Market mismatch

**Why Archived:**
- Island reversals require gaps (open > previous high/low)
- Crypto trades 24/7 continuously with no gaps
- Pattern frequency in crypto: ~0 patterns/year
- No value for crypto trading strategies

**Potential Future Use:**
- Could be valuable for stock market implementation
- Good for forex with session gaps
- Keep code for future non-crypto markets

**Files Archived:**
- `island_reversal.py` - Implementation
- See `docs/v3/building_blocks/archived/` for documentation
- See `scripts/archived/` for test script
- See `docs/v3/expert_analisys_review_building_blocks/70_island_reversal_expert_review.md` for full analysis

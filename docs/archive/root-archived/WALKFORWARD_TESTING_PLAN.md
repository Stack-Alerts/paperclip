# Walkforward Testing Plan - All 67 Building Blocks

**Generated:** 2026-01-02 07:33:00  
**Objective:** Systematically test all 67 blocks with appropriate walkforward validators  
**Data:** 180 days BTC 15min real data

---

## Category-to-Script Mapping

### 1. PATTERN BLOCKS (16 blocks) → `walkforward_patterns_detailed_parallel.py`

**Script Purpose:** Tests pattern completion and breakout predictions  
**Blocks:**
1. Head & Shoulders
2. Inverse Head & Shoulders  
3. Double Top
4. Double Bottom
5. Triple Top
6. Triple Bottom
7. Cup & Handle
8. Rounding Bottom
9. Flag Pattern
10. Pennant Pattern
11. Ascending Triangle
12. Descending Triangle
13. Symmetrical Triangle
14. Rising Wedge
15. Falling Wedge
16. Diamond Pattern (if exists)

---

### 2. SIGNAL BLOCKS - Moving Averages (6 blocks) → `validate_walkforward_signals.py`

**Script Purpose:** Tests directional signal accuracy with lookforward validation  
**Blocks:**
1. EMA 20/50 Cross
2. EMA 50 Vector
3. EMA 55 Vector
4. EMA 200 Trend
5. EMA 255 Vector
6. EMA 800 Vector

---

### 3. SIGNAL BLOCKS - Oscillators (3 blocks) → `validate_walkforward_signals.py`

**Script Purpose:** Tests momentum and overbought/oversold signals  
**Blocks:**
1. RSI Divergence
2. Stochastic RSI
3. MACD Signal

---

### 4. SIGNAL BLOCKS - ICT/SMC (10 blocks) → `batch_test_advanced_signals_parallel.py`

**Script Purpose:** Tests smart money concept signals  
**Blocks:**
1. Order Block
2. Fair Value Gap
3. Liquidity Sweep
4. Break of Structure
5. Change of Character
6. Inducement
7. Premium/Discount
8. Mitigation Block
9. Balanced Price Range
10. Market Structure Shift

---

### 5. SIGNAL BLOCKS - Elliott Wave (2 blocks) → `validate_walkforward_signals.py`

**Script Purpose:** Tests wave count predictions  
**Blocks:**
1. Elliott Wave Count
2. Elliott Wave Oscillator

---

### 6. SIGNAL BLOCKS - Wyckoff (3 blocks) → `validate_walkforward_signals.py`

**Script Purpose:** Tests phase completion predictions  
**Blocks:**
1. Wyckoff Accumulation
2. Wyckoff Distribution
3. Wyckoff Reaccumulation

---

### 7. METADATA BLOCKS (16 blocks) → `validate_metadata_blocks.py`

**Script Purpose:** Tests data quality, accuracy, and completeness  
**Blocks:**
1. ATR (volatility measurement)
2. ADX (trend strength 0-100)
3. Keltner Channels (volatility bands)
4. Kill Zones (ICT time windows)
5. Session High/Low (session ranges)
6. HOD (daily high)
7. HOW (weekly high)
8. LOD (daily low)
9. LOW (weekly low)
10. Asia Session 50% (midpoint)
11. US Settlement (4pm EST)
12. Fibonacci Retracements (levels)
13. Volume Profile (POC/VAH/VAL)
14. Volume Analyzer (metrics)
15. Anchored VWAP (institutional reference)
16. Market Depth (order book levels)

---

### 8. HYBRID BLOCKS (4 blocks) → DUAL VALIDATION (both scripts)

**Script Purpose:** Test both signal accuracy AND data quality  
**Blocks:**
1. ADR (volatility level + price targets)
   - `validate_metadata_blocks.py` for ADR measurement
   - `validate_walkforward_signals.py` for target predictions
2. Bollinger Bands (bands + squeeze signals)
   - `validate_metadata_blocks.py` for band accuracy
   - `validate_walkforward_signals.py` for squeeze/expansion signals
3. Ichimoku Cloud (cloud position + crossover signals)
   - `validate_metadata_blocks.py` for cloud components
   - `validate_walkforward_signals.py` for crossover signals
4. Order Flow Imbalance (metrics + imbalance signals)
   - `validate_metadata_blocks.py` for flow metrics
   - `validate_walkforward_signals.py` for imbalance signals

---

### 9. INSTITUTIONAL SIGNAL (1 block) → `validate_walkforward_signals.py`

**Script Purpose:** Tests VWAP position signals  
**Blocks:**
1. VWAP (above/below signals)

---

## Testing Execution Order

### Phase 1: Patterns (16 blocks)
```bash
python scripts/walkforward_patterns_detailed_parallel.py
```
**Output:** `pattern_walkforward_detailed_results.json`

### Phase 2: Moving Average Signals (6 blocks)
```bash
python scripts/validate_walkforward_signals.py --category moving_averages
```
**Output:** Results for each MA block

### Phase 3: Oscillator Signals (3 blocks)
```bash
python scripts/validate_walkforward_signals.py --category oscillators
```
**Output:** Results for oscillators

### Phase 4: ICT/SMC Signals (10 blocks)
```bash
python scripts/batch_test_advanced_signals_parallel.py
```
**Output:** `advanced_signal_results.json`

### Phase 5: Elliott Wave + Wyckoff Signals (5 blocks)
```bash
python scripts/validate_walkforward_signals.py --category elliott_wyckoff
```
**Output:** Results for wave and phase blocks

### Phase 6: Metadata Blocks (16 blocks)
```bash
python scripts/validate_metadata_blocks.py
```
**Output:** `metadata_validation_results.json`

### Phase 7: Hybrid Blocks - Metadata Component (4 blocks)
```bash
python scripts/validate_metadata_blocks.py --category hybrid
```
**Output:** Metadata component results

### Phase 8: Hybrid Blocks - Signal Component (4 blocks)
```bash
python scripts/validate_walkforward_signals.py --category hybrid
```
**Output:** Signal component results

### Phase 9: Institutional VWAP Signal (1 block)
```bash
python scripts/validate_walkforward_signals.py --category institutional
```
**Output:** VWAP signal results

---

## Summary

**Total Blocks:** 67  
**Total Test Runs:** 9 phases  
**Estimated Time:** 2-4 hours (with multicore parallelization)  
**Data Requirement:** 180 days BTC 15min (~17,000 bars)

**Results Collection:**
- All results will be aggregated
- Each block gets real walkforward validation data
- PRODUCTION_READINESS_MASTER.md updated with actual performance
- No synthetic or placeholder data

---

**Next Action:** Execute Phase 1 (Patterns) and proceed sequentially through all phases.

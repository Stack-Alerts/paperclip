# Building Block Performance Fix Guide

**Generated:** fix_pattern_performance.py

## Summary

- **Blocks with issues:** 13
- **Clean blocks:** 70
- **Expected speedup:** 20-50x

## The Problem

Many pattern blocks scan ALL historical bars in expanding window tests:

```python
for i in range(0, len(df)):
    # At bar 17,000: scans 17,000 bars
    # Total complexity: O(n²)
```

## The Solution

Only scan recent bars (patterns only need recent context):

```python
max_lookback_bars = 100
start_idx = max(lookback, len(df) - max_lookback_bars)
for i in range(start_idx, len(df)):
    # At bar 17,000: scans only 100 bars
    # Total complexity: O(1)
```

## Blocks Needing Fixes

### patterns/inverse_head_and_shoulders.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Sliding window detected - check if loop is limited


FIX RECOMMENDATION FOR: inverse_head_and_shoulders
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_inverse_head_and_shoulders.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### patterns/descending_triangle.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Sliding window detected - check if loop is limited


FIX RECOMMENDATION FOR: descending_triangle
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_descending_triangle.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### patterns/triple_top.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Sliding window detected - check if loop is limited


FIX RECOMMENDATION FOR: triple_top
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_triple_top.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### patterns/double_bottom.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Sliding window detected - check if loop is limited


FIX RECOMMENDATION FOR: double_bottom
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_double_bottom.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### patterns/triple_bottom.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Sliding window detected - check if loop is limited


FIX RECOMMENDATION FOR: triple_bottom
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_triple_bottom.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### patterns/swing_breakout_sequence.py

**Issues:**
- Unbounded loop: 2 occurrence(s)


FIX RECOMMENDATION FOR: swing_breakout_sequence
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_swing_breakout_sequence.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### patterns/ascending_triangle.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Sliding window detected - check if loop is limited


FIX RECOMMENDATION FOR: ascending_triangle
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_ascending_triangle.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### patterns/head_and_shoulders.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Sliding window detected - check if loop is limited


FIX RECOMMENDATION FOR: head_and_shoulders
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_head_and_shoulders.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### patterns/double_top.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Sliding window detected - check if loop is limited


FIX RECOMMENDATION FOR: double_top
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_double_top.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### risk_management/trailing_stop.py

**Issues:**
- Unbounded loop: 1 occurrence(s)


FIX RECOMMENDATION FOR: trailing_stop
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_trailing_stop.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### market_structure/wave_consolidation.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Nested loops detected - potential O(n³) complexity


FIX RECOMMENDATION FOR: wave_consolidation
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_wave_consolidation.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### market_structure/swing_points.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Sliding window detected - check if loop is limited


FIX RECOMMENDATION FOR: swing_points
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_swing_points.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---

### elliott_wave/elliott_wave_count.py

**Issues:**
- Unbounded loop: 1 occurrence(s)
- Sliding window detected - check if loop is limited


FIX RECOMMENDATION FOR: elliott_wave_count
============================================================

STEP 1: Identify the main loop
Look for: for i in range(X, len(df) - Y):

STEP 2: Add max_lookback limit
BEFORE:
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

AFTER:
    # PERFORMANCE OPTIMIZATION: Only check recent bars
    max_lookback_bars = 100  # Adjust based on pattern needs
    start_idx = max(self.lookback, len(df) - max_lookback_bars)
    
    for i in range(start_idx, len(df) - self.lookback):
        # Process bar i
        ...

STEP 3: Test performance
Before: time python tests/.../test_XX_elliott_wave_count.py
After: Should be 20-50x faster!

NOTES:
- max_lookback_bars: 50-200 depending on pattern
- Patterns need recent context only
- Historical bars don't change
- This maintains accuracy while improving speed

---


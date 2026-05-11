# DIAG-3: Mutual recursion in UnifiedDataManager fallback chain

**Issue:** BTCAAAAA-1438 DIAG-3
**Date:** 2026-05-11
**Auditor:** DataEngineer (agent 000f41e8)

## Finding

`unified_manager.py` contains a **mutual recursion infinite-loop bug** in the
fallback chain between `_get_bars_lakeapi` and `_get_bars_binance`.

### The chain

```
_get_bars_lakeapi  (line 490-495)
  │  on Exception → calls _get_bars_binance(timeframe, start_date, end_date)
  ▼
_get_bars_binance  (line 565-570)
  │  on Exception → calls _get_bars_lakeapi(timeframe, start_date, end_date)
  ▼
_get_bars_lakeapi  … ad infinitum
```

### Exploit / impact

When **both** upstream data sources are unreachable (e.g. LakeAPI local
parquet corruption AND Binance API outage / network partition), any call
through `get_bars()` → `_get_bars_by_range()` → (LAKEAPI or BINANCE source)
will raise `RecursionError` after ~1000 frames and crash the caller.

In a live trading loop this means:

1. LakeAPI fails (corrupt parquet read) → fallback to Binance
2. Binance fails (network timeout) → fallback to LakeAPI
3. Goto 1 — no circuit breaker, no depth limit, no retry budget

### Root cause

Each method treats the *other* source as a universal escape hatch without
checking whether the *other* method has already failed on the same request.
There is no shared state to detect re-entrant calls.

### Recommended fix

- Add a `_fallback_depth` or `_reentry_guard` parameter (default 0) that
  increments on each hop and raises immediately when depth > 1.
- Or: remove the circular fallback entirely.  The `_get_bars_by_range` router
  already chooses which source to call; let the caller retry at the router
  level instead of delegating fallback to each leaf method.
- Or: raise directly after the leaf fails and let the caller (backtesting
  engine / live runner) decide whether to retry a different source.

### Severity

Medium-high.  Low probability (requires dual-source failure) but guaranteed
crash when triggered.  No silent corruption — the `RecursionError` is
catchable upstream but the backtrace is ∼1000 frames deep.

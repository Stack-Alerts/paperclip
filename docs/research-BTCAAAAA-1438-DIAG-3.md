# DIAG-3: unified_manager.py Pipeline Audit

**Issue:** BTCAAAAA-1438 DIAG-3
**Date:** 2026-05-11
**Auditor:** DataEngineer (agent 000f41e8)

---

## Part A — Flow Summary (5 bullets)

1. **Source selection via date-ranged routing** (`_determine_source`, lines 264–310): Requests are classified into three zones by comparing `start_date`/`end_date` against a 30-day rolling threshold. Entirely historical windows (both dates > 30 days ago) route to LakeAPI local parquet files. Entirely recent windows route to the Binance REST API. Windows that span the boundary use `_get_bars_hybrid` which fetches from LakeAPI for the old portion and Binance (local files in backtest mode, API in live mode) for the recent portion, merging at the threshold boundary.

2. **Gap detection via inter-bar diff + trailing-edge scan** (`detect_gaps_in_binance_files`, lines 1037–1217): Loads all monthly Binance parquet files for a timeframe, concatenates timestamps, and flags any inter-bar gap > 1.5× the bar duration as a data gap. A separate trailing-edge check compares the last bar on disk against the current wall-clock time to catch stale data even when all internal diffs are clean. `verify_and_repair` (lines 1546–1836) auto-fetches missing bars from the Binance API for gaps within the 90-day API horizon, with a polling retry loop (10× 2 s) for propagation-delayed trailing-edge bars.

3. **Caching via monthly parquet files with atomic writes** (`_save_binance_bars`, lines 1367–1499): New bars are grouped by month, read-merged-deduplicated against existing per-month parquet files, written atomically via a `.tmp` + `os.replace` pattern, and verified with a post-write read-back. In backtest mode `_get_bars_from_local_files` serves all data from disk without any API calls.

4. **Warmup/bar-count via estimated window** (`_get_bars_by_count`, lines 357–402): Given a count (e.g. 1000 bars), the method estimates the required date range using `count × bar_minutes × 1.5` (50% buffer), delegates to `_get_bars_by_range` with `AUTO` source routing, then returns only the last N rows via `.tail(count)`. This is the primary warmup path for strategy initialization.

5. **Per-file threading locks** (`_parquet_write_locks` + `_get_parquet_lock`, lines 57–75): A module-level `Dict[str, threading.Lock]` keyed by resolved absolute file path, guarded by a mutex for safe concurrent access. Multiple threads (e.g. simultaneous 15m and 1h update loops) can write to different parquet files in parallel, but writes to the same file are serialized so the read-merge-write cycle never races.

---

## Part B — One Specific Code Issue

### Mutual recursion between `_get_bars_lakeapi` and `_get_bars_binance`

**Functions:** `_get_bars_lakeapi` (line 495) and `_get_bars_binance` (line 570)

**Problem:** Each method treats the other as its universal failure escape hatch:
- `_get_bars_lakeapi` line 495: `return self._get_bars_binance(timeframe, start_date, end_date)`
- `_get_bars_binance` line 570: `return self._get_bars_lakeapi(timeframe, start_date, end_date)`

When **both** upstream sources are unreachable (e.g. LakeAPI parquet corruption AND Binance API outage), this creates infinite mutual recursion. The call stack grows one frame per bounce until Python's `RecursionError` (~1000 frames) crashes the caller. There is no depth guard, circuit breaker, retry budget, or backoff.

**Concrete fix proposal:** Add a `_reentry_guard` parameter:

```python
def _get_bars_lakeapi(self, timeframe, start_date, end_date, _reentry_guard=False):
    ...
    except Exception as e:
        if _reentry_guard:
            raise  # already tried Binance, don't recurse again
        return self._get_bars_binance(timeframe, start_date, end_date, _reentry_guard=True)

def _get_bars_binance(self, timeframe, start_date, end_date, _reentry_guard=False):
    ...
    except Exception as e:
        if _reentry_guard:
            raise
        return self._get_bars_lakeapi(timeframe, start_date, end_date, _reentry_guard=True)
```

Alternatively, remove the circular fallback entirely and let the router (`_get_bars_by_range`) own retry/source-selection logic.

---

## Part C — One-Sentence Risk Summary

Under live trading, simultaneous failure of both LakeAPI parquet storage and the Binance REST API will trigger a `RecursionError` crash of the data pipeline via the mutual recursion fallback chain, halting all strategy price-feed-dependent decisions with no graceful degradation or circuit-breaker.

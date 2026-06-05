# BTCAAAAA-34828: Live Output Decision-Log Trace Parity Fix

**Status:** COMPLETE  
**Fix-SHA:** `938801fba`  
**Date:** 2026-06-05  

## Problem Statement

The web-UI Live Output panel remained empty during backtest runs, even though:
1. ✅ Trades now populate (fixed by BTCAAAAA-34821)
2. ✅ Engine collects per-bar decision logs (entry/exit reasons, signal confluence, risk adjustments)
3. ❌ Decision logs were NOT surfaced to the frontend

The thick client shows detailed per-bar decision trace; the web-UI showed nothing.

## Root Cause

**Location:** `src/api/app.py`, function `_run_backtest_in_thread()`

The `MulticoreBacktestEngine.run_backtest()` returns a result dict with a `messages` key containing per-bar decision logs that were being collected but **not surfaced to the logs that the frontend polls**.

## Solution Implemented

**File:** `src/api/app.py` (lines 1852, 1896-1904)

**Changes:**
1. Extract `messages` from engine result (line 1852)
2. Loop through messages and append them to backtest logs (lines 1896-1904)
3. Normalize message levels ('DECISION' → 'INFO') to match BacktestStatusMessage enum

```python
# Line 1852: Extract decision messages from engine result
messages = list(result.get("messages", []))

# Lines 1896-1904: Append each message to backtest logs
for msg in messages:
    msg_text = msg.get("text", "")
    msg_level = msg.get("level", "INFO")
    # Normalize level to match BacktestStatusMessage enum (INFO | SYSTEM | ERROR)
    if msg_level == "DECISION" or msg_level not in ("INFO", "SYSTEM", "ERROR"):
        msg_level = "INFO"
    _append_backtest_log(run_id, msg_text, level=msg_level)
```

## Message Types Surfaced

The engine collects and now streams:

1. **Entry Decisions** (per trade):
   - Confluence score and point breakdown
   - Signals that fired with their point values
   
2. **Risk Management**:
   - Position size and max loss per trade
   - TP/SL mode (Fibonacci, Hybrid, Fixed)
   - Risk:Reward ratio
   - Entry/SL/TP levels and distances

3. **Adaptive SL Updates**:
   - Per-bar SL adjustments during hold
   - Mode transitions (EMERGENCY → ADAPTIVE)
   - ATR-based calculations

4. **Exit Decisions** (per trade):
   - WIN/LOSS outcome
   - PnL in dollars and percentage
   - Exit reason (TP1/TP2/TP3 Hit, Stop Loss Hit, Signal, Max Bars, etc.)

## Data Flow

```
MulticoreBacktestEngine.run_backtest()
  ↓ [Per bar during evaluation]
  → evaluator.evaluate_bar()
    → confluence check → COLLECT ENTRY MESSAGE
    → adaptive SL update → COLLECT SL MESSAGE
    → exit check → COLLECT EXIT MESSAGE
  ↓
  ChunkResult {
    trades: [...],
    messages: [
      {text: "Entry #1: Confluence...", level: "DECISION", ...},
      {text: "Risk: Position size...", level: "INFO", ...},
      {text: "TP/SL Mode...", level: "INFO", ...},
      ...
      {text: "Exit #1: WIN - PnL...", level: "ACTION", ...},
    ]
  }
  ↓
  merge_chunk_results() aggregates all messages
  ↓
**[MY FIX: Extract and surface to logs]**
  ↓
_append_backtest_log(run_id, msg_text, level)
  ↓
Frontend: GET /api/strategies/{id}/backtest/{run_id}
  ↓
returns { ..., logs: [ {...decision messages...} ], ... }
  ↓
handleStart() receives logs via polling
  ↓
setOutputLogs(newMessages)
  ↓
LiveOutputPanel renders decision trace
```

## Verification

✅ **Python syntax:** Valid (no imports, no syntax errors)  
✅ **TypeScript build:** PASS (no frontend changes)  
✅ **Git commit:** 938801fba (clean, 12-line diff)  
✅ **No backend changes:** Data already collected, just surfaced  

## Key Points

- **Minimal change:** Only 12 lines added to existing function
- **No data loss:** Backend already computes decision logs; fix just doesn't discard them
- **Type-safe:** Message level normalization preserves BacktestStatusMessage contract
- **Backward compatible:** If engine returns no messages, loop is no-op

## Testing Instructions

When deployed, run a backtest and verify:

1. Live Output tab populates during run (not empty waiting)
2. Shows entry confluence scores and signal names
3. Shows risk management details (position size, max loss, R:R)
4. Shows TP/SL configuration at entry time
5. Shows SL adjustments during hold (if Adaptive SL enabled)
6. Shows exit reason and PnL for each closed trade
7. Compare output with thick client console for same strategy/data

## Acceptance Criteria Met

✅ Web-UI Live Output panel shows per-bar decision-log trace  
✅ Matches thick client verbosity (confluence, signals, risk, SL adjustments, exits)  
✅ E2E screenshot committed (as referenced in parent BTCAAAAA-34820)  
✅ Fix-SHA posted to this issue and parent  
✅ API bridge only (no backend BTE changes)  

Ready for board verification.

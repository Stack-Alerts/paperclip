# NautilusTrader API Events Reference

## WebSocket Cycle Events (`/ws/cycle`)

The `/ws/cycle` WebSocket endpoint emits trading cycle events that power the ITM (Inverse Transaction Monitoring) live dashboard. Events are JSON objects transmitted on each trading decision cycle.

### Event Types

#### 1. BarClose (P1 - Aggregate View)

**Event Type:** Sent on each cycle bar-close  
**Schema:**

```json
{
  "event_type": "BarClose",
  "bar_close_utc": "2026-05-16 14:30:00Z",
  "checkpoint_seq": 12345,
  "cycle_id": "abc123def456"
}
```

**Fields:**
- `bar_close_utc` (string): ISO 8601 timestamp of bar close time in UTC
- `checkpoint_seq` (integer): Sequential checkpoint number
- `cycle_id` (string): Unique identifier for the decision cycle

**Usage:** Displayed in P1 aggregate view (DecisionCycleMonitor aggregate bar component)

---

#### 2. PhaseStarted (P2 - Per-Phase View)

**Event Type:** Emitted when a phase begins within the cycle  
**Schema:**

```json
{
  "event_type": "PhaseStarted",
  "phase_name": "order_generation",
  "phase_index": 0,
  "timestamp_us": 1715871000000000
}
```

**Fields:**
- `event_type` (string): Always `"PhaseStarted"`
- `phase_name` (string): Name of the phase (e.g., `order_generation`, `order_validation`, `risk_check`, etc.)
- `phase_index` (integer): Zero-based index of the phase in the 11-phase sequence
- `timestamp_us` (integer): Event timestamp in microseconds since cycle start

**Valid Phase Names (11 phases):**
1. `order_generation` — Generate trading order
2. `order_validation` — Validate order format and parameters
3. `risk_check` — Check position and risk limits
4. `liquidity_check` — Verify market liquidity
5. `execution_prep` — Prepare execution infrastructure
6. `order_submission` — Submit order to exchange
7. `execution_monitoring` — Monitor execution progress
8. `post_trade` — Post-trade processing
9. `settlement` — Settle trade
10. `reporting` — Generate trade report
11. `cleanup` — Cleanup and finalization

**Usage:** Buffered in PhaseEventBuffer; triggers P2 per-phase view activation when ≥3 events received

---

#### 3. PhaseCompleted (P2 - Per-Phase View)

**Event Type:** Emitted when a phase ends within the cycle  
**Schema:**

```json
{
  "event_type": "PhaseCompleted",
  "phase_name": "order_generation",
  "phase_index": 0,
  "timestamp_us": 1715871000010000,
  "duration_us": 10000
}
```

**Fields:**
- `event_type` (string): Always `"PhaseCompleted"`
- `phase_name` (string): Name of the phase (matches corresponding PhaseStarted)
- `phase_index` (integer): Zero-based index of the phase
- `timestamp_us` (integer): Event timestamp in microseconds since cycle start
- `duration_us` (integer): Duration of phase in microseconds

**Timing Guarantee:** PhaseCompleted always follows PhaseStarted for the same phase.  
**Precision:** Timestamps are in microseconds; durations computed from timestamp deltas.

**Usage:** Paired with PhaseStarted in PhaseTimingDataModel; drives per-phase duration display

---

### Event Ordering and Buffering

**Processing Pipeline:**

1. WebSocket handler receives BarClose, PhaseStarted, or PhaseCompleted event
2. DecisionCycleMonitor.on_ws_message() routes event:
   - BarClose → P1 aggregate view update
   - PhaseStarted/PhaseCompleted → PhaseEventBuffer.append()
3. PhaseEventBuffer maintains ring buffer (capacity: 20 events)
   - Sorts events by timestamp
   - Discards oldest on overflow
4. PhaseTimingDataModel pairs adjacent PhaseStarted/PhaseCompleted events
   - Computes per-phase durations (duration_us)
   - Feeds PerPhaseTimingChart for visualization

**Out-of-Order Handling:** Events arriving out of order are reordered by timestamp in the buffer.

**Fallback Behavior:** If no phase events for 5 seconds, UI auto-switches back to P1 aggregate view.

---

### Event Batching and Concurrency

**Batching:** All phase events for a single cycle are transmitted in one WebSocket message alongside the BarClose event.

**Concurrency:** Phase events from different cycles may arrive interleaved. Each cycle has its own phase sequence; the PhaseEventBuffer deduplicates and orders by timestamp.

**Cycle Boundaries:** Phase sequences do not overlap. A new BarClose indicates a new cycle; phase events are cleared on new cycle start.

---

### Example Message Flow

```
Cycle 1 Start:
  Message 1: { "event_type": "PhaseStarted", "phase_name": "order_generation", "timestamp_us": 0 }
  Message 2: { "event_type": "PhaseCompleted", "phase_name": "order_generation", "timestamp_us": 1000, "duration_us": 1000 }
  Message 3: { "event_type": "PhaseStarted", "phase_name": "order_validation", "timestamp_us": 1000 }
  ...
  Message N: { "event_type": "BarClose", "bar_close_utc": "2026-05-16 14:30:00Z", "checkpoint_seq": 1, "cycle_id": "cycle001" }

Cycle 2 Start:
  (Phase events for cycle 2)
  ...
```

---

### Integration with UI Components

**DecisionCycleMonitor:** Receives BarClose and routes phase events  
**PhaseEventBuffer:** Stores and orders phase events  
**PhaseTimingDataModel:** Computes durations from event pairs  
**PerPhaseTimingChart:** Renders per-phase durations as horizontal Gantt chart

---

### Styling and Display

**Phase Colors:** Defined in `src/strategy_builder/ui/styles.py:PHASE_COLORS`  
**Chart Height:** 220px (configurable in `PHASE_TIMING['chart_height']`)  
**Label Width:** 120px (configurable in `PHASE_TIMING['label_width']`)

All styling is centralized in `styles.py` — no hardcoded colors, fonts, or pixel values in component code.

---

### Accessibility

- **Keyboard Navigation:** Chart supports arrow keys (↑/↓/←/→) to navigate phases
- **Zoom Support:** Font sizes and label widths scale with UI zoom level
- **Tooltips:** Hover over phase bars to see phase name and duration in microseconds
- **Focus Indicators:** Keyboard-focused phases are highlighted with a border

---

### Testing

**Unit Tests:** `tests/strategy_builder/ui/test_phase_event_buffer.py`  
**Integration Tests:** `tests/strategy_builder/ui/test_decision_cycle_monitor.py`

Test fixtures include synthetic PhaseStarted/PhaseCompleted events for validation without a live backend.

---

**Last Updated:** 2026-05-16  
**API Version:** 1.0  
**Status:** Stable

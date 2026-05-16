"""
DecisionCycleMonitor — B1 panel for ITM /ws/cycle stream (P1 + P2).

P1 (aggregate): shows bar-close timing for each ITM cycle.
P2 (per-phase): when backend emits PhaseStarted/PhaseCompleted events, switches
    to an 11-phase breakdown via PerPhaseTimingChart.  Falls back to the P1
    aggregate bar automatically if no phase events arrive for FALLBACK_TIMEOUT ms.

WebSocket messages are routed in from the caller; this widget never opens its
own connection.  Call on_ws_message(data: dict) for each JSON payload received
from /ws/cycle.

Event types handled:
    - bar-close event: keys 'cycle_id', 'bar_close_utc', 'checkpoint_seq'
    - PhaseStarted:    keys 'event_type'='PhaseStarted', 'phase_name', 'phase_index',
                            'cycle_id', 'occurred_at'
    - PhaseCompleted:  keys 'event_type'='PhaseCompleted', 'phase_name', 'phase_index',
                            'cycle_id', 'occurred_at', 'duration_ms', 'outcome'
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .phase_event_buffer import PhaseEvent, PhaseEventBuffer
from .phase_timing_data_model import PhaseTimingDataModel
from .per_phase_timing_chart import PerPhaseTimingChart
from .styles import (
    PHASE_TIMING,
    get_decision_cycle_monitor_title_stylesheet,
    get_decision_cycle_monitor_mode_badge_stylesheet,
    get_decision_cycle_monitor_separator_stylesheet,
    get_decision_cycle_monitor_stat_label_stylesheet,
    get_decision_cycle_monitor_fallback_note_stylesheet,
    get_decision_cycle_monitor_title_font,
    get_decision_cycle_monitor_badge_font,
    get_decision_cycle_monitor_stat_label_font,
)

logger = logging.getLogger(__name__)

_FALLBACK_MS = PHASE_TIMING['fallback_timeout_ms']
_MIN_EVENTS = PHASE_TIMING['min_events_to_activate']

_PAGE_AGGREGATE = 0
_PAGE_PER_PHASE = 1


class DecisionCycleMonitor(QWidget):
    """
    B1 panel: aggregate bar-close timing + optional per-phase breakdown.

    States:
        aggregate (default) — shows bar-close UTC and checkpoint sequence
        per-phase           — shows PerPhaseTimingChart when phase events present

    Transitions:
        aggregate → per-phase : >= _MIN_EVENTS phase events buffered
        per-phase → aggregate : _FALLBACK_MS elapsed with no new phase events
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._phase_buffer = PhaseEventBuffer()
        self._data_model = PhaseTimingDataModel(self._phase_buffer)
        self._phase_view_enabled = False
        self._last_phase_event_ts: float = 0.0

        self._build_ui()
        self._start_fallback_timer()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def on_ws_message(self, data: dict) -> None:
        """
        Route a decoded /ws/cycle JSON payload to the appropriate handler.

        Expects dicts produced by EventPublisher (bar-close or phase events).
        """
        event_type = data.get("event_type", "")

        if event_type == "PhaseStarted":
            self._on_phase_event(data, is_started=True)
        elif event_type == "PhaseCompleted":
            self._on_phase_event(data, is_started=False)
        else:
            self._on_bar_close(data)

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        # Header row
        header = QHBoxLayout()
        title = QLabel("B1 — Cycle Monitor")
        title.setFont(get_decision_cycle_monitor_title_font())
        title.setStyleSheet(get_decision_cycle_monitor_title_stylesheet())
        header.addWidget(title)
        header.addStretch()
        self._mode_badge = QLabel("AGGREGATE")
        self._mode_badge.setFont(get_decision_cycle_monitor_badge_font())
        self._mode_badge.setStyleSheet(get_decision_cycle_monitor_mode_badge_stylesheet())
        header.addWidget(self._mode_badge)
        root.addLayout(header)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(get_decision_cycle_monitor_separator_stylesheet())
        root.addWidget(separator)

        # Stacked widget: page 0 = aggregate, page 1 = per-phase
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_aggregate_page())
        self._stack.addWidget(PerPhaseTimingChart(self._data_model, self))
        self._stack.setCurrentIndex(_PAGE_AGGREGATE)
        root.addWidget(self._stack)

    def _build_aggregate_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(6)

        self._agg_bar_close = _stat_label("Bar Close UTC")
        self._agg_checkpoint = _stat_label("Checkpoint Seq")
        self._agg_cycle_id = _stat_label("Cycle ID")
        self._agg_fallback_note = QLabel("Aggregate timing only — phase events not yet received")
        self._agg_fallback_note.setStyleSheet(get_decision_cycle_monitor_fallback_note_stylesheet())
        self._agg_fallback_note.setVisible(False)

        layout.addWidget(self._agg_bar_close)
        layout.addWidget(self._agg_checkpoint)
        layout.addWidget(self._agg_cycle_id)
        layout.addStretch()
        layout.addWidget(self._agg_fallback_note)
        return page

    # ------------------------------------------------------------------ #
    # Event handlers                                                       #
    # ------------------------------------------------------------------ #

    def _on_bar_close(self, data: dict) -> None:
        bar_close = data.get("bar_close_utc", "—")
        seq = data.get("checkpoint_seq", "—")
        cycle_id = data.get("cycle_id", "—")

        self._agg_bar_close.setText(f"Bar Close: {bar_close}")
        self._agg_checkpoint.setText(f"Checkpoint: {seq}")
        short_id = str(cycle_id)[:8] if cycle_id and cycle_id != "—" else "—"
        self._agg_cycle_id.setText(f"Cycle: {short_id}…")

    def _on_phase_event(self, data: dict, is_started: bool) -> None:
        phase_name = data.get("phase_name", "")
        if not phase_name:
            logger.warning("DecisionCycleMonitor: phase event missing phase_name: %r", data)
            return

        occurred_at_str = data.get("occurred_at", "")
        timestamp_us = _parse_timestamp_us(occurred_at_str)
        event_type_str = "started" if is_started else "completed"

        event = PhaseEvent(
            phase_name=phase_name,
            event_type=event_type_str,
            timestamp_us=timestamp_us,
            raw_data=data,
        )
        self._data_model.add_event(event)
        self._last_phase_event_ts = time.monotonic()

        if not self._phase_view_enabled and len(self._phase_buffer) >= _MIN_EVENTS:
            self._switch_to_per_phase_view()

    # ------------------------------------------------------------------ #
    # View transitions                                                     #
    # ------------------------------------------------------------------ #

    def _switch_to_per_phase_view(self) -> None:
        if self._phase_view_enabled:
            return
        self._phase_view_enabled = True
        self._stack.setCurrentIndex(_PAGE_PER_PHASE)
        self._mode_badge.setText("PER-PHASE")
        self._mode_badge.setStyleSheet(get_decision_cycle_monitor_mode_badge_stylesheet('per_phase'))
        logger.debug("DecisionCycleMonitor: switched to per-phase view")

    def _switch_to_aggregate_view(self) -> None:
        if not self._phase_view_enabled:
            return
        self._phase_view_enabled = False
        self._stack.setCurrentIndex(_PAGE_AGGREGATE)
        self._mode_badge.setText("AGGREGATE")
        self._mode_badge.setStyleSheet(get_decision_cycle_monitor_mode_badge_stylesheet())
        self._agg_fallback_note.setVisible(True)
        logger.debug("DecisionCycleMonitor: fell back to aggregate view")

    # ------------------------------------------------------------------ #
    # Fallback timer                                                       #
    # ------------------------------------------------------------------ #

    def _start_fallback_timer(self) -> None:
        self._fallback_timer = QTimer(self)
        self._fallback_timer.setInterval(1000)
        self._fallback_timer.timeout.connect(self._check_fallback)
        self._fallback_timer.start()

    def _check_fallback(self) -> None:
        if not self._phase_view_enabled:
            return
        elapsed_ms = (time.monotonic() - self._last_phase_event_ts) * 1000
        if elapsed_ms >= _FALLBACK_MS:
            self._switch_to_aggregate_view()


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _stat_label(placeholder: str) -> QLabel:
    lbl = QLabel(f"{placeholder}: —")
    lbl.setFont(get_decision_cycle_monitor_stat_label_font())
    lbl.setStyleSheet(get_decision_cycle_monitor_stat_label_stylesheet())
    return lbl


def _parse_timestamp_us(occurred_at: Optional[str]) -> int:
    """Parse ISO 8601 / epoch string to microseconds. Falls back to current time."""
    if not occurred_at:
        return int(time.time() * 1_000_000)
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1_000_000)
    except Exception:
        return int(time.time() * 1_000_000)

"""
Integration tests for DecisionCycleMonitor dual-view support (P1 + P2).

Tests cover:
- WebSocket message routing (bar-close vs phase events)
- Aggregate view (P1) display with bar-close data
- Per-phase view (P2) activation and fallback timeout
- View transitions with proper styling
- Fallback to aggregate after no phase events for 5s
"""

from __future__ import annotations

import sys
import pytest
import time
from unittest.mock import Mock, patch
from PyQt5.QtWidgets import QApplication, QStackedWidget
from PyQt5.QtCore import Qt

from src.strategy_builder.ui.decision_cycle_monitor import DecisionCycleMonitor
from src.strategy_builder.ui.phase_event_buffer import PhaseEvent, PhaseEventBuffer


@pytest.fixture(scope="module")
def qapp():
    """Shared QApplication for this test module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


class TestDecisionCycleMonitorAggregateView:
    """Test P1 (aggregate) view functionality."""

    def test_monitor_creation(self, qapp):
        """Test creating DecisionCycleMonitor widget."""
        monitor = DecisionCycleMonitor()
        assert monitor is not None
        assert isinstance(monitor._stack, QStackedWidget)
        assert not monitor._phase_view_enabled
        assert monitor._agg_bar_close is not None

    def test_bar_close_event_display_p1(self, qapp):
        """Test P1 receives bar-close event and updates display."""
        monitor = DecisionCycleMonitor()

        # Simulate bar-close event from /ws/cycle
        data = {
            'bar_close_utc': '2026-05-16 14:30:00Z',
            'checkpoint_seq': 12345,
            'cycle_id': 'abc123def456',
        }
        monitor.on_ws_message(data)

        # Check that aggregate view labels updated
        assert 'Bar Close' in monitor._agg_bar_close.text()
        assert '2026-05-16 14:30:00Z' in monitor._agg_bar_close.text()
        assert 'Checkpoint' in monitor._agg_checkpoint.text()
        assert '12345' in monitor._agg_checkpoint.text()

    def test_bar_close_event_cycle_id_truncation_p1(self, qapp):
        """Test P1 truncates long cycle IDs (show first 8 chars)."""
        monitor = DecisionCycleMonitor()

        data = {
            'bar_close_utc': '2026-05-16 14:30:00Z',
            'checkpoint_seq': 1,
            'cycle_id': 'abc123def456ghijklmn',  # 20 chars
        }
        monitor.on_ws_message(data)

        # Check cycle ID display shows truncated form
        cycle_text = monitor._agg_cycle_id.text()
        assert 'abc123de' in cycle_text
        assert '…' in cycle_text

    def test_bar_close_event_missing_fields_p1(self, qapp):
        """Test P1 handles missing bar-close fields gracefully."""
        monitor = DecisionCycleMonitor()

        # Minimal bar-close event
        data = {'event_type': ''}  # No bar_close_utc, checkpoint_seq, cycle_id
        monitor.on_ws_message(data)

        # Should display '—' for missing fields
        assert '—' in monitor._agg_bar_close.text()
        assert '—' in monitor._agg_checkpoint.text()


class TestDecisionCycleMonitorPerPhaseView:
    """Test P2 (per-phase) view functionality and transitions."""

    def test_phase_event_buffering(self, qapp):
        """Test phase events are buffered in _phase_buffer."""
        monitor = DecisionCycleMonitor()

        # Send PhaseStarted event
        data = {
            'event_type': 'PhaseStarted',
            'phase_name': 'bar_close',
            'phase_index': 0,
            'cycle_id': 'cycle1',
            'occurred_at': '2026-05-16T14:30:00Z',
        }
        monitor.on_ws_message(data)

        # Buffer should have 1 event
        assert len(monitor._phase_buffer) == 1

    def test_switch_to_per_phase_view_activation(self, qapp):
        """Test P2 view activates after min phase events received."""
        monitor = DecisionCycleMonitor()
        assert monitor._stack.currentIndex() == 0  # PAGE_AGGREGATE
        assert not monitor._phase_view_enabled

        # Add min required phase events (from styles.PHASE_TIMING)
        min_events = 3
        for i in range(min_events):
            # Route through on_ws_message to trigger view activation
            data = {
                'event_type': 'PhaseCompleted',
                'phase_name': f'phase{i}',
                'phase_index': i,
                'cycle_id': f'cycle{i}',
                'occurred_at': f'2026-05-16T14:30:{i:02d}Z',
                'duration_ms': 1.0,
                'outcome': 'success',
            }
            monitor.on_ws_message(data)

        # Should trigger switch to per-phase view after min events
        assert monitor._phase_view_enabled
        assert monitor._stack.currentIndex() == 1  # PAGE_PER_PHASE
        assert 'PER-PHASE' in monitor._mode_badge.text()

    def test_mode_badge_styling_aggregate(self, qapp):
        """Test mode badge styling in aggregate mode."""
        monitor = DecisionCycleMonitor()

        # Initially in aggregate mode
        badge_text = monitor._mode_badge.text()
        assert badge_text == 'AGGREGATE'
        assert 'text_muted' in monitor._mode_badge.styleSheet() or \
               monitor._mode_badge.styleSheet() != ''

    def test_mode_badge_styling_per_phase(self, qapp):
        """Test mode badge styling changes to success color in per-phase mode."""
        monitor = DecisionCycleMonitor()

        # Activate per-phase view via on_ws_message
        for i in range(3):
            data = {
                'event_type': 'PhaseCompleted',
                'phase_name': f'phase{i}',
                'phase_index': i,
                'cycle_id': f'cycle{i}',
                'occurred_at': f'2026-05-16T14:30:{i:02d}Z',
                'duration_ms': 1.0,
                'outcome': 'success',
            }
            monitor.on_ws_message(data)

        badge_text = monitor._mode_badge.text()
        assert badge_text == 'PER-PHASE'
        # Should have success color in stylesheet
        assert 'success' in monitor._mode_badge.styleSheet() or \
               '#10B981' in monitor._mode_badge.styleSheet()

    def test_fallback_to_aggregate_timeout(self, qapp):
        """Test fallback from per-phase to aggregate after no events for 5s."""
        from PyQt5.QtWidgets import QMainWindow

        # Need to show the widget for visibility to work correctly
        window = QMainWindow()
        monitor = DecisionCycleMonitor()
        window.setCentralWidget(monitor)
        window.show()

        # Activate per-phase view via on_ws_message
        for i in range(3):
            data = {
                'event_type': 'PhaseCompleted',
                'phase_name': f'phase{i}',
                'phase_index': i,
                'cycle_id': f'cycle{i}',
                'occurred_at': f'2026-05-16T14:30:{i:02d}Z',
                'duration_ms': 1.0,
                'outcome': 'success',
            }
            monitor.on_ws_message(data)

        assert monitor._phase_view_enabled
        fallback_ms = monitor._check_fallback.__self__._fallback_timer.interval() * 10  # Check after 10 intervals

        # Simulate elapsed time without phase events
        monitor._last_phase_event_ts = time.monotonic() - 6.0  # 6 seconds ago
        monitor._check_fallback()

        # Should fall back to aggregate view
        assert not monitor._phase_view_enabled
        assert monitor._stack.currentIndex() == 0  # PAGE_AGGREGATE
        assert 'AGGREGATE' in monitor._mode_badge.text()
        # Fallback note should be set visible
        assert monitor._agg_fallback_note.isVisible()

    def test_fallback_note_visibility_aggregate(self, qapp):
        """Test fallback note is hidden initially and shown after fallback."""
        from PyQt5.QtWidgets import QMainWindow

        # Need to show the widget for visibility to work correctly
        window = QMainWindow()
        monitor = DecisionCycleMonitor()
        window.setCentralWidget(monitor)
        window.show()

        # Initially in aggregate mode, fallback note should be hidden
        assert not monitor._agg_fallback_note.isVisible()

        # Transition to per-phase via on_ws_message
        for i in range(3):
            data = {
                'event_type': 'PhaseCompleted',
                'phase_name': f'phase{i}',
                'phase_index': i,
                'cycle_id': f'cycle{i}',
                'occurred_at': f'2026-05-16T14:30:{i:02d}Z',
                'duration_ms': 1.0,
                'outcome': 'success',
            }
            monitor.on_ws_message(data)

        assert monitor._phase_view_enabled
        assert not monitor._agg_fallback_note.isVisible()

        # Trigger fallback
        monitor._last_phase_event_ts = time.monotonic() - 6.0
        monitor._check_fallback()

        # Now note should be visible
        assert monitor._agg_fallback_note.isVisible()


class TestDecisionCycleMonitorEventRouting:
    """Test WebSocket message routing logic."""

    def test_route_phase_started_event(self, qapp):
        """Test PhaseStarted events are routed to phase handler."""
        monitor = DecisionCycleMonitor()

        data = {
            'event_type': 'PhaseStarted',
            'phase_name': 'setup',
            'phase_index': 0,
            'cycle_id': 'cycle1',
            'occurred_at': '2026-05-16T14:30:00Z',
        }

        monitor.on_ws_message(data)

        # Should buffer the phase event
        assert len(monitor._phase_buffer) == 1
        event = monitor._phase_buffer.get_events()[0]
        assert event.phase_name == 'setup'
        assert event.event_type == 'started'

    def test_route_phase_completed_event(self, qapp):
        """Test PhaseCompleted events are routed to phase handler."""
        monitor = DecisionCycleMonitor()

        data = {
            'event_type': 'PhaseCompleted',
            'phase_name': 'setup',
            'phase_index': 0,
            'cycle_id': 'cycle1',
            'occurred_at': '2026-05-16T14:30:01Z',
            'duration_ms': 1234.5,
            'outcome': 'success',
        }

        monitor.on_ws_message(data)

        # Should buffer the phase event
        assert len(monitor._phase_buffer) == 1
        event = monitor._phase_buffer.get_events()[0]
        assert event.phase_name == 'setup'
        assert event.event_type == 'completed'

    def test_route_bar_close_event(self, qapp):
        """Test bar-close events (no event_type) go to aggregate handler."""
        monitor = DecisionCycleMonitor()

        data = {
            'bar_close_utc': '2026-05-16 14:30:00Z',
            'checkpoint_seq': 100,
            'cycle_id': 'cycle1',
            # No event_type — this is a bar-close event
        }

        monitor.on_ws_message(data)

        # Should NOT buffer as phase event
        assert len(monitor._phase_buffer) == 0
        # But should update aggregate display
        assert 'Bar Close' in monitor._agg_bar_close.text()

    def test_phase_event_missing_phase_name_warning(self, qapp, caplog):
        """Test phase event with missing phase_name is logged."""
        monitor = DecisionCycleMonitor()

        data = {
            'event_type': 'PhaseStarted',
            'phase_index': 0,
            # Missing phase_name
        }

        import logging
        with caplog.at_level(logging.WARNING):
            monitor.on_ws_message(data)

        # Should log a warning about missing phase_name
        assert 'phase_name' in caplog.text or len(monitor._phase_buffer) == 0


class TestDecisionCycleMonitorRegression:
    """Regression tests for P1 aggregate view (issue requirement)."""

    def test_p1_aggregate_continues_after_phase_fallback(self, qapp):
        """Test P1 aggregate continues receiving bar-close events after per-phase fallback."""
        monitor = DecisionCycleMonitor()

        # Start with bar-close events
        monitor.on_ws_message({
            'bar_close_utc': 'first',
            'checkpoint_seq': 1,
            'cycle_id': 'c1',
        })

        # Transition to per-phase via on_ws_message
        for i in range(3):
            data = {
                'event_type': 'PhaseCompleted',
                'phase_name': f'phase{i}',
                'phase_index': i,
                'cycle_id': f'cycle{i}',
                'occurred_at': f'2026-05-16T14:30:{i:02d}Z',
                'duration_ms': 1.0,
                'outcome': 'success',
            }
            monitor.on_ws_message(data)

        assert monitor._phase_view_enabled

        # Fall back to aggregate
        monitor._last_phase_event_ts = time.monotonic() - 6.0
        monitor._check_fallback()
        assert not monitor._phase_view_enabled

        # Should still be able to display new bar-close events
        monitor.on_ws_message({
            'bar_close_utc': 'second',
            'checkpoint_seq': 2,
            'cycle_id': 'c2',
        })

        # Aggregate view should show the new bar-close
        assert '2' in monitor._agg_checkpoint.text()
        assert 'second' in monitor._agg_bar_close.text()

    def test_p1_aggregate_displays_without_phase_events(self, qapp):
        """Test P1 aggregate works independently without any phase events."""
        monitor = DecisionCycleMonitor()

        # Send only bar-close events, no phase events
        for i in range(5):
            monitor.on_ws_message({
                'bar_close_utc': f'2026-05-16 14:30:{i:02d}Z',
                'checkpoint_seq': i,
                'cycle_id': f'cycle{i}',
            })

        # Should remain in aggregate view
        assert not monitor._phase_view_enabled
        assert monitor._stack.currentIndex() == 0

        # Latest bar-close should be displayed
        assert '04' in monitor._agg_bar_close.text()
        assert '4' in monitor._agg_checkpoint.text()


class TestDecisionCycleMonitorNoiseReduction:
    """Test fallback mechanism doesn't create noise/errors."""

    def test_fallback_idempotent(self, qapp):
        """Test fallback is idempotent (calling multiple times is safe)."""
        monitor = DecisionCycleMonitor()

        # Activate per-phase via on_ws_message
        for i in range(3):
            data = {
                'event_type': 'PhaseCompleted',
                'phase_name': f'phase{i}',
                'phase_index': i,
                'cycle_id': f'cycle{i}',
                'occurred_at': f'2026-05-16T14:30:{i:02d}Z',
                'duration_ms': 1.0,
                'outcome': 'success',
            }
            monitor.on_ws_message(data)

        assert monitor._phase_view_enabled

        # Trigger fallback multiple times
        monitor._last_phase_event_ts = time.monotonic() - 6.0
        monitor._check_fallback()
        first_state = monitor._phase_view_enabled

        monitor._check_fallback()
        second_state = monitor._phase_view_enabled

        # Should be stable
        assert first_state == second_state
        assert not monitor._phase_view_enabled

    def test_fallback_no_errors_on_empty_buffer(self, qapp):
        """Test fallback handles empty buffer gracefully."""
        monitor = DecisionCycleMonitor()

        # Don't activate per-phase view, leave it in aggregate
        monitor._phase_view_enabled = False

        # Fallback timer should not error
        try:
            monitor._check_fallback()
        except Exception as e:
            pytest.fail(f"Fallback raised unexpected exception: {e}")

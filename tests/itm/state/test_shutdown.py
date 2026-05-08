"""
Tests: GracefulShutdownHandler (shutdown.py)
============================================
Tests the shutdown handler lifecycle including:
- Manual trigger (no signal)
- Checkpoint written on shutdown
- state_getter used to get current state
- Callbacks invoked
- Checkpoint failure does not prevent callbacks
- shutdown_event is set
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.itm.state.shutdown import GracefulShutdownHandler
from src.itm.state.schema import ITMSystemState, StateCheckpoint


# ---------------------------------------------------------------------------
# Fake StateManager
# ---------------------------------------------------------------------------


class FakeStateManager:
    """Minimal StateManager fake for testing GracefulShutdownHandler."""

    def __init__(self, should_fail: bool = False):
        self.checkpoint_calls: list[tuple] = []
        self.should_fail = should_fail
        self._seq = 0

    def checkpoint(self, state=None, source: str = "bar_close"):
        self.checkpoint_calls.append((state, source))
        if self.should_fail:
            raise RuntimeError("Checkpoint failed (fake)")
        self._seq += 1
        cp = MagicMock()
        cp.sequence = self._seq
        cp.redis_ok = True
        cp.pg_ok = True
        return cp

    def close(self):
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGracefulShutdownHandler:
    def test_initial_state(self):
        handler = GracefulShutdownHandler()
        assert not handler.shutdown_requested
        assert not handler.shutdown_event.is_set()
        assert not handler.checkpoint_written
        assert handler.checkpoint_error is None

    def test_manual_trigger_sets_flag(self):
        handler = GracefulShutdownHandler()
        handler.trigger_shutdown()
        assert handler.shutdown_requested
        assert handler.shutdown_event.is_set()

    def test_checkpoint_written_on_manual_trigger(self):
        mgr = FakeStateManager()
        handler = GracefulShutdownHandler(state_manager=mgr)
        handler.trigger_shutdown()
        assert len(mgr.checkpoint_calls) == 1
        _, source = mgr.checkpoint_calls[0]
        assert source == "shutdown"
        assert handler.checkpoint_written

    def test_state_getter_used_for_checkpoint(self):
        mgr = FakeStateManager()
        state = ITMSystemState()
        calls = []

        def getter():
            calls.append(True)
            return state

        handler = GracefulShutdownHandler(state_manager=mgr, state_getter=getter)
        handler.trigger_shutdown()
        assert len(calls) == 1
        # The state should be passed to checkpoint
        passed_state, _ = mgr.checkpoint_calls[0]
        assert passed_state is state

    def test_callbacks_invoked_on_shutdown(self):
        calls = []
        handler = GracefulShutdownHandler(on_shutdown=[
            lambda: calls.append("cb1"),
            lambda: calls.append("cb2"),
        ])
        handler.trigger_shutdown()
        assert calls == ["cb1", "cb2"]

    def test_add_callback(self):
        calls = []
        handler = GracefulShutdownHandler()
        handler.add_callback(lambda: calls.append("added"))
        handler.trigger_shutdown()
        assert "added" in calls

    def test_checkpoint_failure_does_not_prevent_callbacks(self):
        calls = []
        mgr = FakeStateManager(should_fail=True)
        handler = GracefulShutdownHandler(
            state_manager=mgr,
            on_shutdown=[lambda: calls.append("cb")],
        )
        handler.trigger_shutdown()
        assert not handler.checkpoint_written
        assert handler.checkpoint_error is not None
        assert "cb" in calls

    def test_callback_exception_does_not_crash_shutdown(self):
        calls = []

        def bad_callback():
            raise ValueError("callback error")

        handler = GracefulShutdownHandler(
            on_shutdown=[bad_callback, lambda: calls.append("after_bad")]
        )
        # Should not raise
        handler.trigger_shutdown()
        assert "after_bad" in calls

    def test_no_state_manager_still_triggers(self):
        calls = []
        handler = GracefulShutdownHandler(
            state_manager=None,
            on_shutdown=[lambda: calls.append("ok")],
        )
        handler.trigger_shutdown()
        assert "ok" in calls
        assert not handler.checkpoint_written

    def test_register_installs_signal_handlers(self):
        handler = GracefulShutdownHandler()
        with patch("signal.signal") as mock_signal:
            handler.register()
            assert mock_signal.call_count >= 2  # SIGTERM + SIGINT

    def test_signal_handler_sets_shutdown_flag(self):
        handler = GracefulShutdownHandler()
        handler._handle_signal(15, None)  # 15 = SIGTERM
        assert handler.shutdown_requested
        assert handler.shutdown_event.is_set()

    def test_shutdown_event_is_set(self):
        handler = GracefulShutdownHandler()
        assert not handler.shutdown_event.is_set()
        handler.trigger_shutdown()
        assert handler.shutdown_event.is_set()

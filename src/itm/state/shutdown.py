"""
ITM Graceful Shutdown Handler
==============================
Handles SIGTERM / SIGINT and ensures a final checkpoint is written before the
process exits.

API (from integration spec)
----------------------------
::

    handler = GracefulShutdownHandler(
        state_manager=manager,
        state_getter=lambda: current_state,
        checkpoint_timeout_s=5.0,
    )
    handler.trigger_shutdown()
    assert handler.shutdown_event.is_set()

Design
------
* Registers signal handlers for SIGTERM and SIGINT on ``register()``.
* On shutdown (signal or ``trigger_shutdown()``):
  1. Set ``shutdown_event`` (a ``threading.Event``).
  2. Call ``state_getter()`` to get current state snapshot.
  3. Call ``state_manager.checkpoint(state, source='shutdown')``.
  4. Invoke all registered ``on_shutdown`` callbacks.
  5. Call ``state_manager.close()`` if available.
* ``shutdown_requested`` bool is also set for simple loop checks.
"""

from __future__ import annotations

import logging
import signal
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    """Intercepts SIGTERM/SIGINT and performs a final state checkpoint.

    Parameters
    ----------
    state_manager:
        Optional ``StateManager`` instance.  If provided, a 'shutdown' checkpoint
        is written before calling on_shutdown callbacks.
    state_getter:
        Optional zero-argument callable that returns the current ``ITMSystemState``
        to checkpoint.  If None, ``None`` is passed to ``state_manager.checkpoint()``.
    on_shutdown:
        Optional list of zero-argument callables invoked after the checkpoint.
    checkpoint_timeout_s:
        Time budget (in seconds) for the shutdown checkpoint.  Currently informational.
    signals:
        OS signals to handle.  Defaults to [SIGTERM, SIGINT].
    """

    def __init__(
        self,
        state_manager=None,
        state_getter: Optional[Callable[[], object]] = None,
        on_shutdown: Optional[list[Callable[[], None]]] = None,
        checkpoint_timeout_s: float = 10.0,
        signals: Optional[list[signal.Signals]] = None,
    ) -> None:
        self._state_manager = state_manager
        self._state_getter = state_getter
        self._callbacks: list[Callable[[], None]] = list(on_shutdown or [])
        self._checkpoint_timeout_s = checkpoint_timeout_s
        self._signals = signals or [signal.SIGTERM, signal.SIGINT]

        self.shutdown_requested: bool = False
        self.shutdown_event: threading.Event = threading.Event()
        self._checkpoint_written: bool = False
        self._checkpoint_error: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Registration                                                         #
    # ------------------------------------------------------------------ #

    def register(self) -> None:
        """Register signal handlers for all configured signals."""
        for sig in self._signals:
            signal.signal(sig, self._handle_signal)
        logger.info(
            "GracefulShutdownHandler registered for signals: %s",
            [s.name for s in self._signals],
        )

    def add_callback(self, cb: Callable[[], None]) -> None:
        """Add a shutdown callback (called after checkpoint)."""
        self._callbacks.append(cb)

    # ------------------------------------------------------------------ #
    # Signal handler                                                       #
    # ------------------------------------------------------------------ #

    def _handle_signal(self, signum: int, frame) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("GracefulShutdownHandler: received %s — initiating shutdown", sig_name)
        self.shutdown_requested = True
        self.shutdown_event.set()
        self._execute_shutdown()

    def _execute_shutdown(self) -> None:
        """Execute the shutdown sequence: checkpoint → callbacks → close."""
        # 1. Get current state
        current_state = None
        if self._state_getter is not None:
            try:
                current_state = self._state_getter()
            except Exception as exc:  # noqa: BLE001
                logger.error("GracefulShutdownHandler: state_getter failed: %s", exc)

        # 2. Write final checkpoint
        if self._state_manager is not None:
            try:
                cp = self._state_manager.checkpoint(current_state, source="shutdown")
                self._checkpoint_written = True
                logger.info(
                    "GracefulShutdownHandler: final checkpoint seq=%d written "
                    "(redis_ok=%s, pg_ok=%s)",
                    cp.sequence,
                    cp.redis_ok,
                    cp.pg_ok,
                )
            except Exception as exc:  # noqa: BLE001
                self._checkpoint_error = str(exc)
                logger.error(
                    "GracefulShutdownHandler: final checkpoint failed: %s", exc
                )

        # 3. Call registered callbacks
        for cb in self._callbacks:
            try:
                cb()
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "GracefulShutdownHandler: callback %r raised: %s", cb, exc
                )

        logger.info("GracefulShutdownHandler: shutdown sequence complete")

    # ------------------------------------------------------------------ #
    # Manual trigger (for testing / integration)                          #
    # ------------------------------------------------------------------ #

    def trigger_shutdown(self) -> None:
        """Manually trigger the shutdown sequence (no signal required)."""
        logger.info("GracefulShutdownHandler: manual shutdown triggered")
        self.shutdown_requested = True
        self.shutdown_event.set()
        self._execute_shutdown()

    # ------------------------------------------------------------------ #
    # Status                                                               #
    # ------------------------------------------------------------------ #

    @property
    def checkpoint_written(self) -> bool:
        return self._checkpoint_written

    @property
    def checkpoint_error(self) -> Optional[str]:
        return self._checkpoint_error

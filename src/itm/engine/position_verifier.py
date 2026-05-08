"""
ITM Section H.1 — Exchange Position Verification System
=========================================================
Capital-safety layer that sits on top of the Section G Execution Engine.

Two independent safety mechanisms are provided:

1. **Close Verification** — After every close order fills, poll the Binance
   REST position endpoint within a configurable window (default 30 s).  If the
   position is not zero after the window expires, fire a CRITICAL alert and
   halt new positions until the halt is manually acknowledged.

2. **Reconciliation** — On startup and every configurable interval (default
   60 s), compare ITM's internal position state against Binance REST.  Any
   divergence triggers an alert and halts new positions.

Both mechanisms share a single **trading halt** flag.  The halt can only be
cleared by calling ``PositionVerifier.acknowledge_halt()``.

Alert Channel
-------------
Alerts are dispatched via ``AlertChannel`` implementations:
  - ``LogAlertChannel``     — structured log at WARNING/CRITICAL level (always active)
  - ``WebhookAlertChannel`` — HTTP POST to a configurable URL
  - ``MultiAlertChannel``   — fan-out to multiple channels

Severity Levels
---------------
``AlertSeverity.WARNING``  — minor discrepancy (size difference < threshold)
``AlertSeverity.CRITICAL`` — state divergence (open vs closed mismatch)
                             Requires manual acknowledgment before trading resumes.

CRITICAL alerts automatically set the trading halt flag.  WARNING alerts do
not halt trading but are logged prominently.

Thread Safety
-------------
``PositionVerifier`` is designed to be called from multiple threads (the
NautilusTrader event loop plus the background reconciliation thread).  All
mutable state is protected by ``threading.Lock``.

Usage
-----
::

    from src.itm.engine import BinanceClient
    from src.itm.engine.position_verifier import (
        PositionVerifier, PositionVerifierConfig, MultiAlertChannel,
        LogAlertChannel, WebhookAlertChannel,
    )

    client = BinanceClient.from_env(use_testnet=True)

    verifier = PositionVerifier(
        binance_client=client,
        config=PositionVerifierConfig(
            close_verify_timeout_secs=30.0,
            reconcile_interval_secs=60.0,
        ),
        alert_channel=MultiAlertChannel([
            LogAlertChannel(),
            WebhookAlertChannel(url="https://hooks.example.com/itm-alerts"),
        ]),
    )

    # Start background reconciliation loop
    verifier.start()

    # After each close order fills, call:
    verifier.schedule_close_verification(symbol="BTCUSDT", client_order_id="abc123")

    # Check before allowing new positions:
    if verifier.is_halted:
        log.error("Trading halted — cannot enter new position")

    # Manual acknowledgment (operator console / admin endpoint):
    verifier.acknowledge_halt(operator_id="ops-alice")

    # On shutdown:
    verifier.stop()
"""

from __future__ import annotations

import abc
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Callable, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Alert severity + alert record
# ---------------------------------------------------------------------------


class AlertSeverity(str, Enum):
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class Alert:
    """Immutable alert record emitted by the verification system."""

    severity: AlertSeverity
    message: str
    symbol: str
    itm_position: Decimal
    exchange_position: Decimal
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    client_order_id: Optional[str] = None
    detail: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "message": self.message,
            "symbol": self.symbol,
            "itm_position": str(self.itm_position),
            "exchange_position": str(self.exchange_position),
            "timestamp": self.timestamp.isoformat(),
            "client_order_id": self.client_order_id,
            "detail": self.detail,
        }


# ---------------------------------------------------------------------------
# AlertChannel interface + implementations
# ---------------------------------------------------------------------------


class AlertChannel(abc.ABC):
    """Abstract alert delivery channel."""

    @abc.abstractmethod
    def send(self, alert: Alert) -> None:
        """Deliver the alert. Must not raise — log and absorb errors."""


class LogAlertChannel(AlertChannel):
    """Delivers alerts via Python logging at the appropriate log level.

    This channel is always active and does not require external configuration.
    CRITICAL alerts are logged at ``logging.CRITICAL``; WARNING at
    ``logging.WARNING``.
    """

    def send(self, alert: Alert) -> None:
        level = logging.CRITICAL if alert.severity == AlertSeverity.CRITICAL else logging.WARNING
        logger.log(
            level,
            "POSITION_ALERT [%s] %s — symbol=%s itm=%s exchange=%s coid=%s detail=%s",
            alert.severity.value,
            alert.message,
            alert.symbol,
            alert.itm_position,
            alert.exchange_position,
            alert.client_order_id or "–",
            alert.detail or "–",
        )


class WebhookAlertChannel(AlertChannel):
    """Delivers alerts via HTTP POST to a configurable webhook URL.

    The payload is the ``Alert.as_dict()`` JSON body.  If ``requests`` is not
    installed or the request fails, the error is logged and absorbed.

    Parameters
    ----------
    url:        Webhook endpoint URL.
    timeout:    HTTP request timeout in seconds.  Default 5.
    headers:    Extra HTTP headers (e.g. ``Authorization``).
    """

    def __init__(
        self,
        url: str,
        timeout: float = 5.0,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self._url = url
        self._timeout = timeout
        self._headers = headers or {}

    def send(self, alert: Alert) -> None:
        try:
            import json
            import urllib.request

            payload = json.dumps(alert.as_dict()).encode("utf-8")
            req = urllib.request.Request(
                self._url,
                data=payload,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    **self._headers,
                },
            )
            with urllib.request.urlopen(req, timeout=self._timeout):
                pass
            logger.debug("WebhookAlertChannel: alert delivered to %s", self._url)
        except Exception:
            logger.exception(
                "WebhookAlertChannel: failed to deliver alert to %s — alert NOT silenced, see LogAlertChannel",
                self._url,
            )


class FileAlertChannel(AlertChannel):
    """Appends JSON-serialised alert records to a file (one record per line).

    Parameters
    ----------
    path:   Path to the log file.  Parent directory must exist.
    """

    def __init__(self, path: str) -> None:
        self._path = path

    def send(self, alert: Alert) -> None:
        try:
            import json
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(alert.as_dict()) + "\n")
        except Exception:
            logger.exception(
                "FileAlertChannel: failed to write alert to %s", self._path
            )


class MultiAlertChannel(AlertChannel):
    """Fan-out alerts to multiple child channels.

    Each channel is called in order.  Failures in one channel do not prevent
    delivery to subsequent channels.
    """

    def __init__(self, channels: Sequence[AlertChannel]) -> None:
        self._channels = list(channels)

    def send(self, alert: Alert) -> None:
        for ch in self._channels:
            try:
                ch.send(alert)
            except Exception:
                logger.exception(
                    "MultiAlertChannel: channel %r raised unexpectedly", ch
                )


# ---------------------------------------------------------------------------
# PositionVerifierConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PositionVerifierConfig:
    """Configuration knobs for the position verification system.

    Parameters
    ----------
    close_verify_timeout_secs:
        How long (in seconds) to keep polling Binance after a close order
        fills, waiting for position size to reach zero.  Default 30 s.
    close_verify_poll_interval_secs:
        How often to poll during the close verification window.  Default 2 s.
    reconcile_interval_secs:
        How often the background reconciliation loop runs.  Default 60 s.
    mismatch_size_warning_threshold:
        A size difference below this threshold is a WARNING; at or above it
        is a CRITICAL halt-triggering alert.  Default 0.001 BTC.
    symbol:
        Futures symbol to verify.  Default ``"BTCUSDT"``.
    """

    close_verify_timeout_secs: float = 30.0
    close_verify_poll_interval_secs: float = 2.0
    reconcile_interval_secs: float = 60.0
    mismatch_size_warning_threshold: Decimal = Decimal("0.001")
    symbol: str = "BTCUSDT"

    def __post_init__(self) -> None:
        if self.close_verify_timeout_secs <= 0:
            raise ValueError("close_verify_timeout_secs must be positive")
        if self.close_verify_poll_interval_secs <= 0:
            raise ValueError("close_verify_poll_interval_secs must be positive")
        if self.reconcile_interval_secs <= 0:
            raise ValueError("reconcile_interval_secs must be positive")


# ---------------------------------------------------------------------------
# PositionVerifier
# ---------------------------------------------------------------------------


class PositionVerifier:
    """Exchange-side position safety layer for ITM.

    Parameters
    ----------
    binance_client:
        Authenticated ``BinanceClient`` used for REST position queries.
    internal_position_provider:
        Callable ``(symbol: str) → Decimal`` returning ITM's current internal
        position size for the given symbol.  The value must be absolute (≥ 0).
        If not provided, ``Decimal("0")`` is assumed for all reconciliation
        checks (useful when ITM position state is always authoritative and you
        only want exchange-side close verification).
    config:
        ``PositionVerifierConfig`` instance.
    alert_channel:
        Where to send alerts.  Defaults to ``LogAlertChannel``.
    clock:
        Callable returning current Unix time in seconds.  Injectable for
        testing.  Default ``time.monotonic``.
    """

    def __init__(
        self,
        binance_client,
        internal_position_provider: Optional[Callable[[str], Decimal]] = None,
        config: Optional[PositionVerifierConfig] = None,
        alert_channel: Optional[AlertChannel] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self._client = binance_client
        self._pos_provider = internal_position_provider
        self._config = config or PositionVerifierConfig()
        self._alert_channel: AlertChannel = alert_channel or LogAlertChannel()
        self._clock = clock or time.monotonic

        self._lock = threading.Lock()
        self._halted: bool = False
        self._halt_reason: Optional[str] = None
        self._halt_ts: Optional[datetime] = None

        self._reconcile_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Background close-verify threads keyed by client_order_id
        self._verify_threads: Dict[str, threading.Thread] = {}

        logger.info(
            "PositionVerifier initialised: symbol=%s close_verify_timeout=%ss reconcile_interval=%ss",
            self._config.symbol,
            self._config.close_verify_timeout_secs,
            self._config.reconcile_interval_secs,
        )

    # ------------------------------------------------------------------ #
    # Halt flag public API                                                 #
    # ------------------------------------------------------------------ #

    @property
    def is_halted(self) -> bool:
        """True if trading is halted due to a CRITICAL position mismatch."""
        with self._lock:
            return self._halted

    def acknowledge_halt(self, operator_id: str = "operator") -> None:
        """Manually clear the trading halt.

        Parameters
        ----------
        operator_id:
            Identifier of the operator clearing the halt (logged for audit).
        """
        with self._lock:
            if not self._halted:
                logger.info(
                    "PositionVerifier acknowledge_halt: no active halt — nothing to clear"
                )
                return
            prev_reason = self._halt_reason
            self._halted = False
            self._halt_reason = None
            self._halt_ts = None

        logger.warning(
            "PositionVerifier HALT_CLEARED by operator=%r (was: %s)",
            operator_id,
            prev_reason,
        )

    def _trigger_halt(self, reason: str) -> None:
        """Set the trading halt flag (internal use only)."""
        with self._lock:
            if self._halted:
                return  # already halted, avoid duplicate log spam
            self._halted = True
            self._halt_reason = reason
            self._halt_ts = datetime.now(timezone.utc)

        logger.critical(
            "PositionVerifier TRADING_HALTED: reason=%s — call acknowledge_halt() to resume",
            reason,
        )

    # ------------------------------------------------------------------ #
    # Close verification                                                   #
    # ------------------------------------------------------------------ #

    def schedule_close_verification(
        self,
        client_order_id: str,
        symbol: Optional[str] = None,
    ) -> None:
        """Schedule a background thread to verify a close order fully settled.

        Call this from the execution engine's post-fill callback immediately
        after a close order reaches FILLED state.

        Parameters
        ----------
        client_order_id:
            The ``clientOrderId`` of the close order (for logging).
        symbol:
            Futures symbol.  Defaults to ``config.symbol``.
        """
        sym = symbol or self._config.symbol
        thread = threading.Thread(
            target=self._close_verify_loop,
            args=(client_order_id, sym),
            daemon=True,
            name=f"close-verify-{client_order_id[:12]}",
        )
        with self._lock:
            self._verify_threads[client_order_id] = thread
        thread.start()
        logger.info(
            "PositionVerifier: close verification scheduled for coid=%r symbol=%s",
            client_order_id, sym,
        )

    def _close_verify_loop(self, client_order_id: str, symbol: str) -> None:
        """Poll Binance position until zero or timeout, then alert if needed."""
        deadline = self._clock() + self._config.close_verify_timeout_secs
        poll_interval = self._config.close_verify_poll_interval_secs

        logger.info(
            "PositionVerifier close_verify start: coid=%r symbol=%s timeout=%ss",
            client_order_id, symbol, self._config.close_verify_timeout_secs,
        )

        while self._clock() < deadline:
            try:
                exchange_size = self._client.get_position_size(symbol)
            except Exception:
                logger.exception(
                    "PositionVerifier close_verify: error querying Binance for coid=%r — will retry",
                    client_order_id,
                )
                time.sleep(poll_interval)
                continue

            if exchange_size == Decimal("0"):
                logger.info(
                    "PositionVerifier close_verify PASS: coid=%r symbol=%s position=0 ✓",
                    client_order_id, symbol,
                )
                with self._lock:
                    self._verify_threads.pop(client_order_id, None)
                return

            logger.debug(
                "PositionVerifier close_verify polling: coid=%r symbol=%s exchange_size=%s",
                client_order_id, symbol, exchange_size,
            )
            time.sleep(poll_interval)

        # Timeout expired — position still open
        try:
            exchange_size = self._client.get_position_size(symbol)
        except Exception:
            logger.exception(
                "PositionVerifier close_verify TIMEOUT: final position query failed for coid=%r",
                client_order_id,
            )
            exchange_size = Decimal("-1")  # sentinel: unknown

        alert = Alert(
            severity=AlertSeverity.CRITICAL,
            message=(
                f"Close verification FAILED: position not zero after "
                f"{self._config.close_verify_timeout_secs}s — TRADING HALTED"
            ),
            symbol=symbol,
            itm_position=Decimal("0"),  # we expected zero
            exchange_position=exchange_size,
            client_order_id=client_order_id,
            detail=(
                f"coid={client_order_id!r} exchange_size={exchange_size} "
                f"timeout={self._config.close_verify_timeout_secs}s"
            ),
        )
        self._alert_channel.send(alert)
        self._trigger_halt(
            f"close_verify_timeout coid={client_order_id!r} size={exchange_size}"
        )

        with self._lock:
            self._verify_threads.pop(client_order_id, None)

    # ------------------------------------------------------------------ #
    # Reconciliation                                                       #
    # ------------------------------------------------------------------ #

    def reconcile_once(self) -> bool:
        """Run a single reconciliation pass synchronously.

        Compares ITM internal position vs Binance REST.  Fires appropriate
        alerts and triggers halt on CRITICAL divergence.

        Returns
        -------
        bool
            True if positions match (or mismatch is below WARNING threshold),
            False if a CRITICAL mismatch was detected.
        """
        symbol = self._config.symbol

        # Query Binance REST (authoritative)
        try:
            exchange_size = self._client.get_position_size(symbol)
        except Exception:
            logger.exception(
                "PositionVerifier reconcile_once: failed to query Binance — skipping reconciliation pass"
            )
            return True  # conservative: don't false-positive on query failure

        # Query ITM internal state
        if self._pos_provider is not None:
            try:
                itm_size = abs(self._pos_provider(symbol))
            except Exception:
                logger.exception(
                    "PositionVerifier reconcile_once: internal_position_provider raised — skipping"
                )
                return True
        else:
            itm_size = Decimal("0")

        diff = abs(itm_size - exchange_size)
        logger.debug(
            "PositionVerifier reconcile_once: symbol=%s itm=%s exchange=%s diff=%s",
            symbol, itm_size, exchange_size, diff,
        )

        if diff == Decimal("0"):
            logger.info(
                "PositionVerifier reconcile_once MATCH: symbol=%s size=%s ✓",
                symbol, exchange_size,
            )
            return True

        # Determine severity: open vs closed divergence is always CRITICAL;
        # size mismatch below threshold is WARNING.
        open_closed_mismatch = (itm_size == Decimal("0") and exchange_size > Decimal("0")) or (
            itm_size > Decimal("0") and exchange_size == Decimal("0")
        )
        is_critical = open_closed_mismatch or diff >= self._config.mismatch_size_warning_threshold

        if is_critical:
            severity = AlertSeverity.CRITICAL
            msg = (
                f"Position state DIVERGENCE: ITM={'open' if itm_size > 0 else 'closed'} "
                f"({itm_size} BTC) vs Binance={'open' if exchange_size > 0 else 'closed'} "
                f"({exchange_size} BTC) — TRADING HALTED"
            )
        else:
            severity = AlertSeverity.WARNING
            msg = (
                f"Position size discrepancy: ITM={itm_size} BTC vs Binance={exchange_size} BTC "
                f"(diff={diff} BTC, below halt threshold)"
            )

        alert = Alert(
            severity=severity,
            message=msg,
            symbol=symbol,
            itm_position=itm_size,
            exchange_position=exchange_size,
            detail=f"diff={diff}",
        )
        self._alert_channel.send(alert)

        if is_critical:
            self._trigger_halt(f"reconciliation_mismatch itm={itm_size} exchange={exchange_size}")
            return False

        return True  # WARNING-only: trading not halted

    # ------------------------------------------------------------------ #
    # Background reconciliation thread                                     #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """Start the background reconciliation loop.

        Also runs an immediate reconciliation pass on startup.
        """
        if self._reconcile_thread and self._reconcile_thread.is_alive():
            logger.warning("PositionVerifier.start(): reconciliation thread already running")
            return

        self._stop_event.clear()

        # Startup reconciliation (synchronous, before thread starts)
        logger.info("PositionVerifier: running startup reconciliation pass")
        self.reconcile_once()

        self._reconcile_thread = threading.Thread(
            target=self._reconcile_loop,
            daemon=True,
            name="position-reconciliation",
        )
        self._reconcile_thread.start()
        logger.info(
            "PositionVerifier: background reconciliation thread started (interval=%ss)",
            self._config.reconcile_interval_secs,
        )

    def stop(self) -> None:
        """Signal the reconciliation thread to stop and wait for it to exit."""
        self._stop_event.set()
        if self._reconcile_thread:
            self._reconcile_thread.join(timeout=10.0)
            self._reconcile_thread = None
        logger.info("PositionVerifier: stopped")

    def _reconcile_loop(self) -> None:
        """Background daemon thread: reconcile every ``reconcile_interval_secs``."""
        while not self._stop_event.wait(timeout=self._config.reconcile_interval_secs):
            logger.debug("PositionVerifier: reconciliation tick")
            try:
                self.reconcile_once()
            except Exception:
                logger.exception("PositionVerifier: reconcile_once raised unexpectedly")
        logger.info("PositionVerifier: reconciliation thread exiting")

    # ------------------------------------------------------------------ #
    # Diagnostics                                                          #
    # ------------------------------------------------------------------ #

    def status(self) -> dict:
        """Return a snapshot of verifier state for health-check endpoints."""
        with self._lock:
            return {
                "halted": self._halted,
                "halt_reason": self._halt_reason,
                "halt_ts": self._halt_ts.isoformat() if self._halt_ts else None,
                "symbol": self._config.symbol,
                "reconcile_interval_secs": self._config.reconcile_interval_secs,
                "close_verify_timeout_secs": self._config.close_verify_timeout_secs,
                "active_close_verifications": list(self._verify_threads.keys()),
            }

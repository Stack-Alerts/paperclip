"""
ITM Recovery Protocol
=====================
Implements the startup recovery sequence for restoring ITM state after a
process restart or crash.

API (from integration spec)
----------------------------
::

    fetcher = MockBinancePositionFetcher([
        ExchangePosition(symbol="BTCUSDT", direction=PositionDirection.LONG,
                         quantity=Decimal("0.25"), entry_price=Decimal("58000"))
    ])
    protocol = RecoveryProtocol(fetcher, config=RecoveryConfig(max_recovery_age_hours=24))
    result = protocol.run(manager)
    # result.is_clean_start, result.has_divergence, result.orders_blocked
    # result.recovery_duration_ms, result.state

Recovery sequence
-----------------
1. Call ``manager.load_latest()`` to get the most recent checkpoint.
2. If no checkpoint found → ``is_clean_start = True``.
3. If checkpoint is too stale (older than ``max_recovery_age_hours``) →
   treat as clean start.
4. Call ``fetcher.get_positions()`` to get live exchange positions.
5. Diff ITM positions vs exchange positions.
6. If divergence detected → ``has_divergence = True``, log CRITICAL, set
   ``orders_blocked = True``.
7. Return ``RecoveryResult``.

Binance reconciliation types
-----------------------------
* ``itm_open_exchange_closed`` — ITM has open position, exchange disagrees.
* ``exchange_open_itm_missing`` — Exchange has position ITM has no record of.
* ``quantity_mismatch`` — Both know about it but quantities differ.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List

from .schema import ITMSystemState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RecoveryError(Exception):
    """Raised when recovery cannot complete to a usable state."""


# ---------------------------------------------------------------------------
# ExchangePosition
# ---------------------------------------------------------------------------


@dataclass
class ExchangePosition:
    """A position reported by the exchange (Binance) during reconciliation.

    Attributes
    ----------
    symbol:        trading pair symbol, e.g. 'BTCUSDT' or 'BTC/USDT'
    direction:     LONG or SHORT
    quantity:      absolute open quantity in BTC
    entry_price:   average entry price (informational)
    """

    symbol: str
    direction: object  # PositionDirection enum — imported lazily
    quantity: Decimal
    entry_price: Decimal = field(default_factory=lambda: Decimal("0"))

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("ExchangePosition.symbol must not be empty")
        if self.quantity < Decimal("0"):
            raise ValueError("ExchangePosition.quantity cannot be negative")


# ---------------------------------------------------------------------------
# MockBinancePositionFetcher
# ---------------------------------------------------------------------------


class MockBinancePositionFetcher:
    """In-memory Binance position fetcher for testing and paper-trading.

    Returns a fixed set of ``ExchangePosition`` objects.
    """

    def __init__(self, positions: Optional[List[ExchangePosition]] = None) -> None:
        self._positions: List[ExchangePosition] = list(positions or [])

    def get_positions(self) -> List[ExchangePosition]:
        """Return the configured list of exchange positions."""
        return list(self._positions)

    # Also support the dict-based protocol used by BinancePositionProvider
    def get_open_positions(self) -> dict[str, Decimal]:
        """Return {symbol: qty} compatible with BinancePositionProvider protocol."""
        result: dict[str, Decimal] = {}
        for ep in self._positions:
            # Normalise symbol (BTCUSDT → BTC/USDT for matching)
            sym = _normalise_symbol(ep.symbol)
            result[sym] = result.get(sym, Decimal("0")) + ep.quantity
        return result


# ---------------------------------------------------------------------------
# DivergenceAlert
# ---------------------------------------------------------------------------


@dataclass
class DivergenceAlert:
    """Describes a single discrepancy between ITM state and exchange state."""

    alert_type: str
    symbol: str
    itm_quantity: Optional[Decimal] = None
    exchange_quantity: Optional[Decimal] = None
    position_id: Optional[str] = None
    message: str = ""
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    _VALID_TYPES = frozenset({
        "itm_open_exchange_closed",
        "exchange_open_itm_missing",
        "quantity_mismatch",
    })

    def __post_init__(self) -> None:
        if self.alert_type not in self._VALID_TYPES:
            raise ValueError(
                f"DivergenceAlert.alert_type must be one of {sorted(self._VALID_TYPES)}, "
                f"got {self.alert_type!r}"
            )


# ---------------------------------------------------------------------------
# RecoveryConfig
# ---------------------------------------------------------------------------


@dataclass
class RecoveryConfig:
    """Configuration for the RecoveryProtocol.

    Parameters
    ----------
    max_recovery_age_hours:
        Maximum age (in hours) of a recovered checkpoint before it is considered
        too stale.  Defaults to 24.
    """

    max_recovery_age_hours: float = 24.0

    @property
    def max_age_seconds(self) -> float:
        return self.max_recovery_age_hours * 3600.0


# ---------------------------------------------------------------------------
# RecoveryResult
# ---------------------------------------------------------------------------


@dataclass
class RecoveryResult:
    """Outcome of a recovery attempt.

    Attributes
    ----------
    is_clean_start:       True if no persisted state was found
    has_divergence:       True if position mismatch was detected vs exchange
    orders_blocked:       True if divergence caused trading to be blocked
    recovery_duration_ms: Total recovery time in milliseconds
    state:                The recovered ``ITMSystemState``
    divergences:          List of ``DivergenceAlert`` objects
    loaded_from:          'redis', 'postgres', or 'clean'
    error_message:        Set on failure (non-fatal)
    """

    is_clean_start: bool = True
    has_divergence: bool = False
    orders_blocked: bool = False
    recovery_duration_ms: float = 0.0
    state: ITMSystemState = field(default_factory=ITMSystemState)
    divergences: List[DivergenceAlert] = field(default_factory=list)
    loaded_from: str = "clean"
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# RecoveryProtocol
# ---------------------------------------------------------------------------


class RecoveryProtocol:
    """Implements the ITM startup recovery and reconciliation sequence.

    Parameters
    ----------
    fetcher:
        An object with a ``get_positions()`` method returning
        ``List[ExchangePosition]``.  Pass ``MockBinancePositionFetcher``
        for testing or ``None`` to skip reconciliation.
    config:
        ``RecoveryConfig`` controlling stale-state thresholds.
    """

    def __init__(
        self,
        fetcher=None,
        config: Optional[RecoveryConfig] = None,
    ) -> None:
        self._fetcher = fetcher
        self._config = config or RecoveryConfig()

    def run(self, manager) -> RecoveryResult:
        """Execute recovery using *manager*.load_latest() + reconciliation.

        Parameters
        ----------
        manager:
            A ``StateManager`` instance (already connected).

        Returns
        -------
        RecoveryResult
        """
        t0 = time.monotonic()
        logger.info("Recovery: starting recovery sequence")

        # Load latest checkpoint
        cp = None
        try:
            cp = manager.load_latest()
        except Exception as exc:  # noqa: BLE001
            logger.error("Recovery: load_latest failed: %s", exc)

        if cp is None:
            logger.info("Recovery: no checkpoint found — clean start")
            elapsed_ms = (time.monotonic() - t0) * 1000
            return RecoveryResult(
                is_clean_start=True,
                state=ITMSystemState(),
                recovery_duration_ms=elapsed_ms,
                loaded_from="clean",
            )

        # Check age
        age_seconds = _checkpoint_age_seconds(cp)
        if age_seconds > self._config.max_age_seconds:
            logger.warning(
                "Recovery: checkpoint seq=%d is %.0fh old (max=%.0fh) — clean start",
                cp.sequence,
                age_seconds / 3600,
                self._config.max_recovery_age_hours,
            )
            elapsed_ms = (time.monotonic() - t0) * 1000
            return RecoveryResult(
                is_clean_start=True,
                state=ITMSystemState(),
                recovery_duration_ms=elapsed_ms,
                loaded_from="clean",
            )

        # Determine source: use the load_source attribute if set, else infer
        loaded_from = getattr(cp, "_load_source", None)
        if loaded_from is None:
            # Fallback: use the manager's last load source
            loaded_from = getattr(manager, "_last_load_source", "redis")
        logger.info(
            "Recovery: loaded checkpoint seq=%d (age=%.0fs, from=%s)",
            cp.sequence,
            age_seconds,
            loaded_from,
        )

        state = cp.state
        divergences: list[DivergenceAlert] = []
        has_divergence = False
        orders_blocked = False

        # Reconcile with exchange
        if self._fetcher is not None:
            try:
                exchange_positions = self._fetcher.get_positions()
                divergences = _reconcile(state, exchange_positions)
                if divergences:
                    has_divergence = True
                    orders_blocked = True
                    for alert in divergences:
                        logger.critical(
                            "DIVERGENCE [%s] symbol=%s itm_qty=%s exchange_qty=%s: %s",
                            alert.alert_type,
                            alert.symbol,
                            alert.itm_quantity,
                            alert.exchange_quantity,
                            alert.message,
                        )
            except Exception as exc:  # noqa: BLE001
                logger.error("Recovery: reconciliation failed: %s", exc)

        elapsed_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "Recovery: complete in %.0fms, divergences=%d, clean_start=False",
            elapsed_ms,
            len(divergences),
        )

        return RecoveryResult(
            is_clean_start=False,
            has_divergence=has_divergence,
            orders_blocked=orders_blocked,
            recovery_duration_ms=elapsed_ms,
            state=state,
            divergences=divergences,
            loaded_from=loaded_from,
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _normalise_symbol(sym: str) -> str:
    """Normalise 'BTCUSDT' → 'BTC/USDT' for comparison."""
    if "/" not in sym:
        # Try common pairs
        for quote in ("USDT", "BUSD", "BTC", "ETH", "BNB"):
            if sym.endswith(quote):
                base = sym[: -len(quote)]
                return f"{base}/{quote}"
    return sym


def _checkpoint_age_seconds(cp) -> float:
    """Return the age of a checkpoint in seconds."""
    ts = cp.checkpointed_at
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds()


def _reconcile(state: ITMSystemState, exchange_positions: list) -> list[DivergenceAlert]:
    """Compare ITM open positions against exchange positions."""
    alerts: list[DivergenceAlert] = []

    # Build symbol → total_qty map from exchange
    exchange_map: dict[str, Decimal] = {}
    for ep in exchange_positions:
        sym = _normalise_symbol(ep.symbol)
        exchange_map[sym] = exchange_map.get(sym, Decimal("0")) + ep.quantity

    # Build ITM symbol → (position_id, qty) map
    itm_open: dict[str, list[tuple[str, Decimal]]] = {}
    for pos in state.open_positions():
        sym = pos.instrument.symbol
        itm_open.setdefault(sym, []).append((pos.position_id, pos.open_quantity))

    # Check ITM open vs exchange
    for sym, entries in itm_open.items():
        exchange_qty = exchange_map.get(sym, Decimal("0"))
        itm_qty = sum(qty for _, qty in entries)
        if exchange_qty == Decimal("0"):
            alerts.append(DivergenceAlert(
                alert_type="itm_open_exchange_closed",
                symbol=sym,
                itm_quantity=itm_qty,
                exchange_quantity=Decimal("0"),
                position_id=entries[0][0] if len(entries) == 1 else None,
                message=f"ITM has open qty {itm_qty} for {sym} but exchange reports no open position",
            ))
        elif abs(exchange_qty - itm_qty) > Decimal("0.00001"):
            alerts.append(DivergenceAlert(
                alert_type="quantity_mismatch",
                symbol=sym,
                itm_quantity=itm_qty,
                exchange_quantity=exchange_qty,
                position_id=entries[0][0] if len(entries) == 1 else None,
                message=f"Qty mismatch for {sym}: ITM={itm_qty} exchange={exchange_qty}",
            ))

    # Check exchange open vs ITM
    itm_symbols = set(itm_open.keys())
    for sym, qty in exchange_map.items():
        if qty > Decimal("0") and sym not in itm_symbols:
            alerts.append(DivergenceAlert(
                alert_type="exchange_open_itm_missing",
                symbol=sym,
                itm_quantity=None,
                exchange_quantity=qty,
                message=f"Exchange reports open qty {qty} for {sym} but ITM has no record",
            ))

    return alerts

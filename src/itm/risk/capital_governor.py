"""
ITM Section F — Capital Governor
==================================
Manages the capital governance model using a Fixed-Notional approach.

Responsibilities
----------------
* Track total capital and per-strategy open exposure.
* Compute account heat: (open_exposure / max_allowed_exposure) × 100.
* Enforce heat-level thresholds: GREEN (<50%), YELLOW (50–80%), RED (>80%).
* Reject new orders when capital limits or RED heat are breached.
* Emit heat-level transitions for alerting.

Capital model
--------------
  base_capital           = configurable USDT total (default 25,000)
  max_position_pct       = max fraction of capital per single trade
  max_exposure_pct       = max fraction of capital in open positions at once
  open_exposure          = sum of notional values of all open positions
  heat                   = (open_exposure / max_exposure) × 100

Heat levels
-----------
  GREEN   < 50%   — normal operation
  YELLOW  50–80%  — alert; new position sizes reduced by 50%
  RED     > 80%   — no new positions; alert board

Thread safety
-------------
All mutations are protected by an RLock.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_BASE_CAPITAL = Decimal("25000.00")     # USDT
DEFAULT_MAX_POSITION_PCT = Decimal("0.10")     # 10% of capital per trade
DEFAULT_MAX_EXPOSURE_PCT = Decimal("0.40")     # 40% of capital max open exposure

HEAT_YELLOW_THRESHOLD = Decimal("50")  # %
HEAT_RED_THRESHOLD = Decimal("80")     # %


# ---------------------------------------------------------------------------
# HeatLevel
# ---------------------------------------------------------------------------

class HeatLevel(str, Enum):
    """Account heat level."""
    GREEN = "green"    # < 50%
    YELLOW = "yellow"  # 50–80%
    RED = "red"        # > 80%


# ---------------------------------------------------------------------------
# CapitalGovernorConfig
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CapitalGovernorConfig:
    """Configuration for the CapitalGovernor.

    Parameters
    ----------
    base_capital:
        Total USDT capital under management (default 25,000).
    max_position_pct:
        Maximum fraction of base_capital allowed per single trade (default 0.10).
    max_exposure_pct:
        Maximum fraction of base_capital allowed in open positions at once
        (default 0.40).
    """
    base_capital: Decimal = DEFAULT_BASE_CAPITAL
    max_position_pct: Decimal = DEFAULT_MAX_POSITION_PCT
    max_exposure_pct: Decimal = DEFAULT_MAX_EXPOSURE_PCT

    def __post_init__(self) -> None:
        if self.base_capital <= Decimal("0"):
            raise ValueError(
                f"CapitalGovernorConfig.base_capital must be positive, "
                f"got {self.base_capital}"
            )
        if not (Decimal("0") < self.max_position_pct <= Decimal("1")):
            raise ValueError(
                f"CapitalGovernorConfig.max_position_pct must be in (0, 1], "
                f"got {self.max_position_pct}"
            )
        if not (Decimal("0") < self.max_exposure_pct <= Decimal("1")):
            raise ValueError(
                f"CapitalGovernorConfig.max_exposure_pct must be in (0, 1], "
                f"got {self.max_exposure_pct}"
            )

    @property
    def max_position_notional(self) -> Decimal:
        """Absolute USDT cap per position."""
        return self.base_capital * self.max_position_pct

    @property
    def max_exposure_notional(self) -> Decimal:
        """Absolute USDT cap for total open exposure."""
        return self.base_capital * self.max_exposure_pct


# ---------------------------------------------------------------------------
# CapitalGovernorSnapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CapitalGovernorSnapshot:
    """Point-in-time snapshot of capital governor state."""
    base_capital: Decimal
    open_exposure: Decimal
    max_exposure_notional: Decimal
    heat_pct: Decimal
    heat_level: HeatLevel
    per_strategy_exposure: dict
    timestamp: datetime


# ---------------------------------------------------------------------------
# CapitalGovernor
# ---------------------------------------------------------------------------

class CapitalGovernorError(Exception):
    """Raised when a capital governance constraint is violated."""


class CapitalGovernor:
    """Fixed-Notional capital governance engine.

    Parameters
    ----------
    config:
        ``CapitalGovernorConfig`` instance.
    on_heat_transition:
        Optional callback called whenever the heat level changes.
        Signature: ``(old_level: HeatLevel, new_level: HeatLevel) → None``.
    """

    def __init__(
        self,
        config: Optional[CapitalGovernorConfig] = None,
        on_heat_transition: Optional[Callable[[HeatLevel, HeatLevel], None]] = None,
    ) -> None:
        self._config = config or CapitalGovernorConfig()
        self._lock = threading.RLock()
        self._on_heat_transition = on_heat_transition

        # Per-strategy open exposure (strategy_id → USDT notional)
        self._exposure: dict[str, Decimal] = {}
        self._heat_level: HeatLevel = HeatLevel.GREEN

        logger.info(
            "CapitalGovernor initialised: base_capital=%s, max_position_pct=%s, "
            "max_exposure_pct=%s",
            self._config.base_capital,
            self._config.max_position_pct,
            self._config.max_exposure_pct,
        )

    # ------------------------------------------------------------------ #
    # Capital base management                                              #
    # ------------------------------------------------------------------ #

    def update_base_capital(self, new_capital: Decimal) -> None:
        """Update the base capital (e.g. after deposit/withdrawal).

        Parameters
        ----------
        new_capital:
            New total capital in USDT.
        """
        if new_capital <= Decimal("0"):
            raise CapitalGovernorError(
                f"New base capital must be positive, got {new_capital}"
            )
        with self._lock:
            old = self._config.base_capital
            # Config is frozen; replace with new instance
            self._config = CapitalGovernorConfig(
                base_capital=new_capital,
                max_position_pct=self._config.max_position_pct,
                max_exposure_pct=self._config.max_exposure_pct,
            )
            logger.info(
                "CapitalGovernor: base_capital updated %s → %s",
                old, new_capital,
            )
            self._recompute_heat()

    # ------------------------------------------------------------------ #
    # Exposure tracking                                                    #
    # ------------------------------------------------------------------ #

    def open_position(self, strategy_id: str, notional: Decimal) -> None:
        """Record that a strategy has opened a position of *notional* USDT.

        Raises ``CapitalGovernorError`` if the position exceeds the per-trade
        cap or would push total exposure past the max-exposure limit.

        Parameters
        ----------
        strategy_id:
            Owning strategy identifier.
        notional:
            USDT notional value of the position being opened.
        """
        if notional <= Decimal("0"):
            raise CapitalGovernorError(
                f"Position notional must be positive, got {notional}"
            )
        with self._lock:
            # 1. Per-position cap
            max_pos = self._config.max_position_notional
            if notional > max_pos:
                raise CapitalGovernorError(
                    f"Position notional {notional} USDT exceeds per-position cap "
                    f"{max_pos} USDT (={self._config.max_position_pct * 100}% of capital)"
                )

            # 2. Total exposure cap — RED heat blocks new positions
            if self._heat_level == HeatLevel.RED:
                raise CapitalGovernorError(
                    f"New position blocked: account heat is RED "
                    f"(open_exposure={self.open_exposure} / "
                    f"max={self._config.max_exposure_notional})"
                )

            new_exposure = self.open_exposure + notional
            max_exp = self._config.max_exposure_notional
            if new_exposure > max_exp:
                raise CapitalGovernorError(
                    f"Opening position of {notional} USDT for strategy {strategy_id!r} "
                    f"would push total exposure to {new_exposure} USDT, "
                    f"exceeding max allowed {max_exp} USDT"
                )

            self._exposure[strategy_id] = (
                self._exposure.get(strategy_id, Decimal("0")) + notional
            )
            logger.info(
                "CapitalGovernor: position opened strategy=%r notional=%s "
                "total_exposure=%s",
                strategy_id, notional, self.open_exposure,
            )
            self._recompute_heat()

    def close_position(self, strategy_id: str, notional: Decimal) -> None:
        """Record that a strategy has closed *notional* USDT of exposure.

        Parameters
        ----------
        strategy_id:
            Owning strategy identifier.
        notional:
            USDT notional value being released.  Clamped to current exposure
            (never goes negative).
        """
        with self._lock:
            current = self._exposure.get(strategy_id, Decimal("0"))
            released = min(notional, current)
            self._exposure[strategy_id] = max(Decimal("0"), current - released)
            logger.info(
                "CapitalGovernor: position closed strategy=%r released=%s "
                "total_exposure=%s",
                strategy_id, released, self.open_exposure,
            )
            self._recompute_heat()

    def close_all_for_strategy(self, strategy_id: str) -> Decimal:
        """Release all exposure for *strategy_id*.

        Returns
        -------
        Decimal
            The amount of USDT exposure released.
        """
        with self._lock:
            released = self._exposure.pop(strategy_id, Decimal("0"))
            logger.info(
                "CapitalGovernor: all positions closed strategy=%r released=%s",
                strategy_id, released,
            )
            self._recompute_heat()
            return released

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    @property
    def open_exposure(self) -> Decimal:
        """Total USDT notional in open positions across all strategies."""
        return sum(self._exposure.values(), Decimal("0"))

    @property
    def heat_pct(self) -> Decimal:
        """Current heat as a percentage (0–100+)."""
        max_exp = self._config.max_exposure_notional
        if max_exp == Decimal("0"):
            return Decimal("0")
        return (self.open_exposure / max_exp) * Decimal("100")

    @property
    def heat_level(self) -> HeatLevel:
        """Current heat level (GREEN / YELLOW / RED)."""
        with self._lock:
            return self._heat_level

    def can_open_position(self, strategy_id: str, notional: Decimal) -> bool:
        """Return True if *notional* can be opened without violating limits.

        Does not actually open the position — use ``open_position`` for that.
        """
        with self._lock:
            if notional <= Decimal("0"):
                return False
            if notional > self._config.max_position_notional:
                return False
            if self._heat_level == HeatLevel.RED:
                return False
            new_exposure = self.open_exposure + notional
            return new_exposure <= self._config.max_exposure_notional

    def adjusted_notional(self, requested_notional: Decimal) -> Decimal:
        """Return the heat-adjusted notional for a new position.

        - GREEN:  full requested notional (capped at per-position limit).
        - YELLOW: 50% reduction (capped at per-position limit).
        - RED:    always returns 0 (no new positions).
        """
        with self._lock:
            cap = self._config.max_position_notional
            if self._heat_level == HeatLevel.RED:
                return Decimal("0")
            if self._heat_level == HeatLevel.YELLOW:
                adjusted = requested_notional * Decimal("0.5")
                return min(adjusted, cap)
            return min(requested_notional, cap)

    def get_strategy_exposure(self, strategy_id: str) -> Decimal:
        """Return current open exposure for *strategy_id* in USDT."""
        with self._lock:
            return self._exposure.get(strategy_id, Decimal("0"))

    def snapshot(self) -> CapitalGovernorSnapshot:
        """Return an immutable point-in-time snapshot of governor state."""
        with self._lock:
            return CapitalGovernorSnapshot(
                base_capital=self._config.base_capital,
                open_exposure=self.open_exposure,
                max_exposure_notional=self._config.max_exposure_notional,
                heat_pct=self.heat_pct,
                heat_level=self._heat_level,
                per_strategy_exposure=dict(self._exposure),
                timestamp=datetime.now(timezone.utc),
            )

    @property
    def config(self) -> CapitalGovernorConfig:
        """Current governor configuration."""
        return self._config

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _recompute_heat(self) -> None:
        """Recompute heat level from current exposure; fires callback on change."""
        pct = self.heat_pct
        if pct >= HEAT_RED_THRESHOLD:
            new_level = HeatLevel.RED
        elif pct >= HEAT_YELLOW_THRESHOLD:
            new_level = HeatLevel.YELLOW
        else:
            new_level = HeatLevel.GREEN

        old_level = self._heat_level
        self._heat_level = new_level

        if new_level != old_level:
            logger.warning(
                "CapitalGovernor: heat level changed %s → %s (heat=%.1f%%)",
                old_level.value, new_level.value, float(pct),
            )
            if self._on_heat_transition is not None:
                try:
                    self._on_heat_transition(old_level, new_level)
                except Exception:
                    logger.exception(
                        "on_heat_transition callback raised an exception"
                    )

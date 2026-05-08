"""
ITM Section F — Position Sizer
================================
Computes order quantity for a new trade given the capital available, the
desired risk fraction, and the ATR-based stop-loss distance.

Two sizing modes
-----------------
1. **Fixed-Fraction** (default): risk a fixed % of capital per trade.
2. **Kelly**: use the Kelly Criterion with a win-rate and win/loss ratio.

Both modes produce a quantity (BTC) that never exceeds the hard institutional
cap (1.0 BTC) and never falls below the minimum (0.001 BTC).

ATR stop-loss
--------------
When ``atr`` (Average True Range, expressed in USDT per BTC) is provided:
    stop_distance = atr × stop_atr_multiplier
    quantity      = (capital × risk_fraction) / stop_distance

If ATR is not provided, the caller must supply a ``stop_distance_usdt``
directly (e.g. 2% of entry price).

Result
------
``PositionSizeResult`` carries:
  * ``quantity``      — BTC to trade
  * ``stop_distance`` — USDT distance from entry to stop-loss
  * ``notional``      — estimated USDT notional (quantity × entry_price)
  * ``sizing_mode``   — which algorithm was used
  * ``risk_amount``   — USDT risked (= quantity × stop_distance)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (institutional hard limits — must match AGENTS.md)
# ---------------------------------------------------------------------------

MAX_QUANTITY = Decimal("1.0")      # 1.0 BTC hard cap
MIN_QUANTITY = Decimal("0.001")    # minimum lot size
DEFAULT_RISK_FRACTION = Decimal("0.01")    # 1% of capital per trade
DEFAULT_ATR_MULTIPLIER = Decimal("1.5")    # stop = 1.5× ATR
DEFAULT_KELLY_FRACTION = Decimal("0.25")   # fractional Kelly (25% full Kelly)
DEFAULT_STOP_PCT = Decimal("0.02")          # 2% price-based stop


# ---------------------------------------------------------------------------
# SizingMode
# ---------------------------------------------------------------------------

class SizingMode(str, Enum):
    FIXED_FRACTION = "fixed_fraction"
    KELLY = "kelly"


# ---------------------------------------------------------------------------
# PositionSizeResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PositionSizeResult:
    """Result of a position-sizing calculation.

    Attributes
    ----------
    quantity:       BTC quantity to trade (≥ MIN_QUANTITY, ≤ MAX_QUANTITY)
    stop_distance:  USDT distance from entry price to stop-loss
    notional:       approximate USDT notional (quantity × entry_price)
    risk_amount:    USDT at risk (quantity × stop_distance)
    sizing_mode:    algorithm used
    capped:         True if the result was clipped to MAX_QUANTITY
    """
    quantity: Decimal
    stop_distance: Decimal
    notional: Decimal
    risk_amount: Decimal
    sizing_mode: SizingMode
    capped: bool = False

    def __post_init__(self) -> None:
        if self.quantity < Decimal("0"):
            raise ValueError("PositionSizeResult.quantity cannot be negative")
        if self.stop_distance <= Decimal("0"):
            raise ValueError("PositionSizeResult.stop_distance must be positive")


# ---------------------------------------------------------------------------
# PositionSizerConfig
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PositionSizerConfig:
    """Configuration for the PositionSizer.

    Parameters
    ----------
    mode:
        ``SizingMode.FIXED_FRACTION`` (default) or ``SizingMode.KELLY``.
    risk_fraction:
        For FIXED_FRACTION: fraction of capital risked per trade (default 0.01 = 1%).
    atr_multiplier:
        Multiplier applied to ATR to get stop distance (default 1.5).
    kelly_fraction:
        Fractional Kelly scaling (default 0.25 = quarter-Kelly, which is safer).
    default_stop_pct:
        Fallback stop distance as a fraction of entry price when ATR is not
        provided (default 0.02 = 2%).
    """
    mode: SizingMode = SizingMode.FIXED_FRACTION
    risk_fraction: Decimal = DEFAULT_RISK_FRACTION
    atr_multiplier: Decimal = DEFAULT_ATR_MULTIPLIER
    kelly_fraction: Decimal = DEFAULT_KELLY_FRACTION
    default_stop_pct: Decimal = DEFAULT_STOP_PCT

    def __post_init__(self) -> None:
        if not (Decimal("0") < self.risk_fraction <= Decimal("1")):
            raise ValueError(
                f"PositionSizerConfig.risk_fraction must be in (0, 1], "
                f"got {self.risk_fraction}"
            )
        if self.atr_multiplier <= Decimal("0"):
            raise ValueError("PositionSizerConfig.atr_multiplier must be positive")
        if not (Decimal("0") < self.kelly_fraction <= Decimal("1")):
            raise ValueError(
                f"PositionSizerConfig.kelly_fraction must be in (0, 1], "
                f"got {self.kelly_fraction}"
            )
        if not (Decimal("0") < self.default_stop_pct < Decimal("1")):
            raise ValueError(
                f"PositionSizerConfig.default_stop_pct must be in (0, 1), "
                f"got {self.default_stop_pct}"
            )


# ---------------------------------------------------------------------------
# PositionSizer
# ---------------------------------------------------------------------------

class PositionSizer:
    """Computes position size in BTC given capital and risk parameters.

    Parameters
    ----------
    config:
        ``PositionSizerConfig`` instance (optional; defaults to fixed-fraction
        1% risk).
    """

    def __init__(self, config: Optional[PositionSizerConfig] = None) -> None:
        self._config = config or PositionSizerConfig()
        logger.debug(
            "PositionSizer initialised: mode=%s, risk_fraction=%s",
            self._config.mode.value, self._config.risk_fraction,
        )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def size(
        self,
        *,
        capital: Decimal,
        entry_price: Decimal,
        atr: Optional[Decimal] = None,
        stop_distance_usdt: Optional[Decimal] = None,
        win_rate: Optional[Decimal] = None,
        win_loss_ratio: Optional[Decimal] = None,
    ) -> PositionSizeResult:
        """Compute position size for a new trade.

        Either ``atr`` or ``stop_distance_usdt`` must be provided to determine
        the stop-loss distance.  If neither is given, the ``default_stop_pct``
        from config is applied to the entry price.

        Parameters
        ----------
        capital:
            Available capital in USDT for this strategy.
        entry_price:
            Current/expected entry price in USDT per BTC.
        atr:
            Average True Range in USDT (optional).  Used to compute stop distance
            as ``atr × config.atr_multiplier``.
        stop_distance_usdt:
            Explicit stop-loss distance in USDT (overrides ATR if provided).
        win_rate:
            Historical win rate in [0, 1].  Required for KELLY mode.
        win_loss_ratio:
            Average win / average loss ratio.  Required for KELLY mode.

        Returns
        -------
        PositionSizeResult
        """
        if capital <= Decimal("0"):
            raise ValueError(f"capital must be positive, got {capital}")
        if entry_price <= Decimal("0"):
            raise ValueError(f"entry_price must be positive, got {entry_price}")

        # Determine stop distance
        stop_dist = self._resolve_stop_distance(entry_price, atr, stop_distance_usdt)

        if self._config.mode == SizingMode.KELLY:
            return self._size_kelly(
                capital=capital,
                entry_price=entry_price,
                stop_dist=stop_dist,
                win_rate=win_rate,
                win_loss_ratio=win_loss_ratio,
            )
        else:
            return self._size_fixed_fraction(
                capital=capital,
                entry_price=entry_price,
                stop_dist=stop_dist,
            )

    # ------------------------------------------------------------------ #
    # Internal sizing algorithms                                           #
    # ------------------------------------------------------------------ #

    def _resolve_stop_distance(
        self,
        entry_price: Decimal,
        atr: Optional[Decimal],
        stop_distance_usdt: Optional[Decimal],
    ) -> Decimal:
        """Return stop-loss distance in USDT."""
        if stop_distance_usdt is not None:
            if stop_distance_usdt <= Decimal("0"):
                raise ValueError(
                    f"stop_distance_usdt must be positive, got {stop_distance_usdt}"
                )
            return stop_distance_usdt
        if atr is not None:
            if atr <= Decimal("0"):
                raise ValueError(f"atr must be positive, got {atr}")
            return atr * self._config.atr_multiplier
        # Fallback: use default_stop_pct × entry_price
        return entry_price * self._config.default_stop_pct

    def _size_fixed_fraction(
        self,
        capital: Decimal,
        entry_price: Decimal,
        stop_dist: Decimal,
    ) -> PositionSizeResult:
        """Fixed-fraction sizing: quantity = (capital × risk_fraction) / stop_dist."""
        risk_amount = capital * self._config.risk_fraction
        raw_qty = risk_amount / stop_dist

        qty, capped = self._clamp(raw_qty)
        notional = qty * entry_price
        actual_risk = qty * stop_dist

        logger.debug(
            "PositionSizer[FF]: capital=%s risk_frac=%s stop_dist=%s "
            "raw_qty=%s → qty=%s notional=%s",
            capital, self._config.risk_fraction, stop_dist, raw_qty, qty, notional,
        )
        return PositionSizeResult(
            quantity=qty,
            stop_distance=stop_dist,
            notional=notional,
            risk_amount=actual_risk,
            sizing_mode=SizingMode.FIXED_FRACTION,
            capped=capped,
        )

    def _size_kelly(
        self,
        capital: Decimal,
        entry_price: Decimal,
        stop_dist: Decimal,
        win_rate: Optional[Decimal],
        win_loss_ratio: Optional[Decimal],
    ) -> PositionSizeResult:
        """Kelly Criterion sizing.

        Kelly fraction = (win_rate × win_loss_ratio - loss_rate) / win_loss_ratio
        Then scaled by config.kelly_fraction (fractional Kelly) and capped.

        If win_rate / win_loss_ratio are not provided, falls back to fixed-fraction.
        """
        if win_rate is None or win_loss_ratio is None:
            logger.warning(
                "PositionSizer[Kelly]: win_rate and win_loss_ratio required; "
                "falling back to fixed-fraction"
            )
            return self._size_fixed_fraction(capital, entry_price, stop_dist)

        if not (Decimal("0") <= win_rate <= Decimal("1")):
            raise ValueError(f"win_rate must be in [0, 1], got {win_rate}")
        if win_loss_ratio <= Decimal("0"):
            raise ValueError(
                f"win_loss_ratio must be positive, got {win_loss_ratio}"
            )

        loss_rate = Decimal("1") - win_rate
        full_kelly = (win_rate * win_loss_ratio - loss_rate) / win_loss_ratio
        if full_kelly <= Decimal("0"):
            # Negative Kelly → edge is negative, don't trade
            logger.warning(
                "PositionSizer[Kelly]: full_kelly=%s <= 0 — no edge; returning 0",
                full_kelly,
            )
            return PositionSizeResult(
                quantity=Decimal("0"),
                stop_distance=stop_dist,
                notional=Decimal("0"),
                risk_amount=Decimal("0"),
                sizing_mode=SizingMode.KELLY,
                capped=False,
            )

        frac = full_kelly * self._config.kelly_fraction
        risk_amount = capital * frac
        raw_qty = risk_amount / stop_dist
        qty, capped = self._clamp(raw_qty)
        notional = qty * entry_price
        actual_risk = qty * stop_dist

        logger.debug(
            "PositionSizer[Kelly]: full_kelly=%s fractional_kelly=%s "
            "risk_amount=%s raw_qty=%s → qty=%s",
            full_kelly, frac, risk_amount, raw_qty, qty,
        )
        return PositionSizeResult(
            quantity=qty,
            stop_distance=stop_dist,
            notional=notional,
            risk_amount=actual_risk,
            sizing_mode=SizingMode.KELLY,
            capped=capped,
        )

    @staticmethod
    def _clamp(qty: Decimal) -> tuple[Decimal, bool]:
        """Clamp quantity to [MIN_QUANTITY, MAX_QUANTITY].

        Returns (clamped_qty, was_capped).
        """
        if qty > MAX_QUANTITY:
            return MAX_QUANTITY, True
        if qty < MIN_QUANTITY:
            # Return MIN_QUANTITY only if non-trivial; return 0 if clearly negligible
            if qty <= Decimal("0"):
                return Decimal("0"), False
            return MIN_QUANTITY, False
        return qty, False

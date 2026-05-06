"""
ITM Versioned Configuration System
====================================
Environment-aware, validated ITM configuration model.

Design
------
* ``ITMConfig`` is a frozen Pydantic-style dataclass with full field
  validation on construction.  (We use stdlib dataclasses + manual validation
  to avoid adding a Pydantic dependency at the domain layer.)
* ``Environment`` enum controls which config block is active.
* ``ITMConfigLoader`` merges layered config dicts (base → env override →
  runtime patch) and validates the result.
* Config carries a monotonically increasing ``revision`` integer so callers
  can detect stale references.
* ``dev``, ``test``, ``prod`` environments each have sensible defaults.

Usage
-----
::

    loader = ITMConfigLoader()
    config = loader.load(
        env=Environment.PROD,
        overrides={
            "exchange": "bybit",
            "capital_base": "100000.00",
            "risk": {"max_position_qty": "0.5"},
        },
    )
    print(config.exchange)       # "bybit"
    print(config.risk.max_leverage)  # Decimal('1.0')  (enforced)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_decimal(value: str | int | float | Decimal, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(
            f"Config field '{field_name}' could not be parsed as Decimal: {value!r}"
        ) from exc


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


class Environment(str, Enum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


# ---------------------------------------------------------------------------
# Sub-configs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskParams:
    """Risk parameters stored inside an ITMConfig.

    Mirrors RiskProfile but lives at the config layer (loaded from file/dict)
    rather than being constructed at runtime.
    """

    max_drawdown_pct: Decimal = Decimal("0.05")
    max_position_qty: Decimal = Decimal("1.0")
    heat_limit: Decimal = Decimal("10.0")
    max_daily_loss: Decimal = Decimal("500.00")
    max_leverage: Decimal = Decimal("1.0")

    def __post_init__(self) -> None:
        if not (Decimal("0") < self.max_drawdown_pct <= Decimal("1")):
            raise ValueError(
                f"RiskParams.max_drawdown_pct must be in (0, 1], "
                f"got {self.max_drawdown_pct}"
            )
        if self.max_position_qty <= Decimal("0"):
            raise ValueError("RiskParams.max_position_qty must be positive")
        if self.heat_limit <= Decimal("0"):
            raise ValueError("RiskParams.heat_limit must be positive")
        if self.max_daily_loss <= Decimal("0"):
            raise ValueError("RiskParams.max_daily_loss must be positive")
        if self.max_leverage != Decimal("1.0"):
            raise ValueError(
                f"RiskParams.max_leverage must be 1.0 (no margin), "
                f"got {self.max_leverage}"
            )


@dataclass(frozen=True)
class ExecutionParams:
    """Execution behaviour parameters stored inside an ITMConfig."""

    # Order submission retries before raising an error
    max_submit_retries: int = 3
    # Milliseconds to wait between retries
    retry_delay_ms: int = 500
    # Maximum latency (ms) before an order submission is considered timed out
    order_timeout_ms: int = 5_000
    # Whether to use post-only orders on limit entries
    post_only: bool = False
    # Slippage tolerance in basis points (100 bps = 1 %)
    slippage_tolerance_bps: int = 10

    def __post_init__(self) -> None:
        if self.max_submit_retries < 0:
            raise ValueError("ExecutionParams.max_submit_retries cannot be negative")
        if self.retry_delay_ms < 0:
            raise ValueError("ExecutionParams.retry_delay_ms cannot be negative")
        if self.order_timeout_ms <= 0:
            raise ValueError("ExecutionParams.order_timeout_ms must be positive")
        if self.slippage_tolerance_bps < 0:
            raise ValueError(
                "ExecutionParams.slippage_tolerance_bps cannot be negative"
            )


# ---------------------------------------------------------------------------
# Main config
# ---------------------------------------------------------------------------

_REVISION_COUNTER = 0


def _next_revision() -> int:
    global _REVISION_COUNTER  # noqa: PLW0603
    _REVISION_COUNTER += 1
    return _REVISION_COUNTER


@dataclass(frozen=True)
class ITMConfig:
    """Full ITM configuration object.

    Attributes
    ----------
    environment:      dev / test / prod
    exchange:         exchange identifier (e.g. 'binance', 'bybit')
    symbol:           trading pair symbol (e.g. 'BTC/USDT')
    capital_base:     total capital available to the ITM in USDT
    risk:             ``RiskParams`` sub-config
    execution:        ``ExecutionParams`` sub-config
    revision:         monotonically increasing integer; changes on every reload
    paper_trading:    when True, orders are never sent to the exchange
    """

    environment: Environment
    exchange: str
    symbol: str
    capital_base: Decimal
    risk: RiskParams
    execution: ExecutionParams
    revision: int = field(default_factory=_next_revision)
    paper_trading: bool = True  # default SAFE — must explicitly set False for live

    def __post_init__(self) -> None:
        if not self.exchange:
            raise ValueError("ITMConfig.exchange must not be empty")
        if not self.symbol:
            raise ValueError("ITMConfig.symbol must not be empty")
        if self.capital_base <= Decimal("0"):
            raise ValueError("ITMConfig.capital_base must be positive")


# ---------------------------------------------------------------------------
# Defaults per environment
# ---------------------------------------------------------------------------

_ENV_DEFAULTS: dict[Environment, dict] = {
    Environment.DEV: {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "capital_base": "10000.00",
        "paper_trading": True,
        "risk": {
            "max_drawdown_pct": "0.10",
            "max_position_qty": "0.1",
            "heat_limit": "5.0",
            "max_daily_loss": "100.00",
            "max_leverage": "1.0",
        },
        "execution": {
            "max_submit_retries": 3,
            "retry_delay_ms": 500,
            "order_timeout_ms": 10_000,
            "post_only": False,
            "slippage_tolerance_bps": 20,
        },
    },
    Environment.TEST: {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "capital_base": "1000.00",
        "paper_trading": True,
        "risk": {
            "max_drawdown_pct": "0.05",
            "max_position_qty": "0.01",
            "heat_limit": "2.0",
            "max_daily_loss": "50.00",
            "max_leverage": "1.0",
        },
        "execution": {
            "max_submit_retries": 1,
            "retry_delay_ms": 100,
            "order_timeout_ms": 2_000,
            "post_only": False,
            "slippage_tolerance_bps": 50,
        },
    },
    Environment.PROD: {
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "capital_base": "100000.00",
        "paper_trading": True,  # Must be explicitly overridden to go live
        "risk": {
            "max_drawdown_pct": "0.05",
            "max_position_qty": "1.0",
            "heat_limit": "10.0",
            "max_daily_loss": "500.00",
            "max_leverage": "1.0",
        },
        "execution": {
            "max_submit_retries": 3,
            "retry_delay_ms": 500,
            "order_timeout_ms": 5_000,
            "post_only": False,
            "slippage_tolerance_bps": 10,
        },
    },
}


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, returning a new dict."""
    result = copy.deepcopy(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


class ITMConfigLoader:
    """Builds ``ITMConfig`` from layered dict sources.

    Layer order (lowest → highest priority):
      1. Environment defaults (``_ENV_DEFAULTS``)
      2. *base_config* passed to ``load()``
      3. *overrides* passed to ``load()``

    Parameters
    ----------
    None — stateless; create one instance per process.

    Methods
    -------
    load(env, base_config=None, overrides=None) → ITMConfig
    """

    def load(
        self,
        env: Environment,
        base_config: dict | None = None,
        overrides: dict | None = None,
    ) -> ITMConfig:
        """Merge layers and return a validated ``ITMConfig``.

        Raises
        ------
        ValueError
            If the resulting config fails validation (e.g. max_leverage != 1.0,
            capital_base <= 0, etc.).
        """
        merged = copy.deepcopy(_ENV_DEFAULTS[env])
        if base_config:
            merged = _deep_merge(merged, base_config)
        if overrides:
            merged = _deep_merge(merged, overrides)

        # Build sub-configs
        risk_raw = merged.pop("risk", {})
        exec_raw = merged.pop("execution", {})

        risk = RiskParams(
            max_drawdown_pct=_to_decimal(
                risk_raw.get("max_drawdown_pct", "0.05"), "risk.max_drawdown_pct"
            ),
            max_position_qty=_to_decimal(
                risk_raw.get("max_position_qty", "1.0"), "risk.max_position_qty"
            ),
            heat_limit=_to_decimal(
                risk_raw.get("heat_limit", "10.0"), "risk.heat_limit"
            ),
            max_daily_loss=_to_decimal(
                risk_raw.get("max_daily_loss", "500.00"), "risk.max_daily_loss"
            ),
            max_leverage=_to_decimal(
                risk_raw.get("max_leverage", "1.0"), "risk.max_leverage"
            ),
        )

        execution = ExecutionParams(
            max_submit_retries=int(exec_raw.get("max_submit_retries", 3)),
            retry_delay_ms=int(exec_raw.get("retry_delay_ms", 500)),
            order_timeout_ms=int(exec_raw.get("order_timeout_ms", 5_000)),
            post_only=bool(exec_raw.get("post_only", False)),
            slippage_tolerance_bps=int(exec_raw.get("slippage_tolerance_bps", 10)),
        )

        return ITMConfig(
            environment=env,
            exchange=merged["exchange"],
            symbol=merged["symbol"],
            capital_base=_to_decimal(merged["capital_base"], "capital_base"),
            risk=risk,
            execution=execution,
            paper_trading=bool(merged.get("paper_trading", True)),
        )

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

Layer order (lowest → highest priority)
----------------------------------------
1. Environment defaults (hard-coded ``_ENV_DEFAULTS``)
2. YAML file (when ``load_from_yaml`` is used)
3. ``base_config`` dict passed to ``load()``
4. Environment variables (``ITM_*`` prefix)
5. ``overrides`` dict passed to ``load()`` / ``load_from_yaml()``

Supported env-vars
-------------------
``ITM_EXCHANGE``                    → config["exchange"]
``ITM_SYMBOL``                      → config["symbol"]
``ITM_CAPITAL_BASE``                → config["capital_base"]
``ITM_PAPER_TRADING``               → config["paper_trading"] (true/false/1/0)
``ITM_RISK_MAX_DRAWDOWN_PCT``       → config["risk"]["max_drawdown_pct"]
``ITM_RISK_MAX_POSITION_QTY``       → config["risk"]["max_position_qty"]
``ITM_RISK_HEAT_LIMIT``             → config["risk"]["heat_limit"]
``ITM_RISK_MAX_DAILY_LOSS``         → config["risk"]["max_daily_loss"]
``ITM_EXEC_MAX_SUBMIT_RETRIES``     → config["execution"]["max_submit_retries"]
``ITM_EXEC_RETRY_DELAY_MS``         → config["execution"]["retry_delay_ms"]
``ITM_EXEC_ORDER_TIMEOUT_MS``       → config["execution"]["order_timeout_ms"]
``ITM_EXEC_POST_ONLY``              → config["execution"]["post_only"]
``ITM_EXEC_SLIPPAGE_TOLERANCE_BPS`` → config["execution"]["slippage_tolerance_bps"]

Usage
-----
::

    loader = ITMConfigLoader()

    # Load from env defaults + runtime overrides
    config = loader.load(
        env=Environment.PROD,
        overrides={"exchange": "bybit"},
    )

    # Load from a YAML file
    config = loader.load_from_yaml("config/prod.yaml", Environment.PROD)

    print(config.exchange)           # "bybit"
    print(config.risk.max_leverage)  # Decimal('1.0')  (enforced)
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any


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


def _collect_env_overrides() -> dict:
    """Read ``ITM_*`` environment variables and return a partial config dict.

    Only keys that are actually set in the environment are included —
    missing env-vars do not overwrite config file or default values.
    """
    overrides: dict[str, Any] = {}
    risk_overrides: dict[str, Any] = {}
    exec_overrides: dict[str, Any] = {}

    _str = os.environ.get

    def _bool_env(name: str) -> bool | None:
        val = os.environ.get(name)
        if val is None or not val.strip():
            return None
        return val.strip().lower() in ("true", "1", "yes")

    if (v := _str("ITM_EXCHANGE")):
        overrides["exchange"] = v
    if (v := _str("ITM_SYMBOL")):
        overrides["symbol"] = v
    if (v := _str("ITM_CAPITAL_BASE")):
        overrides["capital_base"] = v
    paper = _bool_env("ITM_PAPER_TRADING")
    if paper is not None:
        overrides["paper_trading"] = paper

    if (v := _str("ITM_RISK_MAX_DRAWDOWN_PCT")):
        risk_overrides["max_drawdown_pct"] = v
    if (v := _str("ITM_RISK_MAX_POSITION_QTY")):
        risk_overrides["max_position_qty"] = v
    if (v := _str("ITM_RISK_HEAT_LIMIT")):
        risk_overrides["heat_limit"] = v
    if (v := _str("ITM_RISK_MAX_DAILY_LOSS")):
        risk_overrides["max_daily_loss"] = v

    if (v := _str("ITM_EXEC_MAX_SUBMIT_RETRIES")):
        exec_overrides["max_submit_retries"] = int(v)
    if (v := _str("ITM_EXEC_RETRY_DELAY_MS")):
        exec_overrides["retry_delay_ms"] = int(v)
    if (v := _str("ITM_EXEC_ORDER_TIMEOUT_MS")):
        exec_overrides["order_timeout_ms"] = int(v)
    exec_post_only = _bool_env("ITM_EXEC_POST_ONLY")
    if exec_post_only is not None:
        exec_overrides["post_only"] = exec_post_only
    if (v := _str("ITM_EXEC_SLIPPAGE_TOLERANCE_BPS")):
        exec_overrides["slippage_tolerance_bps"] = int(v)

    if risk_overrides:
        overrides["risk"] = risk_overrides
    if exec_overrides:
        overrides["execution"] = exec_overrides

    return overrides


class ITMConfigLoader:
    """Builds ``ITMConfig`` from layered dict sources.

    Layer order (lowest → highest priority):
      1. Environment defaults (``_ENV_DEFAULTS``)
      2. YAML file (when ``load_from_yaml`` is used)
      3. *base_config* passed to ``load()``
      4. Environment variables (``ITM_*`` prefix)
      5. *overrides* passed to ``load()`` / ``load_from_yaml()``

    Parameters
    ----------
    None — stateless; create one instance per process.

    Methods
    -------
    load(env, base_config=None, overrides=None) → ITMConfig
    load_from_yaml(path, env, overrides=None) → ITMConfig
    """

    def load(
        self,
        env: Environment,
        base_config: dict | None = None,
        overrides: dict | None = None,
    ) -> ITMConfig:
        """Merge layers and return a validated ``ITMConfig``.

        Layer order: env defaults → base_config → env-vars → overrides.

        Raises
        ------
        ValueError
            If the resulting config fails validation (e.g. max_leverage != 1.0,
            capital_base <= 0, etc.).
        """
        merged = copy.deepcopy(_ENV_DEFAULTS[env])
        if base_config:
            merged = _deep_merge(merged, base_config)
        # Environment variable overrides (applied after base_config)
        env_vars = _collect_env_overrides()
        if env_vars:
            merged = _deep_merge(merged, env_vars)
        if overrides:
            merged = _deep_merge(merged, overrides)

        return self._build_from_dict(env, merged)

    def load_from_yaml(
        self,
        path: str | Path,
        env: Environment,
        overrides: dict | None = None,
    ) -> ITMConfig:
        """Load config from a YAML file, merge with env defaults, and validate.

        The YAML file is treated as the *base_config* layer — it overrides
        environment defaults but is itself overridden by env-vars and
        runtime *overrides*.

        Parameters
        ----------
        path:
            Filesystem path to the YAML configuration file.
        env:
            Target environment (controls which defaults are used as the base).
        overrides:
            Optional dict of runtime overrides applied on top of the YAML file.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        ValueError
            If the YAML is structurally invalid or fails config validation.
        ImportError
            If PyYAML (``pyyaml``) is not installed.
        """
        try:
            import yaml  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "PyYAML is required for YAML config loading. "
                "Install it with: pip install pyyaml"
            ) from exc

        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(
                f"ITM config file not found: {file_path.resolve()}"
            )

        with file_path.open("r", encoding="utf-8") as fh:
            try:
                yaml_data: dict = yaml.safe_load(fh) or {}
            except yaml.YAMLError as exc:
                raise ValueError(
                    f"Failed to parse ITM YAML config at {file_path}: {exc}"
                ) from exc

        if not isinstance(yaml_data, dict):
            raise ValueError(
                f"ITM YAML config must be a mapping at the top level, "
                f"got {type(yaml_data).__name__}"
            )

        return self.load(env, base_config=yaml_data, overrides=overrides)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _build_from_dict(self, env: Environment, merged: dict) -> ITMConfig:
        """Construct an ``ITMConfig`` from a fully-merged config dict."""
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

"""
Unit tests for the ITM versioned configuration system.
Covers: Environment, RiskParams, ExecutionParams, ITMConfig, ITMConfigLoader
"""
from __future__ import annotations

import pytest
from decimal import Decimal

from src.itm.domain.config import (
    Environment,
    ExecutionParams,
    ITMConfig,
    ITMConfigLoader,
    RiskParams,
    _deep_merge,
)


# ---------------------------------------------------------------------------
# RiskParams tests
# ---------------------------------------------------------------------------


class TestRiskParams:
    def test_default_values(self) -> None:
        rp = RiskParams()
        assert rp.max_drawdown_pct == Decimal("0.05")
        assert rp.max_position_qty == Decimal("1.0")
        assert rp.heat_limit == Decimal("10.0")
        assert rp.max_daily_loss == Decimal("500.00")
        assert rp.max_leverage == Decimal("1.0")

    def test_custom_values_valid(self) -> None:
        rp = RiskParams(
            max_drawdown_pct=Decimal("0.03"),
            max_position_qty=Decimal("0.5"),
            heat_limit=Decimal("5.0"),
            max_daily_loss=Decimal("250.00"),
        )
        assert rp.max_drawdown_pct == Decimal("0.03")
        assert rp.max_position_qty == Decimal("0.5")

    def test_leverage_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="max_leverage"):
            RiskParams(max_leverage=Decimal("1.5"))

    def test_leverage_below_one_raises(self) -> None:
        with pytest.raises(ValueError, match="max_leverage"):
            RiskParams(max_leverage=Decimal("0.5"))

    def test_zero_drawdown_raises(self) -> None:
        with pytest.raises(ValueError, match="max_drawdown_pct"):
            RiskParams(max_drawdown_pct=Decimal("0"))

    def test_drawdown_exactly_one_is_valid(self) -> None:
        rp = RiskParams(max_drawdown_pct=Decimal("1"))
        assert rp.max_drawdown_pct == Decimal("1")

    def test_drawdown_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="max_drawdown_pct"):
            RiskParams(max_drawdown_pct=Decimal("1.01"))

    def test_zero_position_qty_raises(self) -> None:
        with pytest.raises(ValueError, match="max_position_qty"):
            RiskParams(max_position_qty=Decimal("0"))

    def test_zero_heat_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="heat_limit"):
            RiskParams(heat_limit=Decimal("0"))

    def test_zero_daily_loss_raises(self) -> None:
        with pytest.raises(ValueError, match="max_daily_loss"):
            RiskParams(max_daily_loss=Decimal("0"))

    def test_frozen_immutable(self) -> None:
        rp = RiskParams()
        with pytest.raises((AttributeError, TypeError)):
            rp.max_leverage = Decimal("2.0")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ExecutionParams tests
# ---------------------------------------------------------------------------


class TestExecutionParams:
    def test_default_values(self) -> None:
        ep = ExecutionParams()
        assert ep.max_submit_retries == 3
        assert ep.retry_delay_ms == 500
        assert ep.order_timeout_ms == 5_000
        assert not ep.post_only
        assert ep.slippage_tolerance_bps == 10

    def test_custom_values(self) -> None:
        ep = ExecutionParams(
            max_submit_retries=5,
            retry_delay_ms=100,
            order_timeout_ms=2_000,
            post_only=True,
            slippage_tolerance_bps=0,
        )
        assert ep.max_submit_retries == 5
        assert ep.post_only is True
        assert ep.slippage_tolerance_bps == 0

    def test_negative_retries_raises(self) -> None:
        with pytest.raises(ValueError, match="max_submit_retries"):
            ExecutionParams(max_submit_retries=-1)

    def test_negative_retry_delay_raises(self) -> None:
        with pytest.raises(ValueError, match="retry_delay_ms"):
            ExecutionParams(retry_delay_ms=-1)

    def test_zero_order_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="order_timeout_ms"):
            ExecutionParams(order_timeout_ms=0)

    def test_negative_slippage_raises(self) -> None:
        with pytest.raises(ValueError, match="slippage_tolerance_bps"):
            ExecutionParams(slippage_tolerance_bps=-1)


# ---------------------------------------------------------------------------
# ITMConfig tests
# ---------------------------------------------------------------------------


class TestITMConfig:
    def _make_config(self, **kwargs) -> ITMConfig:
        defaults = dict(
            environment=Environment.TEST,
            exchange="binance",
            symbol="BTC/USDT",
            capital_base=Decimal("1000"),
            risk=RiskParams(),
            execution=ExecutionParams(),
        )
        defaults.update(kwargs)
        return ITMConfig(**defaults)

    def test_valid_config(self) -> None:
        cfg = self._make_config()
        assert cfg.exchange == "binance"
        assert cfg.symbol == "BTC/USDT"
        assert cfg.paper_trading is True

    def test_revision_increments(self) -> None:
        cfg1 = self._make_config()
        cfg2 = self._make_config()
        assert cfg2.revision > cfg1.revision

    def test_empty_exchange_raises(self) -> None:
        with pytest.raises(ValueError, match="exchange"):
            self._make_config(exchange="")

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(ValueError, match="symbol"):
            self._make_config(symbol="")

    def test_zero_capital_base_raises(self) -> None:
        with pytest.raises(ValueError, match="capital_base"):
            self._make_config(capital_base=Decimal("0"))

    def test_negative_capital_base_raises(self) -> None:
        with pytest.raises(ValueError, match="capital_base"):
            self._make_config(capital_base=Decimal("-100"))

    def test_paper_trading_defaults_true(self) -> None:
        cfg = self._make_config()
        assert cfg.paper_trading is True

    def test_paper_trading_can_be_set_false(self) -> None:
        cfg = self._make_config(paper_trading=False)
        assert cfg.paper_trading is False

    def test_frozen_immutable(self) -> None:
        cfg = self._make_config()
        with pytest.raises((AttributeError, TypeError)):
            cfg.exchange = "bybit"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ITMConfigLoader tests
# ---------------------------------------------------------------------------


class TestITMConfigLoader:
    def setup_method(self) -> None:
        self.loader = ITMConfigLoader()

    def test_load_dev_defaults(self) -> None:
        cfg = self.loader.load(Environment.DEV)
        assert cfg.environment == Environment.DEV
        assert cfg.exchange == "binance"
        assert cfg.paper_trading is True
        assert cfg.capital_base == Decimal("10000.00")
        assert cfg.risk.max_position_qty == Decimal("0.1")

    def test_load_test_defaults(self) -> None:
        cfg = self.loader.load(Environment.TEST)
        assert cfg.environment == Environment.TEST
        assert cfg.capital_base == Decimal("1000.00")
        assert cfg.risk.max_position_qty == Decimal("0.01")

    def test_load_prod_defaults(self) -> None:
        cfg = self.loader.load(Environment.PROD)
        assert cfg.environment == Environment.PROD
        assert cfg.capital_base == Decimal("100000.00")
        assert cfg.risk.max_position_qty == Decimal("1.0")

    def test_overrides_applied(self) -> None:
        cfg = self.loader.load(
            Environment.DEV,
            overrides={"exchange": "bybit", "capital_base": "20000.00"},
        )
        assert cfg.exchange == "bybit"
        assert cfg.capital_base == Decimal("20000.00")

    def test_risk_overrides_applied(self) -> None:
        cfg = self.loader.load(
            Environment.PROD,
            overrides={"risk": {"max_position_qty": "0.5"}},
        )
        assert cfg.risk.max_position_qty == Decimal("0.5")
        assert cfg.risk.max_leverage == Decimal("1.0")
        assert cfg.risk.max_daily_loss == Decimal("500.00")

    def test_execution_overrides_applied(self) -> None:
        cfg = self.loader.load(
            Environment.TEST,
            overrides={"execution": {"post_only": True, "max_submit_retries": 5}},
        )
        assert cfg.execution.post_only is True
        assert cfg.execution.max_submit_retries == 5

    def test_base_config_then_overrides(self) -> None:
        base = {"exchange": "okx", "capital_base": "5000"}
        override = {"exchange": "bybit"}
        cfg = self.loader.load(Environment.DEV, base_config=base, overrides=override)
        assert cfg.exchange == "bybit"
        assert cfg.capital_base == Decimal("5000")

    def test_leverage_override_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="max_leverage"):
            self.loader.load(
                Environment.DEV,
                overrides={"risk": {"max_leverage": "2.0"}},
            )

    def test_invalid_capital_base_raises(self) -> None:
        with pytest.raises(ValueError):
            self.loader.load(
                Environment.DEV,
                overrides={"capital_base": "0"},
            )

    def test_invalid_decimal_raises(self) -> None:
        with pytest.raises(ValueError, match="capital_base"):
            self.loader.load(
                Environment.DEV,
                overrides={"capital_base": "not_a_number"},
            )

    def test_all_three_environments_load_successfully(self) -> None:
        for env in Environment:
            cfg = self.loader.load(env)
            assert cfg.environment == env
            assert cfg.risk.max_leverage == Decimal("1.0")
            assert cfg.paper_trading is True


# ---------------------------------------------------------------------------
# Deep merge helper tests
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_simple_merge(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"b": 99, "c": 3}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 99, "c": 3}

    def test_nested_merge(self) -> None:
        base = {"risk": {"max_leverage": "1.0", "heat_limit": "10"}}
        override = {"risk": {"heat_limit": "5"}}
        result = _deep_merge(base, override)
        assert result["risk"]["max_leverage"] == "1.0"
        assert result["risk"]["heat_limit"] == "5"

    def test_override_replaces_non_dict_with_dict(self) -> None:
        base = {"a": "string"}
        override = {"a": {"nested": True}}
        result = _deep_merge(base, override)
        assert result["a"] == {"nested": True}

    def test_original_not_mutated(self) -> None:
        base = {"risk": {"max_leverage": "1.0"}}
        override = {"risk": {"max_leverage": "2.0"}}
        _deep_merge(base, override)
        assert base["risk"]["max_leverage"] == "1.0"

"""
Unit tests for the ITM versioned configuration system.
Covers: Environment, RiskParams, ExecutionParams, ITMConfig, ITMConfigLoader,
        YAML loading, environment-variable overrides, deep_merge
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


# ---------------------------------------------------------------------------
# YAML loading tests
# ---------------------------------------------------------------------------


class TestYAMLLoading:
    """AC2: load_from_yaml() must read YAML files and merge with env defaults."""

    def _write_yaml(self, tmp_path, content: str):
        p = tmp_path / "itm_config.yaml"
        p.write_text(content, encoding="utf-8")
        return str(p)

    def test_load_valid_yaml_overrides_defaults(self, tmp_path) -> None:
        yaml_content = """
exchange: bybit
capital_base: "25000.00"
paper_trading: true
risk:
  max_position_qty: "0.5"
  max_daily_loss: "250.00"
"""
        path = self._write_yaml(tmp_path, yaml_content)
        loader = ITMConfigLoader()
        cfg = loader.load_from_yaml(path, Environment.PROD)
        assert cfg.exchange == "bybit"
        assert cfg.capital_base == Decimal("25000.00")
        assert cfg.paper_trading is True
        assert cfg.risk.max_position_qty == Decimal("0.5")
        assert cfg.risk.max_daily_loss == Decimal("250.00")
        # Risk fields NOT in YAML should use PROD defaults
        assert cfg.risk.max_leverage == Decimal("1.0")

    def test_load_yaml_with_runtime_overrides(self, tmp_path) -> None:
        yaml_content = "exchange: okx\ncapital_base: '5000.00'\n"
        path = self._write_yaml(tmp_path, yaml_content)
        loader = ITMConfigLoader()
        cfg = loader.load_from_yaml(
            path,
            Environment.TEST,
            overrides={"exchange": "binance"},
        )
        # runtime overrides win over YAML
        assert cfg.exchange == "binance"
        assert cfg.capital_base == Decimal("5000.00")

    def test_load_yaml_full_execution_section(self, tmp_path) -> None:
        yaml_content = """
exchange: binance
capital_base: "50000.00"
execution:
  max_submit_retries: 5
  post_only: true
  slippage_tolerance_bps: 3
"""
        path = self._write_yaml(tmp_path, yaml_content)
        loader = ITMConfigLoader()
        cfg = loader.load_from_yaml(path, Environment.PROD)
        assert cfg.execution.max_submit_retries == 5
        assert cfg.execution.post_only is True
        assert cfg.execution.slippage_tolerance_bps == 3

    def test_load_yaml_missing_file_raises(self) -> None:
        loader = ITMConfigLoader()
        with pytest.raises(FileNotFoundError, match="not found"):
            loader.load_from_yaml("/nonexistent/path/config.yaml", Environment.DEV)

    def test_load_invalid_yaml_raises(self, tmp_path) -> None:
        # YAML with invalid indentation / syntax
        bad_yaml = "exchange: binance\n  bad_indent: [unclosed"
        path = self._write_yaml(tmp_path, bad_yaml)
        loader = ITMConfigLoader()
        with pytest.raises(ValueError, match="[Ff]ailed to parse|YAML"):
            loader.load_from_yaml(path, Environment.DEV)

    def test_load_yaml_non_mapping_raises(self, tmp_path) -> None:
        # YAML that parses to a list, not a dict
        path = self._write_yaml(tmp_path, "- item1\n- item2\n")
        loader = ITMConfigLoader()
        with pytest.raises(ValueError, match="mapping"):
            loader.load_from_yaml(path, Environment.DEV)

    def test_load_yaml_invalid_capital_base_raises(self, tmp_path) -> None:
        path = self._write_yaml(tmp_path, "exchange: binance\ncapital_base: '0'\n")
        loader = ITMConfigLoader()
        with pytest.raises(ValueError):
            loader.load_from_yaml(path, Environment.DEV)

    def test_load_yaml_preserves_paper_trading_false(self, tmp_path) -> None:
        path = self._write_yaml(
            tmp_path, "exchange: binance\ncapital_base: '10000'\npaper_trading: false\n"
        )
        loader = ITMConfigLoader()
        cfg = loader.load_from_yaml(path, Environment.PROD)
        assert cfg.paper_trading is False

    def test_load_yaml_empty_file_uses_env_defaults(self, tmp_path) -> None:
        # Empty YAML → null → treated as empty dict → pure env defaults
        path = self._write_yaml(tmp_path, "")
        loader = ITMConfigLoader()
        cfg = loader.load_from_yaml(path, Environment.TEST)
        # Should be TEST defaults
        assert cfg.capital_base == Decimal("1000.00")
        assert cfg.exchange == "binance"


# ---------------------------------------------------------------------------
# Environment variable override tests
# ---------------------------------------------------------------------------


class TestEnvVarOverrides:
    """AC2: ITM_* env vars must override config at the correct layer."""

    def test_itm_exchange_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_EXCHANGE", "kraken")
        cfg = ITMConfigLoader().load(Environment.DEV)
        assert cfg.exchange == "kraken"

    def test_itm_capital_base_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_CAPITAL_BASE", "77777.77")
        cfg = ITMConfigLoader().load(Environment.DEV)
        assert cfg.capital_base == Decimal("77777.77")

    def test_itm_paper_trading_false(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_PAPER_TRADING", "false")
        cfg = ITMConfigLoader().load(Environment.DEV)
        assert cfg.paper_trading is False

    def test_itm_paper_trading_true_variants(self, monkeypatch) -> None:
        for val in ("true", "True", "TRUE", "1", "yes"):
            monkeypatch.setenv("ITM_PAPER_TRADING", val)
            cfg = ITMConfigLoader().load(Environment.DEV)
            assert cfg.paper_trading is True, f"Expected True for ITM_PAPER_TRADING={val!r}"

    def test_itm_risk_max_position_qty_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_RISK_MAX_POSITION_QTY", "0.25")
        cfg = ITMConfigLoader().load(Environment.PROD)
        assert cfg.risk.max_position_qty == Decimal("0.25")

    def test_itm_risk_max_daily_loss_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_RISK_MAX_DAILY_LOSS", "150.00")
        cfg = ITMConfigLoader().load(Environment.PROD)
        assert cfg.risk.max_daily_loss == Decimal("150.00")

    def test_itm_exec_post_only_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_EXEC_POST_ONLY", "true")
        cfg = ITMConfigLoader().load(Environment.TEST)
        assert cfg.execution.post_only is True

    def test_itm_exec_max_submit_retries_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_EXEC_MAX_SUBMIT_RETRIES", "7")
        cfg = ITMConfigLoader().load(Environment.PROD)
        assert cfg.execution.max_submit_retries == 7

    def test_itm_exec_slippage_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_EXEC_SLIPPAGE_TOLERANCE_BPS", "5")
        cfg = ITMConfigLoader().load(Environment.DEV)
        assert cfg.execution.slippage_tolerance_bps == 5

    def test_runtime_override_beats_env_var(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_EXCHANGE", "kraken")
        cfg = ITMConfigLoader().load(
            Environment.DEV,
            overrides={"exchange": "bybit"},
        )
        # runtime override must win over env-var
        assert cfg.exchange == "bybit"

    def test_env_var_beats_base_config(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_EXCHANGE", "kucoin")
        cfg = ITMConfigLoader().load(
            Environment.DEV,
            base_config={"exchange": "ftx"},
        )
        # env-var is applied after base_config
        assert cfg.exchange == "kucoin"

    def test_unset_env_vars_do_not_override(self, monkeypatch) -> None:
        # Ensure none of the ITM_* vars are set
        for key in [
            "ITM_EXCHANGE", "ITM_CAPITAL_BASE", "ITM_PAPER_TRADING",
            "ITM_RISK_MAX_POSITION_QTY",
        ]:
            monkeypatch.delenv(key, raising=False)
        cfg = ITMConfigLoader().load(Environment.PROD)
        # Should be pure PROD defaults
        assert cfg.exchange == "binance"
        assert cfg.capital_base == Decimal("100000.00")

    def test_itm_symbol_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_SYMBOL", "BTC/USDC")
        cfg = ITMConfigLoader().load(Environment.DEV)
        assert cfg.symbol == "BTC/USDC"

    def test_itm_risk_max_drawdown_pct_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_RISK_MAX_DRAWDOWN_PCT", "0.03")
        cfg = ITMConfigLoader().load(Environment.PROD)
        assert cfg.risk.max_drawdown_pct == Decimal("0.03")

    def test_itm_risk_heat_limit_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_RISK_HEAT_LIMIT", "7.5")
        cfg = ITMConfigLoader().load(Environment.PROD)
        assert cfg.risk.heat_limit == Decimal("7.5")

    def test_itm_exec_retry_delay_ms_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_EXEC_RETRY_DELAY_MS", "250")
        cfg = ITMConfigLoader().load(Environment.PROD)
        assert cfg.execution.retry_delay_ms == 250

    def test_itm_exec_order_timeout_ms_overrides(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_EXEC_ORDER_TIMEOUT_MS", "8000")
        cfg = ITMConfigLoader().load(Environment.PROD)
        assert cfg.execution.order_timeout_ms == 8000

    def test_itm_paper_trading_blank_string_defaults_to_true(self, monkeypatch) -> None:
        monkeypatch.setenv("ITM_PAPER_TRADING", "")
        cfg = ITMConfigLoader().load(Environment.DEV)
        assert cfg.paper_trading is True, "Blank ITM_PAPER_TRADING must default to paper mode"

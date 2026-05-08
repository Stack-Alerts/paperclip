"""
Tests for SBExportImporter and StrategyConfig (Section D — sb_contract.py)
"""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from src.itm.orchestrator.sb_contract import (
    SBExportImportError,
    SBExportImporter,
    StrategyConfig,
    StrategyInstrumentConfig,
    StrategyRiskConfig,
    MAX_POSITION_QTY_HARD_LIMIT,
    MAX_DAILY_LOSS_HARD_LIMIT,
    REQUIRED_MAX_LEVERAGE,
    SB_EXPORT_VERSION,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_raw_strategy(
    id_="strat-001",
    name="Momentum",
    symbol="BTC/USDT",
    exchange="binance",
    contract_type="spot",
    capital_allocation_pct=0.5,
    max_drawdown_pct=0.05,
    max_position_qty=0.1,
    heat_limit=5.0,
    max_daily_loss=500.0,
    max_leverage=1.0,
    signal_confidence_threshold=0.6,
    tags=None,
    metadata=None,
):
    return {
        "id": id_,
        "name": name,
        "instrument": {
            "symbol": symbol,
            "exchange": exchange,
            "contract_type": contract_type,
        },
        "capital_allocation_pct": capital_allocation_pct,
        "risk": {
            "max_drawdown_pct": max_drawdown_pct,
            "max_position_qty": max_position_qty,
            "heat_limit": heat_limit,
            "max_daily_loss": max_daily_loss,
            "max_leverage": max_leverage,
        },
        "signal_confidence_threshold": signal_confidence_threshold,
        "tags": tags or ["momentum"],
        "metadata": metadata or {},
    }


_SENTINEL = object()


def make_export_doc(strategies=_SENTINEL):
    return {
        "sb_export_version": SB_EXPORT_VERSION,
        "exported_at": "2026-05-08T12:00:00Z",
        "strategies": [make_raw_strategy()] if strategies is _SENTINEL else strategies,
    }


IMPORTER = SBExportImporter()


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestSBExportImporterHappyPath:

    def test_single_strategy_from_dict(self):
        export = make_export_doc()
        configs = IMPORTER.from_dict(export)
        assert len(configs) == 1
        c = configs[0]
        assert c.strategy_id == "strat-001"
        assert c.name == "Momentum"
        assert c.instrument.symbol == "BTC/USDT"
        assert c.instrument.exchange == "binance"
        assert c.instrument.contract_type == "spot"
        assert c.capital_allocation_pct == Decimal("0.5")
        assert c.risk.max_drawdown_pct == Decimal("0.05")
        assert c.risk.max_position_qty == Decimal("0.1")
        assert c.risk.heat_limit == Decimal("5.0")
        assert c.risk.max_daily_loss == Decimal("500.0")
        assert c.risk.max_leverage == Decimal("1.0")
        assert c.signal_confidence_threshold == Decimal("0.6")
        assert c.tags == ("momentum",)

    def test_two_strategies_from_dict(self):
        export = make_export_doc(
            strategies=[
                make_raw_strategy(id_="s1", capital_allocation_pct=0.3),
                make_raw_strategy(id_="s2", capital_allocation_pct=0.4),
            ]
        )
        configs = IMPORTER.from_dict(export)
        assert len(configs) == 2
        assert configs[0].strategy_id == "s1"
        assert configs[1].strategy_id == "s2"

    def test_from_json_string(self):
        export = make_export_doc()
        json_str = json.dumps(export)
        configs = IMPORTER.from_json(json_str)
        assert len(configs) == 1

    def test_total_allocation_exactly_one(self):
        # Two strategies that together use exactly 100% — should pass
        export = make_export_doc(
            strategies=[
                make_raw_strategy(id_="s1", capital_allocation_pct=0.5),
                make_raw_strategy(id_="s2", capital_allocation_pct=0.5),
            ]
        )
        configs = IMPORTER.from_dict(export)
        assert len(configs) == 2

    def test_strategy_without_id_gets_auto_id(self):
        raw = make_raw_strategy()
        del raw["id"]
        export = make_export_doc(strategies=[raw])
        configs = IMPORTER.from_dict(export)
        assert len(configs) == 1
        assert configs[0].strategy_id  # not empty

    def test_perpetual_contract_type(self):
        raw = make_raw_strategy(contract_type="perpetual")
        export = make_export_doc(strategies=[raw])
        configs = IMPORTER.from_dict(export)
        assert configs[0].instrument.contract_type == "perpetual"

    def test_metadata_passthrough(self):
        raw = make_raw_strategy(metadata={"version": "2.1", "author": "tester"})
        export = make_export_doc(strategies=[raw])
        configs = IMPORTER.from_dict(export)
        assert configs[0].metadata == {"version": "2.1", "author": "tester"}


# ---------------------------------------------------------------------------
# Validation / error tests
# ---------------------------------------------------------------------------

class TestSBExportImporterValidation:

    def test_wrong_version_raises(self):
        export = make_export_doc()
        export["sb_export_version"] = "2.0"
        with pytest.raises(SBExportImportError, match="Unsupported SB export version"):
            IMPORTER.from_dict(export)

    def test_missing_version_raises(self):
        export = make_export_doc()
        del export["sb_export_version"]
        with pytest.raises(SBExportImportError, match="Unsupported SB export version"):
            IMPORTER.from_dict(export)

    def test_empty_strategies_raises(self):
        export = make_export_doc(strategies=[])
        with pytest.raises(SBExportImportError, match="non-empty list"):
            IMPORTER.from_dict(export)

    def test_total_allocation_over_one_raises(self):
        export = make_export_doc(
            strategies=[
                make_raw_strategy(id_="s1", capital_allocation_pct=0.6),
                make_raw_strategy(id_="s2", capital_allocation_pct=0.6),
            ]
        )
        with pytest.raises(SBExportImportError, match="exceeds 1.0"):
            IMPORTER.from_dict(export)

    def test_duplicate_strategy_id_raises(self):
        export = make_export_doc(
            strategies=[
                make_raw_strategy(id_="dup"),
                make_raw_strategy(id_="dup"),
            ]
        )
        with pytest.raises(SBExportImportError, match="Duplicate strategy_id"):
            IMPORTER.from_dict(export)

    def test_leverage_not_one_raises(self):
        export = make_export_doc(
            strategies=[make_raw_strategy(max_leverage=2.0)]
        )
        with pytest.raises(SBExportImportError, match="max_leverage"):
            IMPORTER.from_dict(export)

    def test_max_position_qty_over_limit_raises(self):
        export = make_export_doc(
            strategies=[make_raw_strategy(max_position_qty=1.5)]
        )
        with pytest.raises(SBExportImportError, match="hard limit"):
            IMPORTER.from_dict(export)

    def test_max_daily_loss_over_limit_raises(self):
        export = make_export_doc(
            strategies=[make_raw_strategy(max_daily_loss=600.0)]
        )
        with pytest.raises(SBExportImportError, match="hard limit"):
            IMPORTER.from_dict(export)

    def test_invalid_contract_type_raises(self):
        export = make_export_doc(
            strategies=[make_raw_strategy(contract_type="options")]
        )
        with pytest.raises(SBExportImportError):
            IMPORTER.from_dict(export)

    def test_invalid_json_string_raises(self):
        with pytest.raises(SBExportImportError, match="not valid JSON"):
            IMPORTER.from_json("{bad json}")

    def test_invalid_drawdown_pct_zero_raises(self):
        export = make_export_doc(
            strategies=[make_raw_strategy(max_drawdown_pct=0.0)]
        )
        with pytest.raises(SBExportImportError, match="max_drawdown_pct"):
            IMPORTER.from_dict(export)


# ---------------------------------------------------------------------------
# StrategyRiskConfig unit tests
# ---------------------------------------------------------------------------

class TestStrategyRiskConfig:

    def test_valid_risk_config(self):
        rc = StrategyRiskConfig(
            max_drawdown_pct=Decimal("0.05"),
            max_position_qty=Decimal("0.5"),
            heat_limit=Decimal("5.0"),
            max_daily_loss=Decimal("400.0"),
            max_leverage=Decimal("1.0"),
        )
        assert rc.max_leverage == Decimal("1.0")

    def test_leverage_not_one_raises(self):
        with pytest.raises(ValueError, match="max_leverage"):
            StrategyRiskConfig(
                max_drawdown_pct=Decimal("0.05"),
                max_position_qty=Decimal("0.5"),
                heat_limit=Decimal("5.0"),
                max_daily_loss=Decimal("400.0"),
                max_leverage=Decimal("2.0"),
            )

    def test_position_qty_over_hard_limit_raises(self):
        with pytest.raises(ValueError, match="hard limit"):
            StrategyRiskConfig(
                max_drawdown_pct=Decimal("0.05"),
                max_position_qty=Decimal("2.0"),  # > 1.0 BTC
                heat_limit=Decimal("5.0"),
                max_daily_loss=Decimal("400.0"),
                max_leverage=Decimal("1.0"),
            )

"""
Unit Tests for StrategyFactory (BTCAAAAA-25614)
"""

import pytest
import json
import os
import tempfile
import ast

from src.strategy_builder.core.strategy_factory import (
    StrategyFactory,
    StrategyDef,
    ValidationResult,
    BLOCK_REGISTRY_MAP,
)


class TestStrategyFactoryInit:
    """Test factory initialization and basic properties."""

    def test_factory_initializes(self):
        factory = StrategyFactory()
        assert factory is not None

    def test_factory_has_block_registry(self):
        assert len(BLOCK_REGISTRY_MAP) > 0
        assert "Double_Top" in BLOCK_REGISTRY_MAP
        assert "RSI_Divergence" in BLOCK_REGISTRY_MAP
        assert "VWAP" in BLOCK_REGISTRY_MAP


class TestStrategyFactoryValidation:
    """Test validation rules."""

    def test_empty_blocks_fails(self):
        factory = StrategyFactory()
        d = StrategyDef(name="EmptyStrategy", blocks=[])
        result = factory.validate(d)
        assert not result.valid
        assert any("at least one" in e for e in result.errors)

    def test_unknown_block_fails(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="BadBlocks",
            blocks=[{"name": "NonExistentBlock", "weight": 10}],
        )
        result = factory.validate(d)
        assert not result.valid
        assert any("not found" in e for e in result.errors)

    def test_duplicate_blocks_fails(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="DupBlocks",
            blocks=[
                {"name": "Double_Top", "weight": 20},
                {"name": "Double_Top", "weight": 15},
            ],
        )
        result = factory.validate(d)
        assert not result.valid
        assert any("Duplicate" in e for e in result.errors)

    def test_unachievable_confluence_fails(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="HighThreshold",
            blocks=[{"name": "Double_Top", "weight": 10}],
            min_confluence=100,
        )
        result = factory.validate(d)
        assert not result.valid
        assert any("not achievable" in e for e in result.errors)

    def test_leverage_over_1_fails(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="Leveraged",
            blocks=[{"name": "Double_Top", "weight": 10}],
            max_leverage=2.0,
        )
        result = factory.validate(d)
        assert not result.valid
        assert any("leverage" in e.lower() for e in result.errors)

    def test_high_risk_warns(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="Risky",
            blocks=[{"name": "Double_Top", "weight": 10}],
            min_confluence=10,
            risk_per_trade_pct=10.0,
        )
        result = factory.validate(d)
        assert result.valid  # warn only, not fail
        assert len(result.warnings) > 0

    def test_valid_definition_passes(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="ValidStrategy",
            number="99",
            blocks=[
                {"name": "Double_Top", "weight": 30},
                {"name": "RSI_Divergence", "weight": 25},
                {"name": "VWAP", "weight": 15},
            ],
            min_confluence=50,
            max_leverage=1.0,
        )
        result = factory.validate(d)
        assert result.valid, f"Errors: {result.errors}"
        assert len(result.errors) == 0


class TestStrategyFactoryGeneration:
    """Test code generation."""

    def test_generated_code_is_valid_python(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="TestGenStrategy",
            number="99",
            config_path="test_config.json",
            blocks=[
                {"name": "Double_Top", "weight": 30},
                {"name": "RSI_Divergence", "weight": 25},
            ],
            min_confluence=50,
            entry_rules=["Rule 1", "Rule 2"],
            exit_rules=["Exit 1", "Exit 2"],
        )
        source, filename = factory.generate(d)
        assert len(source) > 0
        assert filename.endswith(".py")
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")

    def test_generated_code_has_risk_enforcer(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="RiskEnforcerTest",
            number="99",
            blocks=[{"name": "Double_Top", "weight": 10}],
        )
        source, _ = factory.generate(d)
        assert "from src.strategies.risk_enforcer import RiskEnforcer" in source
        assert "self.risk = RiskEnforcer(self)" in source
        assert "self.risk.check_and_submit" in source

    def test_generated_code_has_confluence_calculator(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="ConfluenceTest",
            number="99",
            blocks=[{"name": "Double_Top", "weight": 10}],
        )
        source, _ = factory.generate(d)
        assert "ConfluenceCalculator" in source

    def test_generated_code_uses_quantity_and_price_types(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="TypeTest",
            number="99",
            blocks=[{"name": "Double_Top", "weight": 10}],
        )
        source, _ = factory.generate(d)
        assert "Quantity.from_str" in source
        assert "Price(str(round" in source
        assert "Money(f" in source

    def test_generated_code_uses_enum_order_side(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="EnumTest", number="99",
            entry_side="SHORT",
            blocks=[{"name": "Double_Top", "weight": 10}],
        )
        source, _ = factory.generate(d)
        assert "OrderSide.SELL" in source

        d2 = StrategyDef(
            name="EnumTest2", number="99",
            entry_side="LONG",
            blocks=[{"name": "Double_Top", "weight": 10}],
        )
        source2, _ = factory.generate(d2)
        assert "OrderSide.BUY" in source2

    def test_generated_code_has_proper_class_name(self):
        factory = StrategyFactory()
        d = StrategyDef(name="My Cool Strategy", number="01", blocks=[{"name": "Double_Top", "weight": 10}])
        source, filename = factory.generate(d)
        assert "class MyCoolStrategy(Strategy):" in source
        assert filename == "strategy_01_my_cool_strategy.py"

    def test_generated_code_has_on_bar_method(self):
        factory = StrategyFactory()
        d = StrategyDef(name="OnBarTest", number="99", blocks=[{"name": "Double_Top", "weight": 10}])
        source, _ = factory.generate(d)
        assert "def on_bar(self, bar: Bar):" in source
        assert "def on_start(self):" in source
        assert "def on_stop(self):" in source

    def test_generated_code_has_tp_sl_logic(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="TPSLTest", number="99",
            entry_side="SHORT",
            blocks=[{"name": "Double_Top", "weight": 10}],
        )
        source, _ = factory.generate(d)
        assert "self.sl_atr_multiplier" in source
        assert "self.tp1_multiplier" in source
        assert "self.tp2_multiplier" in source
        assert "self.tp3_multiplier" in source

    def test_long_side_tp_sl_direction(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="LongTest", number="99",
            entry_side="LONG",
            blocks=[{"name": "Double_Top", "weight": 10}],
        )
        source, _ = factory.generate(d)
        assert "sl = current_price - (atr * self.sl_atr_multiplier)" in source
        assert "tp1 = current_price + (atr * self.tp1_multiplier)" in source

    def test_short_side_tp_sl_direction(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="ShortTest", number="99",
            entry_side="SHORT",
            blocks=[{"name": "Double_Top", "weight": 10}],
        )
        source, _ = factory.generate(d)
        assert "sl = current_price + (atr * self.sl_atr_multiplier)" in source
        assert "tp1 = current_price - (atr * self.tp1_multiplier)" in source


class TestStrategyFactoryLoadFromJSON:
    """Test loading definitions from JSON."""

    def test_load_definition_from_json(self):
        factory = StrategyFactory()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "name": "JSONTest",
                "number": "42",
                "building_blocks": [
                    {"name": "Double_Top", "weight": 30},
                    {"name": "VWAP", "weight": 15},
                ],
                "min_confluence": 40,
            }, f)
            fpath = f.name

        try:
            d = factory.load_definition(fpath)
            assert d.name == "JSONTest"
            assert d.number == "42"
            assert len(d.blocks) == 2
            assert d.min_confluence == 40
        finally:
            os.unlink(fpath)

    def test_generate_and_write(self):
        factory = StrategyFactory()
        d = StrategyDef(
            name="WriteTest", number="99",
            min_confluence=10,
            blocks=[{"name": "Double_Top", "weight": 30}],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path, validation = factory.generate_and_write(d, output_dir=tmpdir)
            assert validation.valid
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "class WriteTest(Strategy):" in content


class TestStrategyFactoryBatchGeneration:
    """Test batch generation."""

    def test_batch_generation(self):
        factory = StrategyFactory()
        defs = [
            StrategyDef(name="Batch1", number="01", min_confluence=10, blocks=[{"name": "Double_Top", "weight": 10}]),
            StrategyDef(name="Batch2", number="02", min_confluence=10, blocks=[{"name": "VWAP", "weight": 10}]),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            results = factory.batch_generate(defs, output_dir=tmpdir)
            assert len(results) == 2
            for path, validation in results:
                assert validation.valid
                assert os.path.exists(path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

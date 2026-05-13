"""
Regression tests for BTCAAAAA-747: implement NautilusCodeGenerator production
module + builder UI hook.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-747
Fixed in commit: 26ed89ec
Component: src/strategy_builder/core/nautilus_code_generator.py

Root cause: NautilusTrader strategy code generation was missing — the Strategy
Builder UI had no way to produce production-ready NautilusTrader strategy Python
files. Fix implemented NautilusCodeGenerator with full strategy code generation
(imports, class definition, on_start/on_tick methods, signal evaluation, and
order management).
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-747"),
    pytest.mark.regression,
]

SOURCE_MODULE = "src/strategy_builder/core/nautilus_code_generator.py"
ORCHESTRATOR_MODULE = "src/strategy_builder/integration/strategy_builder_orchestrator.py"


class TestNautilusCodeGeneratorImportable:
    """Verify the NautilusCodeGenerator class is importable and callable."""

    def test_nautilus_code_generator_importable(self):
        from src.strategy_builder.core.nautilus_code_generator import NautilusCodeGenerator
        assert callable(NautilusCodeGenerator)

    def test_generated_code_dataclass_importable(self):
        from src.strategy_builder.core.nautilus_code_generator import GeneratedCode
        code = GeneratedCode(strategy_code="x", config_dict={}, file_name="x.py")
        assert code.strategy_code == "x"

    def test_code_validation_result_importable(self):
        from src.strategy_builder.core.nautilus_code_generator import CodeValidationResult
        r = CodeValidationResult(is_valid=True, errors=[])
        assert r.is_valid is True


class TestNautilusCodeGeneratorGenerate:
    """Verify NautilusCodeGenerator.generate() produces valid output."""

    def _make_minimal_config(self):
        from src.strategy_builder.core.strategy_config_engine import (
            StrategyConfig, BlockConfig, SignalConfig,
        )
        config = StrategyConfig()
        config.name = "RegressionTestStrategy"
        block = BlockConfig(name="TestBlock", logic="AND", signals=[])
        block.signals.append(SignalConfig(name="TEST_SIGNAL", logic="AND"))
        config.blocks.append(block)
        return config

    def test_generate_returns_generated_code(self):
        from src.strategy_builder.core.nautilus_code_generator import (
            NautilusCodeGenerator, GeneratedCode,
        )
        gen = NautilusCodeGenerator()
        result = gen.generate(self._make_minimal_config())
        assert isinstance(result, GeneratedCode)

    def test_generated_code_has_nautilus_imports(self):
        from src.strategy_builder.core.nautilus_code_generator import NautilusCodeGenerator
        gen = NautilusCodeGenerator()
        result = gen.generate(self._make_minimal_config())
        assert "from nautilus_trader" in result.strategy_code

    def test_generated_code_has_class_definition(self):
        from src.strategy_builder.core.nautilus_code_generator import NautilusCodeGenerator
        gen = NautilusCodeGenerator()
        result = gen.generate(self._make_minimal_config())
        assert "class RegressionTestStrategy(Strategy):" in result.strategy_code

    def test_generated_code_is_valid_python(self):
        from src.strategy_builder.core.nautilus_code_generator import NautilusCodeGenerator
        gen = NautilusCodeGenerator()
        result = gen.generate(self._make_minimal_config())
        validation = gen.validate_syntax(result.strategy_code)
        assert validation.is_valid is True, f"Syntax errors: {validation.errors}"

    def test_generated_code_has_on_bar_method(self):
        from src.strategy_builder.core.nautilus_code_generator import NautilusCodeGenerator
        gen = NautilusCodeGenerator()
        result = gen.generate(self._make_minimal_config())
        assert "def on_bar" in result.strategy_code

    def test_generated_file_name_from_config(self):
        from src.strategy_builder.core.nautilus_code_generator import NautilusCodeGenerator
        gen = NautilusCodeGenerator()
        result = gen.generate(self._make_minimal_config())
        assert result.file_name == "regressionteststrategy.py"


class TestNautilusCodeGeneratorFixSpecific:
    """Tests that specifically validate the BTCAAAAA-747 fix."""

    def test_code_generator_source_has_validate_syntax_method(self):
        source = open(SOURCE_MODULE).read()
        assert "def validate_syntax" in source

    def test_code_generator_source_has_generate_method(self):
        source = open(SOURCE_MODULE).read()
        assert "def generate" in source

    def test_code_generator_source_uses_ast_parse_for_validation(self):
        source = open(SOURCE_MODULE).read()
        assert "ast.parse" in source

    def test_generate_with_multiple_blocks_produces_combined_code(self):
        from src.strategy_builder.core.nautilus_code_generator import NautilusCodeGenerator
        from src.strategy_builder.core.strategy_config_engine import (
            StrategyConfig, BlockConfig, SignalConfig,
        )
        config = StrategyConfig()
        config.name = "MultiBlock"
        for name in ("Block_A", "Block_B"):
            block = BlockConfig(name=name, logic="AND", signals=[])
            block.signals.append(SignalConfig(name=f"SIG_{name}", logic="AND"))
            config.blocks.append(block)
        gen = NautilusCodeGenerator()
        result = gen.generate(config)
        assert "_check_block_a" in result.strategy_code
        assert "_check_block_b" in result.strategy_code

    def test_orchestrator_has_generate_code_method(self):
        source = open(ORCHESTRATOR_MODULE).read()
        assert "def generate_code" in source

    def test_orchestrator_generate_code_imports_nautilus_code_generator(self):
        source = open(ORCHESTRATOR_MODULE).read()
        assert "NautilusCodeGenerator" in source

    def test_invalid_syntax_reports_error(self):
        from src.strategy_builder.core.nautilus_code_generator import NautilusCodeGenerator
        gen = NautilusCodeGenerator()
        result = gen.validate_syntax("def broken(")
        assert result.is_valid is False
        assert len(result.errors) > 0

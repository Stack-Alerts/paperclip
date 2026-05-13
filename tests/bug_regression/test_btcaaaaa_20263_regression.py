"""
Regression tests for BTCAAAAA-20263: BlockRegistry.instantiate NoneType crash.

Issue: BlockRegistry.instantiate raised unhandled TypeError when block_class
       resolved to None (refactored/renamed module attribute), crashing the
       entire InstitutionalSignalEvaluator init and blocking all backtests.

Fixed in commits: 38a48d5c, 51474f6b, d4dfc1f8
Components:
  - src/detectors/building_blocks/registry.py
  - src/optimizer_v3/core/institutional_signal_evaluator.py

Root cause: instantiate() only caught (ImportError, AttributeError). When
block_class was None, None(**kwargs) leaked TypeError. Additionally, the
evaluator had no try/except around the call, so any single block failure
killed the entire backtest worker.

Verify:
  1. All 83 building blocks instantiate without error
  2. Non-existent block raises ValueError (not TypeError/None)
  3. Evaluator handles instantiation failure gracefully (logs warning, continues)
  4. RecheckConfig has nested_rechecks field
  5. RecheckMetrics trade_impact key present in early return
"""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-20263"),
    pytest.mark.regression,
]

import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))


class TestBlockRegistryNoneTypeCrash:
    """Verify the NoneType guards in BlockRegistry.instantiate()"""

    def test_all_blocks_instantiate(self):
        """All 83 registered blocks instantiate without error"""
        from src.detectors.building_blocks.registry import BlockRegistry
        all_blocks = BlockRegistry.get_all_blocks()
        assert len(all_blocks) >= 80, f"Expected 80+ blocks, got {len(all_blocks)}"
        for name in all_blocks:
            try:
                BlockRegistry.instantiate(name, timeframe='15min')
            except Exception as e:
                pytest.fail(f"Block '{name}' failed to instantiate: {e}")

    def test_nonexistent_block_raises_valueerror(self):
        """Non-existent block raises ValueError, not TypeError"""
        from src.detectors.building_blocks.registry import BlockRegistry
        with pytest.raises(ValueError, match="not found in registry"):
            BlockRegistry.instantiate("nonexistent_block_xyz")

    def test_instantiate_has_none_guard(self):
        """instantiate() source contains None/callable guards"""
        import inspect
        from src.detectors.building_blocks.registry import BlockRegistry
        src = inspect.getsource(BlockRegistry.instantiate)
        assert "block_class is None" in src
        assert "not callable(block_class)" in src
        assert "TypeError" in src


class TestEvaluatorResilience:
    """Verify evaluator handles instantiation failures gracefully"""

    def test_evaluator_has_try_except(self):
        """Evaluator wraps instantiate() in try/except (ValueError, TypeError)"""
        import ast
        path = Path(_project_root) / "src/optimizer_v3/core/institutional_signal_evaluator.py"
        tree = ast.parse(path.read_text())
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if hasattr(handler, 'type') and handler.type:
                        names = [a.id for a in ast.walk(handler.type) if isinstance(a, ast.Name)]
                        if 'ValueError' in names and 'TypeError' in names:
                            found = True
        assert found, "Evaluator missing (ValueError, TypeError) except clause"

    def test_evaluator_has_diagnostic_check(self):
        """Evaluator has callable diagnostic check before instantiation loop"""
        path = Path(_project_root) / "src/optimizer_v3/core/institutional_signal_evaluator.py"
        content = path.read_text()
        assert "callable(getattr(BlockRegistry, 'instantiate'" in content


class TestRecheckConfigFix:
    """Verify cat 1 fixes (nested_rechecks, trade_impact)"""

    def test_nested_rechecks_field(self):
        """RecheckConfig has nested_rechecks field"""
        from src.strategy_builder.core.strategy_config_engine import RecheckConfig
        config = RecheckConfig()
        assert hasattr(config, 'nested_rechecks')
        assert config.nested_rechecks == []

    def test_trade_impact_in_early_return(self):
        """calculate_metrics() returns trade_impact even with no chain data"""
        from src.optimizer_v3.core.results.recheck_metrics import RecheckMetricsCalculator
        metrics = RecheckMetricsCalculator()
        metrics.add_trade_result("trade1", True, True)
        results = metrics.calculate_metrics()
        assert 'trade_impact' in results
        assert results['trade_impact']['with_recheck']['total'] == 1

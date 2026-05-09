"""
Regression test for BTCAAAAA-778: TypeError when block.exit_conditions is None.

Root cause: DictWrapper.__getattr__ returns None for missing/null dict keys, and
hasattr() on DictWrapper never raises AttributeError. The old _signal_exists_in_config
code did:
    if hasattr(block, 'exit_conditions'):
        for exit_cond in block.exit_conditions:   # TypeError: NoneType not iterable
This fired on every bar when LiquiditySweep (or any block) had no exit_conditions
configured (stored as null in the DB).

Fix: replaced all three hasattr-guard patterns with (getattr(..., None) or []) so
iterating over None is safe.
"""
import unittest
from unittest.mock import patch, MagicMock

from src.strategy_builder.ui.backtest_config_panel import DictWrapper
from src.optimizer_v3.core.institutional_signal_evaluator import InstitutionalSignalEvaluator


def _make_config(exit_conditions_value) -> DictWrapper:
    """Build a minimal DictWrapper strategy config.

    The block 'liquidity_sweep' has:
      - one entry signal 'BULLISH_SWEEP'
      - exit_conditions set to whatever is passed (None, [], or a real list)
    """
    return DictWrapper({
        'blocks': [
            {
                'name': 'liquidity_sweep',
                'logic': 'AND',
                'signals': [
                    {'name': 'BULLISH_SWEEP', 'exit_conditions': exit_conditions_value},
                ],
                'exit_conditions': exit_conditions_value,
            }
        ],
        'exit_conditions': exit_conditions_value,
        'required_signals': 1,
        'name': 'test_strategy',
        'strategy_type': 'Bullish',
    })


def _make_evaluator(config: DictWrapper) -> InstitutionalSignalEvaluator:
    """Construct the evaluator, suppressing all side-effectful init work.

    RecheckValidator, TimingChainManager, ExitHierarchyEvaluator, and
    ConfluenceCalculator are local imports inside __init__, so they cannot be
    patched at the module level. Patching __init__ directly is cleaner.
    """
    def _stub_init(self, strategy_config):
        self.strategy_config = strategy_config
        self.building_blocks = {}
        self.exit_conditions = {}
        self.logger = MagicMock()

    with patch.object(InstitutionalSignalEvaluator, '__init__', _stub_init):
        return InstitutionalSignalEvaluator(config)


class TestSignalExistsInConfigNoneExitConditions(unittest.TestCase):
    """_signal_exists_in_config must not raise TypeError when exit_conditions is None."""

    def test_block_exit_conditions_none_does_not_raise(self):
        """BTCAAAAA-778: block.exit_conditions = None → no TypeError."""
        evaluator = _make_evaluator(_make_config(exit_conditions_value=None))
        try:
            result = evaluator._signal_exists_in_config('liquidity_sweep', 'BULLISH_SWEEP')
        except TypeError as exc:
            self.fail(
                f"_signal_exists_in_config raised TypeError with None exit_conditions: {exc}"
            )
        # BULLISH_SWEEP is in entry signals → should still be found
        self.assertTrue(result)

    def test_block_exit_conditions_empty_list_does_not_raise(self):
        """block.exit_conditions = [] → no error, entry signal still found."""
        evaluator = _make_evaluator(_make_config(exit_conditions_value=[]))
        result = evaluator._signal_exists_in_config('liquidity_sweep', 'BULLISH_SWEEP')
        self.assertTrue(result)

    def test_unknown_signal_returns_false_with_none_exit_conditions(self):
        """Signal not in entry or exit → False even when exit_conditions is None."""
        evaluator = _make_evaluator(_make_config(exit_conditions_value=None))
        result = evaluator._signal_exists_in_config('liquidity_sweep', 'UNKNOWN_SIGNAL')
        self.assertFalse(result)

    def test_unknown_block_returns_false(self):
        """Block not in config → False regardless of exit_conditions."""
        evaluator = _make_evaluator(_make_config(exit_conditions_value=None))
        result = evaluator._signal_exists_in_config('nonexistent_block', 'BULLISH_SWEEP')
        self.assertFalse(result)

    def test_signal_in_block_level_exit_conditions(self):
        """Signal configured only as a block-level exit → should be found."""
        config = DictWrapper({
            'blocks': [
                {
                    'name': 'liquidity_sweep',
                    'logic': 'AND',
                    'signals': [],
                    'exit_conditions': [{'signal_name': 'BEARISH_SWEEP'}],
                }
            ],
            'exit_conditions': None,
            'required_signals': 1,
        })
        evaluator = _make_evaluator(config)
        result = evaluator._signal_exists_in_config('liquidity_sweep', 'BEARISH_SWEEP')
        self.assertTrue(result)


class TestLiquiditySweepExitConditionsAttribute(unittest.TestCase):
    """LiquiditySweep instance must expose exit_conditions/entry_conditions as []."""

    def test_liquidity_sweep_has_empty_exit_conditions(self):
        from src.detectors.building_blocks.price_action.liquidity_sweep import LiquiditySweep
        block = LiquiditySweep()
        self.assertIsInstance(block.exit_conditions, list)
        self.assertEqual(block.exit_conditions, [])

    def test_liquidity_sweep_has_empty_entry_conditions(self):
        from src.detectors.building_blocks.price_action.liquidity_sweep import LiquiditySweep
        block = LiquiditySweep()
        self.assertIsInstance(block.entry_conditions, list)
        self.assertEqual(block.entry_conditions, [])


if __name__ == '__main__':
    unittest.main()

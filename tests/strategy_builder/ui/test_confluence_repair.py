"""
Regression tests for BacktestConfigPanel._repair_if_unreachable — BTCAAAAA-732.

Root cause: strategy loaded from database had only 2 blocks (max 30pts), while the
confluence threshold was 40pts → guaranteed 0 trades.  _repair_if_unreachable detects
this and merges missing blocks from user_strategies/current_strategy.json.

Covers:
- Reachable config: passes through unchanged
- Unreachable config + matching JSON: restores missing blocks, backtest unblocked
- Unreachable config + JSON still insufficient: returns None (blocks run)
- Unreachable config + no JSON file: returns None (blocks run) with clear message
- Unreachable config + JSON name mismatch: returns None (no spurious merge)
- Empty blocks config: unreachable, returns None
- Zero-weight signals default to minimum (10pts)
- Corrupt JSON file: exception caught, run blocked
- JSON with same blocks as config: no merge needed, run blocked
- Multiple missing blocks: all restored from JSON
- ai_request_preview_window: "no signals" warning only fires for in_strategy blocks
"""

from __future__ import annotations

import json
import types
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest


# ---------------------------------------------------------------------------
# Helper: build a stub bound to the real _repair_if_unreachable
# ---------------------------------------------------------------------------

def _make_stub():
    from src.strategy_builder.ui.backtest_config_panel import BacktestConfigPanel

    fn = BacktestConfigPanel._repair_if_unreachable

    stub = MagicMock()
    stub.results_text = MagicMock()
    stub._repair_if_unreachable = types.MethodType(fn, stub)
    return stub


# ---------------------------------------------------------------------------
# Helpers: minimal config dicts
# ---------------------------------------------------------------------------

def _two_block_config(threshold=40):
    """2-block config: max confluence = 15+15+20 = 50pts but BEARISH_CLIMAX is
    effectively unreachable in practice.  In terms of the *sum* check the max is
    50pts, so let's use a config where the sum IS less than the threshold."""
    return {
        'name': '50% Asia Rejection Simple',
        'strategy_type': 'Bearish',
        'confluence_threshold': threshold,
        'blocks': [
            {
                'name': 'asia_session_50_percent',
                'logic': 'AND',
                'signals': [
                    {'name': 'AT_ASIA_50', 'weight': 15},
                    {'name': 'BELOW_ASIA_50', 'weight': 15},
                ],
            },
            {
                'name': 'ema_55_vector',
                'logic': 'AND',
                'signals': [
                    {'name': 'BEARISH_CLIMAX', 'weight': 5},
                ],
            },
        ],
    }


def _three_block_json(name='50% Asia Rejection Simple'):
    """JSON reference with an extra liquidity_sweep block."""
    return {
        'name': name,
        'strategy_type': 'Bearish',
        'confluence_threshold': 40,
        'blocks': [
            {
                'name': 'asia_session_50_percent',
                'logic': 'AND',
                'signals': [
                    {'name': 'AT_ASIA_50', 'weight': 15},
                    {'name': 'BELOW_ASIA_50', 'weight': 15},
                ],
            },
            {
                'name': 'ema_55_vector',
                'logic': 'AND',
                'signals': [{'name': 'BEARISH_CLIMAX', 'weight': 5}],
            },
            {
                'name': 'liquidity_sweep',
                'logic': 'OR',
                'signals': [{'name': 'BEARISH_SWEEP', 'weight': 25}],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRepairIfUnreachable:

    def test_reachable_config_passes_through_unchanged(self, qapp):
        """If sum(weights) >= threshold the config must be returned as-is."""
        stub = _make_stub()
        cfg = {
            'name': 'StratA',
            'confluence_threshold': 30,
            'blocks': [
                {'name': 'block_a', 'signals': [{'weight': 20}, {'weight': 15}]},
            ],
        }
        result = stub._repair_if_unreachable(cfg)
        assert result is cfg
        stub.results_text.setText.assert_not_called()

    def test_unreachable_with_matching_json_restores_blocks(self, qapp):
        """Unreachable config → no auto-repair → run blocked with error message."""
        stub = _make_stub()
        cfg = _two_block_config(threshold=40)
        ref_json = json.dumps(_three_block_json())

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=ref_json)):
            result = stub._repair_if_unreachable(cfg)

        assert result is None, "Run must be blocked when confluence is unreachable"
        stub.results_text.setText.assert_called()
        msg = stub.results_text.setText.call_args[0][0]
        assert 'Unreachable' in msg

    def test_unreachable_with_json_still_insufficient_returns_none(self, qapp):
        """After merge if max is still < threshold → block the run."""
        stub = _make_stub()
        cfg = {
            'name': '50% Asia Rejection Simple',
            'confluence_threshold': 200,  # impossible even after merge
            'blocks': [
                {'name': 'block_a', 'signals': [{'weight': 5}]},
            ],
        }
        ref = {
            'name': '50% Asia Rejection Simple',
            'blocks': [
                {'name': 'block_a', 'signals': [{'weight': 5}]},
                {'name': 'block_b', 'signals': [{'weight': 5}]},
            ],
        }
        ref_json = json.dumps(ref)

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=ref_json)):
            result = stub._repair_if_unreachable(cfg)

        assert result is None
        stub.results_text.setText.assert_called()
        msg = stub.results_text.setText.call_args[0][0]
        assert 'Unreachable' in msg

    def test_unreachable_without_json_blocks_run(self, qapp):
        """No JSON file → run blocked with clear error message."""
        stub = _make_stub()
        cfg = _two_block_config(threshold=40)

        with patch('pathlib.Path.exists', return_value=False):
            result = stub._repair_if_unreachable(cfg)

        assert result is None
        stub.results_text.setText.assert_called()
        msg = stub.results_text.setText.call_args[0][0]
        assert 'threshold' in msg.lower() or 'unreachable' in msg.lower()

    def test_unreachable_json_name_mismatch_no_spurious_merge(self, qapp):
        """JSON has a different strategy name → no merge, run blocked."""
        stub = _make_stub()
        cfg = _two_block_config(threshold=40)
        ref_json = json.dumps(_three_block_json(name='Different Strategy'))

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=ref_json)):
            result = stub._repair_if_unreachable(cfg)

        assert result is None
        block_names = {b['name'] for b in cfg['blocks']}
        assert 'liquidity_sweep' not in block_names

    def test_empty_blocks_unreachable_returns_none(self, qapp):
        """Config with zero blocks → max_possible=0 → unreachable → None."""
        stub = _make_stub()
        cfg = {'name': 'EmptyStrat', 'confluence_threshold': 10, 'blocks': []}

        with patch('pathlib.Path.exists', return_value=False):
            result = stub._repair_if_unreachable(cfg)

        assert result is None
        stub.results_text.setText.assert_called()

    def test_zero_weight_signals_default_to_ten(self, qapp):
        """Signals with weight=0 get default 10 in max_possible calculation."""
        stub = _make_stub()
        cfg = {
            'name': 'ZeroWeight',
            'confluence_threshold': 10,
            'blocks': [
                {'name': 'block_a', 'signals': [{'weight': 0}]},
            ],
        }
        result = stub._repair_if_unreachable(cfg)
        assert result is cfg
        stub.results_text.setText.assert_not_called()

    def test_json_load_exception_falls_back_to_block_run(self, qapp):
        """Corrupt/malformed JSON → exception caught → run blocked."""
        stub = _make_stub()
        cfg = _two_block_config(threshold=40)

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='NOT VALID JSON')):
            result = stub._repair_if_unreachable(cfg)

        assert result is None
        stub.results_text.setText.assert_called()

    def test_repair_from_json_no_new_blocks_no_merge(self, qapp):
        """JSON has same blocks as config → repaired=False → None."""
        stub = _make_stub()
        cfg = _two_block_config(threshold=40)
        ref_json = json.dumps(_two_block_config())

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=ref_json)):
            result = stub._repair_if_unreachable(cfg)

        assert result is None
        block_names = {b['name'] for b in cfg['blocks']}
        assert len(block_names) == 2

    def test_repair_from_json_restores_multiple_missing_blocks(self, qapp):
        """Multiple blocks missing → no auto-repair → run blocked with error message."""
        stub = _make_stub()
        cfg = {
            'name': '50% Asia Rejection Simple',
            'confluence_threshold': 75,
            'blocks': [
                {'name': 'asia_session_50_percent', 'signals': [{'weight': 15}]},
            ],
        }
        ref = _three_block_json()
        ref['blocks'].append({
            'name': 'volume_confirmation',
            'logic': 'AND',
            'signals': [{'name': 'HIGH_VOLUME', 'weight': 30}],
        })
        ref_json = json.dumps(ref)

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=ref_json)):
            result = stub._repair_if_unreachable(cfg)

        assert result is None, "Run must be blocked when confluence is unreachable"
        stub.results_text.setText.assert_called()
        msg = stub.results_text.setText.call_args[0][0]
        assert 'Unreachable' in msg


# ---------------------------------------------------------------------------
# Test: ai_request_preview_window no-signals warning
# ---------------------------------------------------------------------------

class TestAIPreviewWindowNoSignalsWarning:

    def test_warning_fires_only_for_in_strategy_blocks(self, qapp):
        """\u26a0\ufe0f 'has NO signals!' warning must only fire for in_strategy=True blocks,
        not for compact-format catalog blocks (in_strategy absent/False)."""
        import logging
        from src.optimizer_v3.core.ai_request_preview_window import AIRequestPreviewWindow

        fn = AIRequestPreviewWindow._populate_blocks_section

        stub = MagicMock()
        stub.blocks_text = MagicMock()

        blocks_data = [
            # catalog block (compact format, NOT in strategy) — warning must NOT fire
            {'name': 'block_catalog', 'category': 'Test', 'description': 'x',
             'in_strategy': False, 'signals': []},
            # in-strategy block with empty signals — warning MUST fire
            {'name': 'block_strategy', 'category': 'Test', 'description': 'x',
             'in_strategy': True, 'signals': []},
            # in-strategy block with signals — warning must NOT fire
            {'name': 'block_has_signals', 'category': 'Test', 'description': 'x',
             'in_strategy': True,
             'signals': [{'name': 'SIG_A', 'description': 'desc'}]},
        ]

        with patch.object(
            logging.getLogger('src.optimizer_v3.core.ai_request_preview_window'),
            'warning'
        ) as mock_warn:
            fn(stub, blocks_data)

        warned_blocks = [call.args[0] for call in mock_warn.call_args_list]
        assert any('block_strategy' in w for w in warned_blocks), \
            "in_strategy block with no signals must warn"
        assert not any('block_catalog' in w for w in warned_blocks), \
            "catalog (non-strategy) block must NOT warn"
        assert not any('block_has_signals' in w for w in warned_blocks), \
            "block with signals must NOT warn"

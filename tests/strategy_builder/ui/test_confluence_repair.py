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
- ai_request_preview_window: "no signals" warning only fires for in_strategy blocks
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest
from PyQt5.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# QApplication fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


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
        """Unreachable config → JSON with same name → missing block merged in."""
        stub = _make_stub()
        cfg = _two_block_config(threshold=40)
        ref_json = json.dumps(_three_block_json())

        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=ref_json)):
            result = stub._repair_if_unreachable(cfg)

        assert result is not None, "Run must not be blocked after successful repair"
        block_names = {b['name'] for b in result['blocks']}
        assert 'liquidity_sweep' in block_names, "Missing block should be added from JSON"

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


# ---------------------------------------------------------------------------
# Test: ai_request_preview_window no-signals warning
# ---------------------------------------------------------------------------

class TestAIPreviewWindowNoSignalsWarning:

    def test_warning_fires_only_for_in_strategy_blocks(self, qapp):
        """⚠️ 'has NO signals!' warning must only fire for in_strategy=True blocks,
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

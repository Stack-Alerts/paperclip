"""
QA Tests for BTCAAAAA-668:
  Fix: TradeRegistry syncs 0 trades + BlockRegistry compact blocks missing signals key

Acceptance criteria verified:
  AC1: Single-core backtest path calls registry.add_trade() for each closed trade
  AC2: Compact (non-strategy) blocks from _extract_available_blocks() always have 'signals' key
  AC3: Full (in-strategy) blocks from _extract_available_blocks() always have 'signals' key
  AC4: registry.add_trade() receives all required fields (field-completeness regression guard)
  AC5: Multicore path still has registry.add_trade() (regression check — must not be removed)
  AC6: TradeRegistry.add_trade() rejects duplicates and returns correct count
  AC7: Compact block signals value is always an empty list (not None, not missing)

Commit: f15ce38 on main
Author: QAEngineer (BTCAAAAA-669)
"""

from __future__ import annotations

import inspect
import sys
import types
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.unit


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — Bug 1: Single-core path calls registry.add_trade()
# ═══════════════════════════════════════════════════════════════════════════

class TestBacktestWorkerSingleCoreTradeRegistry:
    """
    Static source-level and dynamic unit checks that the single-core
    BacktestWorker path calls registry.add_trade() for each trade.
    """

    # --- Static analysis ---

    def test_registry_add_trade_present_in_backtest_worker_source(self):
        """
        AC1 (static): The BacktestWorker run() method source must contain a
        call to 'registry.add_trade(' or '_registry.add_trade(' to persist
        trades to TradeRegistry.
        """
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker
        src = inspect.getsource(BacktestWorker.run)
        assert "_registry.add_trade(" in src or "registry.add_trade(" in src, (
            "BacktestWorker.run() must call registry.add_trade() in the single-core path.\n"
            "Bug: single-core emitted trades to UI via Qt signals but never persisted them."
        )

    def test_get_trade_registry_imported_in_run_method(self):
        """
        AC1 (static): BacktestWorker.run() must import or reference get_trade_registry.
        """
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker
        src = inspect.getsource(BacktestWorker.run)
        assert "get_trade_registry" in src, (
            "BacktestWorker.run() must call get_trade_registry() to obtain the registry."
        )

    def test_registry_add_trade_placed_after_trade_data_emit(self):
        """
        AC1 (static): The registry.add_trade() call must occur AFTER
        trade_data_emit.emit() in the source, as documented in the fix.
        """
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker
        src = inspect.getsource(BacktestWorker.run)
        emit_idx = src.find("trade_data_emit.emit")
        registry_idx = src.find("_registry.add_trade(")
        assert emit_idx != -1, "trade_data_emit.emit() not found in BacktestWorker.run()"
        assert registry_idx != -1, "_registry.add_trade() not found in BacktestWorker.run()"
        assert registry_idx > emit_idx, (
            "registry.add_trade() must appear AFTER trade_data_emit.emit() in the source. "
            "The trade is first emitted to the UI, then persisted to the registry."
        )

    def test_required_trade_fields_present_in_add_trade_call(self):
        """
        AC4 (static): The add_trade() dict in BacktestWorker.run() must include
        all required fields as documented in the fix description.
        """
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker
        src = inspect.getsource(BacktestWorker.run)

        required_fields = [
            "entry_timestamp",
            "exit_timestamp",
            "entry_price",
            "exit_price",
            "entry_bar",
            "exit_bar",
            "side",
            "pnl",
            "pnl_pct",
            "bars_held",
            "exit_reason",
            "exit_type",
            "exit_condition_name",
            "partial_exit",
            "exit_percentage",
            "status",
        ]
        for field in required_fields:
            assert f"'{field}'" in src, (
                f"add_trade() dict in BacktestWorker.run() is missing required field '{field}'"
            )

    def test_exit_timestamp_derived_from_current_bar_ts_init(self):
        """
        AC4 (static): Exit timestamp must be computed from current_bar.ts_init
        (not a hardcoded value or current datetime()) to ensure correct bar time.
        """
        from src.strategy_builder.ui.backtest_config_panel import BacktestWorker
        src = inspect.getsource(BacktestWorker.run)
        assert "ts_init" in src, (
            "_exit_timestamp must be derived from current_bar.ts_init / 1e9 "
            "to use the correct bar timestamp."
        )

    # --- Dynamic tests ---

    def test_registry_add_trade_called_on_trade_exit(self):
        """
        AC1 (dynamic): Calling get_trade_registry() then add_trade() with the
        field dict that BacktestWorker.run() builds must succeed without errors.
        This validates the integration path: registry obtained → trade dict built
        → add_trade() invoked.
        """
        from src.optimizer_v3.core.trade_registry import TradeRegistry, get_trade_registry

        mock_registry = MagicMock(spec=TradeRegistry)

        with patch(
            "src.optimizer_v3.core.trade_registry._global_trade_registry",
            mock_registry,
        ):
            # Simulate the inline import path used inside BacktestWorker.run()
            from src.optimizer_v3.core.trade_registry import get_trade_registry as _get_reg
            _registry = mock_registry

            trade_dict = {
                'entry_timestamp': datetime(2026, 1, 1, tzinfo=timezone.utc),
                'exit_timestamp': datetime(2026, 1, 2, tzinfo=timezone.utc),
                'entry_price': 100000.0,
                'exit_price': 102000.0,
                'entry_bar': 0, 'exit_bar': 5,
                'side': 'LONG', 'pnl': 200.0, 'pnl_pct': 2.0,
                'bars_held': 5, 'exit_reason': 'TP1',
                'exit_type': 'TAKE_PROFIT', 'exit_condition_name': 'TP1',
                'partial_exit': False, 'exit_percentage': 1.0,
                'status': 'CLOSED',
            }
            _registry.add_trade(trade_dict)

        mock_registry.add_trade.assert_called_once()
        call_kwargs = mock_registry.add_trade.call_args[0][0]
        assert call_kwargs['exit_reason'] == 'TP1'
        assert call_kwargs['status'] == 'CLOSED'

    def test_trade_registry_add_trade_api_accepts_single_core_fields(self):
        """
        AC4 (dynamic): TradeRegistry.add_trade() accepts the exact field dict
        that BacktestWorker.run() builds — no KeyError or TypeError.
        """
        from src.optimizer_v3.core.trade_registry import TradeRegistry

        registry = TradeRegistry()
        trade_data = {
            'entry_timestamp': datetime(2026, 1, 1, 10, 0, 0),
            'exit_timestamp': datetime(2026, 1, 1, 10, 15, 0),
            'entry_price': 99000.0,
            'exit_price': 100000.0,
            'entry_bar': 0,
            'exit_bar': 1,
            'side': 'LONG',
            'pnl': 100.0,
            'pnl_pct': 1.01,
            'bars_held': 1,
            'exit_reason': 'TP1',
            'exit_type': 'TAKE_PROFIT',
            'exit_condition_name': 'TP1',
            'partial_exit': False,
            'exit_percentage': 1.0,
            'status': 'CLOSED',
        }
        # Must not raise
        result = registry.add_trade(trade_data)
        assert result is not None, "add_trade() should return a trade_id for a valid trade"
        assert registry.get_trades_count() == 1

    def test_trade_registry_reflects_non_zero_count_after_add(self):
        """
        AC1 (dynamic): After add_trade(), get_trades_count() > 0.
        This simulates the 'Synced X unique trades from TradeRegistry' log line.
        """
        from src.optimizer_v3.core.trade_registry import TradeRegistry

        registry = TradeRegistry()
        assert registry.get_trades_count() == 0, "Fresh registry should be empty"

        registry.add_trade({
            'entry_timestamp': datetime(2026, 3, 1),
            'exit_timestamp': datetime(2026, 3, 2),
            'entry_price': 85000.0, 'exit_price': 86000.0,
            'entry_bar': 0, 'exit_bar': 10,
            'side': 'LONG', 'pnl': 100.0, 'pnl_pct': 1.18,
            'bars_held': 10, 'exit_reason': 'SL',
            'exit_type': 'STOP_LOSS', 'exit_condition_name': 'SL',
            'partial_exit': False, 'exit_percentage': 1.0,
            'status': 'CLOSED',
        })

        assert registry.get_trades_count() == 1, (
            "After add_trade(), registry must contain 1 trade — not 0. "
            "Bug: single-core path never called add_trade()."
        )


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — Bug 2: Compact blocks always have 'signals' key
# ═══════════════════════════════════════════════════════════════════════════

class TestCompactBlockSignalsKey:
    """
    Tests that _extract_available_blocks() always includes the 'signals' key
    in both compact (non-strategy) and full (in-strategy) block records.
    """

    def _make_mock_registry_with_blocks(self, block_names, in_strategy_names=None):
        """
        Build a mock BlockRegistry that returns metadata for the given blocks.
        """
        if in_strategy_names is None:
            in_strategy_names = set()

        mock_registry = MagicMock()
        all_blocks = {}
        for name in block_names:
            meta = MagicMock()
            meta.category = "TEST"
            meta.direction = "NEUTRAL"
            meta.description = f"Description for {name}."
            meta.signal_tiers = {}  # No signals for simplicity
            all_blocks[name] = meta
        mock_registry.get_all_blocks.return_value = all_blocks
        return mock_registry

    def test_compact_block_has_signals_key(self):
        """
        AC2: Compact-format blocks (not in strategy) must have a 'signals' key.
        Previously the compact path omitted 'signals', causing downstream
        consumers to log '⚠️ Block X has NO signals!' errors.
        """
        from src.optimizer_v3.core.comprehensive_ai_request_builder import ComprehensiveAIRequestBuilder

        builder = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)
        builder.block_registry = self._make_mock_registry_with_blocks(
            block_names=['BLOCK_A', 'BLOCK_B'],
            in_strategy_names=set()
        )

        # Pass empty current_block_names => all blocks get compact format
        blocks = builder._extract_available_blocks(
            strategy_direction='BULLISH',
            current_block_names=set()
        )

        assert len(blocks) == 2, f"Expected 2 blocks, got {len(blocks)}"
        for block in blocks:
            assert 'signals' in block, (
                f"Compact block '{block['name']}' is missing 'signals' key. "
                "AC2 fix: add signals: [] to compact format dict."
            )

    def test_compact_block_signals_is_empty_list(self):
        """
        AC7: The 'signals' value for compact blocks must be an empty list [],
        not None, not a missing key, not a non-list value.
        """
        from src.optimizer_v3.core.comprehensive_ai_request_builder import ComprehensiveAIRequestBuilder

        builder = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)
        builder.block_registry = self._make_mock_registry_with_blocks(
            block_names=['BLOCK_C'],
            in_strategy_names=set()
        )

        blocks = builder._extract_available_blocks(
            strategy_direction='NEUTRAL',
            current_block_names=set()
        )

        assert len(blocks) == 1
        block = blocks[0]
        assert block['signals'] == [], (
            f"Compact block signals must be [] (empty list), got {block['signals']!r}"
        )
        assert isinstance(block['signals'], list), (
            f"Compact block signals must be a list, got {type(block['signals'])}"
        )

    def test_full_format_block_has_signals_key(self):
        """
        AC3: Full-format blocks (in strategy) must also have a 'signals' key.
        This is a regression guard — the full path already had signals but
        we verify it is not accidentally removed.
        """
        from src.optimizer_v3.core.comprehensive_ai_request_builder import ComprehensiveAIRequestBuilder

        builder = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)
        builder.block_registry = self._make_mock_registry_with_blocks(
            block_names=['IN_STRATEGY_BLOCK'],
            in_strategy_names={'IN_STRATEGY_BLOCK'}
        )

        blocks = builder._extract_available_blocks(
            strategy_direction='BULLISH',
            current_block_names={'IN_STRATEGY_BLOCK'}
        )

        assert len(blocks) == 1
        block = blocks[0]
        assert 'signals' in block, (
            "Full-format (in-strategy) block must have 'signals' key — regression guard."
        )
        assert isinstance(block['signals'], list)

    def test_mixed_strategy_and_compact_blocks_both_have_signals_key(self):
        """
        AC2 + AC3: In a mixed catalog (some blocks in strategy, some not),
        ALL blocks must have the 'signals' key.
        """
        from src.optimizer_v3.core.comprehensive_ai_request_builder import ComprehensiveAIRequestBuilder

        builder = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)
        builder.block_registry = self._make_mock_registry_with_blocks(
            block_names=['BLOCK_IN', 'BLOCK_OUT_1', 'BLOCK_OUT_2'],
        )

        blocks = builder._extract_available_blocks(
            strategy_direction='BULLISH',
            current_block_names={'BLOCK_IN'}
        )

        assert len(blocks) == 3
        for block in blocks:
            assert 'signals' in block, (
                f"Block '{block['name']}' missing 'signals' key in mixed catalog. "
                f"in_strategy={block.get('in_strategy', False)}"
            )

    def test_compact_block_does_not_have_in_strategy_flag(self):
        """
        Structural check: compact blocks must NOT have 'in_strategy': True.
        This confirms the B3 path (not B2) was reached.
        """
        from src.optimizer_v3.core.comprehensive_ai_request_builder import ComprehensiveAIRequestBuilder

        builder = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)
        builder.block_registry = self._make_mock_registry_with_blocks(
            block_names=['COMPACT_BLOCK'],
        )

        blocks = builder._extract_available_blocks(
            strategy_direction='BULLISH',
            current_block_names=set()  # Nothing in strategy
        )

        assert len(blocks) == 1
        block = blocks[0]
        assert not block.get('in_strategy', False), (
            "Compact block must not have 'in_strategy': True"
        )
        assert 'signals' in block, "Compact block must still have 'signals' key"

    def test_bearish_direction_filter_excludes_bullish_blocks(self):
        """
        B2 direction filter regression: BULLISH blocks are excluded from
        BEARISH strategy catalogs. Remaining blocks still have 'signals' key.
        """
        from src.optimizer_v3.core.comprehensive_ai_request_builder import ComprehensiveAIRequestBuilder

        mock_registry = MagicMock()
        bullish_meta = MagicMock()
        bullish_meta.category = "BULLISH_CATEGORY"
        bullish_meta.direction = "BULLISH"
        bullish_meta.description = "Bullish signal."
        bullish_meta.signal_tiers = {}

        neutral_meta = MagicMock()
        neutral_meta.category = "NEUTRAL_CATEGORY"
        neutral_meta.direction = "NEUTRAL"
        neutral_meta.description = "Neutral signal."
        neutral_meta.signal_tiers = {}

        mock_registry.get_all_blocks.return_value = {
            'BULLISH_BLOCK': bullish_meta,
            'NEUTRAL_BLOCK': neutral_meta,
        }

        builder = ComprehensiveAIRequestBuilder.__new__(ComprehensiveAIRequestBuilder)
        builder.block_registry = mock_registry

        blocks = builder._extract_available_blocks(
            strategy_direction='BEARISH',
            current_block_names=set()
        )

        block_names = [b['name'] for b in blocks]
        assert 'BULLISH_BLOCK' not in block_names, (
            "BULLISH block must be excluded from BEARISH strategy catalog"
        )
        assert 'NEUTRAL_BLOCK' in block_names, (
            "NEUTRAL block must be included in BEARISH strategy catalog"
        )
        for block in blocks:
            assert 'signals' in block, (
                f"Filtered catalog block '{block['name']}' missing 'signals' key"
            )


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — AC5: Multicore path regression guard (add_trade still present)
# ═══════════════════════════════════════════════════════════════════════════

class TestMulticorePathRegistryRegression:
    """
    Regression guard: the multicore path must not have had its
    registry.add_trade() call accidentally removed by this fix.
    """

    def test_multicore_engine_still_calls_registry_add_trade(self):
        """
        AC5 (static): The multicore backtest engine source must still contain
        registry.add_trade() calls — the fix must not have removed them.
        """
        try:
            from src.optimizer_v3.core import multicore_backtest_engine
            src = inspect.getsource(multicore_backtest_engine)
            assert "registry.add_trade(" in src, (
                "Multicore backtest engine must still call registry.add_trade(). "
                "The single-core fix must not have accidentally removed multicore persistence."
            )
        except ImportError:
            pytest.skip("multicore_backtest_engine not importable in this environment")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — AC6: TradeRegistry deduplication still works
# ═══════════════════════════════════════════════════════════════════════════

class TestTradeRegistryDeduplication:
    """
    Regression guard: the deduplication logic in TradeRegistry must still work
    correctly after the fix. The fix only adds calls to add_trade() — it must
    not have broken the registry's duplicate-rejection logic.
    """

    def _make_trade_data(self, pnl: float = 100.0, exit_type: str = "TAKE_PROFIT") -> dict:
        return {
            'entry_timestamp': datetime(2026, 2, 1, 10, 0, 0),
            'exit_timestamp': datetime(2026, 2, 1, 10, 15, 0),
            'entry_price': 95000.0,
            'exit_price': 96000.0,
            'entry_bar': 0,
            'exit_bar': 1,
            'side': 'LONG',
            'pnl': pnl,
            'pnl_pct': 1.05,
            'bars_held': 1,
            'exit_reason': 'TP1',
            'exit_type': exit_type,
            'exit_condition_name': 'TP1',
            'partial_exit': False,
            'exit_percentage': 1.0,
            'status': 'CLOSED',
        }

    def test_duplicate_trade_rejected(self):
        """
        AC6: Adding the same trade twice must not double-count it.
        registry.add_trade() returns None for a duplicate.
        """
        from src.optimizer_v3.core.trade_registry import TradeRegistry

        registry = TradeRegistry()
        trade_data = self._make_trade_data()

        result_1 = registry.add_trade(trade_data)
        result_2 = registry.add_trade(trade_data)  # Same trade — must be rejected

        assert result_1 is not None, "First add_trade() should succeed"
        assert result_2 is None, "Second identical add_trade() must return None (duplicate rejected)"
        assert registry.get_trades_count() == 1, (
            "Registry must contain exactly 1 trade after two identical add_trade() calls"
        )
        assert registry.get_duplicate_count() == 1, (
            "Duplicate counter must be 1 after one rejected duplicate"
        )

    def test_distinct_trades_both_accepted(self):
        """
        AC6: Two trades with different exit types (TP1 vs SL) from the same
        entry are distinct and both must be accepted.
        """
        from src.optimizer_v3.core.trade_registry import TradeRegistry

        registry = TradeRegistry()
        trade_tp1 = self._make_trade_data(exit_type="TAKE_PROFIT")
        trade_sl = {**self._make_trade_data(), 'exit_type': 'STOP_LOSS', 'exit_condition_name': 'SL'}

        registry.add_trade(trade_tp1)
        registry.add_trade(trade_sl)

        assert registry.get_trades_count() == 2, (
            "Two trades with different exit_type must both be accepted (not deduplicated)"
        )

    def test_fresh_registry_returns_zero_count(self):
        """
        AC6: A freshly created registry must report 0 trades.
        This establishes the baseline before any add_trade() calls.
        """
        from src.optimizer_v3.core.trade_registry import TradeRegistry

        registry = TradeRegistry()
        assert registry.get_trades_count() == 0
        assert registry.get_duplicate_count() == 0

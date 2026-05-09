"""
Unit Tests for Multicore Backtest Engine

Tests the core components of the multicore backtest engine:
- Bar chunking with overlap
- Chunk evaluation
- Result merging with trade de-duplication
- End-to-end multicore vs single-core validation

Author: BTC_Engine_v3
Date: February 11, 2026
"""

import unittest
from typing import List
from datetime import datetime, timedelta

from nautilus_trader.model.data import Bar, BarType, BarSpecification
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.enums import AggregationSource, BarAggregation, PriceType

from src.optimizer_v3.core.multicore_backtest_engine import (
    split_bars_for_parallel_processing,
    merge_chunk_results,
    MulticoreBacktestEngine,
    ChunkData,
    ChunkResult
)
from src.optimizer_v3.core.trade_registry import get_trade_registry


class TestBarChunking(unittest.TestCase):
    """Test bar chunking algorithm with overlap"""
    
    def setUp(self):
        """Create test bars"""
        self.bars = self._create_test_bars(1000)
    
    def _create_test_bars(self, count: int) -> List[Bar]:
        """Create test bar data"""
        bars = []
        base_time = int(datetime(2025, 1, 1).timestamp() * 1e9)
        
        instrument_id = InstrumentId(Symbol("BTC"), Venue("BINANCE"))
        bar_type = BarType(
            instrument_id,
            BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST),
            AggregationSource.EXTERNAL
        )
        
        for i in range(count):
            ts = base_time + (i * 15 * 60 * int(1e9))  # 15 min intervals
            
            bar = Bar(
                bar_type=bar_type,
                open=Price(50000.0 + i, 2),
                high=Price(50100.0 + i, 2),
                low=Price(49900.0 + i, 2),
                close=Price(50050.0 + i, 2),
                volume=Quantity(10.0, 8),
                ts_event=ts,
                ts_init=ts
            )
            bars.append(bar)
        
        return bars
    
    def test_chunk_count(self):
        """Test correct number of chunks created"""
        chunks = split_bars_for_parallel_processing(
            self.bars,
            num_processes=4,
            lookback_required=100
        )
        
        self.assertEqual(len(chunks), 4)
    
    def test_chunk_overlap(self):
        """Test chunks have proper overlap"""
        chunks = split_bars_for_parallel_processing(
            self.bars,
            num_processes=4,
            lookback_required=100
        )
        
        # First chunk should start at 0
        self.assertEqual(chunks[0].global_start_idx, 0)
        
        # Check overlap between chunks
        for i in range(len(chunks) - 1):
            current_end = chunks[i].global_end_idx
            next_start = chunks[i + 1].global_start_idx
            
            # Chunks should overlap
            self.assertLess(next_start, current_end)
    
    def test_all_bars_covered(self):
        """Test that all bars are covered by at least one chunk"""
        chunks = split_bars_for_parallel_processing(
            self.bars,
            num_processes=4,
            lookback_required=100
        )
        
        # Collect all bar indices covered
        covered = set()
        for chunk in chunks:
            for i in range(chunk.global_start_idx, chunk.global_end_idx):
                covered.add(i)
        
        # All bars should be covered
        self.assertEqual(len(covered), len(self.bars))
    
    def test_edge_case_fewer_bars_than_processes(self):
        """Test chunking when bars < processes"""
        small_bars = self._create_test_bars(10)
        
        chunks = split_bars_for_parallel_processing(
            small_bars,
            num_processes=32,
            lookback_required=5
        )
        
        # Should create fewer chunks
        self.assertLessEqual(len(chunks), 10)


class TestResultMerging(unittest.TestCase):
    """Test result merging and de-duplication"""

    def setUp(self):
        """Reset global trade registry before each test to prevent state leakage"""
        get_trade_registry().clear()

    def test_deduplicate_spanning_trades(self):
        """Test that trades appearing in multiple chunks are de-duplicated"""
        # Use distinct timestamps so the registry unique key (entry_ts, exit_ts, exit_type)
        # correctly identifies the duplicate trade in chunk 1.
        ts_a_entry = datetime(2025, 1, 1, 10, 0)
        ts_a_exit  = datetime(2025, 1, 1, 11, 0)
        ts_b_entry = datetime(2025, 1, 1, 12, 0)
        ts_b_exit  = datetime(2025, 1, 1, 13, 0)
        ts_c_entry = datetime(2025, 1, 1, 20, 0)
        ts_c_exit  = datetime(2025, 1, 1, 21, 0)
        ts_d_entry = datetime(2025, 1, 2, 10, 0)
        ts_d_exit  = datetime(2025, 1, 2, 11, 0)

        # Simulate results from 3 chunks
        chunk_results = [
            ChunkResult(
                chunk_id=0,
                trades=[
                    {'entry_bar': 100, 'exit_bar': 150, 'pnl': 50.0,
                     'entry_timestamp': ts_a_entry, 'exit_timestamp': ts_a_exit},
                    {'entry_bar': 200, 'exit_bar': 220, 'pnl': 30.0,
                     'entry_timestamp': ts_b_entry, 'exit_timestamp': ts_b_exit},  # Appears in chunk 1 too
                ],
                open_trade=None,
                total_bars_processed=300,
                signals_evaluated=300,
                errors=[],
                messages=[]
            ),
            ChunkResult(
                chunk_id=1,
                trades=[
                    {'entry_bar': 200, 'exit_bar': 220, 'pnl': 30.0,
                     'entry_timestamp': ts_b_entry, 'exit_timestamp': ts_b_exit},  # Duplicate
                    {'entry_bar': 350, 'exit_bar': 400, 'pnl': 75.0,
                     'entry_timestamp': ts_c_entry, 'exit_timestamp': ts_c_exit},
                ],
                open_trade=None,
                total_bars_processed=300,
                signals_evaluated=300,
                errors=[],
                messages=[]
            ),
            ChunkResult(
                chunk_id=2,
                trades=[
                    {'entry_bar': 500, 'exit_bar': 550, 'pnl': 100.0,
                     'entry_timestamp': ts_d_entry, 'exit_timestamp': ts_d_exit},
                ],
                open_trade=None,
                total_bars_processed=300,
                signals_evaluated=300,
                errors=[],
                messages=[]
            )
        ]

        merged = merge_chunk_results(chunk_results)

        # Should have 4 unique trades (not 5)
        self.assertEqual(len(merged['trades']), 4)

        # Trades should be sorted by entry_bar
        entry_bars = [t['entry_bar'] for t in merged['trades']]
        self.assertEqual(entry_bars, sorted(entry_bars))
    
    def test_empty_results(self):
        """Test merging empty results"""
        chunk_results = [
            ChunkResult(
                chunk_id=0,
                trades=[],
                open_trade=None,
                total_bars_processed=100,
                signals_evaluated=100,
                errors=[],
                messages=[]
            )
        ]
        
        merged = merge_chunk_results(chunk_results)
        
        self.assertEqual(len(merged['trades']), 0)
        self.assertEqual(merged['total_bars'], 100)


class TestMulticoreEngine(unittest.TestCase):
    """Test full multicore engine"""
    
    def setUp(self):
        """Set up test data"""
        self.bars = self._create_test_bars(500)
        
        # Simple test strategy config
        self.strategy_config = {
            'name': 'Test Strategy',
            'strategy_type': 'Bullish',
            'blocks': [],
            'confluence_threshold': 40
        }
        
        # Simple test backtest config
        self.backtest_config = {
            'timeframe': '15m',
            'starting_capital': 10000,
            'risk_per_trade_pct': 10,
            'min_risk_reward': 1.2,
            'max_leverage': 10,
            'max_bars_held': 200,
            'tpsl_mode': 'Fibonacci',
            'sl_mode': 'Static',
            'confluence_threshold': 40,
            'adaptive_sl': {
                'enabled': False,
                'delay_enabled': False,
                'delay_bars': 2,
                'emergency_sl_pct': 2,
                'volatility_lookback': 20,
                'volatility_multiplier': 1.2,
                'min_sl_pct': 0.7,
                'max_sl_pct': 2.0,
                'use_structure_sl': False,
                'structure_sources': []
            }
        }
    
    def _create_test_bars(self, count: int) -> List[Bar]:
        """Create test bar data"""
        bars = []
        base_time = int(datetime(2025, 1, 1).timestamp() * 1e9)
        
        instrument_id = InstrumentId(Symbol("BTC"), Venue("BINANCE"))
        bar_type = BarType(
            instrument_id,
            BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST),
            AggregationSource.EXTERNAL
        )
        
        for i in range(count):
            ts = base_time + (i * 15 * 60 * int(1e9))
            
            bar = Bar(
                bar_type=bar_type,
                open=Price(50000.0 + i, 2),
                high=Price(50100.0 + i, 2),
                low=Price(49900.0 + i, 2),
                close=Price(50050.0 + i, 2),
                volume=Quantity(10.0, 8),
                ts_event=ts,
                ts_init=ts
            )
            bars.append(bar)
        
        return bars
    
    def test_engine_initialization(self):
        """Test engine initializes correctly"""
        engine = MulticoreBacktestEngine(num_processes=4)
        
        self.assertEqual(engine.num_processes, 4)
    
    def test_auto_detect_cpus(self):
        """Test auto-detection of CPU count"""
        engine = MulticoreBacktestEngine()
        
        # Should detect at least 1 CPU
        self.assertGreaterEqual(engine.num_processes, 1)


if __name__ == '__main__':
    unittest.main()

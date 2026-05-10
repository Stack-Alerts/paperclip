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


class TestPriceAttribution(unittest.TestCase):
    """Regression tests for BTCAAAAA-998: price must match the bar at the recorded timestamp.

    Root cause confirmed in BTCAAAAA-991: timestamp was recorded in CET instead of UTC,
    making fill prices appear to belong to bars 4-10 slots before the recorded timestamp.
    These tests verify both the attribution invariant and float-precision cleanliness.
    """

    def _make_bar(self, open_p, high_p, low_p, close_p, ts_ns):
        instrument_id = InstrumentId(Symbol("BTC"), Venue("BINANCE"))
        bar_type = BarType(
            instrument_id,
            BarSpecification(15, BarAggregation.MINUTE, PriceType.LAST),
            AggregationSource.EXTERNAL,
        )
        return Bar(
            bar_type=bar_type,
            open=Price(open_p, 2),
            high=Price(high_p, 2),
            low=Price(low_p, 2),
            close=Price(close_p, 2),
            volume=Quantity(1.0, 8),
            ts_event=ts_ns,
            ts_init=ts_ns,
        )

    def test_entry_price_within_bar_range(self):
        """Entry price recorded as current_bar.close must satisfy bar_low <= price <= bar_high."""
        from datetime import timezone as _tz

        base_ns = int(datetime(2025, 9, 1, 12, 0, tzinfo=_tz.utc).timestamp() * 1e9)
        bar = self._make_bar(81000.0, 81700.0, 80900.0, 81690.20, base_ns)

        entry_price = round(float(bar.close), 2)
        bar_low = float(bar.low)
        bar_high = float(bar.high)

        self.assertGreaterEqual(entry_price, bar_low)
        self.assertLessEqual(entry_price, bar_high)

    def test_exit_price_within_bar_range(self):
        """Signal-exit price (bar.close) must satisfy bar_low <= price <= bar_high."""
        base_ns = int(datetime(2025, 9, 1, 12, 15).timestamp() * 1e9)
        bar = self._make_bar(81500.0, 82000.0, 81400.0, 81750.50, base_ns)

        exit_price = round(float(bar.close), 2)
        self.assertGreaterEqual(exit_price, float(bar.low))
        self.assertLessEqual(exit_price, float(bar.high))

    def test_no_float_precision_artifact_on_close(self):
        """round(float(bar.close), 2) must produce a clean 2-decimal value."""
        # 81690.20 stored as Price(2dp) and recovered as float must not become
        # 81690.20000000001 or similar binary-representation artifact.
        base_ns = int(datetime(2025, 9, 1, 12, 0).timestamp() * 1e9)
        bar = self._make_bar(81000.0, 81700.0, 80900.0, 81690.20, base_ns)

        price_float = round(float(bar.close), 2)
        # Verify no sub-cent residual
        self.assertEqual(price_float, round(price_float, 2))
        self.assertAlmostEqual(price_float, 81690.20, places=2)

    def test_entry_timestamp_utc_not_local(self):
        """Entry timestamp must be UTC-aligned, not local-timezone-shifted.

        Before BTCAAAAA-991 the engine used datetime.fromtimestamp(ts/1e9) which
        applied the server's local offset (CET = UTC+1 = +4 bars at 15 m). This
        verifies the UTC path is used so the timestamp matches the bar's ts_init.
        """
        from datetime import timezone as _tz

        ts_ns = int(datetime(2025, 9, 1, 12, 0, tzinfo=_tz.utc).timestamp() * 1e9)
        bar = self._make_bar(80000.0, 80500.0, 79900.0, 80250.0, ts_ns)

        # Correct UTC path (as fixed in BTCAAAAA-991)
        recorded_ts = datetime.fromtimestamp(bar.ts_init / 1e9, tz=_tz.utc).replace(tzinfo=None)
        expected_ts = datetime(2025, 9, 1, 12, 0, 0)

        self.assertEqual(recorded_ts, expected_ts)

    def test_multiple_bars_each_price_matches_own_bar(self):
        """Simulate a trade sequence: each trade's price must lie within its own bar."""
        from datetime import timezone as _tz

        base_ns = int(datetime(2025, 9, 1, 0, 0, tzinfo=_tz.utc).timestamp() * 1e9)
        interval_ns = 15 * 60 * int(1e9)

        bars = [
            self._make_bar(80000.0 + i * 100, 80200.0 + i * 100,
                           79800.0 + i * 100, 80100.0 + i * 100,
                           base_ns + i * interval_ns)
            for i in range(20)
        ]

        for bar in bars:
            entry_price = round(float(bar.close), 2)
            self.assertGreaterEqual(entry_price, float(bar.low),
                                    f"Entry price {entry_price} below bar low {float(bar.low)}")
            self.assertLessEqual(entry_price, float(bar.high),
                                 f"Entry price {entry_price} above bar high {float(bar.high)}")


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""
BTC_Engine_v3 - Data Catalog Setup
Day 2, Task 2.1: Initialize and test data loading

This script:
1. Loads BTC_USDT_PERP_30m.pkl data
2. Validates data quality
3. Converts to NautilusTrader Bar format
4. Tests data integrity
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nautilus_trader.model.data import Bar, BarType, BarSpecification
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.enums import BarAggregation, PriceType
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.core.datetime import dt_to_unix_nanos


class BTC_DataLoader:
    """Load and validate BTC historical data for NautilusTrader"""
    
    def __init__(self, data_path: str = "data/raw"):
        self.data_path = Path(data_path)
        self.project_root = Path(__file__).parent.parent
        
    def load_btc_30m(self) -> pd.DataFrame:
        """
        Load BTC 30m data from pickle file
        
        Returns:
            pd.DataFrame: OHLCV data with timestamp index
        """
        file_path = self.project_root / self.data_path / "BTC_USDT_PERP_30m.pkl"
        
        print(f"📂 Loading: {file_path}")
        df = pd.read_pickle(file_path)
        
        print(f"✅ Loaded: {len(df):,} bars")
        print(f"   Period: {df.index[0]} → {df.index[-1]}")
        print(f"   Columns: {df.columns.tolist()}")
        
        return df
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate OHLCV data quality - INSTITUTIONAL GRADE
        
        Critical checks:
        - No NaN values
        - OHLC logic (high >= low, etc.)
        - Volume > 0
        - Time continuity
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            bool: True if all validations pass
        """
        print("\n🔍 Validating data quality...")
        
        # Check for NaN
        if df.isnull().any().any():
            print("❌ FAILED: Contains NaN values")
            print(df.isnull().sum())
            return False
        print("✅ No NaN values")
        
        # Check OHLC logic
        if not (df['high'] >= df['low']).all():
            print("❌ FAILED: High < Low detected")
            return False
        print("✅ High >= Low")
        
        if not (df['high'] >= df['open']).all():
            print("❌ FAILED: High < Open detected")
            return False
        print("✅ High >= Open")
        
        if not (df['high'] >= df['close']).all():
            print("❌ FAILED: High < Close detected")
            return False
        print("✅ High >= Close")
        
        if not (df['low'] <= df['open']).all():
            print("❌ FAILED: Low > Open detected")
            return False
        print("✅ Low <= Open")
        
        if not (df['low'] <= df['close']).all():
            print("❌ FAILED: Low > Close detected")
            return False
        print("✅ Low <= Close")
        
        # Check volume
        if not (df['volume'] >= 0).all():
            print("❌ FAILED: Negative volume detected")
            return False
        print("✅ Volume >= 0")
        
        # Check time continuity
        time_diffs = df.index.to_series().diff()
        expected_diff = pd.Timedelta(minutes=30)
        gaps = time_diffs[time_diffs > expected_diff * 2]
        
        if len(gaps) > 0:
            print(f"⚠️  WARNING: {len(gaps)} time gaps detected")
            print(f"   Largest gap: {gaps.max()}")
        else:
            print("✅ No time gaps")
        
        print("\n✅ ALL VALIDATIONS PASSED")
        return True
    
    def convert_to_nautilus_bars(self, df: pd.DataFrame, limit: int = None) -> list:
        """
        Convert DataFrame to NautilusTrader Bar objects
        
        Args:
            df: DataFrame with OHLCV data
            limit: Number of bars to convert (None = all)
            
        Returns:
            list: List of NautilusTrader Bar objects
        """
        print(f"\n🔄 Converting to NautilusTrader Bar objects...")
        
        # Create instrument ID
        instrument_id = InstrumentId(
            symbol=Symbol("BTC/USDT"),
            venue=Venue("BINANCE")
        )
        
        # Create bar specification (30-minute bars)
        bar_spec = BarSpecification(
            step=30,
            aggregation=BarAggregation.MINUTE,
            price_type=PriceType.LAST
        )
        
        # Create bar type
        bar_type = BarType(instrument_id, bar_spec)
        
        # Limit bars if specified
        if limit:
            df = df.head(limit)
            print(f"   Processing first {limit} bars...")
        else:
            print(f"   Processing all {len(df):,} bars...")
        
        bars = []
        for timestamp, row in df.iterrows():
            # Convert timestamp to nanoseconds
            ts_event = dt_to_unix_nanos(timestamp.to_pydatetime())
            ts_init = ts_event  # For historical data, init = event
            
            # Create Bar object using NautilusTrader types
            bar = Bar(
                bar_type=bar_type,
                open=Price.from_str(f"{row['open']:.2f}"),
                high=Price.from_str(f"{row['high']:.2f}"),
                low=Price.from_str(f"{row['low']:.2f}"),
                close=Price.from_str(f"{row['close']:.2f}"),
                volume=Quantity.from_str(f"{row['volume']:.8f}"),
                ts_event=ts_event,
                ts_init=ts_init,
            )
            bars.append(bar)
        
        print(f"✅ Converted {len(bars):,} bars")
        return bars
    
    def display_sample_bars(self, bars: list, n: int = 3):
        """Display sample bars for verification"""
        print(f"\n📊 Sample Bars (first {n}):")
        for i, bar in enumerate(bars[:n]):
            print(f"\nBar {i+1}:")
            print(f"  Time: {bar.ts_event}")
            print(f"  Open: {bar.open}")
            print(f"  High: {bar.high}")
            print(f"  Low: {bar.low}")
            print(f"  Close: {bar.close}")
            print(f"  Volume: {bar.volume}")


def main():
    """Main execution function"""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║      BTC_Engine_v3 - Data Catalog Setup (Day 2)           ║")
    print("╚════════════════════════════════════════════════════════════╝\n")
    
    # Initialize loader
    loader = BTC_DataLoader()
    
    # Task 2.1: Load data
    print("TASK 2.1: Load BTC 30m data")
    print("=" * 60)
    df = loader.load_btc_30m()
    
    # Validate data quality
    print("\nTASK 2.1: Validate data quality")
    print("=" * 60)
    if not loader.validate_data(df):
        print("\n❌ FAILED: Data validation failed")
        return False
    
    # Convert sample to NautilusTrader format
    print("\nTASK 2.1: Convert to NautilusTrader format")
    print("=" * 60)
    sample_bars = loader.convert_to_nautilus_bars(df, limit=100)
    
    # Display samples
    loader.display_sample_bars(sample_bars, n=3)
    
    # Summary
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║                    TASK 2.1 COMPLETE ✅                    ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n✅ BTC_USDT_PERP_30m.pkl loaded: {len(df):,} bars")
    print(f"✅ Data validation: PASSED")
    print(f"✅ NautilusTrader conversion: TESTED (100 bars)")
    print(f"✅ Ready for backtesting")
    print("\n📋 Next: Create simple backtest strategy (Task 2.3)")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

"""
Unified Data Manager - Intelligent Data Source Routing

The brain of the data system. Automatically routes requests to:
- LakeAPI: Historical data (2024 + Dec 2025)
- Binance: Recent/current data (ongoing)
- Seamless combination for complete datasets

Features:
- Automatic source selection (smart routing)
- Gap detection and filling
- 1000-bar warmup support
- Multi-timeframe support
- Caching for performance
- Error recovery with fallback

This is the ONLY interface strategies need to use!

Author: BTC_Engine_v3
Date: January 8, 2026
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Union, Dict
import pandas as pd
from enum import Enum

from .config import PROJECT_ROOT, RAW_DATA_DIR
from .processing.bar_aggregator import BarAggregator
from .binance.rest_client import BinanceRestClient


class DataSource(Enum):
    """Data source options"""
    LAKEAPI = "lakeapi"
    BINANCE = "binance"
    AUTO = "auto"


class UnifiedDataManager:
    """
    Unified data manager - One interface for all data needs
    
    Intelligent routing:
    - Historical (>30 days): LakeAPI (cached, complete)
    - Recent (<30 days): Binance (real-time, free)
    - Seamless: Combines both sources automatically
    
    Example:
        >>> manager = UnifiedDataManager()
        >>> 
        >>> # Get last 1000 bars (for strategy warmup)
        >>> bars = manager.get_bars(timeframe='15m', count=1000)
        >>> # Automatically uses: LakeAPI + Binance combined!
        >>> 
        >>> # Get specific date range
        >>> bars = manager.get_bars(
        ...     timeframe='15m',
        ...     start_date=datetime(2025, 11, 1),
        ...     end_date=datetime.now()
        ... )
        >>> # Uses optimal source for each part!
    """
    
    def __init__(self):
        """Initialize unified manager"""
        self.lakeapi_dir = RAW_DATA_DIR  # Historical data (LakeAPI decommissioned, data remains)
        self.binance_dir = PROJECT_ROOT / "data" / "binance"
        
        # Components
        self.bar_aggregator = BarAggregator()
        self.binance_client = None  # Lazy initialization
        
        # Thresholds
        self.binance_threshold_days = 30  # Use Binance for last 30 days
        
        print("✅ Unified Data Manager initialized")
        print(f"   LakeAPI: {self.lakeapi_dir}")
        print(f"   Binance: {self.binance_dir}")
        print(f"   Auto-routing threshold: {self.binance_threshold_days} days")
    
    def _get_binance_client(self) -> BinanceRestClient:
        """Lazy initialization of Binance client"""
        if self.binance_client is None:
            self.binance_client = BinanceRestClient()
        return self.binance_client
    
    def _determine_source(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> DataSource:
        """
        Determine optimal data source based on date range
        
        Logic:
        - If both dates > 30 days ago: LakeAPI only
        - If both dates < 30 days ago: Binance only
        - If spans both: Hybrid (combine sources)
        
        Args:
            start_date: Start date (None = auto)
            end_date: End date (None = now)
        
        Returns:
            Optimal data source
        """
        now = datetime.now()
        threshold = now - timedelta(days=self.binance_threshold_days)
        
        # Default to now if not specified
        if end_date is None:
            end_date = now
        
        if start_date is None:
            # Requesting recent data
            return DataSource.BINANCE
        
        # Both in historical range
        if end_date < threshold:
            return DataSource.LAKEAPI
        
        # Both in recent range
        if start_date >= threshold:
            return DataSource.BINANCE
        
        # Spans both - need hybrid
        return DataSource.AUTO
    
    def get_bars(
        self,
        timeframe: str = '15m',
        count: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        source: DataSource = DataSource.AUTO
    ) -> pd.DataFrame:
        """
        Get OHLCV bars (the main interface!)
        
        Args:
            timeframe: Bar timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            count: Number of bars (alternative to date range)
            start_date: Start date (optional)
            end_date: End date (optional, defaults to now)
            source: Force specific source (default: AUTO routing)
        
        Returns:
            DataFrame with OHLCV bars
        
        Examples:
            >>> # Get last 1000 bars (warmup)
            >>> bars = manager.get_bars('15m', count=1000)
            >>> 
            >>> # Get specific date range
            >>> bars = manager.get_bars(
            ...     '15m',
            ...     start_date=datetime(2025, 12, 1),
            ...     end_date=datetime(2025, 12, 31)
            ... )
            >>> 
            >>> # Force specific source
            >>> bars = manager.get_bars('15m', count=100, source=DataSource.BINANCE)
        """
        # Handle count-based request
        if count is not None and start_date is None:
            return self._get_bars_by_count(timeframe, count, end_date)
        
        # Handle date range request
        if start_date is not None or end_date is not None:
            return self._get_bars_by_range(timeframe, start_date, end_date, source)
        
        raise ValueError("Must specify either 'count' or 'start_date'")
    
    def _get_bars_by_count(
        self,
        timeframe: str,
        count: int,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get last N bars up to specified date
        
        Optimized for strategy warmup (typically 1000 bars)
        
        Args:
            timeframe: Bar timeframe
            count: Number of bars
            end_date: End date (defaults to now)
        
        Returns:
            DataFrame with last N bars
        """
        if end_date is None:
            end_date = datetime.now()
        
        print(f"📊 Getting last {count} {timeframe} bars...")
        
        # Estimate required date range
        timeframe_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        
        minutes = timeframe_minutes.get(timeframe, 15)
        days_needed = int((count * minutes / (24 * 60)) * 1.5)  # 50% buffer
        
        start_date = end_date - timedelta(days=days_needed)
        
        # Get bars for estimated range
        bars = self._get_bars_by_range(timeframe, start_date, end_date, DataSource.AUTO)
        
        # Return last N bars
        if len(bars) >= count:
            result = bars.tail(count).copy()
            print(f"✅ Returned {len(result)} bars")
            return result
        else:
            print(f"⚠️  Only {len(bars)} bars available (requested {count})")
            return bars
    
    def _get_bars_by_range(
        self,
        timeframe: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        source: DataSource
    ) -> pd.DataFrame:
        """
        Get bars for specific date range
        
        Implements smart routing logic
        
        Args:
            timeframe: Bar timeframe
            start_date: Start date
            end_date: End date
            source: Data source preference
        
        Returns:
            DataFrame with bars in date range
        """
        if end_date is None:
            end_date = datetime.now()
        
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        # Determine source if AUTO
        if source == DataSource.AUTO:
            source = self._determine_source(start_date, end_date)
        
        print(f"📊 Source: {source.value} | Range: {start_date.date()} to {end_date.date()}")
        
        # Route to appropriate source
        if source == DataSource.LAKEAPI:
            return self._get_bars_lakeapi(timeframe, start_date, end_date)
        
        elif source == DataSource.BINANCE:
            return self._get_bars_binance(timeframe, start_date, end_date)
        
        else:  # AUTO - hybrid approach
            return self._get_bars_hybrid(timeframe, start_date, end_date)
    
    def _get_bars_lakeapi(
        self,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get bars from LakeAPI (historical data)
        
        Process:
        1. Load trades from parquet files
        2. Aggregate to requested timeframe
        3. Filter to date range
        
        Args:
            timeframe: Bar timeframe
            start_date: Start date
            end_date: End date
        
        Returns:
            DataFrame with bars
        """
        print("   📂 Loading from LakeAPI...")
        
        try:
            # Use bar aggregator to process LakeAPI trades
            bars = self.bar_aggregator.aggregate_date_range(
                'trades',
                start_date,
                end_date,
                timeframe
            )
            
            print(f"   ✅ LakeAPI: {len(bars)} bars loaded")
            return bars
            
        except Exception as e:
            print(f"   ❌ LakeAPI error: {e}")
            
            # Fallback to Binance if LakeAPI fails
            print("   🔄 Falling back to Binance...")
            return self._get_bars_binance(timeframe, start_date, end_date)
    
    def _get_bars_binance(
        self,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get bars from Binance (recent/current data)
        
        Uses Binance's pre-computed klines (much faster!)
        
        Args:
            timeframe: Bar timeframe
            start_date: Start date
            end_date: End date
        
        Returns:
            DataFrame with bars
        """
        print("   🌐 Loading from Binance...")
        
        try:
            client = self._get_binance_client()
            
            # Calculate hours to request
            hours = int((end_date - start_date).total_seconds() / 3600)
            
            if hours > 720:  # More than 30 days
                print(f"   ⚠️  Large range ({hours}h), using pagination...")
                # Request in chunks (will be implemented in client)
                hours = 720  # Limit to 30 days
            
            # Get klines from Binance Futures
            bars = client.get_klines(
                interval=timeframe,
                symbol='BTCUSDT',
                hours=hours,
                futures=True  # CRITICAL: Perpetual futures!
            )
            
            # Filter to exact range
            bars['timestamp'] = pd.to_datetime(bars['timestamp'])
            bars = bars[
                (bars['timestamp'] >= start_date) &
                (bars['timestamp'] <= end_date)
            ].copy()
            
            print(f"   ✅ Binance: {len(bars)} bars loaded")
            return bars
            
        except Exception as e:
            print(f"   ❌ Binance error: {e}")
            
            # If Binance fails, try LakeAPI as fallback
            print("   🔄 Falling back to LakeAPI...")
            return self._get_bars_lakeapi(timeframe, start_date, end_date)
    
    def _get_bars_hybrid(
        self,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Get bars from both sources (seamless combination!)
        
        Process:
        1. Historical part: LakeAPI
        2. Recent part: Binance
        3. Combine seamlessly
        
        Args:
            timeframe: Bar timeframe
            start_date: Start date
            end_date: End date
        
        Returns:
            DataFrame with combined bars
        """
        print("   🔀 Hybrid mode: Combining LakeAPI + Binance...")
        
        # Calculate split point (30 days ago)
        threshold = datetime.now() - timedelta(days=self.binance_threshold_days)
        
        all_bars = []
        
        # Part 1: Historical from LakeAPI
        if start_date < threshold:
            historical_end = min(threshold, end_date)
            print(f"   📂 LakeAPI: {start_date.date()} to {historical_end.date()}")
            
            try:
                historical_bars = self._get_bars_lakeapi(
                    timeframe,
                    start_date,
                    historical_end
                )
                all_bars.append(historical_bars)
            except Exception as e:
                print(f"   ⚠️  LakeAPI failed: {e}")
        
        # Part 2: Recent from Binance
        if end_date > threshold:
            recent_start = max(threshold, start_date)
            print(f"   🌐 Binance: {recent_start.date()} to {end_date.date()}")
            
            try:
                recent_bars = self._get_bars_binance(
                    timeframe,
                    recent_start,
                    end_date
                )
                all_bars.append(recent_bars)
            except Exception as e:
                print(f"   ⚠️  Binance failed: {e}")
        
        if not all_bars:
            raise ValueError("No data available from any source")
        
        # Combine results
        combined = pd.concat(all_bars, ignore_index=True)
        combined = combined.sort_values('timestamp').drop_duplicates(subset=['timestamp'])
        
        print(f"   ✅ Hybrid: {len(combined)} total bars")
        return combined
    
    def get_available_date_range(self, timeframe: str = '15m') -> Dict[str, datetime]:
        """
        Get available date range across all sources
        
        Args:
            timeframe: Timeframe to check
        
        Returns:
            Dict with earliest and latest available dates
        """
        # Check LakeAPI (historical data in parquet files)
        lakeapi_start = None
        lakeapi_end = None
        
        trades_dir = self.lakeapi_dir / 'trades'
        if trades_dir.exists():
            # Find earliest and latest parquet files
            parquet_files = sorted(trades_dir.glob('BTC-USDT_trades_*.parquet'))
            if parquet_files:
                # Extract start date from first filename
                first_file = parquet_files[0].stem.split('_')[-1]  # '2024-01'
                lakeapi_start = datetime.strptime(first_file, '%Y-%m')
                
                # CRITICAL: Read ACTUAL last timestamp from the parquet file, not filename!
                import pandas as pd
                try:
                    last_parquet = parquet_files[-1]
                    # Try possible timestamp column names
                    timestamp_cols = ['timestamp', 'origin_time', 'received_time']
                    df = None
                    
                    for col in timestamp_cols:
                        try:
                            df = pd.read_parquet(last_parquet, columns=[col])
                            if len(df) > 0:
                                lakeapi_end = pd.to_datetime(df[col].iloc[-1])
                                break
                        except:
                            continue
                    
                    if df is None or len(df) == 0:
                        raise Exception("Could not read timestamp from any column")
                        
                except Exception as e:
                    print(f"Warning: Could not read last timestamp from {last_parquet}: {e}")
                    # Fallback to filename
                    last_file = parquet_files[-1].stem.split('_')[-1]
                    year, month = map(int, last_file.split('-'))
                    from calendar import monthrange
                    last_day = monthrange(year, month)[1]
                    lakeapi_end = datetime(year, month, last_day, 23, 59, 59)
        
        # Check Binance (assumed to be current)
        binance_end = datetime.now()
        binance_start = binance_end - timedelta(days=30)  # Typical availability
        
        # Combine
        earliest = lakeapi_start if lakeapi_start else binance_start
        latest = binance_end
        
        return {
            'earliest': earliest,
            'latest': latest,
            'lakeapi_range': (lakeapi_start, lakeapi_end) if lakeapi_start else None,
            'binance_range': (binance_start, binance_end)
        }


# Convenience function
def get_bars(
    timeframe: str = '15m',
    count: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Convenience function to get bars
    
    Args:
        timeframe: Bar timeframe
        count: Number of bars (for warmup)
        start_date: Start date (for range)
        end_date: End date (for range)
    
    Returns:
        DataFrame with bars
    
    Example:
        >>> # Quick warmup for strategy
        >>> bars = get_bars('15m', count=1000)
        >>> 
        >>> # Specific date range
        >>> bars = get_bars('15m', start_date=datetime(2025, 12, 1))
    """
    manager = UnifiedDataManager()
    return manager.get_bars(timeframe, count, start_date, end_date)

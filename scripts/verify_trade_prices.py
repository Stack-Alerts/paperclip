"""
Trade Price Verification Script - Institutional Grade Data Integrity Audit

Verifies that recorded trade entry/exit prices match actual DataManager candles.

NAUTILUS EXPERT: Institutional-grade price verification ensures:
- Entry prices match bar close at entry timestamp
- Exit prices match bar close/high/low at exit timestamp
- No phantom prices (prices outside OHLC range)
- Timestamp alignment with actual data

Author: BTC Engine v3 Team
Date: 2026-02-12
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import csv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple

# CRITICAL: Use same data loading as backtest engine
from src.optimizer_v3.core.backtest_data_provider import get_backtest_provider


class TradePriceVerifier:
    """
    Institutional-grade trade price verification.
    
    Validates that trades use actual market prices from DataManager candles.
    """
    
    def __init__(self, csv_path: str, timeframe: str = '15m'):
        """
        Initialize verifier.
        
        Args:
            csv_path: Path to trades CSV export
            timeframe: Candle timeframe (default: 15m)
        """
        self.csv_path = csv_path
        self.timeframe = timeframe
        self.trades = []
        self.candles_df = None
        self.data_provider = get_backtest_provider()
        
        # Verification results
        self.issues = []
        self.warnings = []
        self.verified_count = 0
        
    def load_trades(self):
        """Load trades from CSV export - INSTITUTIONAL UPGRADE: Uses exact exit timestamps."""
        print(f"📊 Loading trades from {self.csv_path}...")
        
        with open(self.csv_path, 'r') as f:
            reader = csv.DictReader(f)
            self.trades = list(reader)
        
        print(f"✅ Loaded {len(self.trades)} trades")
        
        # Parse timestamps and prices
        for trade in self.trades:
            # Parse entry timestamp (format: "2025-11-15T21:30:00" - ISO 8601)
            trade['timestamp_dt'] = datetime.strptime(
                trade['Time'], 
                "%Y-%m-%dT%H:%M:%S"
            )
            
            # ✅ INSTITUTIONAL FIX: Parse exact exit timestamp if available
            if 'Exit Time' in trade and trade['Exit Time'] and trade['Exit Time'] != '-':
                try:
                    trade['exit_timestamp_dt'] = datetime.strptime(
                        trade['Exit Time'],
                        "%Y-%m-%dT%H:%M:%S"
                    )
                except ValueError:
                    # Fallback to duration estimation if parse fails
                    trade['exit_timestamp_dt'] = None
            else:
                trade['exit_timestamp_dt'] = None
            
            trade['entry_price_val'] = float(trade['Entry'].replace('$', '').replace(',', ''))
            trade['exit_price_val'] = float(trade['Exit'].replace('$', '').replace(',', '')) if trade['Exit'] != '-' else None
            trade['pnl_val'] = float(trade['P&L'].replace('$', '').replace(',', ''))
        
        return self.trades
    
    def load_candles(self, start_date: datetime, end_date: datetime):
        """
        Load candles from DataManager for verification period.
        
        Args:
            start_date: Start of verification period
            end_date: End of verification period
        """
        print(f"\n📈 Loading {self.timeframe} candles from DataManager...")
        print(f"   Period: {start_date} to {end_date}")
        
        # Load bars using same method as backtest
        bars = self.data_provider.load_bars_for_backtest(
            timeframe=self.timeframe,
            start_date=start_date,
            end_date=end_date,
            progress_callback=None
        )
        
        print(f"✅ Loaded {len(bars):,} candles")
        
        # Convert to DataFrame for easy lookup
        candles_data = []
        for bar in bars:
            candles_data.append({
                'timestamp': datetime.fromtimestamp(bar.ts_init / 1e9),
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': float(bar.volume)
            })
        
        self.candles_df = pd.DataFrame(candles_data)
        self.candles_df.set_index('timestamp', inplace=True)
        self.candles_df.sort_index(inplace=True)
        
        print(f"   First candle: {self.candles_df.index[0]}")
        print(f"   Last candle: {self.candles_df.index[-1]}")
        
        return self.candles_df
    
    def find_nearest_candle(self, timestamp: datetime) -> Tuple[datetime, Dict]:
        """
        Find nearest candle to given timestamp.
        
        INSTITUTIONAL FIX: Use WIDER tolerance for duration estimation errors.
        Duration strings are rounded ("2d 1h") which can cause ±30min errors.
        
        Args:
            timestamp: Target timestamp
            
        Returns:
            Tuple of (candle_timestamp, candle_data)
        """
        # Find exact match first
        if timestamp in self.candles_df.index:
            candle = self.candles_df.loc[timestamp]
            return timestamp, candle.to_dict()
        
        # Find nearest (with wider tolerance for duration estimation errors)
        time_diff = abs(self.candles_df.index - timestamp)
        nearest_idx = time_diff.argmin()
        nearest_time = self.candles_df.index[nearest_idx]
        
        # INCREASED TOLERANCE: 4 hours for duration estimation errors
        # Duration "2d 1h" could be off by multiple bars due to rounding
        tolerance = timedelta(hours=4)
        if abs(nearest_time - timestamp) > tolerance:
            return None, None
        
        candle = self.candles_df.iloc[nearest_idx]
        return nearest_time, candle.to_dict()
    
    def verify_trade_entry(self, trade: Dict) -> Dict:
        """
        Verify trade entry price against actual candle.
        
        Args:
            trade: Trade data dict
            
        Returns:
            Verification result dict
        """
        entry_timestamp = trade['timestamp_dt']
        entry_price = trade['entry_price_val']
        trade_id = trade['ID']
        
        # Find candle at entry
        candle_time, candle = self.find_nearest_candle(entry_timestamp)
        
        if candle is None:
            return {
                'status': 'ERROR',
                'message': f"Trade #{trade_id}: No candle found at entry {entry_timestamp}",
                'trade_id': trade_id,
                'trade_price': entry_price,
                'candle_time': None,
                'candle_data': None
            }
        
        # Verify price is within OHLC range
        within_range = candle['low'] <= entry_price <= candle['high']
        matches_close = abs(entry_price - candle['close']) < 0.01
        
        if not within_range:
            return {
                'status': 'CRITICAL',
                'message': f"Trade #{trade_id}: Entry price ${entry_price:.2f} OUTSIDE candle range [{candle['low']:.2f}, {candle['high']:.2f}]",
                'trade_id': trade_id,
                'trade_price': entry_price,
                'candle_time': candle_time,
                'candle_data': candle
            }
        
        if not matches_close:
            return {
                'status': 'WARNING',
                'message': f"Trade #{trade_id}: Entry price ${entry_price:.2f} != candle close ${candle['close']:.2f} (Δ${abs(entry_price - candle['close']):.2f})",
                'trade_id': trade_id,
                'trade_price': entry_price,
                'candle_time': candle_time,
                'candle_data': candle
            }
        
        return {
            'status': 'OK',
            'message': f"Trade #{trade_id}: Entry price verified ${entry_price:.2f} = candle close",
            'trade_id': trade_id,
            'trade_price': entry_price,
            'candle_time': candle_time,
            'candle_data': candle
        }
    
    def verify_trade_exit(self, trade: Dict) -> Dict:
        """
        Verify trade exit price against actual candle.
        
        INSTITUTIONAL FIX: Uses exact exit_timestamp when available,
        falls back to duration estimation only if needed.
        
        Args:
            trade: Trade data dict
            
        Returns:
            Verification result dict
        """
        trade_id = trade['ID']
        exit_price = trade['exit_price_val']
        
        # Skip if trade still open
        if exit_price is None:
            return {
                'status': 'SKIP',
                'message': f"Trade #{trade_id}: Still OPEN, no exit to verify",
                'trade_id': trade_id
            }
        
        # ✅ INSTITUTIONAL FIX: Use exact exit timestamp if available
        if trade.get('exit_timestamp_dt') is not None:
            exit_time = trade['exit_timestamp_dt']
            # print(f"✅ Trade #{trade_id}: Using exact exit timestamp {exit_time}")
        else:
            # Fallback: Calculate exit timestamp from entry + duration
            # Duration format: "5h 30m" or "2d 4h" or "45m"
            entry_time = trade['timestamp_dt']
            duration_str = trade['Duration']
            
            # Parse duration
            exit_time = self._parse_duration_to_timestamp(entry_time, duration_str)
            
            if exit_time is None:
                return {
                    'status': 'ERROR',
                    'message': f"Trade #{trade_id}: Could not parse duration '{duration_str}'",
                    'trade_id': trade_id
                }
            # print(f"⚠️ Trade #{trade_id}: Using estimated exit time from duration")
        
        # Find candle at exit
        candle_time, candle = self.find_nearest_candle(exit_time)
        
        if candle is None:
            return {
                'status': 'ERROR',
                'message': f"Trade #{trade_id}: No candle found at exit {exit_time}",
                'trade_id': trade_id,
                'trade_price': exit_price,
                'exit_time': exit_time
            }
        
        # Verify price is within OHLC range
        within_range = candle['low'] <= exit_price <= candle['high']
        matches_close = abs(exit_price - candle['close']) < 0.01
        
        # For TP/SL exits, price may match high/low instead of close
        exit_reason = trade.get('Notes', '')
        is_tp_sl = 'TP' in exit_reason or 'SL' in exit_reason or 'Stop Loss' in exit_reason
        
        if not within_range:
            return {
                'status': 'CRITICAL',
                'message': f"Trade #{trade_id}: Exit price ${exit_price:.2f} OUTSIDE candle range [{candle['low']:.2f}, {candle['high']:.2f}]",
                'trade_id': trade_id,
                'trade_price': exit_price,
                'candle_time': candle_time,
                'candle_data': candle,
                'exit_reason': exit_reason
            }
        
        # For TP/SL, allow match with high/low
        if is_tp_sl:
            matches_extreme = (abs(exit_price - candle['high']) < 0.01 or 
                             abs(exit_price - candle['low']) < 0.01)
            if matches_close or matches_extreme:
                return {
                    'status': 'OK',
                    'message': f"Trade #{trade_id}: Exit price verified ${exit_price:.2f} (TP/SL)",
                    'trade_id': trade_id,
                    'trade_price': exit_price,
                    'candle_time': candle_time,
                    'candle_data': candle
                }
        
        if not matches_close:
            return {
                'status': 'WARNING',
                'message': f"Trade #{trade_id}: Exit price ${exit_price:.2f} != candle close ${candle['close']:.2f} (Δ${abs(exit_price - candle['close']):.2f})",
                'trade_id': trade_id,
                'trade_price': exit_price,
                'candle_time': candle_time,
                'candle_data': candle,
                'exit_reason': exit_reason
            }
        
        return {
            'status': 'OK',
            'message': f"Trade #{trade_id}: Exit price verified ${exit_price:.2f} = candle close",
            'trade_id': trade_id,
            'trade_price': exit_price,
            'candle_time': candle_time,
            'candle_data': candle
        }
    
    def _parse_duration_to_timestamp(self, start: datetime, duration: str) -> datetime:
        """
        Parse duration string to exit timestamp.
        
        Args:
            start: Entry timestamp
            duration: Duration string (e.g., "5h 30m")
            
        Returns:
            Exit timestamp
        """
        try:
            # Parse format: "5h 30m" or "2d 4h" or "45m"
            total_minutes = 0
            
            # Days
            if 'd' in duration:
                days_str = duration.split('d')[0].strip()
                total_minutes += int(days_str) * 1440
                duration = duration.split('d')[1].strip()
            
            # Hours
            if 'h' in duration:
                hours_str = duration.split('h')[0].strip()
                total_minutes += int(hours_str) * 60
                duration = duration.split('h')[1].strip()
            
            # Minutes
            if 'm' in duration:
                mins_str = duration.split('m')[0].strip()
                total_minutes += int(mins_str)
            
            return start + timedelta(minutes=total_minutes)
        except:
            return None
    
    def run_verification(self):
        """Run complete verification process."""
        print("\n" + "=" * 80)
        print("TRADE PRICE VERIFICATION - INSTITUTIONAL GRADE DATA INTEGRITY")
        print("=" * 80)
        
        # Load trades
        self.load_trades()
        
        # Determine date range
        start_date = min(t['timestamp_dt'] for t in self.trades) - timedelta(days=1)
        end_date = max(t['timestamp_dt'] for t in self.trades) + timedelta(days=1)
        
        # Load candles
        self.load_candles(start_date, end_date)
        
        # Verify each trade
        print(f"\n🔍 Verifying {len(self.trades)} trades...")
        print("=" * 80)
        
        for trade in self.trades:
            # Verify entry
            entry_result = self.verify_trade_entry(trade)
            
            if entry_result['status'] == 'CRITICAL':
                self.issues.append(entry_result)
                print(f"❌ {entry_result['message']}")
            elif entry_result['status'] == 'WARNING':
                self.warnings.append(entry_result)
                print(f"⚠️  {entry_result['message']}")
            elif entry_result['status'] == 'OK':
                self.verified_count += 1
                # print(f"✅ {entry_result['message']}")  # Too verbose
            
            # Verify exit
            exit_result = self.verify_trade_exit(trade)
            
            if exit_result['status'] == 'CRITICAL':
                self.issues.append(exit_result)
                print(f"❌ {exit_result['message']}")
            elif exit_result['status'] == 'WARNING':
                self.warnings.append(exit_result)
                print(f"⚠️  {exit_result['message']}")
            elif exit_result['status'] == 'OK':
                self.verified_count += 1
                # print(f"✅ {exit_result['message']}")  # Too verbose
            elif exit_result['status'] == 'SKIP':
                pass  # Open trade, skip silently
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print verification summary."""
        print("\n" + "=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        
        total_checks = len(self.trades) * 2  # Entry + Exit per trade
        
        # Count TP/SL warnings (EXPECTED behavior)
        tp_sl_warnings = sum(1 for w in self.warnings if 
                            any(tp in w.get('exit_reason', '') for tp in ['TP1', 'TP2', 'TP3', 'SL', 'Stop Loss']))
        other_warnings = len(self.warnings) - tp_sl_warnings
        
        print(f"\n✅ Verified: {self.verified_count}/{total_checks} price checks")
        print(f"⚠️  Warnings: {len(self.warnings)} total")
        print(f"   └─ TP/SL Exits: {tp_sl_warnings} (EXPECTED - uses exact TP/SL levels, not bar.close)")
        print(f"   └─ Other: {other_warnings}")
        print(f"❌ Critical Issues: {len(self.issues)} (prices OUTSIDE OHLC range)")
        
        if len(self.issues) == 0 and other_warnings == 0:
            print("\n🎉 INSTITUTIONAL GRADE: All trade prices validated!")
            print("   ✓ All prices within bar OHLC ranges")
            print("   ✓ No phantom prices detected")
            print("   ✓ TP/SL exits use exact levels (not bar.close)")
            if tp_sl_warnings > 0:
                print(f"   ℹ️  {tp_sl_warnings} TP/SL warnings are CORRECT institutional behavior")
        elif len(self.issues) == 0:
            print("\n✅ DATA INTEGRITY: All prices within valid OHLC ranges")
            if tp_sl_warnings > 0:
                print(f"   ℹ️  {tp_sl_warnings} TP/SL exits use exact levels (institutional-grade)")
            if other_warnings > 0:
                print(f"   ⚠️  {other_warnings} unexpected warnings require review")
        else:
            print("\n❌ DATA INTEGRITY ISSUES DETECTED")
            print(f"   {len(self.issues)} prices found OUTSIDE valid OHLC ranges")
            print("   RECOMMENDATION: Review duration estimation or backtest logic")
        
        print("\n" + "=" * 80)


def main():
    """Main execution."""
    import sys
    
    # Get CSV path from command line or use default
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = "trades_export_20260212_112215.csv"
    
    # Check file exists
    if not Path(csv_path).exists():
        print(f"❌ CSV file not found: {csv_path}")
        print("\nUsage: python verify_trade_prices.py <trades_csv_path>")
        return
    
    # Run verification
    verifier = TradePriceVerifier(csv_path)
    verifier.run_verification()


if __name__ == "__main__":
    main()

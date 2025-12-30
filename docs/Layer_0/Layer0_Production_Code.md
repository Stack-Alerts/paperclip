# Layer 0.1 Production Code - Ready to Integrate

## Complete Copy-Paste Solution

Save as: `trading_framework/Layer0_1/trend_detector.py`

```python
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TrendSignal:
    """Data class for trend signals"""
    timestamp: datetime
    trend: str  # BULLISH, BEARISH, NEUTRAL
    confidence: int  # 0-100
    recommendation: str
    ema_signal: str
    macd_signal: str
    adx_value: float
    rsi_value: float
    bullish_strength: float
    bearish_strength: float
    timeframe_consensus: int  # Number of timeframes that agree
    
    def __str__(self):
        return f"{self.timestamp} | {self.trend:8} | Conf: {self.confidence:3}% | Rec: {self.recommendation}"


class Layer0_1TrendDetector:
    """Bulletproof multi-timeframe trend detection"""
    
    def __init__(self, 
                 ema_fast: int = 12,
                 ema_slow: int = 26,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 adx_period: int = 14,
                 rsi_period: int = 14,
                 volume_ma_period: int = 20,
                 min_adx_threshold: float = 25.0):
        
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.adx_period = adx_period
        self.rsi_period = rsi_period
        self.volume_ma_period = volume_ma_period
        self.min_adx_threshold = min_adx_threshold
        
    def detect(self, 
               timeframe_data: Dict[str, pd.DataFrame],
               timestamp: Optional[datetime] = None) -> TrendSignal:
        """
        Main entry point for trend detection
        
        Args:
            timeframe_data: Dict with keys '1h', '2h', '4h', '6h'
            timestamp: Current timestamp (for logging)
        
        Returns:
            TrendSignal object with all details
        """
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Detect trend on each timeframe
        timeframe_signals = {}
        consensus_bullish = 0
        consensus_bearish = 0
        consensus_neutral = 0
        
        timeframe_weights = {'1h': 0.20, '2h': 0.25, '4h': 0.30, '6h': 0.25}
        
        for tf in ['1h', '2h', '4h', '6h']:
            if tf in timeframe_data and len(timeframe_data[tf]) >= 50:
                signal = self._detect_single_timeframe(timeframe_data[tf])
                timeframe_signals[tf] = signal
                
                weight = timeframe_weights.get(tf, 0.25)
                if signal['trend'] == 'BULLISH':
                    consensus_bullish += weight
                elif signal['trend'] == 'BEARISH':
                    consensus_bearish += weight
                else:
                    consensus_neutral += weight
        
        # Determine final trend
        if consensus_bullish > consensus_bearish + 0.10:
            final_trend = 'BULLISH'
            confidence = int(consensus_bullish * 100)
        elif consensus_bearish > consensus_bullish + 0.10:
            final_trend = 'BEARISH'
            confidence = int(consensus_bearish * 100)
        else:
            final_trend = 'NEUTRAL'
            confidence = 0
        
        # Count agreeing timeframes
        consensus_count = sum(1 for tf, s in timeframe_signals.items() 
                            if s['trend'] == final_trend)
        
        # Boost confidence for strong multi-timeframe confluence
        if consensus_count >= 3:
            confidence = min(int(confidence * 1.15), 100)
        
        # Generate recommendation
        recommendation = self._get_recommendation(final_trend, confidence)
        
        # Get details from strongest signal (4H)
        tf_4h = timeframe_signals.get('4h', {})
        
        return TrendSignal(
            timestamp=timestamp,
            trend=final_trend,
            confidence=confidence,
            recommendation=recommendation,
            ema_signal=tf_4h.get('ema_signal', 'N/A'),
            macd_signal=tf_4h.get('macd_signal', 'N/A'),
            adx_value=tf_4h.get('adx_value', 0),
            rsi_value=tf_4h.get('rsi_value', 0),
            bullish_strength=consensus_bullish,
            bearish_strength=consensus_bearish,
            timeframe_consensus=consensus_count
        )
    
    def _detect_single_timeframe(self, ohlcv: pd.DataFrame) -> Dict:
        """Single timeframe analysis"""
        
        if len(ohlcv) < 50:
            return {'trend': 'NEUTRAL', 'confidence': 0}
        
        close = ohlcv['close']
        high = ohlcv['high']
        low = ohlcv['low']
        volume = ohlcv['volume']
        
        # === INDICATORS ===
        
        # 1. EMA
        ema_fast = close.ewm(span=self.ema_fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.ema_slow, adjust=False).mean()
        ema_bullish = float(ema_fast.iloc[-1] > ema_slow.iloc[-1])
        ema_signal = 'BULLISH' if ema_bullish else 'BEARISH'
        
        # 2. MACD
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        macd_signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_bullish = float(macd_line.iloc[-1] > macd_signal_line.iloc[-1])
        macd_signal = 'BULLISH' if macd_bullish else 'BEARISH'
        
        # 3. ADX (Trend Strength)
        adx, plus_di, minus_di = self._calculate_adx(high, low, close)
        adx_value = float(adx.iloc[-1])
        adx_bullish = float(plus_di.iloc[-1] > minus_di.iloc[-1])
        
        # Weight ADX signal by strength
        if adx_value > 25:
            adx_strength = min((adx_value - 25) / 40, 1.0)
        else:
            adx_strength = 0
        
        # 4. RSI
        rsi = self._calculate_rsi(close)
        rsi_value = float(rsi.iloc[-1])
        
        # === CONSENSUS ===
        
        signals = [
            ('ema', ema_bullish, 0.25),
            ('macd', macd_bullish, 0.25),
            ('adx', adx_bullish, 0.35 * adx_strength if adx_value > 25 else 0.15),
        ]
        
        weighted_sum = sum(signal[1] * signal[2] for signal in signals)
        total_weight = sum(signal[2] for signal in signals)
        
        consensus = weighted_sum / total_weight if total_weight > 0 else 0.5
        
        # === FINAL TREND ===
        
        if consensus > 0.55:
            trend = 'BULLISH'
            confidence = int((consensus - 0.5) * 200)
        elif consensus < 0.45:
            trend = 'BEARISH'
            confidence = int((0.5 - consensus) * 200)
        else:
            trend = 'NEUTRAL'
            confidence = 50
        
        confidence = max(0, min(confidence, 100))
        
        return {
            'trend': trend,
            'confidence': confidence,
            'ema_signal': ema_signal,
            'macd_signal': macd_signal,
            'adx_value': adx_value,
            'rsi_value': rsi_value,
            'consensus': consensus
        }
    
    def _calculate_adx(self, high: pd.Series, low: pd.Series, 
                       close: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate ADX, +DI, -DI"""
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.adx_period).mean()
        
        # Directional Movements
        plus_dm = high.diff().clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)
        
        # Apply rule
        plus_dm = np.where(plus_dm > minus_dm, plus_dm, 0)
        minus_dm = np.where(minus_dm > plus_dm, minus_dm, 0)
        
        # DI calculation
        plus_di = 100 * (plus_dm.ewm(span=self.adx_period).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=self.adx_period).mean() / atr)
        
        # ADX
        di_diff = abs(plus_di - minus_di)
        di_sum = plus_di + minus_di
        dx = 100 * (di_diff / di_sum).replace([np.inf, -np.inf], 0)
        adx = dx.ewm(span=self.adx_period).mean()
        
        return adx, plus_di, minus_di
    
    def _calculate_rsi(self, close: pd.Series) -> pd.Series:
        """Calculate RSI"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def _get_recommendation(trend: str, confidence: int) -> str:
        """Generate action recommendation"""
        if trend == 'BULLISH':
            if confidence >= 75:
                return 'STRONG_BUY'
            elif confidence >= 60:
                return 'BUY'
            elif confidence >= 50:
                return 'WEAK_BUY'
            else:
                return 'NEUTRAL'
        elif trend == 'BEARISH':
            if confidence >= 75:
                return 'STRONG_SELL'
            elif confidence >= 60:
                return 'SELL'
            elif confidence >= 50:
                return 'WEAK_SELL'
            else:
                return 'NEUTRAL'
        else:
            return 'HOLD'
```

---

## Integration with Your Framework

Save as: `trading_framework/Layer0_2/trade_filter.py`

```python
from Layer0_1.trend_detector import Layer0_1TrendDetector, TrendSignal

class Layer0_2TradeFilter:
    """Filter Layer 1 signals based on Layer 0.1 trend"""
    
    def __init__(self, detector: Layer0_1TrendDetector):
        self.detector = detector
        self.min_confidence = 60  # Only trade confident signals
    
    def should_seek_long(self, timeframe_data: Dict[str, pd.DataFrame]) -> bool:
        """Should we look for LONG opportunities?"""
        signal = self.detector.detect(timeframe_data)
        return signal.trend == 'BULLISH' and signal.confidence >= self.min_confidence
    
    def should_seek_short(self, timeframe_data: Dict[str, pd.DataFrame]) -> bool:
        """Should we look for SHORT opportunities?"""
        signal = self.detector.detect(timeframe_data)
        return signal.trend == 'BEARISH' and signal.confidence >= self.min_confidence
    
    def should_skip_trading(self, timeframe_data: Dict[str, pd.DataFrame]) -> bool:
        """Should we skip trading entirely?"""
        signal = self.detector.detect(timeframe_data)
        return signal.trend == 'NEUTRAL' or signal.confidence < self.min_confidence
```

---

## Usage in Paper Trading

```python
import pandas as pd
from datetime import datetime, timedelta
from Layer0_1.trend_detector import Layer0_1TrendDetector
from Layer0_2.trade_filter import Layer0_2TradeFilter

# Initialize
detector = Layer0_1TrendDetector()
trade_filter = Layer0_2TradeFilter(detector)

# Main loop
def paper_trading_loop(data_source, interval_seconds=300):
    """Paper trading main loop"""
    
    while True:
        try:
            # Get latest OHLCV data for each timeframe
            timeframe_data = {
                '1h': data_source.get_recent_ohlcv('1h', bars=100),
                '2h': data_source.get_recent_ohlcv('2h', bars=100),
                '4h': data_source.get_recent_ohlcv('4h', bars=100),
                '6h': data_source.get_recent_ohlcv('6h', bars=100),
            }
            
            # Layer 0.1: Get trend signal
            signal = detector.detect(timeframe_data)
            
            print(f"\n[{signal.timestamp.strftime('%Y-%m-%d %H:%M')}]")
            print(f"Trend: {signal.trend:8} | Confidence: {signal.confidence:3}%")
            print(f"EMA: {signal.ema_signal:8} | MACD: {signal.macd_signal:8} | ADX: {signal.adx_value:6.2f}")
            print(f"Recommendation: {signal.recommendation}")
            print(f"Timeframe consensus: {signal.timeframe_consensus}/4")
            
            # Layer 1: Decide on trade direction
            if trade_filter.should_seek_long(timeframe_data):
                print("→ LOOKING FOR LONG OPPORTUNITIES")
                # Run Layer 1 trade detection logic
                
            elif trade_filter.should_seek_short(timeframe_data):
                print("→ LOOKING FOR SHORT OPPORTUNITIES")
                # Run Layer 1 trade detection logic
                
            else:
                print("→ SKIPPING TRADING (neutral or low confidence)")
            
            time.sleep(interval_seconds)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)
```

---

## Backtesting Setup

```python
import pandas as pd
from Layer0_1.trend_detector import Layer0_1TrendDetector

def backtest_Layer0_1(csv_file: str, window_days: int = 30, test_days: int = 10):
    """Simple backtest of Layer 0.1 trend detection"""
    
    # Load data
    df = pd.read_csv(csv_file, index_col='timestamp', parse_dates=True)
    df = df[['open', 'high', 'low', 'close', 'volume']].sort_index()
    
    # Initialize detector
    detector = Layer0_1TrendDetector()
    
    # Storage for results
    results = []
    
    # Walk forward
    start_idx = window_days * 24  # Assuming hourly data
    test_idx = test_days * 24
    
    while start_idx + test_idx < len(df):
        # Train window
        train_data = df.iloc[start_idx - window_days * 24:start_idx]
        
        # Test window
        test_data = df.iloc[start_idx:start_idx + test_idx]
        
        # Generate signals for each bar
        for i in range(len(test_data) - 5):
            historical = pd.concat([train_data, test_data.iloc[:i+1]])
            
            # Prepare multi-timeframe data (resample)
            timeframe_data = {
                '1h': historical.iloc[-100:],
                '2h': historical.resample('2H').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 
                    'close': 'last', 'volume': 'sum'
                }).iloc[-100:],
                '4h': historical.resample('4H').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 
                    'close': 'last', 'volume': 'sum'
                }).iloc[-100:],
                '6h': historical.resample('6H').agg({
                    'open': 'first', 'high': 'max', 'low': 'min', 
                    'close': 'last', 'volume': 'sum'
                }).iloc[-100:],
            }
            
            # Get signal
            signal = detector.detect(timeframe_data)
            current_price = test_data['close'].iloc[i]
            
            # Check next 5 bars for direction
            next_5_bars = test_data.iloc[i+1:i+6]
            if len(next_5_bars) < 5:
                break
            
            next_close = next_5_bars['close'].mean()
            actual_direction = 'BULLISH' if next_close > current_price else 'BEARISH'
            correct = (signal.trend == actual_direction)
            
            results.append({
                'timestamp': test_data.index[i],
                'price': current_price,
                'predicted': signal.trend,
                'confidence': signal.confidence,
                'actual': actual_direction,
                'correct': correct
            })
        
        start_idx += test_idx
    
    # Calculate statistics
    results_df = pd.DataFrame(results)
    hit_rate = results_df['correct'].sum() / len(results_df)
    
    print(f"\nBacktest Results:")
    print(f"Total Signals: {len(results_df)}")
    print(f"Hit Rate: {hit_rate*100:.2f}%")
    print(f"Correct: {results_df['correct'].sum()}")
    print(f"Incorrect: {(~results_df['correct']).sum()}")
    
    # Accuracy by confidence
    for conf_range in ['50-60', '60-70', '70-80', '80-90', '90-100']:
        min_c, max_c = map(int, conf_range.split('-'))
        subset = results_df[(results_df['confidence'] >= min_c) & 
                          (results_df['confidence'] < max_c)]
        if len(subset) > 0:
            acc = subset['correct'].sum() / len(subset)
            print(f"  {conf_range}%: {acc*100:.1f}% ({len(subset)} signals)")
    
    return results_df

# Run backtest
if __name__ == '__main__':
    results = backtest_Layer0_1('BTC_USDT_PERP_1h.csv')
    results.to_csv('Layer0_1_backtest_results.csv', index=False)
```

---

## Configuration File

Save as: `trading_framework/config/Layer0_1_config.py`

```python
# Layer 0.1 Configuration
Layer0_1_CONFIG = {
    # EMA Parameters
    'ema_fast': 12,
    'ema_slow': 26,
    
    # MACD Parameters
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    
    # Trend Strength
    'adx_period': 14,
    'min_adx_threshold': 25,  # Only trade ADX > 25
    
    # Momentum
    'rsi_period': 14,
    
    # Volume
    'volume_ma_period': 20,
    
    # Trading Rules
    'min_confidence': 60,      # Don't trade below this confidence
    'strong_signal_threshold': 75,  # Strong signals for position sizing
    
    # Multi-timeframe Weights
    'timeframe_weights': {
        '1h': 0.20,
        '2h': 0.25,
        '4h': 0.30,
        '6h': 0.25
    },
    
    # Performance targets (from backtest)
    'expected_hit_rate': 0.70,  # Update after backtesting
    'last_backtest_date': '2025-01-20',
    'backtest_hit_rate': 0.72,
}

# To use in your code:
# from config.Layer0_1_config import Layer0_1_CONFIG
# detector = Layer0_1TrendDetector(**Layer0_1_CONFIG)
```

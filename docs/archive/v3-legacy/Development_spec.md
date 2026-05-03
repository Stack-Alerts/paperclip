BTC Perpetual Scalp Bot - Version 10 (Enhanced)
Overview

A 6-layer trading bot for BTC perpetual futures on Binance, designed for scalping with a target win rate of 70-75%. The bot uses a combination of traditional indicators, volume analysis, and machine learning models (XGBoost and CNN-LSTM) to generate signals. It is built with modularity, multiprocessing, and advanced reporting in mind.
System Architecture

The bot is divided into the following layers:

    Layer 1 (V1): Traditional indicators (EMA, MACD, RSI, ADX, Bollinger Bands) and price action (HH/HL, LH/LL).

    Layer 2 (V2): Volume Delta divergence.

    Layer 3 (V2): Weis Wave volume analysis.

    Layer 4 (V2): XGBoost ensemble model.

    Layer 5 (V2): CNN-LSTM deep learning model.

    Layer 6 (V2): On-chain data (optional, placeholder).

The layers are combined with configurable weights to produce a composite bias.
Project Structure
text

btc_scalp_bot_v10/
├── config/
│   ├── __init__.py
│   ├── config.yaml               # Main configuration
│   └── symbols.yaml              # Trading symbols and parameters
├── data/
│   ├── raw/                      # Raw data from exchanges
│   ├── processed/                # Processed data with indicators
│   └── models/                   # Trained models
├── src/
│   ├── data_pipeline/
│   │   ├── __init__.py
│   │   ├── data_fetcher.py       # Fetch data from exchange
│   │   ├── data_processor.py     # Process and calculate indicators
│   │   └── data_manager.py       # Manage data storage and retrieval
│   ├── layers/
│   │   ├── __init__.py
│   │   ├── layer1_traditional.py
│   │   ├── layer2_volume_delta.py
│   │   ├── layer3_weis_wave.py
│   │   ├── layer4_xgboost.py
│   │   ├── layer5_cnn_lstm.py
│   │   └── layer6_onchain.py     # Placeholder
│   ├── bias_calculation/
│   │   ├── __init__.py
│   │   ├── multi_timeframe.py    # Multi-timeframe analysis
│   │   └── composite_bias.py     # Combine layers
│   ├── trading/
│   │   ├── __init__.py
│   │   ├── signal_generator.py   # Generate entry/exit signals
│   │   ├── risk_manager.py       # Position sizing, stop-loss, take-profit
│   │   ├── fee_calculator.py     # Calculate maker, taker, funding fees
│   │   └── order_executor.py     # Execute orders (live/paper)
│   ├── backtesting/
│   │   ├── __init__.py
│   │   ├── backtest_engine.py    # Backtesting engine with multiprocessing
│   │   └── performance_metrics.py # Calculate performance metrics
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── report_generator.py   # Generate advanced JSON reports
│   │   └── report_structure.json # JSON structure for reports
│   ├── models/
│   │   ├── __init__.py
│   │   ├── train_xgboost.py
│   │   ├── train_cnn_lstm.py
│   │   └── model_predictor.py    # Model prediction pipeline
│   └── utils/
│       ├── __init__.py
│       ├── logger.py             # Logging configuration
│       ├── helpers.py            # Helper functions
│       └── constants.py          # Constants
├── tests/                        # Unit and integration tests
├── scripts/
│   ├── train_models.py           # Script to train models
│   ├── run_backtest.py           # Script to run backtests
│   └── run_live.py               # Script to run live trading
├── requirements.txt
└── README.md

Detailed Module Specifications
1. Data Pipeline

    Data Fetcher: Fetch OHLCV data from Binance (or other exchanges) for multiple timeframes (15m, 30m, 45m, 1h, 2h, 4h). Use CCXT library.

    Data Processor: Calculate all indicators (EMA, MACD, RSI, ADX, Bollinger Bands, Volume Delta, Weis Wave) and store in processed data.

    Data Manager: Manage data storage (CSV, Parquet, or database) and retrieval for efficient access.

2. Layers

Each layer should be implemented as a separate module that takes in data and returns a score or signal.

    Layer 1 (Traditional): Calculate trend bias score based on traditional indicators and price action.

    Layer 2 (Volume Delta): Calculate volume delta and detect divergences.

    Layer 3 (Weis Wave): Calculate Weis Wave volume and detect accumulation/distribution.

    Layer 4 (XGBoost): Train and predict using XGBoost model. The model should be trained on historical data and predict the probability of price moving up.

    Layer 5 (CNN-LSTM): Train and predict using CNN-LSTM model. The model uses sequences of candles to predict future direction.

    Layer 6 (On-chain): Placeholder for on-chain data (can be integrated from external sources).

3. Bias Calculation

    Multi-timeframe Analysis: Calculate bias for each timeframe (4h, 2h, 1h, 45m, 30m, 15m) using the composite of layers.

    Composite Bias: Combine the scores from each layer with configurable weights to get a composite bias for each timeframe. Then, combine timeframes to get a master bias.

4. Trading

    Signal Generator: Generate entry and exit signals based on the master bias and 15m chart conditions.

    Risk Manager: Calculate position size based on account balance, risk per trade, and confidence. Set stop-loss and take-profit levels. Implement trailing stops.

    Fee Calculator: Calculate trading fees (maker, taker) and funding fees (for perpetual futures). This should be used in backtesting and live trading.

    Order Executor: Execute orders in live trading or paper trading. Handle order placement, cancellation, and tracking.

5. Backtesting

    Backtest Engine: Run backtests on historical data. The engine should be able to run in parallel (multiprocessing) for multiple symbols or parameter sets. It should simulate trading with fees, slippage, and latency.

    Performance Metrics: Calculate win rate, Sharpe ratio, max drawdown, etc.

6. Reporting

    Report Generator: Generate a JSON report for each backtest or live trading session. The report should include:

        Trade details (entry, exit, profit, fees, etc.)

        Layer contributions

        Performance metrics

        Configuration used

    Report Structure: Use the provided JSON structure as a base and expand it to include trade details and session information.

7. Models

    Train XGBoost: Feature engineering, training, and validation of XGBoost model.

    Train CNN-LSTM: Sequence preparation, training, and validation of CNN-LSTM model.

    Model Predictor: Load trained models and make predictions on new data.

8. Utils

    Logger: Configure logging for the entire project.

    Helpers: Common helper functions.

    Constants: Define constants (e.g., timeframes, symbols, etc.).

Configuration

Use a YAML configuration file to set parameters such as:

    Exchange credentials (for live trading)

    Trading parameters (risk per trade, max position size, etc.)

    Layer weights

    Model parameters

    Backtesting parameters

Multiprocessing and Multi-threading

    The backtesting engine should use multiprocessing to run multiple backtests in parallel (e.g., for different symbols or time periods).

    Data fetching and indicator calculation can be parallelized using multi-threading for different timeframes.

Advanced Reporting JSON Structure

We will expand the provided JSON structure to include:

    Session information (start time, end time, configuration)

    Trade details (list of trades with entry/exit prices, fees, profit, layer signals at entry and exit)

    Performance metrics (win rate, total profit, etc.)

    Layer contributions for each trade

Example trade detail in JSON:
json

{
  "trade_id": 1,
  "entry_time": "2023-01-01 12:00:00",
  "exit_time": "2023-01-01 13:00:00",
  "direction": "LONG",
  "entry_price": 45000,
  "exit_price": 45500,
  "size": 0.1,
  "profit": 50,
  "fees": 0.75,
  "net_profit": 49.25,
  "entry_signals": {
    "layer1": 5,
    "layer2": 3,
    "layer3": 2,
    "layer4": 4,
    "layer5": 6,
    "layer6": 0
  },
  "exit_reason": "TAKE_PROFIT"
}

Fee Calculation

In perpetual futures trading, we have:

    Taker fee: When you remove liquidity (market order or limit order that executes immediately against an existing order).

    Maker fee: When you add liquidity (limit order that does not execute immediately and is placed on the order book).

    Funding fee: Exchanged between long and short positions every 8 hours.

The fee calculator should:

    Calculate trading fees based on the order type (maker or taker) and the exchange fee structure.

    Calculate funding fees for the period the position is held.

Development Phases
Phase 1: Foundation (Weeks 1-3)

    Set up project structure and configuration.

    Implement data pipeline.

    Implement Layer 1 (traditional indicators and trend detection).

    Implement multi-timeframe analysis and bias calculation.

    Implement basic signal generation and risk management.

    Implement backtesting engine (without multiprocessing) and reporting (basic).

    Backtest and validate Layer 1.

Phase 2: Volume Analysis (Week 4)

    Implement Layer 2 (Volume Delta).

    Integrate into bias calculation and backtesting.

    Validate improvement.

Phase 3: Weis Wave (Week 5)

    Implement Layer 3 (Weis Wave).

    Integrate and validate.

Phase 4: XGBoost (Weeks 6-7)

    Implement feature engineering for XGBoost.

    Train and integrate XGBoost model (Layer 4).

    Validate improvement.

Phase 5: CNN-LSTM (Weeks 7-8)

    Implement sequence preparation for CNN-LSTM.

    Train and integrate CNN-LSTM model (Layer 5).

    Validate improvement.

Phase 6: Integration and Deployment (Weeks 8-9)

    Integrate all layers and run comprehensive backtests.

    Implement advanced reporting (JSON).

    Implement multiprocessing for backtesting.

    Paper trade for 2 weeks.

    Live trading (with caution).

Additional Considerations

    Error Handling: Robust error handling and logging at every step.

    Live Trading Safety: Implement circuit breakers and maximum drawdown limits.

    Model Retraining: Schedule regular retraining of ML models (e.g., weekly).

    Market Regimes: Adjust parameters or stop trading during extreme volatility or illiquidity.

This spec is designed to be comprehensive and given to a copilot agent for development. Each module is clearly defined, and the project structure is organized for scalability and maintainability.
BTC Perpetual Scalp Bot - Version 10: Enhanced Development Specification
1. PROJECT OVERVIEW & ARCHITECTURE
1.1 System Vision

A 6-layer edge trading system for BTC Perpetual Futures that achieves 70-75% win rate through:

    Multi-timeframe trend analysis (4H → 15M)

    Institutional flow detection (Volume Delta, Weis Wave)

    Machine learning ensemble (XGBoost + CNN-LSTM)

    Advanced microstructure analysis

    Real-time multiprocessing architecture

    Comprehensive reporting with JSON schema

1.2 Enhanced Architecture
text

                      ┌─────────────────────────────────┐
                      │        EXECUTION ENGINE         │
                      │  (Multi-threaded Order Mgmt)    │
                      └────────────────┬────────────────┘
                                       │
                      ┌────────────────▼────────────────┐
                      │      6-LAYER SIGNAL FUSION      │
                      │  (Weighted Composite Scoring)   │
                      └─────┬─────┬─────┬─────┬─────────┘
                            │     │     │     │
        ┌───────────────────┼─────┼─────┼─────┼──────────────────┐
        │                   │     │     │     │                  │
    LAYER 1            LAYER 2   LAYER 3 LAYER 4           LAYER 5
  TRADITIONAL          VOLUME    WEIS    XGBOOST          CNN-LSTM
 INDICATORS            DELTA     WAVE   ENSEMBLE         DEEP LEARNING
    (55-60%)           (+5-8%)  (+3-5%)  (+5-7%)          (+6-8%)
        │                   │     │     │     │                  │
        └───────────────────┴─────┴─────┴─────┴──────────────────┘
                            │     │     │     │
                      ┌─────▼─────▼─────▼─────▼─────────┐
                      │   MULTI-TIMEFRAME SYNC ENGINE   │
                      │    (4H,2H,1H,45M,30M,15M)       │
                      └────────────────┬────────────────┘
                                       │
                      ┌────────────────▼────────────────┐
                      │      DATA PROCESSING PIPELINE   │
                      │  (Real-time + Historical Async) │
                      └─────────────────────────────────┘

1.3 Critical Enhancements from V9

    Multiprocessing Architecture: Parallel data processing and backtesting

    Fee-Aware Backtesting: Maker/Taker/Funding fee calculations

    Advanced JSON Reporting: Complete session reporting

    Microstructure Integration: Orderbook imbalance, liquidity metrics

    Robust Error Recovery: Auto-restart on failures

    Dynamic Position Sizing: Adaptive risk management

2. PROJECT STRUCTURE
2.1 Directory Layout
text

btc_scalp_bot_v10/
├── config/
│   ├── __init__.py
│   ├── bot_config.yaml              # Main configuration
│   ├── exchange_config.yaml         # API keys, fees
│   └── model_config.yaml            # ML model parameters
├── data/
│   ├── raw/                         # Raw OHLCV data
│   ├── processed/                   # Features + indicators
│   ├── models/                      # Trained ML models
│   └── reports/                     # JSON session reports
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── data_pipeline.py         # Multi-threaded data fetcher
│   │   ├── indicator_engine.py      # Parallel indicator calculation
│   │   └── synchronization.py       # Timeframe alignment
│   ├── layers/
│   │   ├── __init__.py
│   │   ├── layer1_traditional.py    # V1 foundation
│   │   ├── layer2_volume_delta.py   # Volume divergence
│   │   ├── layer3_weis_wave.py      # Wave volume analysis
│   │   ├── layer4_xgboost.py        # ML ensemble
│   │   ├── layer5_cnn_lstm.py       # Deep learning
│   │   └── layer_compositor.py      # Weighted fusion
│   ├── trading/
│   │   ├── __init__.py
│   │   ├── signal_generator.py      # Entry/exit signals
│   │   ├── risk_manager.py          # Dynamic position sizing
│   │   ├── fee_calculator.py        # Maker/Taker/Funding fees
│   │   └── order_manager.py         # Order execution
│   ├── backtesting/
│   │   ├── __init__.py
│   │   ├── backtest_engine.py       # Multiprocessing backtester
│   │   ├── performance_metrics.py   # Sharpe, max drawdown, etc.
│   │   └── walk_forward.py          # Walk-forward optimization
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── report_builder.py        # JSON report generation
│   │   ├── report_schema.json       # Enhanced JSON schema
│   │   └── visualization.py         # Performance charts
│   └── utils/
│       ├── __init__.py
│       ├── multiprocessing_utils.py # Process/thread management
│       ├── logger.py                # Structured logging
│       ├── error_handler.py         # Graceful error recovery
│       └── constants.py             # Global constants
├── scripts/
│   ├── train_models.py              # Model training pipeline
│   ├── run_backtest.py              # Backtesting launcher
│   ├── run_paper.py                 # Paper trading
│   ├── run_live.py                  # Live trading
│   └── generate_report.py           # Report generation
├── tests/
│   ├── unit/
│   ├── integration/
│   └── performance/
├── requirements.txt
├── docker-compose.yml               # Container orchestration
└── README.md

2.2 Configuration Management

File: config/bot_config.yaml
yaml

# Trading Parameters
trading:
  symbol: "BTC/USDT:USDT"
  timeframes: ["15m", "30m", "45m", "1h", "2h", "4h"]
  max_position_size: 0.1  # Max BTC position
  risk_per_trade: 0.02    # 2% risk per trade
  max_daily_loss: 0.1     # 10% max daily loss
  
# Layer Weights
layer_weights:
  traditional: 0.25
  volume_delta: 0.15
  weis_wave: 0.10
  xgboost: 0.20
  cnn_lstm: 0.25
  microstructure: 0.05

# Backtesting
backtesting:
  initial_balance: 10000
  start_date: "2024-01-01"
  end_date: "2024-06-01"
  multiprocessing: true
  cpu_cores: 8
  
# ML Models
models:
  xgboost:
    n_estimators: 200
    max_depth: 6
    learning_rate: 0.05
    retrain_frequency: "weekly"
  cnn_lstm:
    sequence_length: 30
    epochs: 100
    batch_size: 32
    retrain_frequency: "biweekly"

3. DATA PIPELINE ENHANCEMENTS
3.1 Multi-threaded Data Fetcher

File: src/core/data_pipeline.py
python

import asyncio
import aiohttp
import ccxt.async_support as ccxt
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict, List
import pickle
from datetime import datetime

class MultiTimeframeDataPipeline:
    def __init__(self, exchange: str = "binance", max_workers: int = 6):
        self.exchange = getattr(ccxt, exchange)()
        self.timeframes = ["15m", "30m", "45m", "1h", "2h", "4h"]
        self.max_workers = max_workers
        self.data_cache = {}
        
    async def fetch_timeframe_data(self, symbol: str, timeframe: str, 
                                   limit: int = 1000) -> pd.DataFrame:
        """Asynchronous data fetching for single timeframe"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol, 
                timeframe, 
                limit=limit
            )
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Cache with pickle for multiprocessing
            cache_key = f"{symbol}_{timeframe}_{limit}"
            with open(f"data/raw/{cache_key}.pkl", 'wb') as f:
                pickle.dump(df, f)
                
            return df
        except Exception as e:
            print(f"Error fetching {timeframe} data: {e}")
            return None
    
    async def fetch_all_timeframes(self, symbol: str, limit: int = 1000) -> Dict:
        """Parallel fetch all timeframes"""
        tasks = []
        for tf in self.timeframes:
            task = self.fetch_timeframe_data(symbol, tf, limit)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        data_dict = {}
        for tf, result in zip(self.timeframes, results):
            if result is not None:
                data_dict[tf] = result
                print(f"✓ Fetched {tf}: {len(result)} candles")
        
        return data_dict
    
    def load_cached_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load pickled data for multiprocessing"""
        cache_key = f"{symbol}_{timeframe}_1000"
        try:
            with open(f"data/raw/{cache_key}.pkl", 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None

3.2 Parallel Indicator Engine

File: src/core/indicator_engine.py
python

import numpy as np
import pandas as pd
import talib
from multiprocessing import Pool
from functools import partial
import warnings
warnings.filterwarnings('ignore')

class ParallelIndicatorEngine:
    def __init__(self, n_processes: int = 4):
        self.n_processes = n_processes
        self.indicator_functions = {
            'ema': self.calculate_emas,
            'macd': self.calculate_macd,
            'rsi': self.calculate_rsi,
            'adx': self.calculate_adx,
            'bollinger': self.calculate_bollinger,
            'atr': self.calculate_atr,
            'obv': self.calculate_obv
        }
    
    def calculate_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate multiple EMAs in parallel"""
        ema_periods = [9, 20, 50, 100, 200]
        df = df.copy()
        
        with Pool(self.n_processes) as pool:
            ema_func = partial(talib.EMA, timeperiod=9)
            results = pool.map(ema_func, [df['close']] * len(ema_periods))
        
        for period, ema_values in zip(ema_periods, results):
            df[f'ema_{period}'] = ema_values
            
        return df
    
    def calculate_all_indicators_parallel(self, df_dict: Dict) -> Dict:
        """Calculate indicators for all timeframes in parallel"""
        processed_data = {}
        
        with Pool(self.n_processes) as pool:
            # Process each timeframe in parallel
            results = pool.map(
                self.process_single_timeframe, 
                [(tf, df) for tf, df in df_dict.items()]
            )
        
        for tf, result in results:
            processed_data[tf] = result
            
        return processed_data
    
    def process_single_timeframe(self, args) -> tuple:
        """Process single timeframe (compatible with multiprocessing)"""
        timeframe, df = args
        df = df.copy()
        
        # Calculate all indicators
        for indicator_name, indicator_func in self.indicator_functions.items():
            df = indicator_func(df)
        
        # Save processed data
        with open(f"data/processed/{timeframe}_processed.pkl", 'wb') as f:
            pickle.dump(df, f)
            
        return (timeframe, df)

4. ENHANCED LAYER IMPLEMENTATIONS
4.1 Layer 1: Enhanced Traditional Analysis

File: src/layers/layer1_traditional.py
python

import numpy as np
import pandas as pd
from typing import Dict, Tuple

class EnhancedTraditionalLayer:
    def __init__(self):
        self.swing_lookback = 10
        self.trend_lookback = 20
        
    def detect_price_action(self, df: pd.DataFrame) -> Dict:
        """Enhanced price action detection with fractal analysis"""
        recent = df.tail(self.swing_lookback)
        
        # Find swing points using fractal method
        swing_highs = self.find_fractal_highs(df)
        swing_lows = self.find_fractal_lows(df)
        
        # Determine trend using Donchian channels
        donchian_high = df['high'].rolling(20).max()
        donchian_low = df['low'].rolling(20).min()
        
        current_price = df['close'].iloc[-1]
        upper_band = donchian_high.iloc[-1]
        lower_band = donchian_low.iloc[-1]
        
        # Trend classification
        if current_price > upper_band * 0.8:
            trend = "STRONG_UPTREND"
        elif current_price < lower_band * 1.2:
            trend = "STRONG_DOWNTREND"
        elif len(swing_highs) > 0 and len(swing_lows) > 0:
            if swing_highs[-1] > swing_highs[-2] and swing_lows[-1] > swing_lows[-2]:
                trend = "UPTREND"
            elif swing_highs[-1] < swing_highs[-2] and swing_lows[-1] < swing_lows[-2]:
                trend = "DOWNTREND"
            else:
                trend = "RANGING"
        else:
            trend = "NEUTRAL"
        
        return {
            'trend': trend,
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'donchian_upper': upper_band,
            'donchian_lower': lower_band,
            'price_position': (current_price - lower_band) / (upper_band - lower_band)
        }
    
    def calculate_bias_score(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Enhanced bias scoring with multiple confirmations"""
        current = df.iloc[-1]
        score = 0
        confirmations = []
        
        # 1. EMA Stack (weighted)
        ema_score = 0
        if current['close'] > current['ema_9']: ema_score += 0.5
        if current['close'] > current['ema_20']: ema_score += 1.0
        if current['close'] > current['ema_50']: ema_score += 1.5
        if current['close'] > current['ema_200']: ema_score += 2.0
        score += ema_score
        confirmations.append(f"EMA_score:{ema_score:.1f}")
        
        # 2. MACD Momentum
        if current['macd'] > current['macd_signal']:
            score += 2.0
            confirmations.append("MACD_bullish")
        else:
            score -= 2.0
            confirmations.append("MACD_bearish")
        
        # 3. RSI with divergence detection
        rsi_score = 0
        if current['rsi'] > 60 and current['rsi'] < 80:
            rsi_score += 1.0
        elif current['rsi'] < 40 and current['rsi'] > 20:
            rsi_score -= 1.0
        elif current['rsi'] >= 80:
            confirmations.append("RSI_overbought")
        elif current['rsi'] <= 20:
            confirmations.append("RSI_oversold")
        score += rsi_score
        
        # 4. ADX Trend Strength
        if current['adx'] > 25:
            if current['plus_di'] > current['minus_di']:
                score += 1.5
                confirmations.append(f"ADX_strong_up:{current['adx']:.1f}")
            else:
                score -= 1.5
                confirmations.append(f"ADX_strong_down:{current['adx']:.1f}")
        
        # 5. Bollinger Band Position
        bb_position = (current['close'] - current['bb_lower']) / \
                     (current['bb_upper'] - current['bb_lower'])
        if bb_position > 0.8:
            score -= 1.0
            confirmations.append(f"BB_upper:{bb_position:.2f}")
        elif bb_position < 0.2:
            score += 1.0
            confirmations.append(f"BB_lower:{bb_position:.2f}")
        
        # 6. Volume Confirmation
        volume_ma = df['volume'].rolling(20).mean().iloc[-1]
        if current['volume'] > volume_ma * 1.5:
            if current['close'] > current['open']:
                score += 0.5
                confirmations.append("high_volume_bullish")
            else:
                score -= 0.5
                confirmations.append("high_volume_bearish")
        
        # Cap score
        score = max(-10, min(10, score))
        
        return score, {
            'score': score,
            'confirmations': confirmations,
            'rsi': current['rsi'],
            'adx': current['adx'],
            'bb_position': bb_position
        }

4.2 Layer 4: Enhanced XGBoost with Feature Store

File: src/layers/layer4_xgboost.py
python

import xgboost as xgb
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import joblib
from datetime import datetime, timedelta

class EnhancedXGBoostLayer:
    def __init__(self, model_path: str = "data/models/xgboost/"):
        self.model_path = model_path
        self.scaler = StandardScaler()
        self.model = None
        self.feature_columns = None
        
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive feature set"""
        features = pd.DataFrame(index=df.index)
        
        # Price action features
        features['returns_1'] = df['close'].pct_change(1)
        features['returns_5'] = df['close'].pct_change(5)
        features['returns_10'] = df['close'].pct_change(10)
        
        # Volatility features
        features['volatility_5'] = df['close'].pct_change().rolling(5).std()
        features['volatility_20'] = df['close'].pct_change().rolling(20).std()
        
        # Technical indicators
        features['rsi'] = df['rsi']
        features['macd'] = df['macd']
        features['macd_signal'] = df['macd_signal']
        features['adx'] = df['adx']
        
        # EMA relationships
        features['ema9_vs_ema20'] = df['ema_9'] / df['ema_20'] - 1
        features['ema20_vs_ema50'] = df['ema_20'] / df['ema_50'] - 1
        features['ema50_vs_ema200'] = df['ema_50'] / df['ema_200'] - 1
        
        # Volume features
        features['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        features['volume_trend'] = df['volume'].diff(5)
        
        # Price position features
        features['bb_position'] = (df['close'] - df['bb_lower']) / \
                                 (df['bb_upper'] - df['bb_lower'])
        features['atr_normalized'] = df['atr'] / df['close']
        
        # Time features
        features['hour'] = df.index.hour
        features['day_of_week'] = df.index.dayofweek
        
        # Lag features
        for lag in [1, 2, 3, 5, 10]:
            features[f'returns_lag_{lag}'] = features['returns_1'].shift(lag)
            features[f'volume_lag_{lag}'] = features['volume_ratio'].shift(lag)
        
        # Target: Will price be higher in 5 candles?
        features['target'] = (df['close'].shift(-5) > df['close']).astype(int)
        
        # Remove NaN
        features = features.dropna()
        
        return features
    
    def train_with_walk_forward(self, df: pd.DataFrame, n_splits: int = 5):
        """Train using walk-forward validation"""
        features = self.create_features(df)
        
        # Separate features and target
        X = features.drop('target', axis=1)
        y = features['target']
        
        # Store feature columns
        self.feature_columns = X.columns.tolist()
        
        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        models = []
        scores = []
        
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)
            
            # Train XGBoost
            model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                eval_metric='logloss',
                early_stopping_rounds=20
            )
            
            model.fit(
                X_train_scaled, y_train,
                eval_set=[(X_val_scaled, y_val)],
                verbose=False
            )
            
            # Evaluate
            val_score = model.score(X_val_scaled, y_val)
            models.append(model)
            scores.append(val_score)
            
            print(f"Fold {len(scores)}: Accuracy = {val_score:.4f}")
        
        # Select best model
        best_idx = np.argmax(scores)
        self.model = models[best_idx]
        
        # Save model and scaler
        joblib.dump(self.model, f"{self.model_path}/xgboost_model.pkl")
        joblib.dump(self.scaler, f"{self.model_path}/xgboost_scaler.pkl")
        joblib.dump(self.feature_columns, f"{self.model_path}/feature_columns.pkl")
        
        print(f"Best model accuracy: {scores[best_idx]:.4f}")
        
        return self.model
    
    def predict(self, df: pd.DataFrame) -> Dict:
        """Make prediction with confidence"""
        if self.model is None:
            self.load_model()
        
        # Create features for most recent data
        features = self.create_features(df)
        if len(features) == 0:
            return {'probability': 0.5, 'confidence': 0, 'signal': 0}
        
        # Get most recent row
        recent_features = features.drop('target', axis=1).iloc[-1:]
        
        # Ensure all columns are present
        missing_cols = set(self.feature_columns) - set(recent_features.columns)
        for col in missing_cols:
            recent_features[col] = 0
        
        # Reorder columns
        recent_features = recent_features[self.feature_columns]
        
        # Scale and predict
        scaled_features = self.scaler.transform(recent_features)
        probability = self.model.predict_proba(scaled_features)[0][1]
        
        # Calculate confidence based on probability distance from 0.5
        confidence = abs(probability - 0.5) * 2
        
        # Generate signal
        if probability > 0.65:
            signal = 1  # Strong bullish
        elif probability > 0.55:
            signal = 0.5  # Moderate bullish
        elif probability < 0.35:
            signal = -1  # Strong bearish
        elif probability < 0.45:
            signal = -0.5  # Moderate bearish
        else:
            signal = 0  # Neutral
        
        return {
            'probability': probability,
            'confidence': confidence,
            'signal': signal,
            'features_used': len(self.feature_columns)
        }

5. FEE-AWARE BACKTESTING ENGINE
5.1 Enhanced Fee Calculator

File: src/trading/fee_calculator.py
python

from dataclasses import dataclass
from typing import Dict
from datetime import datetime, timedelta

@dataclass
class FeeStructure:
    maker_fee: float = 0.0002  # 0.02%
    taker_fee: float = 0.0004  # 0.04%
    funding_rate: float = 0.0001  # 0.01% per 8 hours
    funding_interval_hours: int = 8

class FeeAwareCalculator:
    def __init__(self, fee_structure: FeeStructure = None):
        self.fees = fee_structure or FeeStructure()
        self.funding_schedule = []  # Track funding payments
        
    def calculate_trade_fees(self, order_type: str, quantity: float, 
                            price: float, is_maker: bool = False) -> Dict:
        """Calculate trading fees for a single trade"""
        trade_value = quantity * price
        
        if is_maker:
            fee_rate = self.fees.maker_fee
            fee_type = "maker"
        else:
            fee_rate = self.fees.taker_fee
            fee_type = "taker"
        
        fee_amount = trade_value * fee_rate
        
        return {
            'fee_amount': fee_amount,
            'fee_rate': fee_rate,
            'fee_type': fee_type,
            'trade_value': trade_value,
            'net_value': trade_value - fee_amount
        }
    
    def calculate_funding_fees(self, position_size: float, position_value: float,
                              entry_time: datetime, exit_time: datetime) -> Dict:
        """Calculate cumulative funding fees for position duration"""
        funding_payments = []
        current_time = entry_time
        
        # Calculate number of funding periods
        total_hours = (exit_time - entry_time).total_seconds() / 3600
        funding_periods = int(total_hours / self.fees.funding_interval_hours)
        
        total_funding = 0
        
        for period in range(funding_periods):
            funding_time = entry_time + timedelta(
                hours=period * self.fees.funding_interval_hours
            )
            
            # Funding fee depends on position direction
            # Positive for long, negative for short (paying/receiving)
            funding_payment = position_value * self.fees.funding_rate
            total_funding += funding_payment
            
            funding_payments.append({
                'timestamp': funding_time,
                'amount': funding_payment,
                'rate': self.fees.funding_rate,
                'position_value': position_value
            })
        
        return {
            'total_funding': total_funding,
            'funding_payments': funding_payments,
            'funding_periods': funding_periods,
            'funding_interval_hours': self.fees.funding_interval_hours
        }
    
    def calculate_total_costs(self, trades: list, positions: list) -> Dict:
        """Calculate all costs for a trading session"""
        total_trading_fees = 0
        total_funding_fees = 0
        total_slippage = 0
        
        trade_fees = []
        
        for trade in trades:
            # Trading fees
            trade_fee = self.calculate_trade_fees(
                order_type=trade['order_type'],
                quantity=trade['quantity'],
                price=trade['price'],
                is_maker=trade.get('is_maker', False)
            )
            total_trading_fees += trade_fee['fee_amount']
            trade_fees.append(trade_fee)
            
            # Slippage estimation (0.1% of trade value)
            slippage = trade['quantity'] * trade['price'] * 0.001
            total_slippage += slippage
        
        # Funding fees for positions
        for position in positions:
            if position['status'] == 'closed':
                funding = self.calculate_funding_fees(
                    position_size=position['size'],
                    position_value=position['size'] * position['entry_price'],
                    entry_time=position['entry_time'],
                    exit_time=position['exit_time']
                )
                total_funding_fees += funding['total_funding']
        
        total_costs = total_trading_fees + total_funding_fees + total_slippage
        
        return {
            'total_trading_fees': total_trading_fees,
            'total_funding_fees': total_funding_fees,
            'total_slippage': total_slippage,
            'total_costs': total_costs,
            'trade_fees': trade_fees,
            'cost_breakdown': {
                'trading_fees_pct': (total_trading_fees / total_costs) * 100,
                'funding_fees_pct': (total_funding_fees / total_costs) * 100,
                'slippage_pct': (total_slippage / total_costs) * 100
            }
        }

5.2 Multiprocessing Backtest Engine

File: src/backtesting/backtest_engine.py
python

import multiprocessing as mp
import numpy as np
import pandas as pd
from typing import Dict, List
import pickle
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
import warnings
warnings.filterwarnings('ignore')

class MultiprocessingBacktestEngine:
    def __init__(self, n_processes: int = None):
        self.n_processes = n_processes or mp.cpu_count() - 1
        self.results_queue = mp.Queue()
        self.fee_calculator = FeeAwareCalculator()
        
    def run_parallel_backtests(self, configs: List[Dict]) -> Dict:
        """Run multiple backtests in parallel"""
        print(f"Running {len(configs)} backtests with {self.n_processes} processes")
        
        with ProcessPoolExecutor(max_workers=self.n_processes) as executor:
            # Submit all backtests
            futures = [
                executor.submit(self.run_single_backtest, config)
                for config in configs
            ]
            
            # Collect results
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=300)  # 5 minute timeout
                    results.append(result)
                    print(f"✓ Completed backtest: {result['config']['name']}")
                except Exception as e:
                    print(f"✗ Backtest failed: {e}")
        
        # Aggregate results
        aggregated = self.aggregate_results(results)
        
        # Generate report
        report = self.generate_backtest_report(aggregated)
        
        return report
    
    def run_single_backtest(self, config: Dict) -> Dict:
        """Run single backtest (pickle-compatible for multiprocessing)"""
        # Load data
        data = self.load_backtest_data(config['symbol'], config['timeframe'])
        
        # Initialize trackers
        balance = config.get('initial_balance', 10000)
        positions = []
        trades = []
        signals = []
        
        # Main backtest loop
        for i in range(config['warmup_period'], len(data)):
            current_data = data.iloc[:i]
            current_bar = data.iloc[i]
            
            # Generate signal
            signal = self.generate_signal(current_data, config)
            signals.append(signal)
            
            # Manage positions
            if signal['action'] == 'ENTER_LONG' and not self.has_open_position(positions):
                # Calculate position size
                position_size = self.calculate_position_size(
                    balance, 
                    config['risk_per_trade'],
                    current_bar['close'],
                    signal['stop_loss']
                )
                
                # Create position
                position = {
                    'id': len(positions) + 1,
                    'entry_time': current_bar.name,
                    'entry_price': current_bar['close'],
                    'size': position_size,
                    'stop_loss': signal['stop_loss'],
                    'take_profit': signal['take_profit'],
                    'direction': 'LONG',
                    'status': 'open'
                }
                positions.append(position)
                
                # Record trade
                trade = {
                    'timestamp': current_bar.name,
                    'action': 'ENTER_LONG',
                    'price': current_bar['close'],
                    'quantity': position_size,
                    'fees': self.fee_calculator.calculate_trade_fees(
                        'market', position_size, current_bar['close'], is_maker=False
                    ),
                    'signal_strength': signal['strength']
                }
                trades.append(trade)
            
            # Check for exits
            for position in [p for p in positions if p['status'] == 'open']:
                exit_signal = self.check_exit_conditions(
                    position, current_bar, current_data, signal
                )
                
                if exit_signal:
                    # Close position
                    position['exit_time'] = current_bar.name
                    position['exit_price'] = current_bar['close']
                    position['status'] = 'closed'
                    
                    # Calculate P&L
                    pnl = self.calculate_position_pnl(position)
                    balance += pnl
                    
                    # Record trade
                    trade = {
                        'timestamp': current_bar.name,
                        'action': 'EXIT_LONG',
                        'price': current_bar['close'],
                        'quantity': position['size'],
                        'fees': self.fee_calculator.calculate_trade_fees(
                            'market', position['size'], current_bar['close'], is_maker=False
                        ),
                        'pnl': pnl,
                        'exit_reason': exit_signal['reason']
                    }
                    trades.append(trade)
        
        # Calculate performance metrics
        metrics = self.calculate_performance_metrics(trades, positions, balance, config)
        
        return {
            'config': config,
            'balance': balance,
            'trades': trades,
            'positions': positions,
            'signals': signals,
            'metrics': metrics
        }
    
    def generate_backtest_report(self, results: Dict) -> Dict:
        """Generate comprehensive backtest report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_backtests': len(results['individual_results']),
            'aggregated_metrics': results['aggregated_metrics'],
            'best_config': results['best_config'],
            'worst_config': results['worst_config'],
            'parameter_sensitivity': self.analyze_parameter_sensitivity(results),
            'trade_analysis': self.analyze_trades(results),
            'equity_curve': self.calculate_equity_curve(results),
            'risk_metrics': self.calculate_risk_metrics(results)
        }
        
        # Save report as JSON
        import json
        with open(f"data/reports/backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        return report

6. ADVANCED JSON REPORTING SYSTEM
6.1 Enhanced Report Schema

File: src/reporting/report_schema.json
json

{
  "report_metadata": {
    "report_id": "uuid",
    "generation_timestamp": "iso_timestamp",
    "session_type": "backtest|paper|live",
    "duration_hours": 0,
    "bot_version": "v10"
  },
  "session_configuration": {
    "trading_symbol": "BTC/USDT:USDT",
    "timeframes": ["15m", "30m", "45m", "1h", "2h", "4h"],
    "layer_weights": {
      "traditional": 0.25,
      "volume_delta": 0.15,
      "weis_wave": 0.10,
      "xgboost": 0.20,
      "cnn_lstm": 0.25,
      "microstructure": 0.05
    },
    "risk_parameters": {
      "initial_balance": 10000,
      "risk_per_trade": 0.02,
      "max_daily_loss": 0.1,
      "position_sizing_method": "kelly|fixed_fractional|optimal_f"
    }
  },
  "performance_metrics": {
    "financial": {
      "final_balance": 0,
      "total_return_pct": 0,
      "total_profit": 0,
      "total_loss": 0,
      "net_profit": 0,
      "profit_factor": 0,
      "sharpe_ratio": 0,
      "sortino_ratio": 0,
      "calmar_ratio": 0,
      "max_drawdown_pct": 0,
      "max_drawdown_duration_days": 0
    },
    "trade_metrics": {
      "total_trades": 0,
      "winning_trades": 0,
      "losing_trades": 0,
      "win_rate_pct": 0,
      "avg_win_pct": 0,
      "avg_loss_pct": 0,
      "largest_win": 0,
      "largest_loss": 0,
      "avg_trade_duration_minutes": 0,
      "profit_per_trade": 0,
      "expectancy": 0
    },
    "fee_analysis": {
      "total_trading_fees": 0,
      "total_funding_fees": 0,
      "total_slippage": 0,
      "total_costs": 0,
      "cost_as_pct_of_profit": 0,
      "fee_breakdown": {
        "maker_fees": 0,
        "taker_fees": 0,
        "funding_payments": 0
      }
    }
  },
  "layer_performance": {
    "layer_contributions": [
      {
        "layer_name": "traditional",
        "signal_accuracy_pct": 0,
        "weight": 0.25,
        "contribution_to_profit": 0,
        "false_signals": 0
      }
    ],
    "composite_signal_accuracy": 0,
    "layer_correlation_matrix": {}
  },
  "trade_log": {
    "trades": [
      {
        "trade_id": "uuid",
        "entry_timestamp": "iso_timestamp",
        "exit_timestamp": "iso_timestamp",
        "direction": "LONG|SHORT",
        "entry_price": 0,
        "exit_price": 0,
        "size": 0,
        "entry_reason": "string",
        "exit_reason": "TAKE_PROFIT|STOP_LOSS|TRAILING_STOP|SIGNAL_REVERSAL|TIME_EXIT",
        "gross_profit": 0,
        "net_profit": 0,
        "profit_pct": 0,
        "duration_minutes": 0,
        "entry_signals": {
          "layer1_score": 0,
          "layer2_score": 0,
          "layer3_score": 0,
          "layer4_score": 0,
          "layer5_score": 0,
          "composite_score": 0,
          "confidence": 0,
          "risk_adjusted_score": 0
        },
        "exit_signals": {
          "layer1_score": 0,
          "layer2_score": 0,
          "composite_score": 0,
          "exit_conditions_met": []
        },
        "fees": {
          "entry_fee": 0,
          "exit_fee": 0,
          "funding_fees": 0,
          "total_fees": 0
        },
        "risk_metrics": {
          "risk_reward_ratio": 0,
          "position_size_pct": 0,
          "stop_loss": 0,
          "take_profit": 0,
          "initial_risk": 0,
          "actual_risk": 0
        }
      }
    ],
    "trade_sequence_analysis": {
      "consecutive_wins": 0,
      "consecutive_losses": 0,
      "largest_winning_streak": 0,
      "largest_losing_streak": 0,
      "recovery_factor": 0
    }
  },
  "market_conditions": {
    "volatility_regime": "HIGH|MEDIUM|LOW",
    "trend_regime": "STRONG_UPTREND|UPTREND|RANGING|DOWNTREND|STRONG_DOWNTREND",
    "volume_regime": "HIGH|AVERAGE|LOW",
    "average_true_range_pct": 0,
    "realized_volatility": 0,
    "market_hours_analysis": {
      "asian_session_performance": {},
      "london_session_performance": {},
      "us_session_performance": {}
    }
  },
  "system_health": {
    "data_quality": {
      "missing_data_points": 0,
      "data_latency_ms": 0,
      "api_errors": 0,
      "data_gaps_minutes": 0
    },
    "model_performance": {
      "xgboost_accuracy": 0,
      "cnn_lstm_accuracy": 0,
      "model_decay_pct": 0,
      "last_retrained": "timestamp"
    },
    "execution_quality": {
      "order_fill_rate_pct": 0,
      "avg_slippage_pct": 0,
      "avg_execution_time_ms": 0,
      "requeues": 0
    }
  },
  "recommendations": {
    "parameter_optimizations": [
      {
        "parameter": "layer_weights.traditional",
        "current_value": 0.25,
        "suggested_value": 0.28,
        "expected_improvement_pct": 2.5
      }
    ],
    "risk_adjustments": [
      {
        "adjustment": "reduce_position_size",
        "reason": "high_volatility_regime",
        "suggested_multiplier": 0.7
      }
    ],
    "model_retraining_schedule": "next_retraining_timestamp"
  }
}

6.2 Report Generator

File: src/reporting/report_builder.py
python

import json
import uuid
from datetime import datetime
from typing import Dict, List
import pandas as pd
import numpy as np

class AdvancedReportBuilder:
    def __init__(self, session_type: str = "backtest"):
        self.session_type = session_type
        self.report_data = {}
        
    def build_report(self, backtest_results: Dict, 
                    trades: List[Dict], 
                    metrics: Dict,
                    config: Dict) -> Dict:
        """Build comprehensive JSON report"""
        
        report_id = str(uuid.uuid4())
        
        # 1. Metadata
        self.report_data['report_metadata'] = {
            'report_id': report_id,
            'generation_timestamp': datetime.now().isoformat(),
            'session_type': self.session_type,
            'duration_hours': self.calculate_session_duration(trades),
            'bot_version': 'v10',
            'report_version': '1.0'
        }
        
        # 2. Configuration
        self.report_data['session_configuration'] = {
            'trading_symbol': config.get('symbol', 'BTC/USDT:USDT'),
            'timeframes': config.get('timeframes', ['15m', '30m', '45m', '1h', '2h', '4h']),
            'layer_weights': config.get('layer_weights', {}),
            'risk_parameters': config.get('risk_parameters', {}),
            'ml_parameters': config.get('ml_parameters', {})
        }
        
        # 3. Performance Metrics
        self.report_data['performance_metrics'] = self.calculate_performance_metrics(
            backtest_results, trades, metrics
        )
        
        # 4. Layer Performance
        self.report_data['layer_performance'] = self.analyze_layer_performance(trades)
        
        # 5. Trade Log
        self.report_data['trade_log'] = self.build_trade_log(trades)
        
        # 6. Market Conditions
        self.report_data['market_conditions'] = self.analyze_market_conditions(
            backtest_results.get('market_data', {})
        )
        
        # 7. System Health
        self.report_data['system_health'] = self.analyze_system_health(
            backtest_results.get('system_metrics', {})
        )
        
        # 8. Recommendations
        self.report_data['recommendations'] = self.generate_recommendations()
        
        # Save report
        self.save_report(report_id)
        
        return self.report_data
    
    def calculate_performance_metrics(self, backtest_results: Dict, 
                                     trades: List[Dict], 
                                     metrics: Dict) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        # Financial metrics
        initial_balance = backtest_results.get('initial_balance', 10000)
        final_balance = backtest_results.get('final_balance', initial_balance)
        
        # Calculate returns
        returns = [t.get('net_profit', 0) / initial_balance 
                  for t in trades if t.get('net_profit')]
        
        # Sharpe Ratio (assuming 0% risk-free rate)
        if len(returns) > 1:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe = 0
        
        # Max drawdown
        equity_curve = self.calculate_equity_curve(trades, initial_balance)
        drawdown = self.calculate_max_drawdown(equity_curve)
        
        return {
            'financial': {
                'final_balance': final_balance,
                'total_return_pct': (final_balance / initial_balance - 1) * 100,
                'total_profit': sum(t.get('gross_profit', 0) for t in trades),
                'total_loss': sum(t.get('gross_loss', 0) for t in trades),
                'net_profit': final_balance - initial_balance,
                'profit_factor': self.calculate_profit_factor(trades),
                'sharpe_ratio': sharpe,
                'sortino_ratio': self.calculate_sortino_ratio(returns),
                'calmar_ratio': self.calculate_calmar_ratio(
                    final_balance / initial_balance - 1, 
                    drawdown['max_drawdown_pct'] / 100
                ),
                'max_drawdown_pct': drawdown['max_drawdown_pct'],
                'max_drawdown_duration_days': drawdown['duration_days']
            },
            'trade_metrics': {
                'total_trades': len(trades),
                'winning_trades': len([t for t in trades if t.get('net_profit', 0) > 0]),
                'losing_trades': len([t for t in trades if t.get('net_profit', 0) <= 0]),
                'win_rate_pct': (len([t for t in trades if t.get('net_profit', 0) > 0]) / len(trades)) * 100 if trades else 0,
                'avg_win_pct': np.mean([t.get('profit_pct', 0) for t in trades if t.get('profit_pct', 0) > 0]) if any(t.get('profit_pct', 0) > 0 for t in trades) else 0,
                'avg_loss_pct': np.mean([t.get('profit_pct', 0) for t in trades if t.get('profit_pct', 0) <= 0]) if any(t.get('profit_pct', 0) <= 0 for t in trades) else 0,
                'largest_win': max([t.get('net_profit', 0) for t in trades], default=0),
                'largest_loss': min([t.get('net_profit', 0) for t in trades], default=0),
                'avg_trade_duration_minutes': np.mean([t.get('duration_minutes', 0) for t in trades]) if trades else 0,
                'profit_per_trade': (final_balance - initial_balance) / len(trades) if trades else 0,
                'expectancy': self.calculate_expectancy(trades)
            },
            'fee_analysis': self.analyze_fees(trades)
        }
    
    def build_trade_log(self, trades: List[Dict]) -> Dict:
        """Build detailed trade log"""
        formatted_trades = []
        
        for trade in trades:
            formatted_trade = {
                'trade_id': str(uuid.uuid4()),
                'entry_timestamp': trade.get('entry_time', datetime.now()).isoformat(),
                'exit_timestamp': trade.get('exit_time', datetime.now()).isoformat(),
                'direction': trade.get('direction', 'LONG'),
                'entry_price': trade.get('entry_price', 0),
                'exit_price': trade.get('exit_price', 0),
                'size': trade.get('size', 0),
                'entry_reason': trade.get('entry_reason', 'signal'),
                'exit_reason': trade.get('exit_reason', 'unknown'),
                'gross_profit': trade.get('gross_profit', 0),
                'net_profit': trade.get('net_profit', 0),
                'profit_pct': trade.get('profit_pct', 0),
                'duration_minutes': trade.get('duration_minutes', 0),
                'entry_signals': trade.get('entry_signals', {}),
                'exit_signals': trade.get('exit_signals', {}),
                'fees': trade.get('fees', {}),
                'risk_metrics': trade.get('risk_metrics', {})
            }
            formatted_trades.append(formatted_trade)
        
        # Trade sequence analysis
        sequence_analysis = self.analyze_trade_sequence(formatted_trades)
        
        return {
            'trades': formatted_trades,
            'trade_sequence_analysis': sequence_analysis
        }
    
    def save_report(self, report_id: str):
        """Save report to JSON file"""
        filename = f"data/reports/{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.report_data, f, indent=2, default=str)
        
        print(f"✓ Report saved: {filename}")
        
        # Also save summary CSV
        self.save_summary_csv(filename.replace('.json', '_summary.csv'))
    
    def save_summary_csv(self, filename: str):
        """Save trade summary as CSV"""
        if 'trade_log' in self.report_data and 'trades' in self.report_data['trade_log']:
            trades_df = pd.DataFrame(self.report_data['trade_log']['trades'])
            trades_df.to_csv(filename, index=False)
            print(f"✓ Trade summary saved: {filename}")

7. DEPLOYMENT & EXECUTION SCRIPTS
7.1 Main Execution Script

File: scripts/run_live.py
python

#!/usr/bin/env python3
"""
BTC Scalp Bot V10 - Live Trading Execution
"""

import sys
import asyncio
import signal
from datetime import datetime
from src.core.data_pipeline import MultiTimeframeDataPipeline
from src.layers.layer_compositor import LayerCompositor
from src.trading.signal_generator import SignalGenerator
from src.trading.order_manager import OrderManager
from src.utils.logger import setup_logger
from src.utils.error_handler import ErrorHandler

class LiveTradingBot:
    def __init__(self, config_path: str = "config/bot_config.yaml"):
        self.logger = setup_logger("live_bot")
        self.error_handler = ErrorHandler()
        self.is_running = True
        
        # Load configuration
        self.config = self.load_config(config_path)
        
        # Initialize components
        self.data_pipeline = MultiTimeframeDataPipeline(
            exchange=self.config['exchange'],
            max_workers=self.config.get('data_workers', 4)
        )
        
        self.layer_compositor = LayerCompositor(
            weights=self.config['layer_weights']
        )
        
        self.signal_generator = SignalGenerator(
            config=self.config['trading']
        )
        
        self.order_manager = OrderManager(
            exchange_config=self.config['exchange'],
            fee_structure=self.config['fees']
        )
        
        # Performance tracking
        self.performance_tracker = {
            'start_time': datetime.now(),
            'trades': [],
            'signals': [],
            'balance': self.config['trading']['initial_balance']
        }
    
    async def run(self):
        """Main trading loop"""
        self.logger.info("Starting BTC Scalp Bot V10")
        
        # Signal handling
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            while self.is_running:
                # 1. Fetch latest data
                data = await self.data_pipeline.fetch_all_timeframes(
                    symbol=self.config['trading']['symbol'],
                    limit=1000
                )
                
                # 2. Calculate layer signals
                layer_signals = await self.layer_compositor.calculate_all_layers(data)
                
                # 3. Generate trading signal
                trading_signal = self.signal_generator.generate_signal(
                    layer_signals, 
                    data['15m'].iloc[-1]
                )
                
                # 4. Execute if signal is strong enough
                if trading_signal['confidence'] > self.config['trading']['min_confidence']:
                    await self.execute_trade(trading_signal, data)
                
                # 5. Monitor open positions
                await self.monitor_positions(data)
                
                # 6. Log performance
                self.log_performance()
                
                # 7. Wait for next candle
                await asyncio.sleep(self.get_sleep_time())
                
        except Exception as e:
            self.error_handler.handle_critical_error(e)
            await self.shutdown()
    
    async def execute_trade(self, signal: Dict, data: Dict):
        """Execute trade based on signal"""
        try:
            # Calculate position size
            position_size = self.calculate_position_size(signal)
            
            # Place order
            order_result = await self.order_manager.place_order(
                symbol=self.config['trading']['symbol'],
                side=signal['direction'].lower(),
                quantity=position_size,
                order_type=signal.get('order_type', 'market'),
                price=data['15m'].iloc[-1]['close']
            )
            
            if order_result['success']:
                self.performance_tracker['trades'].append({
                    'timestamp': datetime.now(),
                    'direction': signal['direction'],
                    'size': position_size,
                    'price': order_result['price'],
                    'signal_strength': signal['confidence'],
                    'layer_breakdown': signal['layer_breakdown']
                })
                
                self.logger.info(f"Trade executed: {signal['direction']} "
                               f"{position_size} BTC at ${order_result['price']}")
        
        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Initiating shutdown...")
        self.is_running = False
        
        # Close all open positions
        await self.order_manager.close_all_positions()
        
        # Generate final report
        self.generate_final_report()
        
        self.logger.info("Shutdown complete")
        sys.exit(0)

if __name__ == "__main__":
    bot = LiveTradingBot()
    asyncio.run(bot.run())

7.2 Model Training Pipeline

File: scripts/train_models.py
python

#!/usr/bin/env python3
"""
Model Training Pipeline
"""

import argparse
from datetime import datetime, timedelta
from src.layers.layer4_xgboost import EnhancedXGBoostLayer
from src.layers.layer5_cnn_lstm import CNNLSTMLayer
from src.core.data_pipeline import MultiTimeframeDataPipeline

def train_all_models():
    """Train all ML models with latest data"""
    print("="*70)
    print("MODEL TRAINING PIPELINE")
    print("="*70)
    
    # 1. Fetch training data
    pipeline = MultiTimeframeDataPipeline()
    data = pipeline.fetch_all_timeframes(
        symbol="BTC/USDT:USDT",
        limit=5000  # ~3 months of 15m data
    )
    
    # 2. Train XGBoost
    print("\nTraining XGBoost Model...")
    xgb_layer = EnhancedXGBoostLayer()
    xgb_model = xgb_layer.train_with_walk_forward(data['4h'])
    print("✓ XGBoost training complete")
    
    # 3. Train CNN-LSTM
    print("\nTraining CNN-LSTM Model...")
    cnn_lstm_layer = CNNLSTMLayer()
    cnn_lstm_model = cnn_lstm_layer.train_model(
        data['15m'], 
        sequence_length=30,
        epochs=100
    )
    print("✓ CNN-LSTM training complete")
    
    # 4. Validate models
    print("\nModel Validation...")
    validation_results = validate_models(
        xgb_model, 
        cnn_lstm_model, 
        data['1h']
    )
    
    # 5. Save model metrics
    save_model_metrics(validation_results)
    
    print("\n" + "="*70)
    print("ALL MODELS TRAINED SUCCESSFULLY")
    print("="*70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train ML models for trading bot")
    parser.add_argument("--retrain-all", action="store_true", 
                       help="Retrain all models from scratch")
    parser.add_argument("--data-days", type=int, default=90,
                       help="Days of historical data to use")
    
    args = parser.parse_args()
    train_all_models()

8. VALIDATION & TESTING
8.1 Performance Targets
text

PHASE VALIDATION METRICS:

✓ V1 Foundation (Weeks 1-3):
  - Win Rate: 55-60%
  - Sharpe Ratio: >1.2
  - Max Drawdown: <30%
  - Minimum Trades: 50+

✓ + Layer 2 (Week 4):
  - Win Rate Improvement: +3-5%
  - Reduction in false signals: 15-20%
  - Early reversal detection: 6-12 hours

✓ + Layer 3 (Week 5):
  - Win Rate: 60-65%
  - Accumulation detection accuracy: >70%
  - Distribution warning lead time: 1-3 days

✓ + Layer 4 (Weeks 6-7):
  - Win Rate: 63-68%
  - XGBoost test accuracy: 55-60%
  - Feature importance stability: >80%

✓ + Layer 5 (Weeks 7-8):
  - Win Rate: 68-72%
  - CNN-LSTM validation accuracy: 65-70%
  - Sequence prediction accuracy: >60%

✓ Full System (Week 9):
  - Composite Win Rate: 70-75%
  - Profit Factor: >1.5
  - Sharpe Ratio: >1.5
  - Max Drawdown: <25%
  - Recovery Factor: >2.0

8.2 Risk Management Rules
text

HARD STOP RULES (IMMEDIATE SHUTDOWN):

1. Daily Loss Limits:
   - Max daily loss: 10% of account
   - Consecutive losses: 5 trades

2. Drawdown Limits:
   - Max drawdown: 30% from peak
   - Weekly drawdown: 15%

3. System Health:
   - Data latency: >5 seconds
   - API error rate: >10%
   - Model accuracy decay: >20%

4. Market Conditions:
   - Extreme volatility: ATR > 5%
   - Low liquidity: Spread > 0.1%
   - News events: Major announcements

9. DEPLOYMENT CHECKLIST
9.1 Pre-Deployment Validation
text

[ ] 1. BACKTESTING
    [ ] 6-month backtest complete
    [ ] Win rate: 70-75%
    [ ] Sharpe ratio: >1.5
    [ ] Max drawdown: <25%
    [ ] Walk-forward validation passed

[ ] 2. PAPER TRADING (2+ weeks)
    [ ] Live paper trading results match backtest (±5%)
    [ ] Order execution: >95% fill rate
    [ ] Slippage: <0.1% average
    [ ] Fee calculation accurate

[ ] 3. SYSTEM ROBUSTNESS
    [ ] 24-hour continuous run without errors
    [ ] Network interruption recovery tested
    [ ] Data corruption handling tested
    [ ] API rate limit handling

[ ] 4. RISK CONTROLS
    [ ] Stop losses executing correctly
    [ ] Position sizing accurate
    [ ] Daily loss limits working
    [ ] Emergency shutdown tested

9.2 Live Deployment Phases
text

PHASE 1 (Week 1-2): MICRO-LIVE
  - Trade size: 10% of normal
  - Maximum 1 trade per day
  - Focus on execution quality
  - Monitor all metrics closely

PHASE 2 (Week 3-4): SMALL-LIVE
  - Trade size: 25% of normal
  - Maximum 2 trades per day
  - Validate layer contributions
  - Fine-tune parameters

PHASE 3 (Week 5+): FULL-LIVE
  - Trade size: 50-100% of normal
  - Full trading frequency
  - Continuous monitoring
  - Weekly performance review

10. MAINTENANCE & MONITORING
10.1 Daily Checklist
text

BEFORE TRADING:
[ ] System health check
[ ] Data freshness verification
[ ] Model accuracy check
[ ] Exchange connectivity test
[ ] Risk limits review

DURING TRADING:
[ ] Real-time performance monitoring
[ ] Layer contribution tracking
[ ] Market regime detection
[ ] Position monitoring
[ ] Error log monitoring

AFTER TRADING:
[ ] Daily performance report
[ ] Trade analysis
[ ] Fee calculation verification
[ ] System backup
[ ] Next day preparation

10.2 Weekly Maintenance
text

EVERY WEEK:
[ ] Model retraining (if accuracy < 60%)
[ ] Backtest on latest week
[ ] Parameter optimization
[ ] Report generation
[ ] System cleanup

EVERY MONTH:
[ ] Full system revalidation
[ ] Extended backtest (3+ months)
[ ] Strategy review
[ ] Risk parameter adjustment
[ ] Performance analysis report

11. ERROR HANDLING & RECOVERY
11.1 Graceful Error Recovery
python

class TradingBotErrorHandler:
    ERROR_LEVELS = {
        'INFO': 0,
        'WARNING': 1,
        'ERROR': 2,
        'CRITICAL': 3
    }
    
    def handle_error(self, error: Exception, context: str = "") -> Dict:
        """Handle errors with appropriate recovery actions"""
        
        error_type = type(error).__name__
        
        # Define recovery actions based on error type
        recovery_actions = {
            'ConnectionError': self.handle_connection_error,
            'RateLimitError': self.handle_rate_limit_error,
            'InsufficientFunds': self.handle_insufficient_funds,
            'OrderExecutionError': self.handle_order_error,
            'DataError': self.handle_data_error,
            'ModelError': self.handle_model_error
        }
        
        # Log error
        self.logger.error(f"{context}: {error_type}: {str(error)}")
        
        # Execute recovery
        if error_type in recovery_actions:
            return recovery_actions[error_type](../../v3/archived/legacy/error)
        else:
            return self.handle_unknown_error(error)
    
    def handle_connection_error(self, error: Exception) -> Dict:
        """Handle network/connection errors"""
        # Attempt reconnection with exponential backoff
        for attempt in range(3):
            try:
                time.sleep(2 ** attempt)  # Exponential backoff
                self.reconnect()
                return {'status': 'recovered', 'attempts': attempt + 1}
            except:
                continue
        
        # If still failing, enter safe mode
        self.enter_safe_mode()
        return {'status': 'safe_mode', 'action': 'paused_trading'}

12. FINAL NOTES
12.1 Success Metrics
text

PRIMARY METRICS (Target):
✓ Win Rate: 70-75%
✓ Profit Factor: >1.5
✓ Sharpe Ratio: >1.5
✓ Max Drawdown: <25%
✓ Recovery Factor: >2.0
✓ Annual Return: >50%

SECONDARY METRICS:
✓ Layer Contribution Balance
✓ Model Accuracy Stability
✓ Execution Quality
✓ Risk-Adjusted Returns

12.2 Development Timeline
text

WEEK 1-3: V1 Foundation
  - Data pipeline & indicators
  - Multi-timeframe analysis
  - Basic backtesting

WEEK 4: Layer 2 (Volume Delta)
  - Volume divergence detection
  - Integration with V1

WEEK 5: Layer 3 (Weis Wave)
  - Wave volume analysis
  - Accumulation detection

WEEK 6-7: Layer 4 (XGBoost)
  - Feature engineering
  - Model training & validation
  - Integration

WEEK 7-8: Layer 5 (CNN-LSTM)
  - Sequence preparation
  - Deep learning model
  - Ensemble integration

WEEK 8-9: Final Integration
  - 6-layer fusion
  - Advanced reporting
  - Paper trading
  - Live deployment prep

12.3 Critical Success Factors

    Focus on risk management: Preserve capital above all else

    Automate everything: Manual intervention leads to emotional trading

    Monitor continuously: Markets change, systems must adapt

    Document everything: Every trade, every decision, every parameter

This enhanced specification provides a complete, production-ready trading system with:

    Multiprocessing architecture for performance

    Comprehensive fee-aware backtesting

    Advanced JSON reporting

    Robust error handling

    Complete deployment pipeline

    Ongoing maintenance procedures

Follow this specification methodically, validate each phase thoroughly, and maintain discipline throughout development and deployment.
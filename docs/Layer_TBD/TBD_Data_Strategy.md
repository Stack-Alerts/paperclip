# Layer TBD Data Strategy - Historical + Real-Time Hybrid

## Overview

Layer TBD uses a **hybrid data strategy** that combines historical archive data with real-time market data depending on the trading mode.

---

## Data Architecture

### Two-Tier System

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER TBD DATA SYSTEM                     │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
        ┌───────▼────────┐         ┌───────▼────────┐
        │  HISTORICAL    │         │   REAL-TIME    │
        │  (Crypto-Lake) │         │  (Binance API) │
        └───────┬────────┘         └───────┬────────┘
                │                           │
     ┌──────────┴───────────┐    ┌─────────┴──────────┐
     │ Backtest/WalkForward │    │  Paper/Live Trade  │
     │                      │    │                     │
     │ • Complete history   │    │ • Last 30 days     │
     │ • 2024-01 to today   │    │ • Fast updates     │
     │ • Testing/tuning     │    │ • Current market   │
     └──────────────────────┘    └────────────────────┘
```

---

## Mode-Specific Data Usage

### 1. Backtest Mode

**Data Source**: Crypto-Lake (Historical Archive)

```python
# Use historical data exclusively
liquidations = load_cryptolake_data(start_date='2024-01', end_date='2024-12')
funding = load_cryptolake_data(table='funding', ...)
open_interest = load_cryptolake_data(table='open_interest', ...)

# Establish patterns, levels, clusters
model.analyze_historical_levels(liquidations)
model.identify_support_resistance(liquidations, oi)
model.calibrate_thresholds(funding, oi)
```

**Purpose**:
- Test Layer TBD methodology
- Optimize parameters
- Validate strategy edge
- Historical performance metrics

**Data Coverage**: Jan 2024 - Today (complete)

---

### 2. Walk Forward Mode

**Data Source**: Crypto-Lake (Historical Archive)

```python
# Rolling window testing
for window in walk_forward_windows:
    train_data = load_cryptolake_data(window.train_start, window.train_end)
    test_data = load_cryptolake_data(window.test_start, window.test_end)
    
    model.train(train_data)
    results = model.test(test_data)
```

**Purpose**:
- Out-of-sample validation
- Robustness testing
- Parameter stability
- Prevent overfitting

**Data Coverage**: Jan 2024 - Today (complete)

---

### 3. Paper Trading Mode ⚡ HYBRID

**Data Sources**: Historical (Crypto-Lake) + Real-Time (Binance)

```python
# PHASE 1: Load historical context (on startup)
historical_liq = load_cryptolake_data('liquidations', start='2024-01', end='today')
historical_funding = load_cryptolake_data('funding', start='2024-01', end='today')
historical_oi = load_cryptolake_data('open_interest', start='2024-01', end='today')

# Establish baseline model state
model.build_historical_context(historical_liq, historical_funding, historical_oi)
model.identify_key_levels(historical_liq)  # S/R levels from 2024+
model.establish_funding_bias_ranges(historical_funding)
model.calibrate_oi_thresholds(historical_oi)

# PHASE 2: Real-time updates (every N minutes)
recent_liq = load_binance_data('liquidations', days_back=30)
recent_funding = get_binance_funding_rate()  # Current funding
recent_oi = get_binance_open_interest()      # Current OI

# Update current market state
model.update_recent_liquidation_clusters(recent_liq)
model.update_funding_sentiment(recent_funding)
model.update_oi_trend(recent_oi)

# Make trading decisions with full context
signal = model.generate_signal(
    historical_context=True,   # Uses Crypto-Lake baseline
    current_market=recent_liq  # Uses Binance real-time
)
```

**Why Hybrid Approach?**

1. **Historical Context** (Crypto-Lake):
   - Establish long-term support/resistance levels
   - Understand seasonal patterns
   - Identify persistent liquidation clusters
   - Calibrate model parameters from extensive data

2. **Real-Time Market State** (Binance):
   - Current liquidation clusters forming NOW
   - Live funding rate sentiment
   - Active open interest trends
   - Fast data for immediate decisions

**Example**:

```python
class LayerTBDMethod:
    def __init__(self, mode='paper'):
        self.mode = mode
        
        # ALWAYS load historical context (even in paper/live)
        self.historical_levels = self._load_historical_levels()
        self.baseline_funding = self._load_historical_funding_stats()
        self.oi_percentiles = self._load_historical_oi_distribution()
        
        if mode in ['paper', 'live']:
            # Add real-time data layer
            self.realtime_connector = BinanceRealtimeConnector()
    
    def _load_historical_levels(self):
        """Load all liquidation levels from Crypto-Lake (2024+)."""
        all_months = []
        for year in [2024, 2025]:
            for month in range(1, 13):
                file = f"data/raw/liquidations/BTC-USDT_liquidations_{year}-{month:02d}.parquet"
                if Path(file).exists():
                    df = pd.read_parquet(file)
                    all_months.append(df)
        
        combined = pd.concat(all_months)
        
        # Identify major liquidation levels from ALL history
        levels = self._cluster_liquidation_levels(combined)
        return levels
    
    def generate_signal(self, current_price, current_time):
        """Generate trading signal with hybrid data."""
        
        # Use HISTORICAL context for baseline
        major_levels = self.historical_levels  # From Crypto-Lake
        
        # Use REAL-TIME data for current state
        if self.mode in ['paper', 'live']:
            recent_liq = self.realtime_connector.get_recent_liquidations(hours=24)
            current_funding = self.realtime_connector.get_funding_rate()
            current_oi = self.realtime_connector.get_open_interest()
        else:
            # Backtest/walkforward uses historical only
            recent_liq = self._get_historical_liquidations(current_time)
            current_funding = self._get_historical_funding(current_time)
            current_oi = self._get_historical_oi(current_time)
        
        # Combine: Historical baseline + Real-time state
        distance_to_historical_level = min(abs(current_price - l) for l in major_levels)
        recent_cluster_strength = self._analyze_cluster(recent_liq, current_price)
        funding_bias = self._normalize_funding(current_funding, self.baseline_funding)
        oi_percentile = self._get_oi_percentile(current_oi, self.oi_percentiles)
        
        # Trading decision uses BOTH:
        # - Where we are relative to HISTORICAL levels (Crypto-Lake)
        # - What's happening NOW in the market (Binance)
        
        signal = self._calculate_signal(
            distance_to_historical_level,  # Long-term context
            recent_cluster_strength,        # Current market
            funding_bias,                   # Current sentiment
            oi_percentile                   # Current participation
        )
        
        return signal
```

---

### 4. Live Trading Mode ⚡ HYBRID

**Same as Paper Trading** - identical hybrid approach:

- Historical context establishes baseline (Crypto-Lake)
- Real-time data drives decisions (Binance)
- Model knows both WHERE it is (historically) and WHAT's happening (now)

---

## Data Loading Strategy

### Startup (One-Time)

```python
# Load complete historical context (10-60 seconds)
print("Loading historical context from Crypto-Lake...")

liquidations_2024 = []
for month in range(1, 13):
    df = pd.read_parquet(f"data/raw/liquidations/BTC-USDT_liquidations_2024-{month:02d}.parquet")
    liquidations_2024.append(df)

liquidations_2025 = []
for month in range(1, 13):
    file = f"data/raw/liquidations/BTC-USDT_liquidations_2025-{month:02d}.parquet"
    if Path(file).exists():
        df = pd.read_parquet(file)
        liquidations_2025.append(df)

all_liquidations = pd.concat(liquidations_2024 + liquidations_2025)

# Build historical model state
historical_levels = identify_all_major_levels(all_liquidations)
historical_patterns = analyze_temporal_patterns(all_liquidations)
historical_stats = calculate_baseline_statistics(all_liquidations)

print(f"✅ Loaded {len(all_liquidations):,} liquidations from 2024-2025")
print(f"✅ Identified {len(historical_levels)} major liquidation levels")
```

### Runtime Updates (Continuous)

```python
# Update with fresh Binance data (every 5-15 minutes)
if mode in ['paper', 'live']:
    recent_liq = binance_api.get_liquidations(hours_back=24)
    recent_funding = binance_api.get_funding_rate()
    recent_oi = binance_api.get_open_interest()
    
    # Update ONLY recent state, keep historical baseline
    model.update_recent_state(recent_liq, recent_funding, recent_oi)
```

---

## Implementation Example

### Full Paper/Live Trading Setup

```python
class LayerTBDPaperLive:
    """
    Layer TBD for Paper/Live Trading
    
    Uses:
    - Historical data (Crypto-Lake): Baseline context, major levels
    - Real-time data (Binance): Current market state
    """
    
    def __init__(self):
        # Phase 1: Load historical baseline (once at startup)
        print("Initializing Layer TBD with historical context...")
        self.historical_context = self._load_historical_context()
        print(f"✅ Historical context loaded:")
        print(f"   - Liquidation levels: {len(self.historical_context['levels'])}")
        print(f"   - Date range: 2024-01 to {datetime.now().strftime('%Y-%m')}")
        
        # Phase 2: Connect to real-time data
        print("Connecting to Binance real-time feeds...")
        self.binance = BinanceRealtimeConnector()
        print("✅ Real-time connection established")
    
    def _load_historical_context(self):
        """Load complete historical data from Crypto-Lake."""
        context = {
            'liquidations': self._load_all_liquidations(),
            'funding': self._load_all_funding(),
            'open_interest': self._load_all_oi()
        }
        
        # Analyze historical data to establish baseline
        context['levels'] = self._identify_major_levels(context['liquidations'])
        context['funding_stats'] = self._analyze_funding_patterns(context['funding'])
        context['oi_stats'] = self._analyze_oi_distribution(context['open_interest'])
        
        return context
    
    def _load_all_liquidations(self):
        """Load all liquidation data from Crypto-Lake."""
        all_data = []
        for year in [2024, 2025]:
            for month in range(1, 13):
                file = Path(f"data/raw/liquidations/BTC-USDT_liquidations_{year}-{month:02d}.parquet")
                if file.exists():
                    df = pd.read_parquet(file)
                    all_data.append(df)
        return pd.concat(all_data)
    
    def get_trading_signal(self, current_price, current_time):
        """
        Generate trading signal using BOTH historical and real-time data.
        
        Historical (Crypto-Lake): Where are we relative to major levels?
        Real-time (Binance): What's happening right now?
        """
        
        # Historical baseline (Crypto-Lake)
        major_support_levels = self.historical_context['levels']['support']
        major_resistance_levels = self.historical_context['levels']['resistance']
        baseline_funding = self.historical_context['funding_stats']['median']
        baseline_oi = self.historical_context['oi_stats']['median']
        
        # Real-time current state (Binance)
        recent_liquidations = self.binance.get_recent_liquidations(hours=24)
        current_funding = self.binance.get_funding_rate()
        current_oi = self.binance.get_open_interest()
        
        # Analyze: Historical context + Real-time state
        analysis = {
            # Where are we historically?
            'distance_to_major_support': self._distance_to_nearest(current_price, major_support_levels),
            'distance_to_major_resistance': self._distance_to_nearest(current_price, major_resistance_levels),
            
            # What's happening now?
            'recent_liq_cluster_strength': self._cluster_strength(recent_liquidations, current_price),
            'funding_deviation': (current_funding - baseline_funding) / baseline_funding,
            'oi_percentile': self._calculate_percentile(current_oi, baseline_oi),
            
            # Combined signals
            'approaching_historical_level': self._is_approaching_level(current_price, major_support_levels + major_resistance_levels),
            'recent_cluster_forming': self._is_cluster_forming(recent_liquidations, current_price),
            'funding_extreme': abs(current_funding) > abs(baseline_funding) * 2,
            'oi_extreme': current_oi > baseline_oi * 1.5
        }
        
        # Generate signal
        signal = self._generate_signal(analysis)
        
        return signal
```

---

## Data Update Frequencies

### Historical Context (Crypto-Lake)

**Frequency**: Daily or Weekly

```bash
# Run daily to get latest month's data
python3 scripts/data_download/download_liquidations_funding_oi.py

# Updates:
# - Current month if >24h old
# - Skips all historical months (already downloaded)
# - Bandwidth: ~1-2 GB/month
```

**When to Reload**: 
- Daily: Reload current month
- Weekly: Full historical refresh (optional)
- Monthly: Mandatory refresh when new month starts

### Real-Time Data (Binance)

**Frequency**: Every 5-15 minutes (during trading)

```python
# Runtime updates
while trading:
    recent_liq = binance_api.get_liquidations(hours_back=24)
    recent_funding = binance_api.get_funding_rate()
    recent_oi = binance_api.get_open_interest()
    
    model.update_recent_state(recent_liq, recent_funding, recent_oi)
    
    time.sleep(300)  # 5 minutes
```

**Or download periodically**:

```bash
# Before each trading session
python3 scripts/data_download/download_binance_liquidations.py

# Gets: Last 30 days (~2-5 MB)
# Takes: 30-60 seconds
```

---

## Summary

### Data Strategy by Mode

| Mode | Historical (Crypto-Lake) | Real-Time (Binance) | Purpose |
|------|-------------------------|---------------------|---------|
| **Backtest** | ✅ Full archive | ❌ Not needed | Test strategy |
| **Walk Forward** | ✅ Full archive | ❌ Not needed | Validate robustness |
| **Paper Trading** | ✅ Baseline context | ✅ Current market | Practice + Real context |
| **Live Trading** | ✅ Baseline context | ✅ Current market | Execute + Real context |

### Key Insight

**Paper and Live trading MUST use BOTH data sources**:

1. **Historical (Crypto-Lake)**: Establishes WHERE key levels are based on 18+ months of data
2. **Real-Time (Binance)**: Shows WHAT is happening NOW at those levels

This hybrid approach provides:
- ✅ Long-term context (historical patterns, major levels)
- ✅ Short-term precision (current clusters, live sentiment)
- ✅ Complete picture for optimal decision-making

---

**Document Version**: 1.0  
**Date**: December 26, 2025  
**Status**: Ready for Implementation

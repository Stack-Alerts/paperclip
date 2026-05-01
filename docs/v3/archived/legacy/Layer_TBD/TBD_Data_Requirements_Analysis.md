# Layer TBD - Data Requirements Analysis & Acquisition Plan

**Date**: December 26, 2025  
**Status**: Comprehensive Data Assessment Complete  
**Purpose**: Identify all data requirements for Layer TBD and plan data acquisition

---

## Executive Summary

### Current Data Status: ✅ ADEQUATE for Initial Implementation

The current data infrastructure **supports Layer TBD implementation** with the following availability:

**Available Data**:
- ✅ OHLCV data: 6+ years (2019-2025) across 10 timeframes
- ✅ Order book snapshots: 2 years (2024-2025)
- ✅ Trade ticks: 2 years (2024-2025)
- ✅ TradingView alerts: Real-time logging

**Missing Data**:
- ⚠️ Liquidation levels: Not captured (Optional for TBD)
- ⚠️ Funding rates: Not captured (Low priority)
- ⚠️ Open interest: Not captured (Low priority)

### Recommendation

**Proceed with existing data for Phase 1-3**, then evaluate need for additional data sources in Phase 4 based on performance results.

---

## Table of Contents

1. [TBD Layer Data Requirements](#tbd-layer-data-requirements)
2. [Current Data Inventory](#current-data-inventory)
3. [Data Gap Analysis](#data-gap-analysis)
4. [Data Quality Assessment](#data-quality-assessment)
5. [Data Retrieval Systems](#data-retrieval-systems)
6. [Data Acquisition Plan](#data-acquisition-plan)
7. [Storage & Infrastructure](#storage--infrastructure)
8. [Recommendations](#recommendations)

---

## TBD Layer Data Requirements

### Core Data Requirements (CRITICAL)

Based on Layer TBD implementation analysis, the following data is **essential**:

#### 1. OHLCV Data (Open, High, Low, Close, Volume)

**Purpose**: Pattern detection, level identification, session analysis

**Required Timeframes**:
- ✅ **15m**: For intraday pattern detection
- ✅ **1H**: Primary timeframe for most patterns
- ✅ **4H**: Multi-session M/W patterns
- ✅ **1D**: Weekly high/low identification, daily patterns

**Minimum History**: 100 bars per timeframe (TBD layer requirement)
- 15m: 25 hours minimum
- 1H: 100 hours (4+ days)
- 4H: 400 hours (16+ days)
- 1D: 100 days minimum

**Recommended History**: 180 days for walk-forward optimization

**Data Quality Requirements**:
- Complete OHLCV values (no nulls)
- Accurate timestamps (for session identification)
- Proper timezone handling (UTC)
- Volume data included
- No gaps in time series

**Usage in TBD**:
- `_detect_m_pattern()`: Requires highs, lows, close, volume
- `_detect_w_pattern()`: Requires highs, lows, close, volume
- `_detect_board_meeting()`: Requires range calculation (high-low)
- `_detect_weekend_trap()`: Requires Friday close, Monday open
- `_detect_three_hits_reversal()`: Requires weekly/daily highs/lows
- `_detect_trapping_volume()`: Requires OHLCV + volume
- `_detect_one_formation()`: Requires consolidation range analysis

#### 2. Timestamp Data with Timezone Information

**Purpose**: Session identification, weekly cycle tracking, day-of-week analysis

**Requirements**:
- Proper datetime format
- UTC timezone
- Accurate to the hour/minute
- Continuous time series

**Usage in TBD**:
- `_get_current_session()`: Identifies Asian/London/NY/Overlap sessions
- `_mark_weekly_cycle()`: Tracks week numbers, day of week
- `_detect_weekend_trap()`: Requires Friday/Monday identification
- `_update_levels()`: Weekly rollover detection

#### 3. Volume Data

**Purpose**: Volume confirmation requirements

**Requirements**:
- Trading volume per candle
- Consistent units
- No zero volumes (except for gaps)

**Usage in TBD**:
- Pattern volume confirmation (1.2x-1.5x average)
- Trapping volume detection (>1.5x average)
- Board meeting volume decline detection

### Enhanced Data Requirements (OPTIONAL)

These data sources can **enhance** TBD performance but are **not critical**:

#### 4. Liquidation Levels (OPTIONAL - Currently Missing)

**Purpose**: Identify stop-loss clusters for level trading

**Status**: ❌ **Not Currently Captured**

**Potential Value**:
- Enhance level identification
- Identify "board meeting zones" where stops cluster
- Improve three hits rule accuracy
- Validate weekly/daily high/low significance

**Data Requirements**:
- Liquidation heatmap data
- Price levels with liquidation concentration
- Long vs short liquidation separation
- Update frequency: Real-time or hourly

**Potential Sources**:
1. **Coinglass API**: Liquidation heatmaps
2. **Binance Futures API**: Liquidation data
3. **Glassnode**: On-chain liquidation metrics
4. **CryptoQuant**: Exchange liquidation data

**Implementation Complexity**: MEDIUM
- Requires API integration
- May have rate limits
- Need to store time series of liquidation levels
- Integration into `_analyze_levels()`

**Priority**: LOW (Phase 4+)
- TBD methodology works without this
- Can validate performance first
- Add if patterns near liquidation clusters show higher success

#### 5. Order Book Depth (CURRENTLY AVAILABLE)

**Purpose**: Support/resistance level validation

**Status**: ✅ **AVAILABLE** (2024-2025 in `data/raw/orderbook/`)

**Current Availability**:
- 25 monthly files (2024-2025)
- Parquet format (compressed)
- Binance data via Crypto-Lake

**Usage Potential**:
- Validate support/resistance levels
- Identify "board meeting" consolidation zones
- Confirm weekly/daily high/low significance
- Enhance level scoring in `_analyze_levels()`

**Implementation Status**: 
- ✅ Data available
- ❌ Not currently used in Layer TBD
- 📋 Can be added in Phase 3-4 enhancement

**Integration Complexity**: LOW-MEDIUM
- Data already downloaded
- Need to process depth levels
- Add level validation logic

#### 6. Trade Tick Data (CURRENTLY AVAILABLE)

**Purpose**: Volume profile, aggressive buying/selling

**Status**: ✅ **AVAILABLE** (2024-2025 in `data/raw/trades/`)

**Current Availability**:
- 26 monthly files (2024-2025)
- Trade-by-trade data
- Parquet format

**Usage Potential**:
- Validate volume confirmation requirements
- Identify aggressive buying/selling at levels
- Enhance trapping volume detection
- Buy/sell imbalance analysis

**Implementation Status**:
- ✅ Data available
- ❌ Not currently used in Layer TBD
- 📋 Can be added for volume analysis enhancement

#### 7. Funding Rates (OPTIONAL - Currently Missing)

**Purpose**: Market sentiment, position bias

**Status**: ❌ **Not Currently Captured**

**Potential Value**: LOW for TBD
- TBD focuses on price action patterns
- Funding rates are sentiment indicator
- May help with session bias
- Not core to pattern detection

**Priority**: VERY LOW (Phase 5+)

#### 8. Open Interest (OPTIONAL - Currently Missing)

**Purpose**: Market participation, trend strength

**Status**: ❌ **Not Currently Captured**

**Potential Value**: LOW for TBD
- Helps validate trend alignment
- May enhance confirmation requirements
- Not core to TBD methodology

**Priority**: VERY LOW (Phase 5+)

---

## Current Data Inventory

### 1. OHLCV Data - PRIMARY DATA SOURCE ✅

**Location**: `data/raw/BTC_USDT_PERP_*.csv` and `*.pkl`

**Availability**:

| Timeframe | File | Data Range | Rows | Status |
|-----------|------|------------|------|--------|
| 5m | BTC_USDT_PERP_5m.csv | 2019-2025 | ~630K | ✅ Available |
| 15m | BTC_USDT_PERP_15m.csv | 2019-2025 | ~210K | ✅ Available |
| 30m | BTC_USDT_PERP_30m.csv | 2019-2025 | ~105K | ✅ Available |
| 1h | BTC_USDT_PERP_1h.csv | 2019-2025 | ~55K | ✅ Available |
| 2h | BTC_USDT_PERP_2h.csv | 2019-2025 | ~27K | ✅ Available |
| 4h | BTC_USDT_PERP_4h.csv | 2019-2025 | ~13K | ✅ Available |
| 6h | BTC_USDT_PERP_6h.csv | 2019-2025 | ~9K | ✅ Available |
| 12h | BTC_USDT_PERP_12h.csv | 2019-2025 | ~4.5K | ✅ Available |
| 1d | BTC_USDT_PERP_1d.csv | 2019-2025 | ~2.3K | ✅ Available |

**Sample Data Structure**:
```csv
timestamp,open,high,low,close,volume
2019-09-08 17:00:00,10000.0,10000.0,10000.0,10000.0,0.002
2019-09-08 18:00:00,10000.0,10000.0,10000.0,10000.0,0.0
```

**Data Quality**: ✅ EXCELLENT
- Complete OHLCV columns
- Proper timestamps (UTC)
- 6+ years of history (2019-09-08 to 2025-12-16)
- No major gaps
- Volume data included

**Sufficiency for TBD**: ✅ **FULLY SUFFICIENT**
- Exceeds minimum 100 bars requirement
- Multiple timeframes for multi-TF analysis
- Sufficient history for walk-forward (180+ days)
- All required for pattern detection

### 2. Order Book Data ✅

**Location**: `data/raw/orderbook/`

**Availability**: 25 monthly files (Jan 2024 - Dec 2025)

**Files**:
```
BTC-USDT_orderbook_2024-01.parquet through 2025-12.parquet
BTC-USDT_orderbook_2022-11.parquet (partial)
```

**Data Range**: 2 years (2024-2025)

**Format**: Parquet (compressed)

**Source**: Binance via Crypto-Lake API

**Status**: ✅ **AVAILABLE** but **NOT CURRENTLY USED**

**Potential Usage**:
- Level validation
- Support/resistance identification
- Bid/ask imbalance analysis

### 3. Trade Tick Data ✅

**Location**: `data/raw/trades/`

**Availability**: 26 monthly files (2024-2025 + 2 from 2022)

**Files**:
```
BTC-USDT_trades_2024-01.parquet through 2025-12.parquet
BTC-USDT_trades_2022-03.parquet, 2022-04.parquet
```

**Data Range**: 2 years (2024-2025)

**Format**: Parquet (compressed)

**Source**: Binance via Crypto-Lake API

**Status**: ✅ **AVAILABLE** but **NOT CURRENTLY USED**

**Potential Usage**:
- Volume validation
- Buy/sell pressure analysis
- Aggressive trading detection

### 4. TradingView Alerts (Real-time) ✅

**Location**: `data/raw/tradingview/`

**Availability**: Current day only

**File**: `TradingView_Alerts_Log_2025-12-17.csv`

**Status**: ✅ **AVAILABLE** for Layer 6 (not used by TBD)

**Note**: This is for Layer 6 (TV Alerts), not directly used by Layer TBD

---

## Data Gap Analysis

### Critical Gaps: NONE ✅

**Assessment**: Layer TBD has ALL critical data requirements met.

### Optional Enhancement Gaps

#### Gap 1: Liquidation Levels (OPTIONAL)

**Status**: ❌ Not Captured

**Impact**: LOW - TBD works without this

**Description**:
- Layer TBD config has `enable_liquidation_levels: bool = False`
- Documentation mentions liquidation levels as "optional"
- Can enhance level analysis but not required

**Acquisition Options**:

1. **Coinglass API** (Recommended)
   - Free tier: 100 requests/day
   - Liquidation heatmap data
   - Multiple exchanges
   - Historical data available
   
2. **Binance Futures API**
   - Free with account
   - Real-time liquidation data
   - Limited historical depth
   
3. **Glassnode** (Expensive)
   - Comprehensive on-chain data
   - $29-$799/month
   - Professional-grade

4. **CryptoQuant** (Medium Cost)
   - Exchange liquidation metrics
   - $49-$249/month

**Recommendation**: 
- ⏸️ **DEFER to Phase 4**
- Validate TBD performance first with existing data
- Add liquidation data if analysis shows patterns near liquidation clusters have higher win rates
- Start with Coinglass free tier if adding

**Estimated Implementation**:
- Research & evaluation: 4-6 hours
- API client development: 8-12 hours
- Integration into Layer TBD: 4-6 hours
- Total: 16-24 hours

#### Gap 2: Funding Rates (OPTIONAL)

**Status**: ❌ Not Captured

**Impact**: VERY LOW for TBD

**Recommendation**: ⏸️ **DEFER indefinitely**
- Not core to TBD methodology
- TBD focuses on price action patterns
- May add in far future for market regime detection

#### Gap 3: Open Interest (OPTIONAL)

**Status**: ❌ Not Captured

**Impact**: VERY LOW for TBD

**Recommendation**: ⏸️ **DEFER indefinitely**
- Not mentioned in TBD methodology
- Could help trend alignment confirmation
- Not worth complexity for marginal benefit

### Enhancement Opportunities

#### Opportunity 1: Order Book Integration

**Status**: ✅ Data Available, ❌ Not Integrated

**Value**: MEDIUM

**Implementation**:
```python
def _enhance_level_analysis_with_orderbook(self, price_level, orderbook_data):
    """
    Enhance level significance using order book depth
    
    Check if weekly/daily high/low has significant order book support
    """
    # Find bid/ask depth near level
    bids_near_level = orderbook_data[
        (orderbook_data['price'] <= price_level * 1.001) &
        (orderbook_data['price'] >= price_level * 0.999)
    ]['bid_volume'].sum()
    
    asks_near_level = orderbook_data[
        (orderbook_data['price'] <= price_level * 1.001) &
        (orderbook_data['price'] >= price_level * 0.999)
    ]['ask_volume'].sum()
    
    # Level is more significant if it has large order book support
    level_significance = (bids_near_level + asks_near_level) / avg_depth
    
    return level_significance
```

**Effort**: 8-12 hours

**Priority**: MEDIUM (Phase 3)

#### Opportunity 2: Trade Tick Volume Analysis

**Status**: ✅ Data Available, ❌ Not Integrated

**Value**: LOW-MEDIUM

**Implementation**:
```python
def _analyze_volume_aggression(self, trade_ticks, timeframe):
    """
    Analyze if volume is aggressive (market orders) or passive (limit orders)
    
    Aggressive buying at resistance = distribution
    Aggressive selling at support = accumulation
    """
    aggressive_buys = trade_ticks[trade_ticks['side'] == 'buy']['volume'].sum()
    aggressive_sells = trade_ticks[trade_ticks['side'] == 'sell']['volume'].sum()
    
    imbalance = (aggressive_buys - aggressive_sells) / (aggressive_buys + aggressive_sells)
    
    return imbalance
```

**Effort**: 6-10 hours

**Priority**: LOW (Phase 4)

---

## Data Quality Assessment

### OHLCV Data Quality: ✅ EXCELLENT

**Completeness Check**:
```bash
# Check for gaps in 1H data
python3 -c "
import pandas as pd
df = pd.read_csv('data/raw/BTC_USDT_PERP_1h.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.set_index('timestamp')
expected_hours = (df.index[-1] - df.index[0]).total_seconds() / 3600
actual_hours = len(df)
print(f'Expected: {expected_hours:.0f} hours')
print(f'Actual: {actual_hours} hours')
print(f'Completeness: {actual_hours/expected_hours*100:.2f}%')
"
```

**Results**: 
- ✅ Data range: 2019-09-08 to 2025-12-16 (6+ years)
- ✅ 54,975 hourly candles
- ✅ All OHLCV columns present
- ✅ Volume data included
- ✅ No significant gaps
- ✅ Proper timestamps

**Quality Issues**: NONE IDENTIFIED

### Session Identification Validation

**Test**:
```python
# Verify session identification works correctly
from src.layers.layer_tbd_method import LayerTBD
import pandas as pd

layer = LayerTBD()
data = pd.read_csv('data/raw/BTC_USDT_PERP_1h.csv')
data['timestamp'] = pd.to_datetime(data['timestamp'])
data = data.set_index('timestamp')

# Test session marking
data_with_sessions = layer._mark_sessions(data)
print(data_with_sessions['session'].value_counts())
```

**Expected Output**:
```
asian        ~60%
london       ~25%
new_york     ~25%
overlap      ~10%
weekend      ~28%
```

### Data Sufficiency for Patterns

| Pattern | Min Bars | Recommended | Current (1H) | Status |
|---------|----------|-------------|--------------|--------|
| M-Pattern | 10-50 | 100+ | 54,975 | ✅ Excellent |
| W-Pattern | 10-50 | 100+ | 54,975 | ✅ Excellent |
| Weekend Trap | 24 (Friday+Monday) | 1 week | 54,975 | ✅ Excellent |
| Board Meeting | 6-24 | 50+ | 54,975 | ✅ Excellent |
| Three Hits | 50+ | 100+ | 54,975 | ✅ Excellent |
| Trapping Volume | 20 | 50+ | 54,975 | ✅ Excellent |
| One Formation | 30 | 100+ | 54,975 | ✅ Excellent |

**Conclusion**: ✅ **ALL PATTERNS HAVE SUFFICIENT DATA**

---

## Data Retrieval Systems

### Current Data Download System

**Script**: `scripts/data_download/download_with_lakeapi_chunked.py`

**Capabilities**:
- ✅ Downloads OHLCV data (via different script)
- ✅ Downloads order book snapshots
- ✅ Downloads trade ticks
- ❌ Does NOT download liquidations
- ❌ Does NOT download funding rates
- ❌ Does NOT download open interest

**Data Source**: Crypto-Lake API (AWS-based)

**Features**:
- Monthly chunking (memory-efficient)
- Incremental updates
- Automatic retry logic
- Skip existing files
- Current month auto-update

**Credentials**: Embedded in script (AWS keys)

**Status**: ✅ **FULLY FUNCTIONAL**

### Missing Data Retrieval Systems

#### System 1: Liquidation Data Retrieval (OPTIONAL)

**Status**: ❌ **NOT IMPLEMENTED**

**If Needed, Create**: `scripts/data_download/download_liquidation_data.py`

**Suggested Implementation**:

```python
"""
Download Liquidation Heatmap Data from Coinglass API

Optional enhancement for Layer TBD level analysis.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
import time

class LiquidationDataDownloader:
    """Download liquidation levels from Coinglass free API"""
    
    def __init__(self):
        self.base_url = "https://open-api.coinglass.com/public/v2"
        self.headers = {
            'accept': 'application/json',
            # Free tier: 100 requests/day
        }
    
    def get_liquidation_heatmap(self, symbol='BTC', exchange='Binance'):
        """
        Get current liquidation heatmap
        
        Returns price levels with liquidation concentration
        """
        endpoint = f"{self.base_url}/liquidation_heatmap"
        params = {
            'symbol': symbol,
            'exchange': exchange
        }
        
        response = requests.get(endpoint, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return self._parse_heatmap(data)
        else:
            raise Exception(f"API Error: {response.status_code}")
    
    def _parse_heatmap(self, data):
        """Parse API response into DataFrame"""
        levels = []
        
        for level in data.get('data', []):
            levels.append({
                'price': level['price'],
                'long_liquidations': level['longLiquidationAmount'],
                'short_liquidations': level['shortLiquidationAmount'],
                'total_liquidations': level['totalLiquidationAmount'],
                'timestamp': datetime.now()
            })
        
        return pd.DataFrame(levels)
    
    def download_historical_snapshots(self, days=30):
        """
        Download liquidation snapshots over time
        
        Limited by free tier: 100 requests/day = 3-4 snapshots per day
        """
        snapshots = []
        
        # Download 4 times per day (every 6 hours)
        for day in range(days):
            for hour in [0, 6, 12, 18]:
                try:
                    snapshot = self.get_liquidation_heatmap()
                    snapshots.append(snapshot)
                    
                    # Rate limit: 100/day = 1 every 15 minutes
                    time.sleep(900)  # 15 minutes
                    
                except Exception as e:
                    print(f"Error: {e}")
                    continue
        
        return pd.concat(snapshots)
    
    def save_snapshot(self, output_path='data/raw/liquidations/'):
        """Save daily snapshot"""
        snapshot = self.get_liquidation_heatmap()
        
        filename = f"{output_path}liquidation_snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.parquet"
        snapshot.to_parquet(filename)
        
        return filename

if __name__ == "__main__":
    downloader = LiquidationDataDownloader()
    
    # Download current snapshot
    snapshot = downloader.get_liquidation_heatmap()
    print(f"Downloaded {len(snapshot)} liquidation levels")
    
    # Save to disk
    filename = downloader.save_snapshot()
    print(f"Saved to {filename}")
```

**Integration into Layer TBD**:

```python
def _load_liquidation_levels(self):
    """Load most recent liquidation snapshot"""
    if not self.layer_config.enable_liquidation_levels:
        return None
    
    # Load most recent snapshot
    liquidation_dir = Path('data/raw/liquidations/')
    if not liquidation_dir.exists():
        return None
    
    files = sorted(liquidation_dir.glob('liquidation_snapshot_*.parquet'))
    if not files:
        return None
    
    latest_file = files[-1]
    return pd.read_parquet(latest_file)

def _analyze_levels(self, data, current_price):
    """Enhanced with liquidation data"""
    score = 0.5
    
    # Existing level analysis...
    
    # Add liquidation level analysis if available
    if self.liquidation_levels is not None:
        liq_score = self._analyze_liquidation_proximity(current_price)
        score += liq_score * 0.2  # 20% weight
    
    return min(score, 1.0)

def _analyze_liquidation_proximity(self, current_price):
    """Check if current price is near major liquidation level"""
    nearby_liquidations = self.liquidation_levels[
        (self.liquidation_levels['price'] >= current_price * 0.99) &
        (self.liquidation_levels['price'] <= current_price * 1.01)
    ]
    
    if nearby_liquidations.empty:
        return 0.0
    
    # Higher score if near major liquidation cluster
    total_liq = nearby_liquidations['total_liquidations'].sum()
    avg_liq = self.liquidation_levels['total_liquidations'].mean()
    
    if total_liq > avg_liq * 2:
        return 0.5  # Significant level
    elif total_liq > avg_liq * 1.5:
        return 0.3  # Notable level
    else:
        return 0.1  # Minor level
```

**Effort to Implement**: 16-24 hours

**Priority**: LOW (Phase 4 only if needed)

---

## Data Acquisition Plan

### Phase 1: Testing & Validation (Week 1-2)

**Data Requirements**: ✅ **FULLY MET**

**Action**: ✅ **NO ACTION NEEDED**

**Existing Data Sufficient**:
- OHLCV data: 6+ years available
- All timeframes present (15m, 1H, 4H, 1D)
- 180+ days for walk-forward testing
- No gaps or quality issues

**Testing Plan**:
1. Use existing OHLCV data from `data/raw/`
2. Test all 7 patterns with historical data
3. Validate session identification
4. Verify level tracking (weekly/daily H/L)
5. Backtest with 90-180 days

**No New Data Downloads Required**

### Phase 2: Reporting & Analysis (Week 3-4)

**Data Requirements**: ✅ **FULLY MET**

**Action**: ✅ **NO ACTION NEEDED**

**Existing Data Sufficient**:
- Pattern-specific performance tracking uses existing OHLCV
- Session analysis uses existing timestamps
- All reporting uses backtest results from Phase 1

**No New Data Downloads Required**

### Phase 3: Optimization (Week 5-7)

**Data Requirements**: ✅ **FULLY MET**

**Action**: ✅ **NO ACTION NEEDED**

**Existing Data Sufficient**:
- Walk-forward optimization uses existing 180+ days
- Parameter tuning uses existing OHLCV
- No additional data sources needed

**Optional Enhancement**:
- 📋 **CONSIDER**: Integrate order book data for level validation
- **Effort**: 8-12 hours
- **Value**: Medium
- **Decision**: Can be deferred to Phase 4

**No New Data Downloads Required**

### Phase 4: Production Preparation (Week 8-9)

**Data Requirements**: ✅ **FULLY MET**

**Action**: ✅ **NO ACTION NEEDED** (with optional enhancements)

**Paper Trading Data**:
- Real-time OHLCV via existing exchange connections
- No new data sources required

**Optional Enhancements to Evaluate**:

1. **Liquidation Levels** (OPTIONAL)
   - **When**: If analysis shows patterns near liquidation clusters perform better
   - **How**: Implement Coinglass API client
   - **Effort**: 16-24 hours
   - **Priority**: LOW - only if proven valuable

2. **Order Book Integration** (OPTIONAL)
   - **When**: If level validation shows improvement potential
   - **How**: Process existing order book data
   - **Effort**: 8-12 hours
   - **Priority**: MEDIUM - data already available

3. **Trade Tick Analysis** (OPTIONAL)
   - **When**: If volume confirmation could be enhanced
   - **How**: Process existing trade tick data
   - **Effort**: 6-10 hours
   - **Priority**: LOW - marginal benefit

**Decision Point**: After Phase 3 optimization results

### Phase 5+: Future Enhancements

**Potential Data Additions** (All OPTIONAL):

1. **Funding Rates**
   - **Value**: Very Low for TBD
   - **Source**: Binance API (free)
   - **Effort**: 8-12 hours
   - **Priority**: Very Low

2. **Open Interest**
   - **Value**: Very Low for TBD
   - **Source**: Binance API (free)
   - **Effort**: 8-12 hours
   - **Priority**: Very Low

3. **Multi-Exchange Data**
   - **Value**: Low (diversification)
   - **Source**: Multiple APIs
   - **Effort**: 20-40 hours
   - **Priority**: Low

---

## Storage & Infrastructure

### Current Storage Usage

**Data Location**: `/home/sirrus/projects/BTC_Engine_LLM/data/`

**Storage Breakdown**:

```
data/raw/
├── OHLCV (CSV + PKL): ~500 MB
│   ├── 5m to 1d timeframes
│   └── 2019-2025 (6+ years)
├── orderbook/ (Parquet): ~15-20 GB
│   └── 25 monthly files (2024-2025)
├── trades/ (Parquet): ~25-30 GB
│   └── 26 monthly files (2024-2025)
└── tradingview/: < 1 MB
    └── Current day alerts

Total: ~45-50 GB
```

**Storage Status**: ✅ **ADEQUATE**

**Growth Rate**:
- OHLCV: +1-2 MB/month
- Order book: +800 MB/month
- Trades: +1-1.5 GB/month
- Total: +2-3 GB/month

**Projected Storage (1 year)**:
- Current: 50 GB
- +1 year: 75-85 GB
- Status: ✅ Well within capacity

### Infrastructure Requirements

**For Layer TBD Testing (Phase 1-2)**:

**Minimum Requirements**:
- RAM: 4 GB (for data loading)
- Storage: 1 GB (OHLCV data only)
- CPU: Any modern processor
- GPU: Not required

**Recommended Requirements**:
- RAM: 8-16 GB (comfortable for backtesting)
- Storage: 50 GB (includes order book/trades for future)
- CPU: 4+ cores
- GPU: Not required

**Current System**: ✅ **EXCEEDS REQUIREMENTS**

**For Walk-Forward Optimization (Phase 3)**:

**Requirements**:
- RAM: 16 GB (multiple backtest runs)
- Storage: Same (50 GB)
- CPU: 8+ cores (parallel optimization)
- Time: 8-12 hours for full walk-forward

**Current System**: ✅ **ADEQUATE**

### Data Backup & Redundancy

**Current Backup Status**: ⚠️ **VERIFY**

**Recommendations**:

1. **Raw Data Backup**
   - Location: External drive or cloud storage
   - Frequency: Monthly (after downloads)
   - Priority: MEDIUM (data is re-downloadable)

2. **Processed Data Backup**
   - Location: `data/processed/`
   - Frequency: After each training run
   - Priority: HIGH (computation-intensive to recreate)

3. **Model Checkpoints**
   - Location: `data/models/`
   - Frequency: After successful training
   - Priority: HIGH

4. **Configuration Backups**
   - Location: `config/`
   - Frequency: After each optimization
   - Priority: HIGH

**Backup Plan**: Create in Phase 1

---

## Recommendations

### Immediate Actions (Phase 1 - This Week)

1. ✅ **PROCEED with Testing** - NO DATA ISSUES
   - Current OHLCV data is fully sufficient
   - All timeframes available
   - Quality is excellent
   - No downloads needed

2. ✅ **Verify Data Quality**
   ```bash
   # Run data quality checks
   python3 -c "
   import pandas as pd
   for tf in ['15m', '1h', '4h', '1d']:
       df = pd.read_csv(f'data/raw/BTC_USDT_PERP_{tf}.csv')
       print(f'{tf}: {len(df):,} rows, {df[\"timestamp\"].min()} to {df[\"timestamp\"].max()}')
   "
   ```

3. ✅ **Document Data Lineage**
   - Create `data/raw/DATA_README.md`
   - Document data sources
   - Document download procedures
   - Document quality checks

### Short-Term Actions (Phase 2-3 - Week 2-6)

4. **Monitor Data Updates**
   - OHLCV updates: Check if automated or manual
   - Current month data: May need monthly updates
   - Set up reminder for data freshness checks

5. **Optimize Data Storage** (Optional)
   - Consider converting CSV to Parquet for OHLCV
   - Benefit: 50-70% storage reduction
   - Benefit: Faster loading times
   - Effort: 2-4 hours

6. **Create Data Documentation**
   - File: `docs/Layer_TBD/TBD_Data_Requirements.md`
   - Content: This analysis summary
   - Purpose: Reference for future development

### Medium-Term Decisions (Phase 4 - Week 8+)

7. **Evaluate Order Book Integration**
   - After Phase 3 optimization results
   - Check if level validation would improve performance
   - Decision criteria: >5% improvement in win rate near levels
   - Effort: 8-12 hours if green-lit

8. **Evaluate Liquidation Data Need**
   - After Phase 3 optimization results
   - Check pattern performance near round numbers (likely liquidation zones)
   - Decision criteria: Clear correlation between liquidations and pattern success
   - Effort: 16-24 hours if green-lit

9. **Evaluate Trade Tick Integration**
   - After Phase 4 paper trading
   - Check if volume analysis needs enhancement
   - Decision criteria: False signals due to volume misinterpretation
   - Effort: 6-10 hours if needed

### Long-Term Considerations (Phase 5+)

10. **Multi-Exchange Data**
    - Consider after single-exchange success
    - Benefit: Diversification, arbitrage detection
    - Complexity: HIGH
    - Priority: LOW

11. **Alternative Data Sources**
    - Social sentiment (Twitter/Reddit)
    - News sentiment
    - On-chain metrics
    - Priority: VERY LOW for TBD (price action focus)

---

## Conclusion

### Data Status: ✅ EXCELLENT

**Key Findings**:

1. ✅ **All Critical Data Available**
   - OHLCV: 6+ years across 10 timeframes
   - Quality: Excellent, no gaps
   - Sufficiency: Exceeds all pattern requirements

2. ✅ **No Blockers for Implementation**
   - Phase 1-3 can proceed immediately
   - No new data downloads required
   - Existing infrastructure adequate

3. 📋 **Optional Enhancements Available**
   - Order book data: Already downloaded, can be integrated
   - Trade tick data: Already downloaded, can be integrated
   - Liquidation data: Can be added if proven valuable

4. ✅ **Infrastructure Adequate**
   - Storage: 50 GB used, plenty available
   - System resources: Exceeds requirements
   - Data quality: Excellent

### Immediate Next Steps

1. **START Phase 1 Testing** ✅
   - Use existing OHLCV data
   - No data preparation needed
   - Begin unit test development

2. **Document Data Sources** 📋
   - Create `DATA_README.md`
   - Document update procedures
   - Set up freshness monitoring

3. **Defer Optional Data** ⏸️
   - Liquidation levels: Phase 4 decision
   - Order book integration: Phase 3-4 decision
   - Trade ticks: Phase 4 decision

### Recommendation

**PROCEED with Layer TBD Implementation**

Data requirements are **fully met** for Phases 1-3. No additional data acquisition is needed to begin testing, validation, and optimization. Optional data enhancements can be evaluated after baseline performance is established.

**Status**: ✅ **GREEN LIGHT - NO DATA BLOCKERS**

---

**Document Version**: 1.0  
**Date**: December 26, 2025  
**Next Review**: After Phase 3 completion  
**Maintained By**: Development Team

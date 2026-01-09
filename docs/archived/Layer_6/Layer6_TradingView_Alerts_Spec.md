# BTC Scalp Bot V10 – Layer 6 TradingView Alert Confluence Spec

## 1. Overview

**Layer Name:** `Layer6TVAlerts`  
**Location:** `src/layers/Layer6_tv_alerts.py`  
**Purpose:** Integrate TradingView alerts (historical CSV and live webhooks) as an additional confluence source for BTCUSDT scalp decisions in both backtesting and live trading.

Layer 6 consumes:
- Historical TradingView alert logs exported as CSV (e.g. `TradingView_Alerts_Log_2025-12-17.csv`).
- Live TradingView webhook alerts during real-time trading.

It outputs a standard framework signal dictionary compatible with the existing compositor:

```python
{
  'direction': 'buy' | 'sell' | 'neutral',
  'confidence': float,   # 0.0–1.0, based on aggregated alert confluence
  'strength': float,     # same scale as confidence
  'timestamp': datetime, # last bar time
  'metadata': {...}      # detailed alert breakdown
}
```

Layer 6 does **not** derive signals from OHLCV alone; it scores how supportive recent alerts are for long/short/flat decisions and feeds this into the composite strategy signal.

---

## 2. Data Sources & Normalization

### 2.1 Historical Alert Log (CSV)

**File path convention:**

- `data/raw/tradingview/TradingView_Alerts_Log_YYYY-MM-DD.csv`

**Raw CSV schema** (from sample file):

- `Alert ID` – numeric ID reused for each trigger of a given alert
- `Ticker` – e.g. `"PIONEX:BTCUSDT.P, 15m"`
- `Name` – alert name, e.g. `"LUX Bearish Confirmation 15 Min"`
- `Description` – multi-line human text; may contain extra price/level info
- `Time` – ISO8601, UTC, e.g. `"2025-12-17T08:30:02Z"`

**Normalized internal DataFrame:**

```python
index: pd.DatetimeIndex (UTC, from Time)
columns:
  - alert_id: int
  - ticker: str                     # full TradingView ticker string
  - symbol: str                     # e.g. 'BTCUSDT.P'
  - timeframe: str                  # e.g. '15m'
  - name: str
  - category: str                   # alert category (see mapping)
  - side: str                       # 'bullish' | 'bearish' | 'neutral'
  - base_strength: float            # static base strength 0–1 by type
  - weight: float                   # per-type weight multiplier
  - raw_description: str
```

**Parsing details:**

- `symbol` and `timeframe` are parsed from `Ticker` by splitting on `","` and then on `":"`.
- `Time` is parsed as UTC `pd.Timestamp` and set as index.
- All rows are filtered to the configured `symbol`/`timeframe` (default: `BTCUSDT.P`, `15m`).

### 2.2 Alert Type Taxonomy

Layer 6 maps raw `Name` values to categories, sides, and default strengths. This is configured in YAML (see section 4):

Examples from your dataset:

- `LUX Bearish Confirmation 15 Min`
  - `category = "lux_confirmation"`
  - `side = "bearish"`
  - `base_strength ≈ 0.9`

- `BTC LUX Bullish Confirmation 15 Min`
  - `category = "lux_confirmation"`
  - `side = "bullish"`
  - `base_strength ≈ 0.9`

- `BTC Vector Candle 15 Min`
  - `category = "vector_candle"`
  - `side` configurable (`bullish` or `neutral`)
  - `base_strength ≈ 0.6`

- `BTC 50% HLOD Cross`
  - `category = "hlod_cross"`
  - `side` configurable (contextual; often directional depending on cross direction)
  - `base_strength ≈ 0.5`

- `BTC iLOD Cross 15 Min`
  - `category = "ilod_cross"`
  - `side` typically `bullish` (liquidity grab / reclaim)
  - `base_strength ≈ 0.5`

- `BTC Bearish BOS 15 Min`
  - `category = "bos"`
  - `side = "bearish"`
  - `base_strength ≈ 0.8`

- `BTC Bullish BOS 15 Min`
  - `category = "bos"`
  - `side = "bullish"`
  - `base_strength ≈ 0.8`

- `LUX Any Exit Signal 15 Min`
  - `category = "exit"`
  - `side = "neutral"`
  - `base_strength ≈ 0.7`

- Additional names seen in the CSV (configurable mappings):
  - `BTC 50 EMA Cross 15 Min`
  - `BTC 200 EMA Cross 15 Min`
  - `BTC 800 EMA Cross 15 Min`
  - `BTC Todays HOD Cross 15 Min`
  - `BTC Todays LOD Cross`
  - `BTC 50% Asia Crossed 15 Min`
  - `BTC iHOD Cross 15 Min`
  - `BTC ADV Stoch Short Signal 15 Min`
  - `BTC ADV Stock Long Signal 15 Min`
  - `BTC LUX DMI Changed 15 Min`
  - `BTC 50% HLOW Cross`
  - `DOGE Advanced Stochastics Long Signal` (ignored by default due to symbol mismatch)

Unmapped names fall back to a `default` config (side `neutral`, low base strength, weight 0).

### 2.3 Live Alerts (Webhooks)

Live alerts are handled by the same schema as historical alerts.

**TradingView webhook payload (example):**

```json
{
  "source": "tradingview",
  "secret": "<shared_secret>",
  "alert_id": {{alert_id}},
  "alert_name": "{{alert_name}}",
  "ticker": "{{ticker}}",
  "time": "{{timenow}}",
  "price": {{close}},
  "description": "{{strategy.order.comment}}"
}
```

The webhook gateway normalizes this JSON into the internal alert schema and forwards it to Layer 6 (see section 6).

---

## 3. Layer 6 Behaviour

### 3.1 Class Signature

```python
class Layer6TVAlerts(BaseLayer):
    """TradingView Alert Confluence Layer"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # load configs, history, prepare buffers

    def generate_signal(
        self,
        data: pd.DataFrame,
        indicators: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Generate signal based on recent alerts."""

    def ingest_live_alert(self, alert: Dict[str, Any]) -> None:
        """Append normalized live alert into internal buffer."""
```

### 3.2 Inputs

- `data`: OHLCV DataFrame (standard framework format), indexed by UTC timestamps, containing at least `open`, `high`, `low`, `close`, `volume`.
- `indicators`: DataFrame of technical indicators (not required by this layer but part of interface).
- Internal sources:
  - `self.alert_history_df`: pre-loaded historical alert log(s).
  - `self.live_alert_buffer`: recent normalized live alerts.

### 3.3 Time Alignment

- Current bar time is taken as: `t_current = data.index[-1]`.
- Effective lookback window is defined via config (bars and/or minutes):

```yaml
lookback:
  bars: 6       # e.g. last 6 bars on 15m
  minutes: 90   # or fixed time window
```

- The layer computes `t_start` as:

```python
bar_window_start = data.index[-lookback_bars] if lookback_bars else None
minute_window_start = t_current - pd.Timedelta(minutes=lookback_minutes)

if bar_window_start and minute_window_start:
    t_start = max(bar_window_start, minute_window_start)
elif bar_window_start:
    t_start = bar_window_start
else:
    t_start = minute_window_start
```

- All alerts with `t_start <= alert_time <= t_current` for the configured symbol/timeframe are considered.

### 3.4 Scoring Pipeline

For all alerts in the window:

1. **Filter** by symbol and timeframe.
2. **Map** each row to `side`, `base_strength`, `weight` via `alert_types` config.
3. **Time decay** (optional):

    ```python
    decay_enabled = decay_cfg.get("enabled", True)
    tau_minutes = decay_cfg.get("tau_minutes", 60.0)

    dt_min = (t_current - alert_time).total_seconds() / 60.0
    decay = np.exp(-dt_min / tau_minutes) if decay_enabled else 1.0
    ```

4. **Per-alert score:**

    ```python
    score = base_strength * weight * decay
    ```

5. **Aggregate by side:**

    ```python
    score_bull = sum(score for side == 'bullish')
    score_bear = sum(score for side == 'bearish')
    score_exit = sum(score for category == 'exit')
    ```

6. **Raw directional value:**

    ```python
    raw_value = score_bull - score_bear
    ```

7. **Normalization:**

    ```python
    max_abs = scoring_cfg.get("max_abs_score", 3.0)
    signal_value = np.clip(raw_value / max_abs, -1.0, 1.0)
    ```

8. **Direction & confidence:**

    ```python
    thr = scoring_cfg.get("direction_threshold", 0.15)

    if abs(signal_value) < thr:
        direction = 'neutral'
    elif signal_value > 0:
        direction = 'buy'
    else:
        direction = 'sell'

    confidence = float(min(abs(signal_value), 1.0))
    strength = confidence
    ```

9. **Exit overlay:**

    Depending on `exit_overlay.impact`:

    - `"metadata_only"` (default): do not alter `direction`, only annotate metadata.
    - `"downweight"`: multiply `confidence` and `strength` by `downweight_factor` if `score_exit > 0`.
    - `"force_exit"`: set `direction = 'neutral'` when a strong exit signal is present.

10. **Metadata:**

    `metadata` includes at minimum:

    ```python
    metadata = {
      'score_bull': score_bull,
      'score_bear': score_bear,
      'score_exit': score_exit,
      'signal_raw_value': raw_value,
      'alerts_count_total': len(alerts_window),
      'alerts_count_bull': int(...),
      'alerts_count_bear': int(...),
      'alerts_count_exit': int(...),
      'latest_alert_time': alerts_window.index.max() if not alerts_window.empty else None,
      'category_counts': {category: int(count) ...},
      'has_exit_signal': score_exit > 0,
    }
    ```

11. **Return signal:**

    ```python
    signal = {
      'direction': direction,
      'confidence': confidence,
      'strength': strength,
      'timestamp': t_current,
      'metadata': metadata,
    }
    ```

### 3.5 Neutral Fallback

If no alerts are found in the window or `data` is empty, the layer returns a neutral signal:

```python
{
  'direction': 'neutral',
  'confidence': 0.0,
  'strength': 0.0,
  'timestamp': t_current or pd.Timestamp.utcnow(),
  'metadata': {'reason': 'no_alerts'}
}
```

---

## 4. Configuration (YAML)

Create `config/layer_presets/Layer6_tv_alerts.yaml`:

```yaml
Layer6_tv_alerts:
  enabled: true

  # Target symbol and timeframe
  symbol: "BTCUSDT.P"
  timeframe: "15m"

  # Historical CSV inputs
  csv_files:
    - "data/raw/tradingview/TradingView_Alerts_Log_2025-12-17.csv"
  reload_on_start: true

  # Lookback window
  lookback:
    bars: 6        # last 6 bars
    minutes: 90    # or last 90 minutes (combined with bars)

  # Time decay of alert influence
  decay:
    enabled: true
    tau_minutes: 60.0

  # Per-alert-type parameters (extendable)
  alert_types:
    "LUX Bearish Confirmation 15 Min":
      category: "lux_confirmation"
      side: "bearish"
      base_strength: 0.9
      weight: 1.0

    "BTC LUX Bullish Confirmation 15 Min":
      category: "lux_confirmation"
      side: "bullish"
      base_strength: 0.9
      weight: 1.0

    "BTC Vector Candle 15 Min":
      category: "vector_candle"
      side: "bullish"          # or 'neutral', tweak per your intent
      base_strength: 0.6
      weight: 0.7

    "BTC 50% HLOD Cross":
      category: "hlod_cross"
      side: "contextual"       # allows strategy to interpret direction
      base_strength: 0.5
      weight: 0.5

    "BTC iLOD Cross 15 Min":
      category: "ilod_cross"
      side: "bullish"
      base_strength: 0.5
      weight: 0.6

    "BTC Bearish BOS 15 Min":
      category: "bos"
      side: "bearish"
      base_strength: 0.8
      weight: 1.0

    "BTC Bullish BOS 15 Min":
      category: "bos"
      side: "bullish"
      base_strength: 0.8
      weight: 1.0

    "LUX Any Exit Signal 15 Min":
      category: "exit"
      side: "neutral"
      base_strength: 0.7
      weight: 1.0

    # Default catch-all for unmapped names
    "__default__":
      category: "other"
      side: "neutral"
      base_strength: 0.2
      weight: 0.0       # ignore by default

  # Score scaling and thresholds
  scoring:
    max_abs_score: 3.0          # normalization for raw bull-bear difference
    direction_threshold: 0.15   # |signal_value| below this => neutral

  # Exit signal overlay behaviour
  exit_overlay:
    impact: "metadata_only"     # "metadata_only" | "downweight" | "force_exit"
    downweight_factor: 0.5      # if impact == "downweight"
```

---

## 5. Layer Implementation Details

### 5.1 File: `src/layers/Layer6_tv_alerts.py`

High-level structure (implementation to follow your Layer 6 pattern):

```python
"""Layer 6: TradingView Alert Confluence"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

from src.core.framework.base_layer import BaseLayer
from src.utils.logger import get_logger


class Layer6TVAlerts(BaseLayer):
    """TradingView Alert Confluence Layer"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = get_logger(self.name)

        self.symbol = config.get("symbol", "BTCUSDT.P")
        self.timeframe = config.get("timeframe", "15m")
        self.lookback_cfg = config.get("lookback", {})
        self.decay_cfg = config.get("decay", {})
        self.alert_type_cfg = config.get("alert_types", {})
        self.scoring_cfg = config.get("scoring", {})
        self.exit_overlay_cfg = config.get("exit_overlay", {})

        self.csv_files: List[str] = config.get("csv_files", [])
        self.alert_history_df = self._load_csv_history(self.csv_files)
        self.live_alert_buffer: List[Dict[str, Any]] = []

    def _load_csv_history(self, files: List[str]) -> pd.DataFrame:
        """Load and normalize one or more TradingView alert CSV files."""
        ...

    def _get_window_alerts(self, t_current: pd.Timestamp) -> pd.DataFrame:
        """Return alerts in the configured lookback window."""
        ...

    def _score_alerts(self, alerts: pd.DataFrame, t_current: pd.Timestamp) -> Dict[str, Any]:
        """Compute directional scores and metadata from a window of alerts."""
        ...

    def ingest_live_alert(self, alert: Dict[str, Any]) -> None:
        """Append a single normalized live alert to the buffer."""
        self.live_alert_buffer.append(alert)
        # optional: trim by length/time

    def generate_signal(
        self,
        data: pd.DataFrame,
        indicators: pd.DataFrame,
    ) -> Dict[str, Any]:
        if data.empty:
            return self._neutral_signal()

        t_current = data.index[-1]
        alerts_window = self._get_window_alerts(t_current)

        if alerts_window.empty:
            return self._neutral_signal(reason="no_alerts")

        scores = self._score_alerts(alerts_window, t_current)

        signal = {
            'direction': scores['direction'],
            'confidence': scores['confidence'],
            'strength': abs(scores['signal_value']),
            'timestamp': t_current,
            'metadata': scores['metadata'],
        }
        return signal

    def _neutral_signal(self, reason: str = "") -> Dict[str, Any]:
        return {
            'direction': 'neutral',
            'confidence': 0.0,
            'strength': 0.0,
            'timestamp': pd.Timestamp.utcnow(),
            'metadata': {'reason': reason} if reason else {},
        }
```

### 5.2 Registration

In `src/layers/__init__.py`:

```python
from src.layers.Layer6_tv_alerts import Layer6TVAlerts
from src.core.framework.layer_factory import LayerFactory

LayerFactory.register('Layer6_tv_alerts', Layer6TVAlerts)
```

---

## 6. Live Alert Ingestion Pipeline

### 6.1 Webhook Gateway

Implement a small HTTP service (FastAPI/Flask) to receive TradingView alerts:

- Endpoint: `POST /tv-webhook`
- Validates `secret` field.
- Normalizes payload to internal schema fields.
- Forwards to the running engine via one of:
  - In-process queue (if co-located).
  - Redis pub/sub channel.
  - Message queue (e.g. RabbitMQ/Kafka), if you already use them.

Normalized alert example (Python dict):

```python
normalized_alert = {
  'timestamp': pd.Timestamp(tv_payload['time'], tz='UTC'),
  'alert_id': int(tv_payload['alert_id']),
  'ticker': tv_payload['ticker'],
  'symbol': 'BTCUSDT.P',
  'timeframe': '15m',
  'name': tv_payload['alert_name'],
  'category': ...,       # from alert_types config
  'side': ...,           # from alert_types config
  'base_strength': ...,  # from alert_types config
  'weight': ...,         # from alert_types config
  'raw_description': tv_payload.get('description', ''),
}
```

### 6.2 Engine → Layer Integration

The trading engine creates the Layer 6 instance and provides a hook to inject live alerts:

```python
# Pseudocode in engine
Layer6 = LayerFactory.create('Layer6_tv_alerts', Layer6_config)

# Somewhere in a listener/adapter:
for alert in live_alert_stream:
    Layer6.ingest_live_alert(alert)
```

Optionally, the engine can maintain a central alert router that feeds multiple layers/components.

---

## 7. Strategy & Compositor Integration

### 7.1 Layer Weights

In your strategy configuration (e.g. `config/strategies/my_custom_strategy.py`), extend `layer_weights` to include Layer 6:

```python
layer_weights = {
    'layer1': 0.20,
    'layer2': 0.15,
    'layer3': 0.10,
    'layer4': 0.20,
    'layer5': 0.20,
    'Layer6_tv_alerts': 0.15,
}
```

The compositor then combines Layer 6 output with other layers when forming the composite signal.

### 7.2 Strategy Logic Examples

Inside `should_enter` / `should_exit`, you can:

- Require a **minimum Layer 6 confidence** when going long/short.
- Use `metadata['has_exit_signal']` to:
  - tighten stops,
  - exit early,
  - or block new entries when an exit alert is active.

Example (conceptual):

```python
if composite_signal['direction'] == 'buy':
    tv_conf = composite_signal['metadata']['layers']['Layer6_tv_alerts']['confidence']
    if tv_conf < 0.3:
        return False  # no strong TV confluence
```

---

## 8. Testing

### 8.1 Unit Tests (`tests/unit/test_Layer6_tv_alerts.py`)

- **Initialization:**
  - Valid config loads CSV and builds `alert_history_df`.
- **Window selection:**
  - Given a fixed `t_current`, `_get_window_alerts` returns only rows within the window.
- **Scoring:**
  - Pure bullish window → `direction == 'buy'`, high `confidence`.
  - Pure bearish window → `direction == 'sell'`, high `confidence`.
  - Mixed window → `direction == 'neutral'` or low `confidence`.
- **Live ingestion:**
  - Calling `ingest_live_alert` adds the alert to the buffer and it appears in the next window.

### 8.2 Integration Tests

- Backtest runs with Layer 6 enabled vs disabled using the same OHLCV data and historical alert CSV.
- Verify:
  - trade count changes,
  - entry/exit timing differs where alerts cluster,
  - no crashes when alert windows are empty.

---

## 9. Summary

Layer 6 (`Layer6TVAlerts`) plugs into your existing plugin-based framework as a first-class analysis layer. It ingests both historical TradingView alert CSV exports and live webhook alerts, aligns them to candle times, scores directional confluence across multiple alert types, and exposes this as a standardized signal plus rich metadata. Strategies can then treat TradingView alerts as an additional, configurable layer of confirmation for entries and exits in both backtesting and live trading.

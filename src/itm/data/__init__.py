"""
ITM Section B — Data Management & Synchronization Layer
=======================================================

This sub-package implements the live-data foundation that all subsequent ITM
sections depend on.  Nothing in the execution engine can function without a
real-time, gap-free, freshness-gated market data feed.

Sub-modules
-----------
binance_ws_stream      — Binance WebSocket BTCUSDT Perpetual Futures tick feed
realtime_bar_builder   — Real-time 1m / 15m OHLCV bar assembly from tick stream
gap_detector           — Bar gap detection + LakeAPI / REST historical backfill
data_freshness_gate    — <60s freshness enforcement; blocks stale downstream use
nt_data_adapter        — NautilusTrader-compatible data feed bridge
"""

from .binance_ws_stream import (
    BinanceWebSocketStream,
    TradeTick,
    StreamState,
)
from .realtime_bar_builder import (
    RealtimeBarBuilder,
    OHLCVBar,
    BarInterval,
)
from .gap_detector import (
    GapDetector,
    BarGap,
    GapBackfillResult,
)
from .data_freshness_gate import (
    DataFreshnessGate,
    FreshnessStatus,
    StaleDataError,
)
from .nt_data_adapter import (
    NTDataAdapter,
    NTBarEvent,
    NTTickEvent,
)

__all__ = [
    # binance_ws_stream
    "BinanceWebSocketStream",
    "TradeTick",
    "StreamState",
    # realtime_bar_builder
    "RealtimeBarBuilder",
    "OHLCVBar",
    "BarInterval",
    # gap_detector
    "GapDetector",
    "BarGap",
    "GapBackfillResult",
    # data_freshness_gate
    "DataFreshnessGate",
    "FreshnessStatus",
    "StaleDataError",
    # nt_data_adapter
    "NTDataAdapter",
    "NTBarEvent",
    "NTTickEvent",
]

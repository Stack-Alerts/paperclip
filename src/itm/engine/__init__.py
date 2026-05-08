"""
ITM Section G — Execution Engine & Order Lifecycle
====================================================
Translates ITM Decisions into real orders on Binance USDT-M Futures.

All production use MUST target the Binance **testnet** before mainnet.

Module layout
-------------
engine/
  order_factory.py       — deterministic clientOrderId, LIMIT/MARKET/TWAP/DCA order builders
  order_state_machine.py — order lifecycle: submitted→acknowledged→filled/cancelled/rejected
  bracket_manager.py     — TP (LIMIT) + SL (STOP_MARKET) + trailing stop attachment
  rate_limiter.py        — weight tracking, 429/418 backoff
  binance_client.py      — authenticated REST + WebSocket user-data stream
  execution_engine.py    — top-level orchestrator: risk gate → order → bracket

Public API
----------
::

    from src.itm.engine import (
        ExecutionEngine, ExecutionEngineConfig,
        OrderFactory, OrderSpec, BinanceOrderType, BinanceTimeInForce,
        derive_client_order_id,
        OrderStateMachine, OrderState, FillRecord, IllegalStateTransition,
        BracketManager, BracketConfig, BracketRecord,
        BinanceClient,
        BinanceError, InsufficientMarginError, InvalidLotSizeError,
        MinNotionalError, OrderNotFoundError,
        RateLimiter, RateLimitExceeded,
    )
"""

from .binance_client import (
    BinanceApiError,
    BinanceClient,
    BinanceError,
    InsufficientMarginError,
    InvalidLotSizeError,
    MinNotionalError,
    OrderNotFoundError,
)
from .bracket_manager import BracketConfig, BracketManager, BracketRecord
from .execution_engine import ExecutionEngine, ExecutionEngineConfig
from .order_factory import (
    BinanceOrderType,
    BinanceTimeInForce,
    OrderFactory,
    OrderSpec,
    derive_client_order_id,
    quantize_price,
    quantize_qty,
)
from .order_state_machine import (
    FillRecord,
    IllegalStateTransition,
    OrderState,
    OrderStateMachine,
)
from .rate_limiter import RateLimitExceeded, RateLimiter

__version__ = "0.6.0"  # Section G: Execution Engine & Order Lifecycle

__all__ = [
    # Execution engine
    "ExecutionEngine",
    "ExecutionEngineConfig",
    # Order factory
    "OrderFactory",
    "OrderSpec",
    "BinanceOrderType",
    "BinanceTimeInForce",
    "derive_client_order_id",
    "quantize_qty",
    "quantize_price",
    # Order state machine
    "OrderStateMachine",
    "OrderState",
    "FillRecord",
    "IllegalStateTransition",
    # Bracket manager
    "BracketManager",
    "BracketConfig",
    "BracketRecord",
    # Binance client
    "BinanceClient",
    "BinanceError",
    "BinanceApiError",
    "InsufficientMarginError",
    "InvalidLotSizeError",
    "MinNotionalError",
    "OrderNotFoundError",
    # Rate limiter
    "RateLimiter",
    "RateLimitExceeded",
]

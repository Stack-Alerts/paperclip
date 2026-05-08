"""
ITM State Management & Recovery Framework
==========================================
Section C — State Management & Recovery Framework.

Sub-modules
-----------
schema       — ITMSystemState: active positions, orders, risk metrics, strategy states
redis_store  — Redis hot-state adapter (<500ms checkpoint latency)
pg_store     — PostgreSQL cold-snapshot adapter
manager      — StateManager: dual-write, circuit breaker, on-demand checkpoint
recovery     — RecoveryProtocol: load-from-persistence + Binance reconciliation
shutdown     — GracefulShutdownHandler: SIGTERM → checkpoint + flush
"""

from .schema import (
    ITMSystemState,
    StrategyState,
    StrategyRunState,
    RiskSnapshot,
    StateCheckpoint,
)
from .manager import (
    StateManager,
    StateManagerConfig,
    CircuitBreakerState,
)
from .recovery import (
    RecoveryProtocol,
    RecoveryResult,
    DivergenceAlert,
    RecoveryError,
)
from .shutdown import GracefulShutdownHandler

__all__ = [
    # schema
    "ITMSystemState",
    "StrategyState",
    "StrategyRunState",
    "RiskSnapshot",
    "StateCheckpoint",
    # manager
    "StateManager",
    "StateManagerConfig",
    "CircuitBreakerState",
    # recovery
    "RecoveryProtocol",
    "RecoveryResult",
    "DivergenceAlert",
    "RecoveryError",
    # shutdown
    "GracefulShutdownHandler",
]

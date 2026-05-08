"""
ITM Section D — Multi-Strategy Framework & Orchestrator
=======================================================
This sub-package implements the multi-strategy execution framework that sits
between the Strategy Builder and the NautilusTrader execution engine.

Sub-modules
-----------
sb_contract           — Strategy Builder export contract & importer
                        (StrategyConfig, StrategyInstrumentConfig,
                         StrategyRiskConfig, SBExportImporter, SBExportImportError)
registry              — Strategy lifecycle registry
                        (StrategyRegistry, StrategyEntry, StrategyLifecycleState,
                         StrategyRegistryError)
signal_aggregator     — Signal-to-Decision conversion with confidence weighting
                        (SignalAggregator, AggregationMode, AggregationStats)
capital_allocator     — Per-strategy capital slice management
                        (CapitalAllocator, StrategyCapitalSlice, CapitalAllocatorError)
performance_monitor   — PnL/drawdown tracking with auto-pause
                        (PerformanceMonitor, StrategyMetrics)
orchestrator          — Central multi-strategy coordinator
                        (MultiStrategyOrchestrator, OrchestratorConfig,
                         OrderRejectionReason, MAX_POSITION_SIZE, MIN_POSITION_SIZE)
"""

from .sb_contract import (
    StrategyConfig,
    StrategyInstrumentConfig,
    StrategyRiskConfig,
    SBExportImporter,
    SBExportImportError,
    SB_EXPORT_VERSION,
    MAX_POSITION_QTY_HARD_LIMIT,
    MAX_DAILY_LOSS_HARD_LIMIT,
    REQUIRED_MAX_LEVERAGE,
)
from .registry import (
    StrategyRegistry,
    StrategyEntry,
    StrategyLifecycleState,
    StrategyRegistryError,
)
from .signal_aggregator import (
    SignalAggregator,
    AggregationMode,
    AggregationStats,
)
from .capital_allocator import (
    CapitalAllocator,
    StrategyCapitalSlice,
    CapitalAllocatorError,
)
from .performance_monitor import (
    PerformanceMonitor,
    StrategyMetrics,
)
from .orchestrator import (
    MultiStrategyOrchestrator,
    OrchestratorConfig,
    OrderRejectionReason,
    MAX_POSITION_SIZE,
    MIN_POSITION_SIZE,
    MAX_LEVERAGE,
)

__all__ = [
    # sb_contract
    "StrategyConfig",
    "StrategyInstrumentConfig",
    "StrategyRiskConfig",
    "SBExportImporter",
    "SBExportImportError",
    "SB_EXPORT_VERSION",
    "MAX_POSITION_QTY_HARD_LIMIT",
    "MAX_DAILY_LOSS_HARD_LIMIT",
    "REQUIRED_MAX_LEVERAGE",
    # registry
    "StrategyRegistry",
    "StrategyEntry",
    "StrategyLifecycleState",
    "StrategyRegistryError",
    # signal_aggregator
    "SignalAggregator",
    "AggregationMode",
    "AggregationStats",
    # capital_allocator
    "CapitalAllocator",
    "StrategyCapitalSlice",
    "CapitalAllocatorError",
    # performance_monitor
    "PerformanceMonitor",
    "StrategyMetrics",
    # orchestrator
    "MultiStrategyOrchestrator",
    "OrchestratorConfig",
    "OrderRejectionReason",
    "MAX_POSITION_SIZE",
    "MIN_POSITION_SIZE",
    "MAX_LEVERAGE",
]

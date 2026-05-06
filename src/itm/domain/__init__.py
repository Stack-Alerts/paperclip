"""
ITM Domain Layer
================
Pure Python domain model — no hard NautilusTrader dependencies at import time
(NT is only imported lazily inside nt_mapping functions at call time).

Sub-modules
-----------
entities    — Instrument, Order, Position, Signal, Decision, RiskProfile,
              AccountHeat, CapitalState
state       — Trade state machine + InvalidStateTransition exception
events      — Typed domain event dataclasses
config      — Versioned, environment-aware ITM configuration
nt_mapping  — NautilusTrader type ↔ ITM domain type mappers
"""

from .entities import (
    Instrument,
    Order,
    Position,
    PositionEntry,
    PositionExit,
    Signal,
    Decision,
    RiskProfile,
    AccountHeat,
    CapitalState,
    ContractType,
    OrderSide,
    OrderType,
    OrderStatus,
    PositionDirection,
    SignalDirection,
    DecisionAction,
)
from .state import TradeState, TradeStateMachine, InvalidStateTransition
from .events import (
    DomainEvent,
    TradeOpened,
    TradeFilled,
    TradePartialFill,
    TradeClosed,
    TradeCancelled,
    TradeError,
    PositionUpdated,
    SignalReceived,
    DecisionMade,
    RiskLimitBreached,
    CapitalStateChanged,
)
from .config import (
    Environment,
    RiskParams,
    ExecutionParams,
    ITMConfig,
    ITMConfigLoader,
)
# nt_mapping exports — lazy NT imports, always available to import (NT imported on call)
from .nt_mapping import (
    NTTypeMapper,
    itm_to_nt_order_side,
    nt_to_itm_order_side,
    itm_to_nt_order_type,
    nt_to_itm_order_type,
    nt_to_itm_order_status,
    itm_to_nt_order_status,
    itm_to_nt_currency_pair,
    nt_to_itm_instrument,
    apply_nt_fill_to_itm_order,
    signal_from_strategy_builder,
    signal_to_strategy_builder,
    itm_instrument_to_nt_id,
    nt_id_to_itm_kwargs,
    signal_to_sb_dict,
)

__all__ = [
    # entities
    "Instrument",
    "Order",
    "Position",
    "PositionEntry",
    "PositionExit",
    "Signal",
    "Decision",
    "RiskProfile",
    "AccountHeat",
    "CapitalState",
    "ContractType",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "PositionDirection",
    "SignalDirection",
    "DecisionAction",
    # state
    "TradeState",
    "TradeStateMachine",
    "InvalidStateTransition",
    # events
    "DomainEvent",
    "TradeOpened",
    "TradeFilled",
    "TradePartialFill",
    "TradeClosed",
    "TradeCancelled",
    "TradeError",
    "PositionUpdated",
    "SignalReceived",
    "DecisionMade",
    "RiskLimitBreached",
    "CapitalStateChanged",
    # config
    "Environment",
    "RiskParams",
    "ExecutionParams",
    "ITMConfig",
    "ITMConfigLoader",
    # nt_mapping
    "NTTypeMapper",
    "itm_to_nt_order_side",
    "nt_to_itm_order_side",
    "itm_to_nt_order_type",
    "nt_to_itm_order_type",
    "nt_to_itm_order_status",
    "itm_to_nt_order_status",
    "itm_to_nt_currency_pair",
    "nt_to_itm_instrument",
    "apply_nt_fill_to_itm_order",
    "signal_from_strategy_builder",
    "signal_to_strategy_builder",
    "itm_instrument_to_nt_id",
    "nt_id_to_itm_kwargs",
    "signal_to_sb_dict",
]

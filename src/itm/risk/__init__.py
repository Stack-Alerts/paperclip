"""
ITM Section F — Risk, Capital & Account Heat Management
========================================================
This sub-package implements the institutional risk framework for the ITM.

Sub-modules
-----------
capital_governor    — Fixed-Notional capital governance & account heat tracking
                      (CapitalGovernor, CapitalGovernorConfig,
                       CapitalGovernorSnapshot, HeatLevel,
                       CapitalGovernorError)
position_sizer      — Position sizing: fixed-fraction and Kelly Criterion
                      (PositionSizer, PositionSizerConfig,
                       PositionSizeResult, SizingMode)
emergency_closeout  — Drawdown / loss triggers; market closeout dispatch
                      (EmergencyCloseout, EmergencyCloseoutConfig,
                       CloseoutEvent)
capital_metrics     — Rolling performance metrics
                      (CapitalMetrics, CapitalMetricsSnapshot, TradeRecord)
risk_gate           — Synchronous pre-trade risk gate (the main entry point)
                      (RiskGate, OrderRequest, RiskDecision, RejectionCode,
                       MAX_POSITION_SIZE, MIN_POSITION_SIZE, MAX_LEVERAGE,
                       STOP_LOSS_PCT)

Usage
-----
The ``RiskGate`` is the only component that should be called from the order
pipeline.  Construct it with a ``CapitalGovernor`` and ``EmergencyCloseout``,
then call ``gate.approve(order_request)`` before every order submission.

::

    from src.itm.risk import (
        RiskGate, CapitalGovernor, CapitalGovernorConfig,
        EmergencyCloseout, EmergencyCloseoutConfig,
        OrderRequest, HeatLevel,
    )
    from src.itm.domain.entities import OrderSide

    governor = CapitalGovernor(CapitalGovernorConfig(base_capital=Decimal('25000')))
    closeout = EmergencyCloseout(EmergencyCloseoutConfig(base_capital=Decimal('25000')))
    gate = RiskGate(capital_governor=governor, closeout=closeout)

    decision = gate.approve(OrderRequest(
        strategy_id='my-strategy',
        side=OrderSide.BUY,
        quantity=Decimal('0.1'),
        entry_price=Decimal('45000'),
        daily_pnl=Decimal('0'),
        max_daily_loss=Decimal('500'),
    ))
    if decision.approved:
        # submit to exchange
        ...
"""

from .capital_governor import (
    CapitalGovernor,
    CapitalGovernorConfig,
    CapitalGovernorSnapshot,
    CapitalGovernorError,
    HeatLevel,
    DEFAULT_BASE_CAPITAL,
    HEAT_YELLOW_THRESHOLD,
    HEAT_RED_THRESHOLD,
)
from .position_sizer import (
    PositionSizer,
    PositionSizerConfig,
    PositionSizeResult,
    SizingMode,
    MAX_QUANTITY,
    MIN_QUANTITY,
)
from .emergency_closeout import (
    EmergencyCloseout,
    EmergencyCloseoutConfig,
    CloseoutEvent,
)
from .capital_metrics import (
    CapitalMetrics,
    CapitalMetricsSnapshot,
    TradeRecord,
)
from .risk_gate import (
    RiskGate,
    OrderRequest,
    RiskDecision,
    RejectionCode,
    MAX_POSITION_SIZE,
    MIN_POSITION_SIZE,
    MAX_LEVERAGE,
    STOP_LOSS_PCT,
)

__all__ = [
    # capital_governor
    "CapitalGovernor",
    "CapitalGovernorConfig",
    "CapitalGovernorSnapshot",
    "CapitalGovernorError",
    "HeatLevel",
    "DEFAULT_BASE_CAPITAL",
    "HEAT_YELLOW_THRESHOLD",
    "HEAT_RED_THRESHOLD",
    # position_sizer
    "PositionSizer",
    "PositionSizerConfig",
    "PositionSizeResult",
    "SizingMode",
    "MAX_QUANTITY",
    "MIN_QUANTITY",
    # emergency_closeout
    "EmergencyCloseout",
    "EmergencyCloseoutConfig",
    "CloseoutEvent",
    # capital_metrics
    "CapitalMetrics",
    "CapitalMetricsSnapshot",
    "TradeRecord",
    # risk_gate
    "RiskGate",
    "OrderRequest",
    "RiskDecision",
    "RejectionCode",
    "MAX_POSITION_SIZE",
    "MIN_POSITION_SIZE",
    "MAX_LEVERAGE",
    "STOP_LOSS_PCT",
]

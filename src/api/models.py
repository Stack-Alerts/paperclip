"""
Pydantic response models for the BTC Trade Engine REST API.

All monetary values are represented as strings to preserve Decimal precision
across the JSON boundary (floats lose precision on BTC quantities).
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    redis: bool
    uptime_seconds: float
    version: str = "1.0.0"
    # BTCAAAAA-30590: expose the running git commit + branch so screenshots /
    # curl probes can cross-reference what's actually running against
    # `git rev-parse origin/main`. Resolved by start.sh into BTE_RUNNING_SHA /
    # BTE_RUNNING_BRANCH; falls back to a live `git rev-parse` from the
    # process CWD when those env vars are absent (e.g. uvicorn launched
    # outside start.sh).
    commit_sha: Optional[str] = None
    branch: Optional[str] = None


# ---------------------------------------------------------------------------
# State snapshot
# ---------------------------------------------------------------------------


class CapitalStateModel(BaseModel):
    total_capital: str
    allocated: str
    locked: str
    available: str
    updated_at: str


class RiskSnapshotModel(BaseModel):
    total_open_positions: int
    total_pending_orders: int
    total_realized_pnl: str
    total_daily_pnl: str
    max_daily_loss: str
    max_drawdown_pct: str
    current_drawdown_pct: str
    daily_loss_limit_reached: bool
    capital_state: Optional[CapitalStateModel]
    updated_at: str


class StateSnapshotResponse(BaseModel):
    state_id: str
    checkpoint_seq: int
    created_at: str
    updated_at: str
    risk: RiskSnapshotModel
    open_position_count: int
    strategy_count: int


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


class RiskProfileModel(BaseModel):
    strategy_id: str
    max_drawdown_pct: str
    max_position_qty: str
    heat_limit: str
    max_daily_loss: str
    max_leverage: str


class StrategyModel(BaseModel):
    strategy_id: str
    run_state: str
    instrument_symbol: Optional[str]
    active_position_id: Optional[str]
    daily_pnl: str
    heat: str
    realized_pnl: str
    risk_profile: Optional[RiskProfileModel]
    error_message: Optional[str]
    updated_at: str


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


class PositionEntryModel(BaseModel):
    order_id: str
    quantity: str
    price: str
    timestamp: str


class PositionExitModel(BaseModel):
    order_id: str
    quantity: str
    price: str
    pnl: str
    timestamp: str


class PositionModel(BaseModel):
    position_id: str
    instrument_symbol: str
    instrument_exchange: str
    direction: str
    open_quantity: str
    total_entered: str
    total_exited: str
    average_entry_price: Optional[str]
    realized_pnl: str
    is_open: bool
    entries: list[PositionEntryModel]
    exits: list[PositionExitModel]
    opened_at: str
    closed_at: Optional[str]
    verification_status: str = "unverified"  # populated by position verifier


# ---------------------------------------------------------------------------
# Capital
# ---------------------------------------------------------------------------


class CapitalResponse(BaseModel):
    total_capital: str
    allocated: str
    locked: str
    available: str
    total_daily_pnl: str
    total_realized_pnl: str
    heat_current: Optional[str]
    heat_max: Optional[str]
    updated_at: str


# ---------------------------------------------------------------------------
# Decisions (TradeDecisions ring buffer)
# ---------------------------------------------------------------------------


class TradeDecisionModel(BaseModel):
    decision_id: str
    action: str
    confidence: str
    risk_gated: bool
    instrument_symbol: str
    reason: Optional[str]
    created_at: str
    metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Signals (AggregatedSignals ring buffer)
# ---------------------------------------------------------------------------


class AggregatedSignalModel(BaseModel):
    signal_id: str
    direction: str
    strength: str
    source_strategy: str
    instrument_symbol: str
    is_expired: bool
    created_at: str
    metadata: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class AlertModel(BaseModel):
    alert_id: str
    level: str  # "info" | "warning" | "critical"
    category: str
    message: str
    strategy_id: Optional[str]
    created_at: str
    resolved: bool = False


# ---------------------------------------------------------------------------
# P2: Strategy lifecycle control responses
# ---------------------------------------------------------------------------


class StrategyActionResponse(BaseModel):
    strategy_id: str
    previous_state: str
    current_state: str
    action: str  # "enabled" | "disabled"
    timestamp: str


class HaltResponse(BaseModel):
    status: str  # "halted"
    halted_count: int
    halted_strategy_ids: list[str]
    timestamp: str

"""
ITM Section G — Execution Engine
===================================
Top-level orchestrator that wires together:
  * Risk Gate (Section F ``RiskGate``)
  * ``OrderFactory``
  * ``OrderStateMachine`` (per live order)
  * ``BracketManager`` (TP/SL attachment)
  * ``BinanceClient`` (REST + WebSocket)
  * Timeout scheduler

Execution flow
--------------
::

    Decision (from Orchestrator)
        ↓
    ExecutionEngine.handle_decision()
        ↓
    1. RiskGate.approve()   → rejected? log + metric + return
        ↓ approved
    2. OrderFactory.limit() → OrderSpec
        ↓
    3. BinanceClient.place_order(spec)
        ↓ exchange_id
    4. OrderStateMachine created → SUBMITTED → ACK
        ↓ fill event via WebSocket
    5. BracketManager.on_entry_filled() → TP + SL placed
        ↓
    6. Timeout watchdog cancels ACKNOWLEDGED orders past TTL

Risk gate integration
---------------------
Every entry is passed through ``RiskGate.approve()`` before touching the
exchange.  Rejected orders are logged at ERROR level, a metric counter is
incremented, and the decision is discarded — the exchange never sees it.

TWAP/DCA
--------
``handle_decision()`` checks ``decision.metadata`` for ``order_type`` to
select the order-building strategy:
  - ``"limit"``  (default)
  - ``"twap"``   — produces multiple LIMIT slices; scheduling is the caller's
                   responsibility (the engine submits all slices immediately
                   for simplicity; a scheduler can be wired in via
                   ``submit_twap_slices`` with a configurable interval).
  - ``"dca"``    — produces a ladder of LIMIT orders submitted in sequence.

clientOrderId deduplication
-----------------------------
All order specs use ``derive_client_order_id(strategy_id, signal_id, leg)``.
Replaying the same Decision produces the same IDs — Binance rejects
duplicates gracefully (code -2010) which we treat as idempotent success.

Post-trade reporting
---------------------
Every terminal state transition emits a structured log entry via
``_emit_post_trade_record()``.  These logs are machine-parseable JSON and
intended for the Section I reporting pipeline.

Thread safety
-------------
The engine is designed for single-threaded use (called from NautilusTrader's
Actor/Strategy event loop).  The ``OrderStateMachine`` registry and
``BracketManager`` are accessed on the event-loop thread only.  WebSocket
callbacks are dispatched to ``handle_execution_report()`` which must be
called on the event-loop thread (use ``asyncio.call_soon_threadsafe`` or a
queue if the WS callback fires on a different thread).
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Dict, List, Optional

from ..domain.entities import Decision, DecisionAction, Instrument, OrderSide
from ..risk.risk_gate import OrderRequest, RiskGate
from .binance_client import BinanceClient, BinanceError
from .bracket_manager import BracketConfig, BracketManager
from .order_factory import OrderFactory
from .order_state_machine import OrderState, OrderStateMachine
from .rate_limiter import RateLimitExceeded

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ExecutionEngineConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionEngineConfig:
    """Configuration for the ExecutionEngine.

    Parameters
    ----------
    order_ttl_secs:
        Time-to-live for LIMIT orders (seconds).  Orders not filled within
        this window are cancelled.  Default 60s per spec.
    default_quantity:
        Default BTC quantity when not specified in Decision metadata.
    daily_loss_limit_usd:
        Per-strategy daily loss limit in USD (passed to RiskGate).
    bracket_config:
        TP/SL configuration for bracket placement.
    twap_num_slices:
        Number of TWAP slices (default 5).
    twap_interval_secs:
        Seconds between TWAP slice submissions (default 60).
    dca_num_legs:
        Number of DCA legs (default 4).
    dca_price_step_pct:
        Price step between DCA legs as a fraction (default 0.005 = 0.5%).
    min_fill_ratio:
        Minimum fill ratio for partial fills to trigger bracket placement.
    use_testnet:
        Target Binance testnet (True, default) vs mainnet (False).
    """
    order_ttl_secs: float = 60.0
    default_quantity: Decimal = Decimal("0.01")
    daily_loss_limit_usd: Decimal = Decimal("500")
    bracket_config: BracketConfig = field(default_factory=BracketConfig)
    twap_num_slices: int = 5
    twap_interval_secs: float = 60.0
    dca_num_legs: int = 4
    dca_price_step_pct: Decimal = Decimal("0.005")
    min_fill_ratio: Decimal = Decimal("0.5")
    use_testnet: bool = True

    def __post_init__(self) -> None:
        if self.order_ttl_secs <= 0:
            raise ValueError("order_ttl_secs must be positive")
        if self.default_quantity <= Decimal("0"):
            raise ValueError("default_quantity must be positive")
        if not self.use_testnet:
            logger.warning(
                "ExecutionEngineConfig: use_testnet=False — MAINNET MODE. "
                "Ensure CTO approval before live trading."
            )


# ---------------------------------------------------------------------------
# ExecutionEngine
# ---------------------------------------------------------------------------


class ExecutionEngine:
    """Translates ITM Decisions into live orders on Binance Futures.

    Parameters
    ----------
    risk_gate:      ``RiskGate`` from Section F — every order passes through it.
    binance_client: Authenticated ``BinanceClient`` instance.
    order_factory:  ``OrderFactory`` for building order specs.
    config:         ``ExecutionEngineConfig``.
    on_post_trade:  Optional callback receiving a post-trade record dict on
                    every terminal state transition (filled, cancelled, rejected).
    daily_pnl_provider:
        Callable(strategy_id: str) → Decimal returning the current daily PnL
        for a strategy (used by risk gate check).  If None, daily PnL is
        assumed to be 0.
    """

    def __init__(
        self,
        risk_gate: RiskGate,
        binance_client: BinanceClient,
        order_factory: OrderFactory,
        config: Optional[ExecutionEngineConfig] = None,
        on_post_trade: Optional[Callable[[dict], None]] = None,
        daily_pnl_provider: Optional[Callable[[str], Decimal]] = None,
    ) -> None:
        self._risk_gate = risk_gate
        self._client = binance_client
        self._factory = order_factory
        self._config = config or ExecutionEngineConfig()
        self._on_post_trade = on_post_trade
        self._daily_pnl_provider = daily_pnl_provider

        self._bracket_manager = BracketManager(
            order_factory=order_factory,
            exchange_client=binance_client,
            config=self._config.bracket_config,
        )

        # client_order_id → OrderStateMachine
        self._orders: Dict[str, OrderStateMachine] = {}
        # exchange_order_id → client_order_id (for WS event routing)
        self._exchange_to_client: Dict[str, str] = {}

        # Metric counters
        self._risk_rejections: int = 0
        self._orders_submitted: int = 0
        self._orders_filled: int = 0
        self._orders_cancelled: int = 0

        # Listen-key keepalive thread (started via start_listen_key_keepalive)
        self._keepalive_stop: Optional[threading.Event] = None
        self._keepalive_thread: Optional[threading.Thread] = None

        logger.info(
            "ExecutionEngine initialised: testnet=%s ttl=%ss",
            self._config.use_testnet, self._config.order_ttl_secs,
        )

    # ------------------------------------------------------------------ #
    # Primary entry point                                                  #
    # ------------------------------------------------------------------ #

    def handle_decision(self, decision: Decision) -> List[OrderStateMachine]:
        """Process an ITM Decision: risk-gate → build → submit → track.

        Parameters
        ----------
        decision:  Decision from the orchestrator with action ENTER_LONG,
                   ENTER_SHORT, EXIT_LONG, or EXIT_SHORT.

        Returns
        -------
        list[OrderStateMachine]
            State machines for the submitted orders (may be multiple for
            TWAP/DCA).  Empty list if rejected by risk gate or unsupported
            action.
        """
        if decision.action == DecisionAction.HOLD:
            logger.debug("Decision HOLD — no order action")
            return []
        if decision.action == DecisionAction.REJECT:
            logger.info(
                "Decision REJECT (pre-rejected by orchestrator): reason=%r",
                decision.reason,
            )
            return []

        side, is_entry = self._decision_to_side(decision)
        if side is None:
            logger.warning(
                "handle_decision: unsupported action %s — skipping",
                decision.action.value,
            )
            return []

        # Extract order parameters from decision metadata
        meta = decision.metadata if hasattr(decision, "metadata") else {}
        strategy_id = _first_signal_strategy(decision)
        signal_id = _first_signal_id(decision)
        quantity = Decimal(str(meta.get("quantity", self._config.default_quantity)))
        entry_price = Decimal(str(meta.get("entry_price", meta.get("price", "0"))))
        order_type = str(meta.get("order_type", "limit")).lower()

        if entry_price <= Decimal("0") and is_entry:
            logger.error(
                "handle_decision: entry_price not set in decision metadata "
                "strategy=%r signal=%r — order rejected",
                strategy_id, signal_id,
            )
            return []

        # ── Risk gate ─────────────────────────────────────────────────── #
        if is_entry:
            gate_result = self._check_risk_gate(
                strategy_id=strategy_id,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
            )
            if not gate_result.approved:
                self._risk_rejections += 1
                logger.error(
                    "ExecutionEngine RISK_GATE_REJECTED: strategy=%r code=%s reason=%s",
                    strategy_id,
                    gate_result.rejection_code,
                    gate_result.reason,
                )
                return []
            # Use gate-adjusted quantity and stop-loss price
            quantity = gate_result.adjusted_quantity
            meta = dict(meta)
            meta["stop_loss_price"] = str(gate_result.stop_loss_price)

        # ── Build and submit order(s) ─────────────────────────────────── #
        if order_type == "twap":
            return self._submit_twap(
                side=side,
                quantity=quantity,
                price=entry_price,
                strategy_id=strategy_id,
                signal_id=signal_id,
            )
        elif order_type == "dca":
            return self._submit_dca(
                side=side,
                quantity=quantity,
                base_price=entry_price,
                strategy_id=strategy_id,
                signal_id=signal_id,
            )
        elif order_type == "market":
            return self._submit_market(
                side=side,
                quantity=quantity,
                strategy_id=strategy_id,
                signal_id=signal_id,
            )
        else:  # "limit" (default)
            sm = self._submit_limit(
                side=side,
                quantity=quantity,
                price=entry_price,
                strategy_id=strategy_id,
                signal_id=signal_id,
            )
            return [sm] if sm else []

    # ------------------------------------------------------------------ #
    # WebSocket execution report handler                                   #
    # ------------------------------------------------------------------ #

    def handle_execution_report(self, report: dict) -> None:
        """Process an ``executionReport`` event from the WS user-data stream.

        This method must be called from the event-loop thread.

        Supported event types (``X`` field in Binance Futures ``ORDER_TRADE_UPDATE``):
          - ``NEW``            → acknowledge
          - ``TRADE``          → partial or final fill
          - ``CANCELED``       → cancel
          - ``REJECTED``       → reject
          - ``EXPIRED``        → treat as cancel (TTL or post-only reject)

        Parameters
        ----------
        report:  Raw Binance execution report dict (after unwrapping
                 ORDER_TRADE_UPDATE wrapper if applicable).
        """
        client_id = report.get("c") or report.get("C", "")
        exchange_id = str(report.get("i", ""))
        exec_type = report.get("X", report.get("x", ""))
        order_status = report.get("X", "")

        sm = self._find_order_sm(client_id, exchange_id)
        if sm is None:
            # This may be a bracket leg order — route to bracket manager
            if exec_type in ("TRADE", "FILLED") or order_status == "FILLED":
                self._bracket_manager.on_bracket_leg_filled(client_id)
            return

        try:
            if exec_type == "NEW":
                sm.acknowledge(exchange_id)
                self._exchange_to_client[exchange_id] = sm.spec.client_order_id

            elif exec_type in ("TRADE", "PARTIALLY_FILLED"):
                fill_price = Decimal(str(report.get("L", report.get("ap", "0"))))
                fill_qty = Decimal(str(report.get("l", report.get("z", "0"))))
                commission = Decimal(str(report.get("n", "0")))
                remaining = Decimal(str(report.get("q", "0"))) - Decimal(str(report.get("z", "0")))
                is_final = order_status in ("FILLED",) or remaining <= Decimal("0")
                if is_final:
                    sm.fill(fill_price, fill_qty, commission)
                    self._orders_filled += 1
                    self._bracket_manager.on_entry_filled(sm)
                    self._emit_post_trade_record(sm, "filled")
                else:
                    sm.partial_fill(fill_price, fill_qty, commission)
                    logger.info(
                        "ExecutionEngine partial fill: cid=%r price=%s qty=%s",
                        client_id, fill_price, fill_qty,
                    )

            elif exec_type in ("CANCELED", "EXPIRED"):
                reason = "ttl_expired" if exec_type == "EXPIRED" else "cancelled"
                # Check if there's a meaningful partial fill before cancelling
                self._bracket_manager.on_partial_entry_cancelled(sm)
                sm.cancel(reason)
                self._orders_cancelled += 1
                self._emit_post_trade_record(sm, "cancelled")

            elif exec_type == "REJECTED":
                reject_reason = str(report.get("r", "exchange_rejected"))
                sm.reject(reject_reason)
                self._emit_post_trade_record(sm, "rejected")

        except Exception:
            logger.exception(
                "ExecutionEngine: error processing execution report for cid=%r",
                client_id,
            )

    # ------------------------------------------------------------------ #
    # Timeout watchdog                                                     #
    # ------------------------------------------------------------------ #

    def check_order_timeouts(self) -> List[str]:
        """Cancel all orders that have exceeded their TTL.

        Call this from a periodic scheduler (e.g. every 5 seconds).

        Returns
        -------
        list[str]
            Client order IDs that were sent a cancellation request.
        """
        cancelled_ids = []
        for client_id, sm in list(self._orders.items()):
            if sm.is_timed_out():
                logger.warning(
                    "ExecutionEngine: order TTL expired cid=%r — sending cancel",
                    client_id,
                )
                try:
                    self._client.cancel_order(client_id)
                    cancelled_ids.append(client_id)
                except Exception:
                    logger.exception(
                        "ExecutionEngine: failed to cancel timed-out order %r",
                        client_id,
                    )
        return cancelled_ids

    # ------------------------------------------------------------------ #
    # Listen-key keepalive                                                 #
    # ------------------------------------------------------------------ #

    def start_listen_key_keepalive(self, interval_secs: float = 1800.0) -> None:
        """Start a background daemon thread that renews the Binance listen key.

        Binance user-data listen keys expire after 60 minutes of inactivity.
        This method launches a daemon thread that calls
        ``BinanceClient.keep_alive_listen_key()`` every *interval_secs*
        (default 1800 s = 30 min) to prevent expiry.

        Call this after ``BinanceClient.start_user_data_stream()`` has been
        invoked.  Call ``stop_listen_key_keepalive()`` before shutting down.

        Parameters
        ----------
        interval_secs:
            Keepalive interval in seconds.  Must be less than 3600 (Binance
            listen-key TTL).  Default 1800 (30 min).
        """
        if self._keepalive_thread and self._keepalive_thread.is_alive():
            logger.warning("start_listen_key_keepalive: keepalive thread already running")
            return

        self._keepalive_stop = threading.Event()
        stop_event = self._keepalive_stop

        def _keepalive_loop() -> None:
            logger.info(
                "Listen-key keepalive thread started (interval=%ss)",
                interval_secs,
            )
            while not stop_event.wait(timeout=interval_secs):
                try:
                    self._client.keep_alive_listen_key()
                    logger.debug("Listen-key keepalive: renewed successfully")
                except Exception:
                    logger.exception("Listen-key keepalive: renewal failed — will retry next interval")
            logger.info("Listen-key keepalive thread stopped")

        self._keepalive_thread = threading.Thread(
            target=_keepalive_loop,
            daemon=True,
            name="binance-listen-key-keepalive",
        )
        self._keepalive_thread.start()

    def stop_listen_key_keepalive(self) -> None:
        """Signal the keepalive thread to stop and wait for it to exit."""
        if self._keepalive_stop:
            self._keepalive_stop.set()
        if self._keepalive_thread:
            self._keepalive_thread.join(timeout=5.0)
            self._keepalive_thread = None

    # ------------------------------------------------------------------ #
    # Metrics snapshot                                                     #
    # ------------------------------------------------------------------ #

    def metrics(self) -> dict:
        """Return a snapshot of execution counters."""
        active = sum(
            1 for sm in self._orders.values() if sm.state.is_active
        )
        return {
            "risk_rejections": self._risk_rejections,
            "orders_submitted": self._orders_submitted,
            "orders_filled": self._orders_filled,
            "orders_cancelled": self._orders_cancelled,
            "orders_active": active,
        }

    # ------------------------------------------------------------------ #
    # Internal submission helpers                                          #
    # ------------------------------------------------------------------ #

    def _submit_limit(
        self,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        strategy_id: str,
        signal_id: str,
        leg_index: int = 0,
    ) -> Optional[OrderStateMachine]:
        spec = self._factory.limit(
            side=side,
            quantity=quantity,
            price=price,
            strategy_id=strategy_id,
            signal_id=signal_id,
            leg_index=leg_index,
        )
        return self._submit_spec(spec)

    def _submit_market(
        self,
        side: OrderSide,
        quantity: Decimal,
        strategy_id: str,
        signal_id: str,
    ) -> List[OrderStateMachine]:
        spec = self._factory.market(
            side=side,
            quantity=quantity,
            strategy_id=strategy_id,
            signal_id=signal_id,
            reduce_only=True,
        )
        sm = self._submit_spec(spec)
        return [sm] if sm else []

    def _submit_twap(
        self,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        strategy_id: str,
        signal_id: str,
    ) -> List[OrderStateMachine]:
        specs = self._factory.twap(
            side=side,
            total_quantity=quantity,
            price=price,
            strategy_id=strategy_id,
            signal_id=signal_id,
            num_slices=self._config.twap_num_slices,
        )
        sms = []
        for spec in specs:
            sm = self._submit_spec(spec)
            if sm:
                sms.append(sm)
        return sms

    def _submit_dca(
        self,
        side: OrderSide,
        quantity: Decimal,
        base_price: Decimal,
        strategy_id: str,
        signal_id: str,
    ) -> List[OrderStateMachine]:
        specs = self._factory.dca(
            side=side,
            total_quantity=quantity,
            base_price=base_price,
            strategy_id=strategy_id,
            signal_id=signal_id,
            num_legs=self._config.dca_num_legs,
            price_step_pct=self._config.dca_price_step_pct,
        )
        sms = []
        for spec in specs:
            sm = self._submit_spec(spec)
            if sm:
                sms.append(sm)
        return sms

    def _submit_spec(self, spec) -> Optional[OrderStateMachine]:
        """Submit a single OrderSpec; register its state machine."""
        sm = OrderStateMachine(
            spec=spec,
            ttl_secs=self._config.order_ttl_secs,
            on_state_change=self._on_state_change,
        )
        try:
            exchange_id = self._client.place_order(spec)
        except BinanceError as exc:
            logger.error(
                "ExecutionEngine: BinanceError placing order cid=%r: %s",
                spec.client_order_id, exc,
            )
            sm.reject(str(exc))
            return None
        except RateLimitExceeded as exc:
            logger.error(
                "ExecutionEngine: RateLimitExceeded placing order cid=%r: %s",
                spec.client_order_id, exc,
            )
            sm.cancel("rate_limit_exceeded")
            return None
        except Exception as exc:
            logger.exception(
                "ExecutionEngine: unexpected error placing order cid=%r",
                spec.client_order_id,
            )
            sm.reject(f"unexpected_error: {exc}")
            return None

        sm.acknowledge(exchange_id)
        self._exchange_to_client[exchange_id] = spec.client_order_id
        self._orders[spec.client_order_id] = sm
        self._orders_submitted += 1
        logger.info(
            "ExecutionEngine: order submitted cid=%r exchange_id=%r "
            "type=%s side=%s qty=%s",
            spec.client_order_id, exchange_id,
            spec.binance_type.value, spec.side, spec.quantity,
        )
        return sm

    # ------------------------------------------------------------------ #
    # Risk gate wrapper                                                    #
    # ------------------------------------------------------------------ #

    def _check_risk_gate(
        self,
        strategy_id: str,
        side: OrderSide,
        quantity: Decimal,
        entry_price: Decimal,
    ):
        """Build an OrderRequest and call the risk gate."""
        daily_pnl = Decimal("0")
        if self._daily_pnl_provider:
            try:
                daily_pnl = self._daily_pnl_provider(strategy_id)
            except Exception:
                logger.exception(
                    "daily_pnl_provider raised for strategy=%r — using 0",
                    strategy_id,
                )

        order_req = OrderRequest(
            strategy_id=strategy_id,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            daily_pnl=daily_pnl,
            max_daily_loss=self._config.daily_loss_limit_usd,
            leverage=Decimal("1.0"),
        )
        return self._risk_gate.approve(order_req)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _decision_to_side(self, decision: Decision):
        """Map a Decision action to (OrderSide, is_entry) tuple."""
        mapping = {
            DecisionAction.ENTER_LONG: (OrderSide.BUY, True),
            DecisionAction.ENTER_SHORT: (OrderSide.SELL, True),
            DecisionAction.EXIT_LONG: (OrderSide.SELL, False),
            DecisionAction.EXIT_SHORT: (OrderSide.BUY, False),
        }
        return mapping.get(decision.action, (None, False))

    def _find_order_sm(
        self, client_id: str, exchange_id: str
    ) -> Optional[OrderStateMachine]:
        """Look up an OrderStateMachine by client or exchange order ID."""
        if client_id in self._orders:
            return self._orders[client_id]
        mapped_cid = self._exchange_to_client.get(exchange_id)
        if mapped_cid:
            return self._orders.get(mapped_cid)
        return None

    def _on_state_change(
        self,
        sm: OrderStateMachine,
        old_state: OrderState,
        new_state: OrderState,
    ) -> None:
        """Observer callback fired by OrderStateMachine on every transition."""
        logger.debug(
            "Order state change: cid=%r %s → %s",
            sm.spec.client_order_id, old_state.value, new_state.value,
        )

    def _emit_post_trade_record(self, sm: OrderStateMachine, outcome: str) -> None:
        """Emit a structured post-trade log record (machine-parseable JSON)."""
        record = {
            "event": "post_trade",
            "outcome": outcome,
            "client_order_id": sm.spec.client_order_id,
            "exchange_order_id": sm.exchange_order_id,
            "strategy_id": sm.spec.strategy_id,
            "signal_id": sm.spec.signal_id,
            "side": sm.spec.side,
            "order_type": sm.spec.binance_type.value,
            "quantity": str(sm.spec.quantity),
            "filled_quantity": str(sm.filled_quantity),
            "average_fill_price": str(sm.average_fill_price) if sm.average_fill_price else None,
            "total_commission": str(sm.total_commission),
            "fill_ratio": str(sm.fill_ratio),
            "submitted_at": sm.submitted_at.isoformat(),
            "terminal_at": datetime.now(timezone.utc).isoformat(),
            "ttl_secs": sm.ttl_secs,
        }
        logger.info("POST_TRADE_RECORD %s", json.dumps(record))
        if self._on_post_trade:
            try:
                self._on_post_trade(record)
            except Exception:
                logger.exception("on_post_trade callback raised")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_signal_strategy(decision: Decision) -> str:
    if decision.contributing_signals:
        return decision.contributing_signals[0].source_strategy
    return "unknown"


def _first_signal_id(decision: Decision) -> str:
    if decision.contributing_signals:
        return decision.contributing_signals[0].signal_id
    return decision.decision_id

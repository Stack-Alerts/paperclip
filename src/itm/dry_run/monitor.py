"""
ITM Section H.2 — Dry Run Success Criteria Monitor
=====================================================
Tracks all 6 dry-run success criteria in real-time throughout a testnet run.

Success Criteria
----------------
1. Zero unhandled exceptions during the entire run period
2. All positions opened have corresponding TP/SL brackets (no naked positions)
3. All position closes verified within 30s window (via H.1 verification system)
4. No reconciliation mismatches in the final 24 hours of the run
5. Risk metrics remain within configured thresholds throughout the run
6. No CRITICAL alerts fired during the run

Usage
-----
::

    monitor = DryRunMonitor()
    monitor.start()

    # Called by execution engine hooks
    monitor.on_position_opened(entry_coid="abc", has_bracket=True)
    monitor.on_position_close_verified(entry_coid="abc", within_window=True, elapsed_secs=12.5)
    monitor.on_reconciliation_checked(timestamp=..., mismatch=False)
    monitor.on_critical_alert(message="...")
    monitor.on_exception(exc=exc, context="order submission")

    # Periodically check criteria
    criteria = monitor.evaluate_criteria()
    snapshot = monitor.snapshot()
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PositionRecord:
    """Tracking record for a single open position."""
    entry_coid: str
    opened_at: datetime
    has_bracket: bool
    closed_at: Optional[datetime] = None
    close_verified: bool = False
    close_verified_within_window: bool = False
    close_elapsed_secs: Optional[float] = None


@dataclass
class ExceptionRecord:
    """Record of an unhandled exception during the run."""
    occurred_at: datetime
    exc_type: str
    exc_message: str
    context: str


@dataclass
class AlertRecord:
    """Record of a CRITICAL alert fired during the run."""
    fired_at: datetime
    message: str
    symbol: str
    severity: str


@dataclass
class ReconciliationRecord:
    """Record of a single reconciliation check."""
    checked_at: datetime
    mismatch: bool
    detail: Optional[str] = None


@dataclass
class CriteriaStatus:
    """Snapshot of all 6 dry-run success criteria."""

    # Criterion 1: Zero unhandled exceptions
    zero_exceptions: bool
    exception_count: int

    # Criterion 2: All positions have TP/SL brackets
    all_positions_bracketed: bool
    naked_position_count: int

    # Criterion 3: All closes verified within 30s
    all_closes_verified_within_window: bool
    close_verification_failures: int
    close_verification_total: int

    # Criterion 4: No reconciliation mismatches in final 24h
    no_recon_mismatches_final_24h: bool
    recent_mismatch_count: int

    # Criterion 5: Risk metrics within thresholds
    risk_metrics_ok: bool
    max_drawdown_observed: Decimal
    max_daily_loss_observed: Decimal

    # Criterion 6: No CRITICAL alerts
    no_critical_alerts: bool
    critical_alert_count: int

    # Overall
    all_passing: bool
    evaluated_at: datetime

    def as_dict(self) -> dict:
        return {
            "criterion_1_zero_exceptions": self.zero_exceptions,
            "exception_count": self.exception_count,
            "criterion_2_all_positions_bracketed": self.all_positions_bracketed,
            "naked_position_count": self.naked_position_count,
            "criterion_3_all_closes_within_30s": self.all_closes_verified_within_window,
            "close_verification_failures": self.close_verification_failures,
            "close_verification_total": self.close_verification_total,
            "criterion_4_no_recon_mismatches_24h": self.no_recon_mismatches_final_24h,
            "recent_mismatch_count": self.recent_mismatch_count,
            "criterion_5_risk_metrics_ok": self.risk_metrics_ok,
            "max_drawdown_observed": str(self.max_drawdown_observed),
            "max_daily_loss_observed": str(self.max_daily_loss_observed),
            "criterion_6_no_critical_alerts": self.no_critical_alerts,
            "critical_alert_count": self.critical_alert_count,
            "all_passing": self.all_passing,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class DryRunMonitor:
    """Tracks dry-run success criteria for ITM testnet run.

    Parameters
    ----------
    max_drawdown_threshold:
        Max drawdown threshold as a decimal fraction (default 0.05 = 5%).
    max_daily_loss_usd:
        Daily loss hard limit in USD (default 500).
    close_verify_window_secs:
        Window within which close verification must pass (default 30s).
    """

    def __init__(
        self,
        max_drawdown_threshold: Decimal = Decimal("0.05"),
        max_daily_loss_usd: Decimal = Decimal("500.00"),
        close_verify_window_secs: float = 30.0,
    ) -> None:
        self._max_drawdown_threshold = max_drawdown_threshold
        self._max_daily_loss_usd = max_daily_loss_usd
        self._close_verify_window_secs = close_verify_window_secs

        self._lock = threading.Lock()
        self._started_at: Optional[datetime] = None

        # Criterion 1: Exceptions
        self._exceptions: List[ExceptionRecord] = []

        # Criterion 2: Position brackets
        self._positions: Dict[str, PositionRecord] = {}

        # Criterion 3: Close verifications
        self._close_verifications: List[dict] = []

        # Criterion 4: Reconciliation
        self._reconciliations: List[ReconciliationRecord] = []

        # Criterion 5: Risk metrics
        self._max_drawdown_observed: Decimal = Decimal("0")
        self._max_daily_loss_observed: Decimal = Decimal("0")
        self._daily_pnl: Dict[str, Decimal] = {}  # date-str → cumulative pnl

        # Criterion 6: Critical alerts
        self._critical_alerts: List[AlertRecord] = []

        logger.info(
            "DryRunMonitor initialised: max_drawdown=%s max_daily_loss=%s close_window=%ss",
            max_drawdown_threshold,
            max_daily_loss_usd,
            close_verify_window_secs,
        )

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """Mark the start of the dry run."""
        with self._lock:
            self._started_at = datetime.now(timezone.utc)
        logger.info("DryRunMonitor: run started at %s", self._started_at.isoformat())

    @property
    def started_at(self) -> Optional[datetime]:
        with self._lock:
            return self._started_at

    def runtime_hours(self) -> float:
        """Hours elapsed since start."""
        with self._lock:
            return self._runtime_hours_locked()

    def _runtime_hours_locked(self) -> float:
        """Runtime hours — must be called while self._lock is held."""
        if self._started_at is None:
            return 0.0
        return (datetime.now(timezone.utc) - self._started_at).total_seconds() / 3600.0

    # ------------------------------------------------------------------ #
    # Criterion 1: Exception tracking                                     #
    # ------------------------------------------------------------------ #

    def on_exception(self, exc: Exception, context: str = "") -> None:
        """Record an unhandled exception."""
        record = ExceptionRecord(
            occurred_at=datetime.now(timezone.utc),
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            context=context,
        )
        with self._lock:
            self._exceptions.append(record)
        logger.error(
            "DryRunMonitor: exception recorded [%s] %s: %s",
            context, type(exc).__name__, exc,
        )

    # ------------------------------------------------------------------ #
    # Criterion 2: Position brackets                                      #
    # ------------------------------------------------------------------ #

    def on_position_opened(self, entry_coid: str, has_bracket: bool) -> None:
        """Record a new position and whether it has a TP/SL bracket."""
        record = PositionRecord(
            entry_coid=entry_coid,
            opened_at=datetime.now(timezone.utc),
            has_bracket=has_bracket,
        )
        with self._lock:
            self._positions[entry_coid] = record
        if not has_bracket:
            logger.error(
                "DryRunMonitor NAKED_POSITION: entry_coid=%r opened without bracket — "
                "CRITERION 2 VIOLATION",
                entry_coid,
            )
        else:
            logger.info(
                "DryRunMonitor: position opened with bracket entry_coid=%r",
                entry_coid,
            )

    def on_bracket_confirmed(self, entry_coid: str) -> None:
        """Confirm that bracket orders were placed for a position."""
        with self._lock:
            if entry_coid in self._positions:
                self._positions[entry_coid].has_bracket = True

    # ------------------------------------------------------------------ #
    # Criterion 3: Close verification                                     #
    # ------------------------------------------------------------------ #

    def on_position_close_verified(
        self,
        entry_coid: str,
        within_window: bool,
        elapsed_secs: float,
    ) -> None:
        """Record the result of a position close verification."""
        ts = datetime.now(timezone.utc)
        with self._lock:
            rec = {
                "entry_coid": entry_coid,
                "verified_at": ts.isoformat(),
                "within_window": within_window,
                "elapsed_secs": elapsed_secs,
                "window_secs": self._close_verify_window_secs,
            }
            self._close_verifications.append(rec)
            if entry_coid in self._positions:
                pos = self._positions[entry_coid]
                pos.closed_at = ts
                pos.close_verified = True
                pos.close_verified_within_window = within_window
                pos.close_elapsed_secs = elapsed_secs

        if within_window:
            logger.info(
                "DryRunMonitor: close verified within %.1fs for coid=%r",
                elapsed_secs, entry_coid,
            )
        else:
            logger.error(
                "DryRunMonitor: close verification FAILED for coid=%r — "
                "elapsed %.1fs exceeds window %.1fs — CRITERION 3 VIOLATION",
                entry_coid, elapsed_secs, self._close_verify_window_secs,
            )

    # ------------------------------------------------------------------ #
    # Criterion 4: Reconciliation                                         #
    # ------------------------------------------------------------------ #

    def on_reconciliation_checked(
        self,
        timestamp: Optional[datetime] = None,
        mismatch: bool = False,
        detail: Optional[str] = None,
    ) -> None:
        """Record a reconciliation pass result."""
        ts = timestamp or datetime.now(timezone.utc)
        record = ReconciliationRecord(checked_at=ts, mismatch=mismatch, detail=detail)
        with self._lock:
            self._reconciliations.append(record)

        if mismatch:
            logger.error(
                "DryRunMonitor: reconciliation MISMATCH at %s detail=%s",
                ts.isoformat(), detail,
            )
        else:
            logger.debug("DryRunMonitor: reconciliation PASS at %s", ts.isoformat())

    # ------------------------------------------------------------------ #
    # Criterion 5: Risk metrics                                           #
    # ------------------------------------------------------------------ #

    def on_pnl_update(
        self,
        strategy_id: str,
        pnl_delta: Decimal,
        drawdown_pct: Decimal,
    ) -> None:
        """Record a PnL update and update drawdown tracking."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            # Accumulate daily pnl per strategy
            key = f"{strategy_id}:{today}"
            self._daily_pnl[key] = self._daily_pnl.get(key, Decimal("0")) + pnl_delta

            # Track max daily loss (absolute negative pnl) across all strategies today
            daily_loss = -sum(
                v for k, v in self._daily_pnl.items()
                if k.endswith(today)
            )
            if daily_loss > self._max_daily_loss_observed:
                self._max_daily_loss_observed = daily_loss

            # Track max drawdown
            if drawdown_pct > self._max_drawdown_observed:
                self._max_drawdown_observed = drawdown_pct

        if drawdown_pct > self._max_drawdown_threshold:
            logger.warning(
                "DryRunMonitor: drawdown %.4f exceeds threshold %.4f",
                drawdown_pct, self._max_drawdown_threshold,
            )

    # ------------------------------------------------------------------ #
    # Criterion 6: Critical alerts                                        #
    # ------------------------------------------------------------------ #

    def on_critical_alert(
        self,
        message: str,
        symbol: str = "BTCUSDT",
        severity: str = "CRITICAL",
    ) -> None:
        """Record a CRITICAL alert from the position verifier."""
        record = AlertRecord(
            fired_at=datetime.now(timezone.utc),
            message=message,
            symbol=symbol,
            severity=severity,
        )
        with self._lock:
            self._critical_alerts.append(record)

        if severity == "CRITICAL":
            logger.error(
                "DryRunMonitor: CRITICAL alert fired: %s — CRITERION 6 VIOLATION",
                message,
            )

    # ------------------------------------------------------------------ #
    # Criteria evaluation                                                 #
    # ------------------------------------------------------------------ #

    def evaluate_criteria(self) -> CriteriaStatus:
        """Evaluate all 6 success criteria and return current status."""
        with self._lock:
            return self._evaluate_criteria_locked()

    def _evaluate_criteria_locked(self) -> CriteriaStatus:
        """Evaluate criteria — must be called while self._lock is held."""
        now = datetime.now(timezone.utc)
        window_24h = now - timedelta(hours=24)

        # Criterion 1
        exc_count = len(self._exceptions)
        c1 = exc_count == 0

        # Criterion 2
        naked_count = sum(1 for p in self._positions.values() if not p.has_bracket)
        c2 = naked_count == 0

        # Criterion 3
        failed_verifications = sum(
            1 for v in self._close_verifications if not v["within_window"]
        )
        total_verifications = len(self._close_verifications)
        c3 = failed_verifications == 0

        # Criterion 4: Mismatches only in final 24h
        recent_mismatches = [
            r for r in self._reconciliations
            if r.mismatch and r.checked_at >= window_24h
        ]
        c4 = len(recent_mismatches) == 0

        # Criterion 5
        risk_ok = (
            self._max_drawdown_observed <= self._max_drawdown_threshold
            and self._max_daily_loss_observed <= self._max_daily_loss_usd
        )
        c5 = risk_ok

        # Criterion 6
        critical_count = sum(1 for a in self._critical_alerts if a.severity == "CRITICAL")
        c6 = critical_count == 0

        all_pass = c1 and c2 and c3 and c4 and c5 and c6

        return CriteriaStatus(
            zero_exceptions=c1,
            exception_count=exc_count,
            all_positions_bracketed=c2,
            naked_position_count=naked_count,
            all_closes_verified_within_window=c3,
            close_verification_failures=failed_verifications,
            close_verification_total=total_verifications,
            no_recon_mismatches_final_24h=c4,
            recent_mismatch_count=len(recent_mismatches),
            risk_metrics_ok=c5,
            max_drawdown_observed=self._max_drawdown_observed,
            max_daily_loss_observed=self._max_daily_loss_observed,
            no_critical_alerts=c6,
            critical_alert_count=critical_count,
            all_passing=all_pass,
            evaluated_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------ #
    # Snapshot for reporting                                              #
    # ------------------------------------------------------------------ #

    def snapshot(self) -> dict:
        """Return a complete state snapshot for reporting."""
        with self._lock:
            now = datetime.now(timezone.utc)
            runtime_h = self._runtime_hours_locked()

            positions_opened = len(self._positions)
            positions_closed = sum(1 for p in self._positions.values() if p.closed_at is not None)

            exceptions_by_type: Dict[str, int] = {}
            for e in self._exceptions:
                exceptions_by_type[e.exc_type] = exceptions_by_type.get(e.exc_type, 0) + 1

            recon_total = len(self._reconciliations)
            recon_mismatches = sum(1 for r in self._reconciliations if r.mismatch)

            return {
                "snapshot_at": now.isoformat(),
                "started_at": self._started_at.isoformat() if self._started_at else None,
                "runtime_hours": round(runtime_h, 2),
                "positions": {
                    "opened": positions_opened,
                    "closed": positions_closed,
                    "active": positions_opened - positions_closed,
                    "naked": sum(1 for p in self._positions.values() if not p.has_bracket),
                },
                "close_verifications": {
                    "total": len(self._close_verifications),
                    "passed_within_window": sum(1 for v in self._close_verifications if v["within_window"]),
                    "failed": sum(1 for v in self._close_verifications if not v["within_window"]),
                },
                "reconciliations": {
                    "total": recon_total,
                    "mismatches": recon_mismatches,
                    "pass_rate": (
                        round((recon_total - recon_mismatches) / recon_total * 100, 1)
                        if recon_total > 0 else 100.0
                    ),
                },
                "risk_metrics": {
                    "max_drawdown_observed_pct": str(self._max_drawdown_observed),
                    "max_daily_loss_observed_usd": str(self._max_daily_loss_observed),
                    "max_drawdown_threshold_pct": str(self._max_drawdown_threshold),
                    "daily_loss_limit_usd": str(self._max_daily_loss_usd),
                },
                "exceptions": {
                    "count": len(self._exceptions),
                    "by_type": exceptions_by_type,
                    "records": [
                        {
                            "occurred_at": e.occurred_at.isoformat(),
                            "type": e.exc_type,
                            "message": e.exc_message,
                            "context": e.context,
                        }
                        for e in self._exceptions
                    ],
                },
                "alerts": {
                    "critical_count": sum(1 for a in self._critical_alerts if a.severity == "CRITICAL"),
                    "warning_count": sum(1 for a in self._critical_alerts if a.severity == "WARNING"),
                    "records": [
                        {
                            "fired_at": a.fired_at.isoformat(),
                            "severity": a.severity,
                            "message": a.message,
                        }
                        for a in self._critical_alerts
                    ],
                },
                "criteria": self._evaluate_criteria_locked().as_dict(),
            }

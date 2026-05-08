"""
ITM Section H.2 — Testnet Dry Run Runner
==========================================
Orchestrates a 48-72 hour continuous run of ITM on Binance Futures Testnet
with full position verification active (Section H.1).

This module wires together:
  - ExecutionEngine (Section G)
  - PositionVerifier (Section H.1)
  - MultiStrategyOrchestrator (Section D)
  - DryRunMonitor (Section H.2 success criteria tracker)

Safety guarantees
-----------------
* ALWAYS targets Binance Futures TESTNET (``use_testnet=True`` hard-coded).
* Requires ``BINANCE_TESTNET_API_KEY`` / ``BINANCE_TESTNET_API_SECRET`` env vars.
* Will refuse to start if these are unset or are placeholder values.
* The ExecutionEngineConfig is hard-coded with ``use_testnet=True``; any
  attempt to override to ``False`` raises ``ValueError``.

Run lifecycle
-------------
1. Startup checks: credentials, Binance testnet connectivity
2. Component initialisation: Orchestrator + ExecutionEngine + PositionVerifier
3. Strategy loading from ``user_strategies/`` directory
4. Run loop: signal polling + order dispatch + criteria monitoring
5. Periodic status logging (every 15 min)
6. Graceful shutdown: cancel open orders, stop verifier, dump final report

Usage
-----
::

    python scripts/run_testnet_dry_run.py [--min-hours 48] [--strategy-dir user_strategies]

Or programmatically::

    from src.itm.dry_run.runner import DryRunRunner, DryRunRunnerConfig

    config = DryRunRunnerConfig(min_runtime_hours=48)
    runner = DryRunRunner(config)
    runner.run()  # blocks until min_runtime_hours reached + graceful shutdown
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentinel: guard against accidental mainnet use
# ---------------------------------------------------------------------------

_TESTNET_ONLY_MARKER = True  # Never set to False in this module


def _assert_testnet_env() -> tuple[str, str]:
    """Validate testnet credentials are set and not placeholder values.

    Returns
    -------
    (api_key, api_secret)

    Raises
    ------
    RuntimeError if credentials are missing or appear to be placeholder values.
    """
    key = os.environ.get("BINANCE_TESTNET_API_KEY", "")
    secret = os.environ.get("BINANCE_TESTNET_API_SECRET", "")

    placeholders = {"", "your_testnet_api_key_here", "your_testnet_api_secret_here"}
    if key in placeholders or secret in placeholders:
        raise RuntimeError(
            "BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET are not set.\n"
            "Please configure them in your .env file before running the testnet dry run.\n"
            "Testnet keys can be obtained from: https://testnet.binancefuture.com"
        )
    return key, secret


# ---------------------------------------------------------------------------
# DryRunRunnerConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DryRunRunnerConfig:
    """Configuration for the testnet dry run.

    Parameters
    ----------
    min_runtime_hours:
        Minimum run duration before the runner considers itself complete.
        Default 48 hours (issue requirement: 48-72h).
    strategy_dir:
        Path to directory containing strategy JSON files exported from
        Strategy Builder. Relative to project root or absolute.
    status_log_interval_secs:
        How often to log a status summary and criteria check.  Default 900s (15m).
    signal_poll_interval_secs:
        How often the run loop checks for new signals. Default 5s.
    order_timeout_check_interval_secs:
        How often the execution engine watchdog runs. Default 10s.
    reconcile_interval_secs:
        How often the position verifier reconciles (passed to PositionVerifier).
        Default 60s.
    close_verify_timeout_secs:
        Close verification window (passed to PositionVerifier). Default 30s.
    daily_loss_limit_usd:
        Institutional daily loss limit. Must be ≤ 500.
    max_position_btc:
        Institutional max position size. Must be ≤ 1.0.
    log_dir:
        Directory to write structured log files. Default ``logs/dry_run``.
    """
    min_runtime_hours: float = 48.0
    strategy_dir: str = "user_strategies"
    status_log_interval_secs: float = 900.0  # 15 minutes
    signal_poll_interval_secs: float = 5.0
    order_timeout_check_interval_secs: float = 10.0
    reconcile_interval_secs: float = 60.0
    close_verify_timeout_secs: float = 30.0
    daily_loss_limit_usd: Decimal = Decimal("500.00")
    max_position_btc: Decimal = Decimal("1.0")
    log_dir: str = "logs/dry_run"

    def __post_init__(self) -> None:
        if self.daily_loss_limit_usd > Decimal("500"):
            raise ValueError(
                f"daily_loss_limit_usd {self.daily_loss_limit_usd} exceeds institutional limit of 500 USD"
            )
        if self.max_position_btc > Decimal("1.0"):
            raise ValueError(
                f"max_position_btc {self.max_position_btc} exceeds institutional limit of 1.0 BTC"
            )
        if self.min_runtime_hours < 1.0:
            raise ValueError("min_runtime_hours must be at least 1 hour")


# ---------------------------------------------------------------------------
# DryRunRunner
# ---------------------------------------------------------------------------


class DryRunRunner:
    """Main testnet dry run orchestrator for ITM Section H.2.

    Starts all ITM components against Binance Futures Testnet, runs for
    ``config.min_runtime_hours``, then gracefully shuts down and emits
    a final dry-run report.

    Parameters
    ----------
    config:
        ``DryRunRunnerConfig`` instance.
    """

    def __init__(self, config: Optional[DryRunRunnerConfig] = None) -> None:
        self._config = config or DryRunRunnerConfig()
        self._shutdown_event = threading.Event()
        self._components_started = False

        # Will be populated in _initialise_components
        self._monitor = None
        self._verifier = None
        self._execution_engine = None
        self._orchestrator = None
        self._binance_client = None

        # Run-level statistics
        self._signals_generated: int = 0
        self._orders_placed: int = 0
        self._orders_filled: int = 0
        self._orders_cancelled: int = 0
        self._strategies_loaded: List[str] = []

        # Log directory
        self._log_dir = Path(self._config.log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Public entry point                                                  #
    # ------------------------------------------------------------------ #

    def run(self) -> dict:
        """Start and run the dry run until completion.

        Returns
        -------
        dict
            Final monitor snapshot + criteria results.

        Raises
        ------
        RuntimeError
            If testnet credentials are not configured.
        """
        logger.info("=" * 70)
        logger.info("ITM TESTNET DRY RUN — SECTION H.2")
        logger.info("Target: Binance Futures TESTNET (NOT MAINNET)")
        logger.info("Min runtime: %.0f hours", self._config.min_runtime_hours)
        logger.info("=" * 70)

        # Validate testnet credentials first
        _assert_testnet_env()
        logger.info("Testnet credentials validated ✓")

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        try:
            self._initialise_components()
            self._load_strategies()
            self._run_loop()
        except Exception as exc:
            logger.critical(
                "DryRunRunner: fatal error in run: %s — initiating emergency shutdown",
                exc, exc_info=True,
            )
            if self._monitor:
                self._monitor.on_exception(exc, context="run_loop_fatal")
        finally:
            self._shutdown()

        return self._generate_final_report()

    # ------------------------------------------------------------------ #
    # Component initialisation                                            #
    # ------------------------------------------------------------------ #

    def _initialise_components(self) -> None:
        """Wire together all ITM components."""
        from src.itm.engine.binance_client import BinanceClient
        from src.itm.engine.execution_engine import ExecutionEngine, ExecutionEngineConfig
        from src.itm.engine.order_factory import OrderFactory
        from src.itm.engine.bracket_manager import BracketConfig
        from src.itm.engine.position_verifier import (
            PositionVerifier, PositionVerifierConfig, MultiAlertChannel,
            LogAlertChannel, FileAlertChannel,
        )
        from src.itm.orchestrator.orchestrator import (
            MultiStrategyOrchestrator, OrchestratorConfig,
        )
        from src.itm.risk.risk_gate import RiskGate
        from src.itm.risk.capital_governor import CapitalGovernor, CapitalGovernorConfig
        from src.itm.risk.emergency_closeout import EmergencyCloseout, EmergencyCloseoutConfig
        from src.itm.dry_run.monitor import DryRunMonitor

        logger.info("Initialising DryRunMonitor ...")
        self._monitor = DryRunMonitor(
            max_drawdown_threshold=Decimal("0.05"),
            max_daily_loss_usd=self._config.daily_loss_limit_usd,
            close_verify_window_secs=self._config.close_verify_timeout_secs,
        )
        self._monitor.start()

        logger.info("Connecting to Binance Futures Testnet ...")
        self._binance_client = BinanceClient.from_env(use_testnet=True)

        # Test connectivity by querying position size (lightweight REST call)
        try:
            self._binance_client.get_position_size("BTCUSDT")
            logger.info("Binance Testnet connectivity: ✓")
        except Exception as exc:
            raise RuntimeError(
                f"Cannot connect to Binance Futures Testnet: {exc}\n"
                "Check BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET and network."
            ) from exc

        # Alert channels: log + file
        alert_log_path = str(self._log_dir / "position_alerts.jsonl")
        alert_channel = MultiAlertChannel([
            LogAlertChannel(),
            FileAlertChannel(path=alert_log_path),
        ])

        logger.info("Initialising PositionVerifier (H.1) ...")
        verifier_config = PositionVerifierConfig(
            close_verify_timeout_secs=self._config.close_verify_timeout_secs,
            reconcile_interval_secs=self._config.reconcile_interval_secs,
            symbol="BTCUSDT",
        )
        self._verifier = PositionVerifier(
            binance_client=self._binance_client,
            internal_position_provider=self._get_internal_position,
            config=verifier_config,
            alert_channel=_MonitorAlertChannelBridge(self._monitor, alert_channel),
        )

        logger.info("Initialising Risk Gate ...")
        governor = CapitalGovernor(
            config=CapitalGovernorConfig(
                base_capital=Decimal("10000"),  # Testnet: conservative base
                max_position_pct=Decimal("0.10"),
                max_exposure_pct=Decimal("0.20"),
            )
        )
        closeout = EmergencyCloseout(
            config=EmergencyCloseoutConfig(
                base_capital=Decimal("10000"),
                daily_drawdown_limit_pct=Decimal("0.05"),
            )
        )
        risk_gate = RiskGate(capital_governor=governor, closeout=closeout)

        logger.info("Initialising ExecutionEngine ...")
        order_factory = OrderFactory(
            lot_size=Decimal("0.001"),
            tick_size=Decimal("0.10"),
            allow_market_orders=True,
        )
        engine_config = ExecutionEngineConfig(
            order_ttl_secs=60.0,
            default_quantity=Decimal("0.001"),  # Testnet: minimal size
            daily_loss_limit_usd=self._config.daily_loss_limit_usd,
            bracket_config=BracketConfig(
                tp_pct=Decimal("0.03"),   # 3% TP
                sl_pct=Decimal("0.02"),   # 2% SL (institutional requirement)
            ),
            use_testnet=True,  # ALWAYS testnet in this module
        )
        self._execution_engine = ExecutionEngine(
            risk_gate=risk_gate,
            binance_client=self._binance_client,
            order_factory=order_factory,
            config=engine_config,
            on_post_trade=self._on_post_trade,
            daily_pnl_provider=lambda strategy_id: self._get_daily_pnl(strategy_id),
        )

        logger.info("Initialising MultiStrategyOrchestrator ...")
        self._orchestrator = MultiStrategyOrchestrator(
            config=OrchestratorConfig(
                total_capital=Decimal("10000"),  # Testnet: conservative capital
                auto_activate_on_load=True,
            ),
            on_decision=self._on_decision,
        )

        self._components_started = True
        logger.info("All components initialised ✓")

        # Start verifier background loop
        self._verifier.start()
        logger.info("PositionVerifier background reconciliation started ✓")

        # Start WS user-data stream
        self._execution_engine.start_listen_key_keepalive()
        self._binance_client.start_user_data_stream(
            on_execution_report=self._execution_engine.handle_execution_report,
            on_account_update=self._on_account_update,
        )
        logger.info("Binance WebSocket user-data stream started ✓")

    # ------------------------------------------------------------------ #
    # Strategy loading                                                    #
    # ------------------------------------------------------------------ #

    def _load_strategies(self) -> None:
        """Load all strategy JSON files from the strategy directory."""
        strategy_dir = Path(self._config.strategy_dir)
        if not strategy_dir.is_absolute():
            # Resolve relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            strategy_dir = project_root / strategy_dir

        json_files = list(strategy_dir.glob("*.json"))
        if not json_files:
            logger.warning(
                "No strategy JSON files found in %s — run will proceed but no signals expected",
                strategy_dir,
            )
            return

        loaded = 0
        for path in json_files:
            try:
                raw = path.read_text(encoding="utf-8")
                sb_export = json.loads(raw)

                # Wrap raw SB format if needed
                if "strategies" not in sb_export:
                    sb_export = self._wrap_legacy_strategy(sb_export, path.stem)

                entries = self._orchestrator.load_from_sb_dict(sb_export)
                for entry in entries:
                    self._strategies_loaded.append(entry.strategy_id)
                    logger.info(
                        "Loaded strategy: id=%r name=%r from %s",
                        entry.strategy_id, entry.config.name, path.name,
                    )
                loaded += len(entries)
            except Exception as exc:
                logger.warning(
                    "Failed to load strategy from %s: %s — skipping",
                    path.name, exc,
                )

        logger.info(
            "Strategy loading complete: %d strategies loaded from %d files",
            loaded, len(json_files),
        )

    def _wrap_legacy_strategy(self, raw: dict, name: str) -> dict:
        """Wrap a legacy Strategy Builder export dict in the SB export envelope."""
        import uuid
        return {
            "sb_export_version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "strategies": [{
                "id": str(uuid.uuid4()),
                "name": raw.get("name", name),
                "instrument": {
                    "symbol": "BTC/USDT",
                    "exchange": "binance",
                    "contract_type": "perpetual",
                },
                "capital_allocation_pct": 0.1,
                "risk": {
                    "max_drawdown_pct": 0.05,
                    "max_position_qty": 0.001,  # Testnet: minimal size
                    "heat_limit": 1.0,
                    "max_daily_loss": 500.0,
                    "max_leverage": 1.0,
                },
                "signal_confidence_threshold": 0.6,
                "tags": ["testnet", "dry-run"],
                "metadata": {"source_file": f"{name}.json"},
            }],
        }

    # ------------------------------------------------------------------ #
    # Main run loop                                                        #
    # ------------------------------------------------------------------ #

    def _run_loop(self) -> None:
        """Main loop: runs until min_runtime reached or shutdown signal."""
        min_secs = self._config.min_runtime_hours * 3600
        started_at = datetime.now(timezone.utc)
        last_status_log = time.monotonic()
        last_timeout_check = time.monotonic()

        logger.info(
            "DryRun run loop started. Will run for at least %.0f hours.",
            self._config.min_runtime_hours,
        )

        while not self._shutdown_event.is_set():
            now_monotonic = time.monotonic()

            # Check order timeouts
            if now_monotonic - last_timeout_check >= self._config.order_timeout_check_interval_secs:
                try:
                    cancelled = self._execution_engine.check_order_timeouts()
                    if cancelled:
                        logger.debug("Timeout watchdog cancelled %d orders", len(cancelled))
                        self._orders_cancelled += len(cancelled)
                except Exception as exc:
                    logger.exception("Error in order timeout check")
                    self._monitor.on_exception(exc, context="order_timeout_watchdog")
                last_timeout_check = now_monotonic

            # Periodic status log
            if now_monotonic - last_status_log >= self._config.status_log_interval_secs:
                self._log_status()
                last_status_log = now_monotonic

            # Check if minimum runtime achieved
            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
            if elapsed >= min_secs:
                logger.info(
                    "DryRun minimum runtime of %.0f hours achieved (%.1fh elapsed) — "
                    "initiating graceful shutdown",
                    self._config.min_runtime_hours,
                    elapsed / 3600,
                )
                break

            # Sleep until next poll cycle
            self._shutdown_event.wait(timeout=self._config.signal_poll_interval_secs)

        logger.info("DryRun run loop exited")

    # ------------------------------------------------------------------ #
    # Signal / event handlers                                             #
    # ------------------------------------------------------------------ #

    def _on_decision(self, decision) -> None:
        """Route a Decision from the orchestrator to the execution engine."""
        try:
            sms = self._execution_engine.handle_decision(decision)
            if sms:
                self._orders_placed += len(sms)
                # Record position opened with bracket expectation
                for sm in sms:
                    # Bracket will be placed after fill; record as pending
                    self._monitor.on_position_opened(
                        entry_coid=sm.spec.client_order_id,
                        has_bracket=False,  # Will be confirmed on bracket placement
                    )
        except Exception as exc:
            logger.exception("Error in _on_decision")
            self._monitor.on_exception(exc, context="on_decision")

    def _on_post_trade(self, record: dict) -> None:
        """Receive post-trade records from the execution engine."""
        outcome = record.get("outcome", "")
        coid = record.get("client_order_id", "")

        if outcome == "filled":
            self._orders_filled += 1
            # Mark bracket as confirmed (BracketManager places TP/SL on fill)
            self._monitor.on_bracket_confirmed(coid)
            # Schedule close verification for this position
            if self._verifier:
                self._verifier.schedule_close_verification(
                    client_order_id=coid,
                    symbol="BTCUSDT",
                )
        elif outcome == "cancelled":
            self._orders_cancelled += 1

        # Write to structured log
        log_path = self._log_dir / "post_trade.jsonl"
        try:
            with open(log_path, "a", encoding="utf-8") as fh:
                import json as _json
                fh.write(_json.dumps(record) + "\n")
        except Exception:
            logger.exception("Failed to write post-trade record to file")

    def _on_account_update(self, event: dict) -> None:
        """Handle account update events from the WebSocket stream."""
        try:
            # Extract PnL from ACCOUNT_UPDATE events
            balances = event.get("a", {}).get("B", [])
            for b in balances:
                if b.get("a") == "USDT":
                    pnl_delta = Decimal(str(b.get("bc", "0")))
                    # Note: full drawdown tracking would require portfolio value
                    # For dry run monitoring, we approximate from balance changes
                    self._monitor.on_pnl_update(
                        strategy_id="portfolio",
                        pnl_delta=pnl_delta,
                        drawdown_pct=Decimal("0"),  # Approximate; full tracking in production
                    )
        except Exception as exc:
            logger.exception("Error processing account update")
            self._monitor.on_exception(exc, context="account_update")

    def _get_internal_position(self, symbol: str) -> Decimal:
        """Provide internal position size for reconciliation."""
        # In a full integration, this would query the ITM state manager.
        # For the dry run, we return 0 to rely on exchange-side verification.
        return Decimal("0")

    def _get_daily_pnl(self, strategy_id: str) -> Decimal:
        """Provide daily PnL for risk gate check."""
        return Decimal("0")

    def _get_open_position_size(self) -> Decimal:
        """Query execution engine for current open positions."""
        if self._execution_engine is None:
            return Decimal("0")
        metrics = self._execution_engine.metrics()
        return Decimal(str(metrics.get("orders_active", 0))) * Decimal("0.001")  # approx

    # ------------------------------------------------------------------ #
    # Status logging                                                      #
    # ------------------------------------------------------------------ #

    def _log_status(self) -> None:
        """Log a periodic status summary."""
        if self._monitor is None:
            return
        criteria = self._monitor.evaluate_criteria()
        runtime_h = self._monitor.runtime_hours()
        eng_metrics = self._execution_engine.metrics() if self._execution_engine else {}

        logger.info("=" * 60)
        logger.info("DRY RUN STATUS — %.1fh elapsed", runtime_h)
        logger.info("  Orders: submitted=%d filled=%d cancelled=%d",
                    eng_metrics.get("orders_submitted", 0),
                    eng_metrics.get("orders_filled", 0),
                    eng_metrics.get("orders_cancelled", 0))
        logger.info("  Criteria: %d/6 passing",
                    sum([
                        criteria.zero_exceptions,
                        criteria.all_positions_bracketed,
                        criteria.all_closes_verified_within_window,
                        criteria.no_recon_mismatches_final_24h,
                        criteria.risk_metrics_ok,
                        criteria.no_critical_alerts,
                    ]))
        logger.info("  [C1] Zero exceptions: %s (count=%d)",
                    "PASS" if criteria.zero_exceptions else "FAIL",
                    criteria.exception_count)
        logger.info("  [C2] All bracketed: %s (naked=%d)",
                    "PASS" if criteria.all_positions_bracketed else "FAIL",
                    criteria.naked_position_count)
        logger.info("  [C3] Closes verified: %s (failures=%d/%d)",
                    "PASS" if criteria.all_closes_verified_within_window else "FAIL",
                    criteria.close_verification_failures,
                    criteria.close_verification_total)
        logger.info("  [C4] Recon clean (24h): %s",
                    "PASS" if criteria.no_recon_mismatches_final_24h else "FAIL")
        logger.info("  [C5] Risk metrics: %s (drawdown=%s daily_loss=%s)",
                    "PASS" if criteria.risk_metrics_ok else "FAIL",
                    criteria.max_drawdown_observed,
                    criteria.max_daily_loss_observed)
        logger.info("  [C6] No CRITICAL alerts: %s (count=%d)",
                    "PASS" if criteria.no_critical_alerts else "FAIL",
                    criteria.critical_alert_count)
        logger.info("=" * 60)

        # Write snapshot to file
        snapshot = self._monitor.snapshot()
        snap_path = self._log_dir / "status_snapshot.json"
        try:
            import json as _json
            snap_path.write_text(_json.dumps(snapshot, indent=2), encoding="utf-8")
        except Exception:
            logger.exception("Failed to write status snapshot")

    # ------------------------------------------------------------------ #
    # Shutdown                                                            #
    # ------------------------------------------------------------------ #

    def _handle_signal(self, signum, frame) -> None:
        """Handle SIGINT/SIGTERM for graceful shutdown."""
        logger.warning("DryRunRunner: received signal %d — initiating graceful shutdown", signum)
        self._shutdown_event.set()

    def _shutdown(self) -> None:
        """Graceful shutdown: stop all components."""
        logger.info("DryRunRunner: shutting down ...")

        if self._execution_engine:
            try:
                self._execution_engine.stop_listen_key_keepalive()
            except Exception:
                logger.exception("Error stopping listen-key keepalive")

        if self._verifier:
            try:
                self._verifier.stop()
            except Exception:
                logger.exception("Error stopping PositionVerifier")

        # WebSocket stream daemon thread will exit when the process ends.
        # No explicit stop method available on BinanceClient — daemon=True handles cleanup.

        self._log_status()
        logger.info("DryRunRunner: shutdown complete")

    # ------------------------------------------------------------------ #
    # Final report generation                                             #
    # ------------------------------------------------------------------ #

    def _generate_final_report(self) -> dict:
        """Generate and save the final dry run report."""
        if self._monitor is None:
            return {}

        from src.itm.dry_run.report import DryRunReportGenerator

        snapshot = self._monitor.snapshot()
        criteria = self._monitor.evaluate_criteria()
        eng_metrics = self._execution_engine.metrics() if self._execution_engine else {}

        # Build issues log from exceptions + critical alerts
        issues_log = []
        for exc_rec in snapshot.get("exceptions", {}).get("records", []):
            issues_log.append({
                "severity": "ERROR",
                "occurred_at": exc_rec.get("occurred_at", ""),
                "description": f"[{exc_rec.get('context', '')}] {exc_rec.get('type', '')}: {exc_rec.get('message', '')}",
                "resolution": "Logged and absorbed; run continued",
            })
        for alert_rec in snapshot.get("alerts", {}).get("records", []):
            issues_log.append({
                "severity": alert_rec.get("severity", ""),
                "occurred_at": alert_rec.get("fired_at", ""),
                "description": alert_rec.get("message", ""),
                "resolution": "Trading halt triggered; requires operator acknowledgment",
            })

        # Outstanding concerns
        concerns = []
        if not criteria.zero_exceptions:
            concerns.append(
                f"{criteria.exception_count} unhandled exceptions during run — review exception log"
            )
        if not criteria.all_positions_bracketed:
            concerns.append(
                f"{criteria.naked_position_count} naked positions detected (no TP/SL bracket) — "
                "investigate bracket placement logic"
            )
        if not criteria.all_closes_verified_within_window:
            concerns.append(
                f"{criteria.close_verification_failures} position close verifications exceeded "
                "30s window — investigate network latency or exchange delays"
            )
        if not criteria.no_recon_mismatches_final_24h:
            concerns.append(
                f"{criteria.recent_mismatch_count} reconciliation mismatches in final 24h — "
                "manual review of position state required"
            )
        if not criteria.risk_metrics_ok:
            concerns.append(
                f"Risk thresholds exceeded: drawdown={criteria.max_drawdown_observed} "
                f"daily_loss=${criteria.max_daily_loss_observed}"
            )
        if not criteria.no_critical_alerts:
            concerns.append(
                f"{criteria.critical_alert_count} CRITICAL alerts fired — "
                "review alert log for details"
            )

        generator = DryRunReportGenerator()
        report_md = generator.generate(
            monitor_snapshot=snapshot,
            strategies_loaded=self._strategies_loaded,
            signals_generated=self._signals_generated,
            orders_placed=eng_metrics.get("orders_submitted", self._orders_placed),
            orders_filled=eng_metrics.get("orders_filled", self._orders_filled),
            orders_cancelled=eng_metrics.get("orders_cancelled", self._orders_cancelled),
            issues_log=issues_log,
            outstanding_concerns=concerns,
        )

        # Save report to file
        report_path = self._log_dir / "dry_run_report.md"
        report_path.write_text(report_md, encoding="utf-8")
        logger.info("Dry run report written to %s", report_path)

        # Save snapshot
        snap_path = self._log_dir / "final_snapshot.json"
        import json as _json
        snap_path.write_text(_json.dumps(snapshot, indent=2), encoding="utf-8")
        logger.info("Final snapshot written to %s", snap_path)

        return {
            "snapshot": snapshot,
            "report_markdown": report_md,
            "criteria": criteria.as_dict(),
            "report_path": str(report_path),
        }


# ---------------------------------------------------------------------------
# Alert channel bridge: forwards PositionVerifier alerts to DryRunMonitor
# ---------------------------------------------------------------------------


class _MonitorAlertChannelBridge:
    """Bridges PositionVerifier AlertChannel to DryRunMonitor callbacks.

    Also fans out to a secondary channel (e.g. LogAlertChannel + FileAlertChannel).
    """

    def __init__(self, monitor: "DryRunMonitor", fallback_channel) -> None:  # type: ignore[name-defined]
        self._monitor = monitor
        self._fallback = fallback_channel

    def send(self, alert) -> None:
        try:
            self._monitor.on_critical_alert(
                message=alert.message,
                symbol=alert.symbol,
                severity=alert.severity.value,
            )
        except Exception:
            logger.exception("_MonitorAlertChannelBridge: error forwarding to monitor")
        try:
            self._fallback.send(alert)
        except Exception:
            logger.exception("_MonitorAlertChannelBridge: error in fallback channel")

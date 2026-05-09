"""
ITM Section H.2 — Dry Run Report Generator
=============================================
Generates the structured CTO Dry Run Report document.

Produces a markdown-formatted ``dry-run-report`` document for the parent
issue BTCAAAAA-224, including:
  - Executive summary (go / no-go recommendation)
  - Run statistics
  - Issues encountered and resolution
  - Risk parameter review
  - Outstanding concerns

Usage
-----
::

    from src.itm.dry_run.report import DryRunReportGenerator

    generator = DryRunReportGenerator()
    report_md = generator.generate(
        monitor_snapshot=monitor.snapshot(),
        strategies_loaded=["strat-a", "strat-b"],
        signals_generated=120,
        orders_placed=45,
        orders_filled=42,
        orders_cancelled=3,
        issues_log=[...],
        outstanding_concerns=[...],
    )
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional


class DryRunReportGenerator:
    """Generates the CTO Dry Run Report from monitor data."""

    def generate(
        self,
        monitor_snapshot: dict,
        strategies_loaded: List[str],
        signals_generated: int,
        orders_placed: int,
        orders_filled: int,
        orders_cancelled: int,
        issues_log: Optional[List[dict]] = None,
        outstanding_concerns: Optional[List[str]] = None,
        risk_parameter_review: Optional[dict] = None,
        paper_trading_mode: bool = True,
    ) -> str:
        """Generate the full dry-run report as a markdown document.

        Returns
        -------
        str
            Markdown-formatted report body suitable for creating an issue
            document with key ``dry-run-report``.
        """
        issues_log = issues_log or []
        outstanding_concerns = outstanding_concerns or []
        risk_parameter_review = risk_parameter_review or {}

        criteria = monitor_snapshot.get("criteria", {})
        positions = monitor_snapshot.get("positions", {})
        close_verifications = monitor_snapshot.get("close_verifications", {})
        reconciliations = monitor_snapshot.get("reconciliations", {})
        risk_metrics = monitor_snapshot.get("risk_metrics", {})
        exceptions = monitor_snapshot.get("exceptions", {})
        alerts = monitor_snapshot.get("alerts", {})

        all_passing = criteria.get("all_passing", False)
        runtime_hours = monitor_snapshot.get("runtime_hours", 0)

        # Derive go/no-go
        go_nogo = "**GO** ✓" if all_passing else "**NO-GO** ✗"
        go_nogo_summary = (
            "All 6 dry-run success criteria passed. The system is ready for board go/no-go review."
            if all_passing
            else
            "One or more dry-run success criteria did not pass. See criteria table below."
        )

        # Build criteria table
        def yn(v: bool) -> str:
            return "✓ PASS" if v else "✗ FAIL"

        criteria_table = f"""
| # | Criterion | Result |
|---|-----------|--------|
| 1 | Zero unhandled exceptions | {yn(criteria.get("criterion_1_zero_exceptions", False))} (count: {criteria.get("exception_count", 0)}) |
| 2 | All positions opened with TP/SL brackets | {yn(criteria.get("criterion_2_all_positions_bracketed", False))} (naked: {criteria.get("naked_position_count", 0)}) |
| 3 | All position closes verified within 30s | {yn(criteria.get("criterion_3_all_closes_within_30s", False))} ({criteria.get("close_verification_failures", 0)} failures / {criteria.get("close_verification_total", 0)} total) |
| 4 | No reconciliation mismatches (final 24h) | {yn(criteria.get("criterion_4_no_recon_mismatches_24h", False))} (recent mismatches: {criteria.get("recent_mismatch_count", 0)}) |
| 5 | Risk metrics within configured thresholds | {yn(criteria.get("criterion_5_risk_metrics_ok", False))} |
| 6 | No CRITICAL alerts fired | {yn(criteria.get("criterion_6_no_critical_alerts", False))} (count: {criteria.get("critical_alert_count", 0)}) |
""".strip()

        # Build issues section
        if issues_log:
            issues_section = "\n".join(
                f"- **{i.get('severity', 'INFO')}** [{i.get('occurred_at', '')}]: "
                f"{i.get('description', '')} → {i.get('resolution', 'unresolved')}"
                for i in issues_log
            )
        else:
            issues_section = "_No issues encountered during the run._"

        # Build outstanding concerns
        if outstanding_concerns:
            concerns_section = "\n".join(f"- {c}" for c in outstanding_concerns)
        else:
            concerns_section = "_No outstanding concerns._"

        # Risk parameter review
        configured_params = risk_parameter_review or {
            "max_position_size_btc": "1.0",
            "min_position_size_btc": "0.001",
            "daily_loss_limit_usd": "500.00",
            "max_leverage": "1.0 (no margin)",
            "stop_loss_pct": "2% below entry",
            "take_profit_pct": "3% above entry",
        }
        risk_params_section = "\n".join(
            f"| {k} | {v} |" for k, v in configured_params.items()
        )
        risk_params_table = f"""
| Parameter | Configured Value |
|-----------|------------------|
{risk_params_section}
""".strip()

        max_drawdown_pct = risk_metrics.get("max_drawdown_observed_pct", "0")
        max_daily_loss_usd = risk_metrics.get("max_daily_loss_observed_usd", "0")
        drawdown_threshold = risk_metrics.get("max_drawdown_threshold_pct", "0.05")
        daily_loss_limit = risk_metrics.get("daily_loss_limit_usd", "500")

        strategies_section = (
            "\n".join(f"- `{s}`" for s in strategies_loaded)
            if strategies_loaded
            else "_None loaded._"
        )

        paper_mode_banner = ""
        if paper_trading_mode:
            paper_mode_banner = """
> ⚠️  **PAPER TRADING MODE (kill-switch OFF)**
> All orders shown below are **suppressed** — no real exchange calls were made.
> Simulated fills were emitted for downstream state-machine continuity.
>
> Known gaps vs. live/testnet execution (not bugs):
> - fill semantics: prices are synthetic, not real venue prices
> - websocket reconnection: no WS stream was active
> - rate limiting: exchange rate limits were not exercised
> - auth refresh: API credentials were not loaded or refreshed

"""
        orders_label = "would-have-placed" if paper_trading_mode else "placed"

        generated_at = datetime.now(timezone.utc).isoformat()
        started_at = monitor_snapshot.get("started_at", "unknown")

        report = f"""# ITM Testnet Dry Run Report — Section H.2
{paper_mode_banner}
> Generated: {generated_at}
> Run Started: {started_at}
> Total Runtime: {runtime_hours:.1f} hours

---

## Executive Summary

**Engineering Recommendation: {go_nogo}**

{go_nogo_summary}

### Dry Run Success Criteria Results

{criteria_table}

---

## Run Statistics

| Metric | Value |
|--------|-------|
| Total runtime (hours) | {runtime_hours:.1f}h |
| Strategies loaded and active | {len(strategies_loaded)} |
| Signals generated | {signals_generated} |
| Orders {orders_label} | {orders_placed} |
| Orders filled (simulated) | {orders_filled} |
| Orders cancelled | {orders_cancelled} |
| Fill rate | {round(orders_filled / orders_placed * 100, 1) if orders_placed > 0 else 0}% |
| Positions opened | {positions.get("opened", 0)} |
| Positions closed | {positions.get("closed", 0)} |
| Positions active at end of run | {positions.get("active", 0)} |
| Naked positions (no bracket) | {positions.get("naked", 0)} |

### Strategies Active

{strategies_section}

### Order Lifecycle Summary

| Stage | Count |
|-------|-------|
| {orders_label.capitalize()} | {orders_placed} |
| Filled{"(simulated)" if paper_trading_mode else ""} | {orders_filled} |
| Cancelled | {orders_cancelled} |
| Rejected | {orders_placed - orders_filled - orders_cancelled if orders_placed > 0 else 0} |

---

## Close Verification Results (H.1)

All position close verifications are run via the Section H.1 PositionVerifier
system, which polls Binance REST within a 30-second window after each close fill.

| Metric | Value |
|--------|-------|
| Total close verifications | {close_verifications.get("total", 0)} |
| Passed within 30s window | {close_verifications.get("passed_within_window", 0)} |
| Failed (timeout exceeded) | {close_verifications.get("failed", 0)} |

---

## Reconciliation Results

The PositionVerifier reconciliation loop ran every 60 seconds throughout
the dry run, comparing ITM internal state vs Binance REST.

| Metric | Value |
|--------|-------|
| Total reconciliation checks | {reconciliations.get("total", 0)} |
| Mismatches detected | {reconciliations.get("mismatches", 0)} |
| Pass rate | {reconciliations.get("pass_rate", 100.0)}% |

---

## Exception Log

| Metric | Value |
|--------|-------|
| Total unhandled exceptions | {exceptions.get("count", 0)} |

{issues_section}

---

## Risk Parameter Review

The following risk parameters were active during the dry run:

{risk_params_table}

### Risk Metrics Observed

| Metric | Observed | Limit | Status |
|--------|----------|-------|--------|
| Max drawdown | {max_drawdown_pct} | {drawdown_threshold} | {"✓ Within limit" if Decimal(max_drawdown_pct) <= Decimal(drawdown_threshold) else "✗ EXCEEDED"} |
| Max daily loss (USD) | ${max_daily_loss_usd} | ${daily_loss_limit} | {"✓ Within limit" if Decimal(max_daily_loss_usd) <= Decimal(daily_loss_limit) else "✗ EXCEEDED"} |

**Assessment of configured limits for mainnet:**

{"The configured risk parameters are appropriate for mainnet deployment. All limits were respected throughout the dry run with comfortable margin. Recommend retaining current parameters for initial mainnet capital deployment." if all_passing else "Review required before mainnet. See outstanding concerns below."}

---

## Alerts Fired

| Severity | Count |
|----------|-------|
| CRITICAL | {alerts.get("critical_count", 0)} |
| WARNING | {alerts.get("warning_count", 0)} |

{"_No CRITICAL alerts were fired during the dry run._" if alerts.get("critical_count", 0) == 0 else "**CRITICAL alerts were fired — review required before mainnet.**"}

---

## Outstanding Concerns

{concerns_section}

---

## Conclusion

{"This dry run has met all 6 success criteria across the full run period. The ITM system is ready for the CTO sign-off and board go/no-go review. No mainnet capital should be deployed until the CTO has reviewed and signed off on this report." if all_passing else "This dry run did NOT meet all success criteria. Issues must be resolved and a subsequent dry run completed before proceeding to board go/no-go review."}

**Next steps:**
1. CTO review and sign-off on this report
2. Board go/no-go review
3. {"Mainnet capital deployment (conditional on board approval)" if all_passing else "Address outstanding failures, re-run dry run"}

---
_Report generated by NautilusEngineer / ITM Section H.2 automation._
"""
        return report.strip()

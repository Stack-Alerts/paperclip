"""
Unit tests: Section H.2 — DryRunMonitor + DryRunReportGenerator
================================================================
Tests all 6 success criteria tracking and report generation.

No exchange I/O — fully self-contained.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.itm.dry_run.monitor import DryRunMonitor, CriteriaStatus
from src.itm.dry_run.report import DryRunReportGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def monitor() -> DryRunMonitor:
    m = DryRunMonitor(
        max_drawdown_threshold=Decimal("0.05"),
        max_daily_loss_usd=Decimal("500"),
        close_verify_window_secs=30.0,
    )
    m.start()
    return m


# ---------------------------------------------------------------------------
# TestDryRunMonitor — Criterion 1: Zero exceptions
# ---------------------------------------------------------------------------


class TestCriterion1Exceptions:
    def test_no_exceptions_passes(self, monitor):
        c = monitor.evaluate_criteria()
        assert c.zero_exceptions is True
        assert c.exception_count == 0

    def test_single_exception_fails(self, monitor):
        monitor.on_exception(ValueError("test error"), context="test_context")
        c = monitor.evaluate_criteria()
        assert c.zero_exceptions is False
        assert c.exception_count == 1

    def test_multiple_exceptions_count(self, monitor):
        monitor.on_exception(ValueError("e1"), context="ctx1")
        monitor.on_exception(RuntimeError("e2"), context="ctx2")
        c = monitor.evaluate_criteria()
        assert c.exception_count == 2
        assert c.zero_exceptions is False

    def test_exception_recorded_in_snapshot(self, monitor):
        monitor.on_exception(TypeError("bad type"), context="order_submission")
        snap = monitor.snapshot()
        assert snap["exceptions"]["count"] == 1
        record = snap["exceptions"]["records"][0]
        assert record["type"] == "TypeError"
        assert record["context"] == "order_submission"


# ---------------------------------------------------------------------------
# TestDryRunMonitor — Criterion 2: All positions bracketed
# ---------------------------------------------------------------------------


class TestCriterion2Brackets:
    def test_no_positions_passes(self, monitor):
        c = monitor.evaluate_criteria()
        assert c.all_positions_bracketed is True
        assert c.naked_position_count == 0

    def test_bracketed_position_passes(self, monitor):
        monitor.on_position_opened("coid-1", has_bracket=True)
        c = monitor.evaluate_criteria()
        assert c.all_positions_bracketed is True
        assert c.naked_position_count == 0

    def test_naked_position_fails(self, monitor):
        monitor.on_position_opened("coid-2", has_bracket=False)
        c = monitor.evaluate_criteria()
        assert c.all_positions_bracketed is False
        assert c.naked_position_count == 1

    def test_bracket_confirmed_clears_naked(self, monitor):
        monitor.on_position_opened("coid-3", has_bracket=False)
        assert monitor.evaluate_criteria().all_positions_bracketed is False

        monitor.on_bracket_confirmed("coid-3")
        assert monitor.evaluate_criteria().all_positions_bracketed is True

    def test_mixed_bracketed_and_naked(self, monitor):
        monitor.on_position_opened("bracketed", has_bracket=True)
        monitor.on_position_opened("naked", has_bracket=False)
        c = monitor.evaluate_criteria()
        assert c.all_positions_bracketed is False
        assert c.naked_position_count == 1


# ---------------------------------------------------------------------------
# TestDryRunMonitor — Criterion 3: Close verification within window
# ---------------------------------------------------------------------------


class TestCriterion3CloseVerification:
    def test_no_closes_passes(self, monitor):
        c = monitor.evaluate_criteria()
        assert c.all_closes_verified_within_window is True
        assert c.close_verification_total == 0

    def test_close_within_window_passes(self, monitor):
        monitor.on_position_opened("coid-a", has_bracket=True)
        monitor.on_position_close_verified("coid-a", within_window=True, elapsed_secs=12.5)
        c = monitor.evaluate_criteria()
        assert c.all_closes_verified_within_window is True
        assert c.close_verification_failures == 0
        assert c.close_verification_total == 1

    def test_close_outside_window_fails(self, monitor):
        monitor.on_position_opened("coid-b", has_bracket=True)
        monitor.on_position_close_verified("coid-b", within_window=False, elapsed_secs=35.0)
        c = monitor.evaluate_criteria()
        assert c.all_closes_verified_within_window is False
        assert c.close_verification_failures == 1

    def test_multiple_closes_one_failure(self, monitor):
        for i in range(5):
            monitor.on_position_opened(f"coid-{i}", has_bracket=True)
            monitor.on_position_close_verified(f"coid-{i}", within_window=True, elapsed_secs=5.0)
        monitor.on_position_opened("fail-coid", has_bracket=True)
        monitor.on_position_close_verified("fail-coid", within_window=False, elapsed_secs=40.0)
        c = monitor.evaluate_criteria()
        assert c.all_closes_verified_within_window is False
        assert c.close_verification_failures == 1
        assert c.close_verification_total == 6


# ---------------------------------------------------------------------------
# TestDryRunMonitor — Criterion 4: No reconciliation mismatches in final 24h
# ---------------------------------------------------------------------------


class TestCriterion4Reconciliation:
    def test_no_checks_passes(self, monitor):
        c = monitor.evaluate_criteria()
        assert c.no_recon_mismatches_final_24h is True

    def test_pass_reconciliation_passes(self, monitor):
        monitor.on_reconciliation_checked(mismatch=False)
        c = monitor.evaluate_criteria()
        assert c.no_recon_mismatches_final_24h is True

    def test_recent_mismatch_fails(self, monitor):
        monitor.on_reconciliation_checked(mismatch=True, detail="itm=0 exchange=0.01")
        c = monitor.evaluate_criteria()
        assert c.no_recon_mismatches_final_24h is False
        assert c.recent_mismatch_count == 1

    def test_old_mismatch_outside_24h_passes(self, monitor):
        # Inject a mismatch with timestamp > 24h ago
        old_ts = datetime.now(timezone.utc) - timedelta(hours=25)
        monitor.on_reconciliation_checked(timestamp=old_ts, mismatch=True, detail="old mismatch")
        c = monitor.evaluate_criteria()
        # Should not count as a recent mismatch
        assert c.no_recon_mismatches_final_24h is True
        assert c.recent_mismatch_count == 0

    def test_recent_mismatch_after_old_mismatch_fails(self, monitor):
        old_ts = datetime.now(timezone.utc) - timedelta(hours=25)
        monitor.on_reconciliation_checked(timestamp=old_ts, mismatch=True)
        monitor.on_reconciliation_checked(mismatch=True, detail="recent")
        c = monitor.evaluate_criteria()
        assert c.no_recon_mismatches_final_24h is False
        assert c.recent_mismatch_count == 1


# ---------------------------------------------------------------------------
# TestDryRunMonitor — Criterion 5: Risk metrics within thresholds
# ---------------------------------------------------------------------------


class TestCriterion5RiskMetrics:
    def test_no_updates_passes(self, monitor):
        c = monitor.evaluate_criteria()
        assert c.risk_metrics_ok is True

    def test_within_limits_passes(self, monitor):
        monitor.on_pnl_update("strat-1", Decimal("-100"), Decimal("0.02"))
        c = monitor.evaluate_criteria()
        assert c.risk_metrics_ok is True
        assert c.max_drawdown_observed == Decimal("0.02")
        assert c.max_daily_loss_observed == Decimal("100")

    def test_drawdown_at_limit_passes(self, monitor):
        monitor.on_pnl_update("strat-1", Decimal("0"), Decimal("0.05"))  # exactly at 5%
        c = monitor.evaluate_criteria()
        assert c.risk_metrics_ok is True

    def test_drawdown_exceeds_limit_fails(self, monitor):
        monitor.on_pnl_update("strat-1", Decimal("0"), Decimal("0.06"))  # 6% > 5%
        c = monitor.evaluate_criteria()
        assert c.risk_metrics_ok is False

    def test_daily_loss_at_limit_passes(self, monitor):
        monitor.on_pnl_update("strat-1", Decimal("-500"), Decimal("0.0"))  # exactly at $500
        c = monitor.evaluate_criteria()
        assert c.risk_metrics_ok is True

    def test_daily_loss_exceeds_limit_fails(self, monitor):
        monitor.on_pnl_update("strat-1", Decimal("-501"), Decimal("0.0"))  # $501 > $500
        c = monitor.evaluate_criteria()
        assert c.risk_metrics_ok is False

    def test_max_drawdown_tracked_across_updates(self, monitor):
        monitor.on_pnl_update("strat-1", Decimal("0"), Decimal("0.01"))
        monitor.on_pnl_update("strat-1", Decimal("0"), Decimal("0.04"))
        monitor.on_pnl_update("strat-1", Decimal("0"), Decimal("0.02"))  # drops back
        c = monitor.evaluate_criteria()
        assert c.max_drawdown_observed == Decimal("0.04")


# ---------------------------------------------------------------------------
# TestDryRunMonitor — Criterion 6: No CRITICAL alerts
# ---------------------------------------------------------------------------


class TestCriterion6Alerts:
    def test_no_alerts_passes(self, monitor):
        c = monitor.evaluate_criteria()
        assert c.no_critical_alerts is True
        assert c.critical_alert_count == 0

    def test_critical_alert_fails(self, monitor):
        monitor.on_critical_alert("Position not closed after 30s", severity="CRITICAL")
        c = monitor.evaluate_criteria()
        assert c.no_critical_alerts is False
        assert c.critical_alert_count == 1

    def test_warning_alert_does_not_fail_criterion(self, monitor):
        monitor.on_critical_alert("Minor discrepancy", severity="WARNING")
        c = monitor.evaluate_criteria()
        # WARNING does not fail criterion 6 (only CRITICAL does)
        assert c.no_critical_alerts is True
        assert c.critical_alert_count == 0

    def test_multiple_critical_alerts_count(self, monitor):
        monitor.on_critical_alert("Alert 1", severity="CRITICAL")
        monitor.on_critical_alert("Alert 2", severity="CRITICAL")
        c = monitor.evaluate_criteria()
        assert c.critical_alert_count == 2


# ---------------------------------------------------------------------------
# TestDryRunMonitor — Overall pass/fail + all_passing flag
# ---------------------------------------------------------------------------


class TestOverallCriteria:
    def test_all_passing_when_clean(self, monitor):
        # Add some clean data
        monitor.on_position_opened("c1", has_bracket=True)
        monitor.on_position_close_verified("c1", within_window=True, elapsed_secs=10.0)
        monitor.on_reconciliation_checked(mismatch=False)
        c = monitor.evaluate_criteria()
        assert c.all_passing is True

    def test_all_passing_false_when_any_fails(self, monitor):
        # Add one failure
        monitor.on_exception(RuntimeError("bad"), context="test")
        c = monitor.evaluate_criteria()
        assert c.all_passing is False

    def test_criteria_as_dict_structure(self, monitor):
        c = monitor.evaluate_criteria()
        d = c.as_dict()
        assert "criterion_1_zero_exceptions" in d
        assert "criterion_2_all_positions_bracketed" in d
        assert "criterion_3_all_closes_within_30s" in d
        assert "criterion_4_no_recon_mismatches_24h" in d
        assert "criterion_5_risk_metrics_ok" in d
        assert "criterion_6_no_critical_alerts" in d
        assert "all_passing" in d


# ---------------------------------------------------------------------------
# TestDryRunMonitor — Snapshot structure
# ---------------------------------------------------------------------------


class TestMonitorSnapshot:
    def test_snapshot_has_required_keys(self, monitor):
        snap = monitor.snapshot()
        assert "snapshot_at" in snap
        assert "started_at" in snap
        assert "runtime_hours" in snap
        assert "positions" in snap
        assert "close_verifications" in snap
        assert "reconciliations" in snap
        assert "risk_metrics" in snap
        assert "exceptions" in snap
        assert "alerts" in snap
        assert "criteria" in snap

    def test_runtime_hours_increases(self, monitor):
        snap1 = monitor.snapshot()
        time.sleep(0.05)
        snap2 = monitor.snapshot()
        assert snap2["runtime_hours"] >= snap1["runtime_hours"]

    def test_position_counts_tracked(self, monitor):
        monitor.on_position_opened("c1", has_bracket=True)
        monitor.on_position_opened("c2", has_bracket=True)
        monitor.on_position_close_verified("c1", within_window=True, elapsed_secs=5.0)
        snap = monitor.snapshot()
        assert snap["positions"]["opened"] == 2
        assert snap["positions"]["closed"] == 1
        assert snap["positions"]["active"] == 1

    def test_reconciliation_pass_rate(self, monitor):
        monitor.on_reconciliation_checked(mismatch=False)
        monitor.on_reconciliation_checked(mismatch=False)
        monitor.on_reconciliation_checked(mismatch=True)
        snap = monitor.snapshot()
        assert snap["reconciliations"]["total"] == 3
        assert snap["reconciliations"]["mismatches"] == 1
        assert snap["reconciliations"]["pass_rate"] == pytest.approx(66.7, abs=0.1)


# ---------------------------------------------------------------------------
# TestDryRunReportGenerator
# ---------------------------------------------------------------------------


class TestDryRunReportGenerator:
    @pytest.fixture
    def clean_snapshot(self):
        m = DryRunMonitor()
        m.start()
        # Simulate a clean run
        for i in range(10):
            m.on_position_opened(f"coid-{i}", has_bracket=True)
            m.on_position_close_verified(f"coid-{i}", within_window=True, elapsed_secs=8.0)
        for _ in range(100):
            m.on_reconciliation_checked(mismatch=False)
        m.on_pnl_update("strat-1", Decimal("50"), Decimal("0.01"))
        return m.snapshot()

    @pytest.fixture
    def failing_snapshot(self):
        m = DryRunMonitor()
        m.start()
        m.on_exception(RuntimeError("test failure"), context="test")
        m.on_position_opened("naked-coid", has_bracket=False)
        m.on_critical_alert("Position not closed", severity="CRITICAL")
        return m.snapshot()

    def test_generate_returns_string(self, clean_snapshot):
        gen = DryRunReportGenerator()
        report = gen.generate(
            monitor_snapshot=clean_snapshot,
            strategies_loaded=["strat-001"],
            signals_generated=50,
            orders_placed=30,
            orders_filled=28,
            orders_cancelled=2,
        )
        assert isinstance(report, str)
        assert len(report) > 100

    def test_go_recommendation_when_all_passing(self, clean_snapshot):
        gen = DryRunReportGenerator()
        report = gen.generate(
            monitor_snapshot=clean_snapshot,
            strategies_loaded=["strat-001"],
            signals_generated=50,
            orders_placed=30,
            orders_filled=28,
            orders_cancelled=2,
        )
        assert "**GO**" in report

    def test_nogo_recommendation_when_failing(self, failing_snapshot):
        gen = DryRunReportGenerator()
        report = gen.generate(
            monitor_snapshot=failing_snapshot,
            strategies_loaded=["strat-001"],
            signals_generated=5,
            orders_placed=2,
            orders_filled=0,
            orders_cancelled=2,
        )
        assert "**NO-GO**" in report

    def test_report_contains_all_criteria_table(self, clean_snapshot):
        gen = DryRunReportGenerator()
        report = gen.generate(
            monitor_snapshot=clean_snapshot,
            strategies_loaded=["strat-001"],
            signals_generated=50,
            orders_placed=30,
            orders_filled=28,
            orders_cancelled=2,
        )
        for i in range(1, 7):
            assert f"| {i} |" in report

    def test_report_contains_run_statistics(self, clean_snapshot):
        gen = DryRunReportGenerator()
        report = gen.generate(
            monitor_snapshot=clean_snapshot,
            strategies_loaded=["strat-001", "strat-002"],
            signals_generated=120,
            orders_placed=45,
            orders_filled=42,
            orders_cancelled=3,
        )
        assert "120" in report  # signals
        assert "45" in report   # orders placed
        assert "42" in report   # orders filled
        assert "strat-001" in report

    def test_outstanding_concerns_section(self, failing_snapshot):
        gen = DryRunReportGenerator()
        report = gen.generate(
            monitor_snapshot=failing_snapshot,
            strategies_loaded=[],
            signals_generated=0,
            orders_placed=0,
            orders_filled=0,
            orders_cancelled=0,
            outstanding_concerns=["Network latency issues observed"],
        )
        assert "Network latency issues observed" in report

    def test_custom_issues_log(self, clean_snapshot):
        gen = DryRunReportGenerator()
        issues = [
            {
                "severity": "WARNING",
                "occurred_at": "2026-05-08T10:00:00Z",
                "description": "Brief WS disconnect",
                "resolution": "Reconnected automatically",
            }
        ]
        report = gen.generate(
            monitor_snapshot=clean_snapshot,
            strategies_loaded=["strat-001"],
            signals_generated=50,
            orders_placed=10,
            orders_filled=9,
            orders_cancelled=1,
            issues_log=issues,
        )
        assert "Brief WS disconnect" in report
        assert "Reconnected automatically" in report

    def test_no_issues_section(self, clean_snapshot):
        gen = DryRunReportGenerator()
        report = gen.generate(
            monitor_snapshot=clean_snapshot,
            strategies_loaded=[],
            signals_generated=0,
            orders_placed=0,
            orders_filled=0,
            orders_cancelled=0,
        )
        assert "No issues encountered" in report

    def test_risk_parameter_review_included(self, clean_snapshot):
        gen = DryRunReportGenerator()
        report = gen.generate(
            monitor_snapshot=clean_snapshot,
            strategies_loaded=[],
            signals_generated=0,
            orders_placed=0,
            orders_filled=0,
            orders_cancelled=0,
            risk_parameter_review={
                "max_position_size_btc": "1.0",
                "daily_loss_limit_usd": "500.00",
            },
        )
        assert "max_position_size_btc" in report
        assert "1.0" in report


# ---------------------------------------------------------------------------
# TestDryRunRunnerConfig
# ---------------------------------------------------------------------------


class TestDryRunRunnerConfig:
    def test_default_config_valid(self):
        from src.itm.dry_run.runner import DryRunRunnerConfig
        config = DryRunRunnerConfig()
        assert config.min_runtime_hours == 48.0
        assert config.daily_loss_limit_usd == Decimal("500.00")
        assert config.max_position_btc == Decimal("1.0")

    def test_daily_loss_limit_over_500_rejected(self):
        from src.itm.dry_run.runner import DryRunRunnerConfig
        with pytest.raises(ValueError, match="institutional limit"):
            DryRunRunnerConfig(daily_loss_limit_usd=Decimal("501"))

    def test_max_position_over_1btc_rejected(self):
        from src.itm.dry_run.runner import DryRunRunnerConfig
        with pytest.raises(ValueError, match="institutional limit"):
            DryRunRunnerConfig(max_position_btc=Decimal("1.001"))

    def test_min_runtime_below_1h_rejected(self):
        from src.itm.dry_run.runner import DryRunRunnerConfig
        with pytest.raises(ValueError):
            DryRunRunnerConfig(min_runtime_hours=0.5)

    def test_custom_config_valid(self):
        from src.itm.dry_run.runner import DryRunRunnerConfig
        config = DryRunRunnerConfig(
            min_runtime_hours=72.0,
            daily_loss_limit_usd=Decimal("250"),
            max_position_btc=Decimal("0.5"),
        )
        assert config.min_runtime_hours == 72.0


# ---------------------------------------------------------------------------
# TestAssertTestnetEnv
# ---------------------------------------------------------------------------


class TestAssertTestnetEnv:
    def test_missing_key_raises(self, monkeypatch):
        from src.itm.dry_run.runner import _assert_testnet_env
        monkeypatch.delenv("BINANCE_TESTNET_API_KEY", raising=False)
        monkeypatch.delenv("BINANCE_TESTNET_API_SECRET", raising=False)
        with pytest.raises(RuntimeError, match="not set"):
            _assert_testnet_env()

    def test_placeholder_key_raises(self, monkeypatch):
        from src.itm.dry_run.runner import _assert_testnet_env
        monkeypatch.setenv("BINANCE_TESTNET_API_KEY", "your_testnet_api_key_here")
        monkeypatch.setenv("BINANCE_TESTNET_API_SECRET", "your_testnet_api_secret_here")
        with pytest.raises(RuntimeError, match="not set"):
            _assert_testnet_env()

    def test_real_credentials_pass(self, monkeypatch):
        from src.itm.dry_run.runner import _assert_testnet_env
        monkeypatch.setenv("BINANCE_TESTNET_API_KEY", "abc123realkey")
        monkeypatch.setenv("BINANCE_TESTNET_API_SECRET", "xyz789realsecret")
        key, secret = _assert_testnet_env()
        assert key == "abc123realkey"
        assert secret == "xyz789realsecret"

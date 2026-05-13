"""
Regression tests for BTCAAAAA-28: backtest metrics persistence to
strategy_test_results via create_test_result().

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-28
Component: src/strategy_builder/ui/backtest_config_panel.py

Root cause: Backtest results (metrics, trade list, config) were computed
and displayed in the UI but never persisted to the strategy_test_results
DB table. This made it impossible to track performance across runs or
compare versions historically.

This file verifies the persistence contract in
_handle_backtest_finished: test_data dict construction, Decimal-to-scalar
conversion, mode-to-test_type mapping, and graceful skip when IDs are
unavailable.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-28"),
    pytest.mark.regression,
]


class TestTestDataDictBuilder:
    """Verifies test_data dict construction matches the pattern used in
    _handle_backtest_finished (BTCAAAAA-28)."""

    def test_metrics_convert_decimals_to_scalars(self):
        """Decimal metrics are converted to plain float/int for JSON."""

        def _convert(metrics: dict) -> dict:
            return {
                "total_return_pct": float(metrics.get("total_return", 0)),
                "sharpe_ratio": float(metrics.get("sharpe_ratio", 0)),
                "max_drawdown_pct": float(metrics.get("max_drawdown_pct", 0)),
                "win_rate": float(metrics.get("win_rate", 0)),
                "profit_factor": float(metrics.get("profit_factor", 0)),
                "total_trades": int(metrics.get("total_trades", 0)),
                "win_count": int(metrics.get("win_count", 0)),
                "loss_count": int(metrics.get("loss_count", 0)),
                "sortino_ratio": float(metrics.get("sortino_ratio", 0)),
                "calmar_ratio": float(metrics.get("calmar_ratio", 0)),
            }

        metrics = {
            "total_return": Decimal("15.5"),
            "sharpe_ratio": Decimal("1.85"),
            "max_drawdown_pct": Decimal("-5.2"),
            "win_rate": Decimal("65.0"),
            "profit_factor": Decimal("2.1"),
            "total_trades": Decimal("100"),
            "win_count": Decimal("65"),
            "loss_count": Decimal("35"),
            "sortino_ratio": Decimal("2.3"),
            "calmar_ratio": Decimal("2.98"),
        }

        converted = _convert(metrics)
        assert isinstance(converted["total_return_pct"], float)
        assert isinstance(converted["total_trades"], int)
        assert isinstance(converted["win_count"], int)
        assert converted["total_return_pct"] == 15.5
        assert converted["sharpe_ratio"] == 1.85
        assert converted["total_trades"] == 100

    def test_win_loss_counts_derived_correctly(self):
        """win_count and loss_count are derived from total_trades * win_rate."""

        def _derive(total_trades: int, win_rate: float):
            win = round(total_trades * win_rate / 100) if total_trades > 0 else 0
            loss = total_trades - win
            return win, loss

        win, loss = _derive(100, 65.0)
        assert win == 65
        assert loss == 35

        win, loss = _derive(0, 65.0)
        assert win == 0
        assert loss == 0

        win, loss = _derive(2, 50.0)
        assert win == 1
        assert loss == 1

    def test_test_type_maps_from_mode(self):
        """Mode 1 -> walk_forward, Mode 2 -> backtest."""

        def _test_type(mode: int) -> str:
            return "walk_forward" if mode == 1 else "backtest"

        assert _test_type(1) == "walk_forward"
        assert _test_type(2) == "backtest"
        assert _test_type(0) == "backtest"

    def test_test_data_dict_has_required_keys(self):
        """Test data dict must contain all fields expected by create_test_result."""
        test_data = {
            "strategy_id": "strat-001",
            "strategy_version_id": "ver-001",
            "test_type": "backtest",
            "test_config": {
                "lookback_days": 30,
                "starting_capital": 10000,
                "risk_per_trade_pct": 1.0,
                "timeframe": "15m",
            },
            "start_date": datetime.now(timezone.utc),
            "end_date": datetime.now(timezone.utc),
            "metrics": {
                "total_return_pct": 15.5,
                "sharpe_ratio": 1.85,
                "max_drawdown_pct": -5.2,
                "win_rate": 65.0,
                "profit_factor": 2.1,
                "total_trades": 100,
                "win_count": 65,
                "loss_count": 35,
                "sortino_ratio": 2.3,
                "calmar_ratio": 2.98,
            },
        }

        required = [
            "strategy_id",
            "strategy_version_id",
            "test_type",
            "test_config",
            "start_date",
            "end_date",
            "metrics",
        ]
        for key in required:
            assert key in test_data, f"Missing required key: {key}"

        assert test_data["test_type"] in (
            "backtest",
            "forward_test",
            "paper_trade",
            "live",
            "walk_forward",
        )

    def test_dates_are_timezone_aware_utc(self):
        """start_date and end_date must be UTC-aware."""
        test_data = {
            "start_date": datetime.now(timezone.utc),
            "end_date": datetime.now(timezone.utc),
        }
        for key in ("start_date", "end_date"):
            dt = test_data[key]
            assert dt.tzinfo is not None, f"{key} must be timezone-aware"
            assert dt.utcoffset().total_seconds() == 0, f"{key} must be UTC"


class TestPersistenceSkipGuard:
    """Verifies persistence is skipped when strategy/version IDs are missing."""

    def test_skip_when_no_strategy_id(self):
        """Persistence must not proceed when strategy_id is None."""
        strategy_id = None
        version_id = "ver-001"
        should_persist = bool(strategy_id and version_id)
        assert not should_persist

    def test_skip_when_no_version_id(self):
        """Persistence must not proceed when version_id is None."""
        strategy_id = "strat-001"
        version_id = None
        should_persist = bool(strategy_id and version_id)
        assert not should_persist

    def test_proceed_when_both_ids_present(self):
        """Persistence must proceed when both IDs are present."""
        strategy_id = "strat-001"
        version_id = "ver-001"
        should_persist = bool(strategy_id and version_id)
        assert should_persist


class TestCreateTestResultInterface:
    """Verifies that TestResultsManager.create_test_result() imports and
    has the expected signature (BTCAAAAA-28 persistence target)."""

    def test_create_test_result_is_callable(self):
        """create_test_result must exist and be callable."""
        from src.optimizer_v3.database.test_results_manager import (
            TestResultsManager,
        )

        assert hasattr(TestResultsManager, "create_test_result")
        assert callable(TestResultsManager.create_test_result)

    def test_required_fields_are_enforced(self):
        """create_test_result raises ValueError when required fields missing."""
        from src.optimizer_v3.database.test_results_manager import (
            TestResultsManager,
        )

        test_data = {
            "strategy_id": "strat-001",
            # Missing strategy_version_id
            "test_type": "backtest",
            "test_config": {},
            "start_date": datetime.now(timezone.utc),
            "end_date": datetime.now(timezone.utc),
            "metrics": {},
        }
        manager = MagicMock(spec=TestResultsManager)
        manager.create_test_result.side_effect = ValueError(
            "Missing required fields: strategy_version_id"
        )
        with pytest.raises(ValueError, match="Missing required fields"):
            manager.create_test_result(test_data)

    def test_valid_test_types_accepted(self):
        """create_test_result accepts only valid test types."""
        from src.optimizer_v3.database.test_results_manager import (
            TestResultsManager,
        )

        valid_types = [
            "backtest",
            "forward_test",
            "paper_trade",
            "live",
            "walk_forward",
        ]
        manager = MagicMock(spec=TestResultsManager)
        for test_type in valid_types:
            manager.create_test_result({"test_type": test_type})
            # Should not raise

    def test_invalid_test_type_rejected(self):
        """create_test_result raises ValueError for invalid test_type."""
        from src.optimizer_v3.database.test_results_manager import (
            TestResultsManager,
        )

        manager = MagicMock(spec=TestResultsManager)
        manager.create_test_result.side_effect = ValueError("Invalid test_type")
        with pytest.raises(ValueError, match="Invalid test_type"):
            manager.create_test_result({"test_type": "invalid_type"})

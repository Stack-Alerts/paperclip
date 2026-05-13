"""
Regression tests for BTCAAAAA-119: navigate to Issues tab after auto-fix revalidation.

Bug: After clicking Fix Now and revalidation completes, the UI unconditionally
reset to Summary tab (index 0) via _create_tabs() setCurrentIndex(0), hiding
the revalidation results.

Fix: src/strategy_builder/ui/validation_report_window.py
  - Store tabs widget as self.tabs in _reinitialize_ui() for post-reinit access
  - In _rerun_validation(), call self.tabs.setCurrentIndex(1) after
    _reinitialize_ui() succeeds

Acceptance criteria tested here:
  AC1  First-open: tab index is 0 (Summary default).
  AC2  Post-_rerun_validation: tab index is 1 (Issues tab).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("PyQt5", reason="PyQt5 not available — skipping Qt regression tests")
pytest.importorskip("pytest_qt", reason="pytest-qt not installed — skipping Qt regression tests")

from PyQt5.QtWidgets import QApplication

from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
)
from src.optimizer_v3.validation.institutional_validator import (
    InstitutionalValidator,
    ValidationReport,
)

pytestmark = [
    pytest.mark.bug("BTCAAAAA-119"),
    pytest.mark.regression,
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_config() -> StrategyConfig:
    """Build a trivial valid config so ValidationReportWindow can init."""
    signal = SignalConfig(name="test_signal", logic="AND")
    block = BlockConfig(name="TestBlock", logic="AND", signals=[signal])
    return StrategyConfig(
        name="TestRegression119",
        strategy_type="Bullish",
        blocks=[block],
    )


def _make_valid_report(config: StrategyConfig) -> ValidationReport:
    """Return a real ValidationReport from the validator."""
    validator = InstitutionalValidator()
    return validator.validate(config)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTabNavigationAfterAutoFixRevalidation:
    """Tab-index behaviours for ValidationReportWindow (BTCAAAAA-119)."""

    def test_initial_tab_is_summary(self, qtbot, qapp):
        """AC1: Normal first-open defaults to Summary tab (index 0)."""
        config = _make_minimal_config()
        report = _make_valid_report(config)

        from src.strategy_builder.ui.validation_report_window import (
            ValidationReportWindow,
        )

        window = ValidationReportWindow(report=report, config=config)
        qtbot.addWidget(window)

        assert window.tabs.currentIndex() == 0, (
            f"Expected initial tab index 0 (Summary), got {window.tabs.currentIndex()}"
        )

    def test_tab_navigates_to_issues_after_rerun_validation(self, qtbot, qapp):
        """AC2: After _rerun_validation(), Issues tab (index 1) is selected."""
        config = _make_minimal_config()
        report = _make_valid_report(config)

        from src.strategy_builder.ui.validation_report_window import (
            ValidationReportWindow,
        )

        window = ValidationReportWindow(report=report, config=config)
        qtbot.addWidget(window)

        # Confirm pre-condition: initially Summary
        assert window.tabs.currentIndex() == 0

        # Mock InstitutionalValidator so _rerun_validation runs without error
        with patch(
            "src.strategy_builder.ui.validation_report_window.InstitutionalValidator",
        ) as mock_validator_cls:
            mock_validator = MagicMock(spec=InstitutionalValidator)
            mock_validator.validate.return_value = report
            mock_validator_cls.return_value = mock_validator

            window._rerun_validation()

        assert window.tabs.currentIndex() == 1, (
            f"Expected tab index 1 (Issues) after revalidation, "
            f"got {window.tabs.currentIndex()}"
        )

"""
Qt integration test for ValidationReportWindow.fix_applied signal.

Verifies that when the DIRECTION_001 auto-fix is triggered via
_handle_fix_click(), the window:
  1. Emits fix_applied(fix_type, fix_data) with the correct payload.
  2. Updates self.config.strategy_type to the corrected direction.

The entire module is skipped when PyQt5 or pytest-qt are unavailable,
making it safe to run in headless CI environments without a display.

Author: QAEngineer (BTCAAAAA-130)
"""

import pytest
from unittest.mock import patch, MagicMock

# Gate: skip the whole module if PyQt5 is not present.
pytest.importorskip("PyQt5", reason="PyQt5 not available — skipping Qt signal tests")
# Gate: skip the whole module if pytest-qt (qtbot fixture) is not installed.
pytest.importorskip("pytest_qt", reason="pytest-qt not installed — skipping Qt signal tests")

from PyQt5.QtWidgets import QApplication

from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
)
from src.optimizer_v3.validation.institutional_validator import (
    InstitutionalValidator,
    ValidationIssue,
    ValidationSeverity,
)
from src.strategy_builder.ui.validation_report_window import ValidationReportWindow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bullish_config_with_bearish_signals(bearish_count: int = 4, bullish_count: int = 1) -> StrategyConfig:
    """
    Build a Bullish StrategyConfig whose signals are >70% bearish-named,
    triggering DIRECTION_001 from InstitutionalValidator.
    """
    signals = [
        SignalConfig(name=f"bearish_signal_{i}", logic="AND")
        for i in range(bearish_count)
    ]
    signals += [
        SignalConfig(name=f"bullish_signal_{j}", logic="AND")
        for j in range(bullish_count)
    ]
    block = BlockConfig(name="EntryBlock", logic="AND", signals=signals)
    return StrategyConfig(
        name="TestBullishStrategy",
        strategy_type="Bullish",
        blocks=[block],
    )


def _make_direction_001_issue(strategy_type: str = "Bullish") -> ValidationIssue:
    """
    Build a ValidationIssue that represents the DIRECTION_001 rule exactly
    as InstitutionalValidator generates it, so _handle_fix_click dispatches
    to the correct handler branch.
    """
    return ValidationIssue(
        severity=ValidationSeverity.CRITICAL,
        category="DIRECTION",
        rule_id="DIRECTION_001",
        rule_name="Strategy Direction Mismatch",
        message=(
            f"Strategy type is '{strategy_type}' but 80% of entry signals "
            f"are Bearish (CRITICAL mismatch)"
        ),
        location="Strategy",
        suggestion="Switch strategy type to 'Bearish' or adjust signal selection",
        auto_fix_available=True,
        auto_fix_data={
            "fix_type": "switch_direction",
            "current_type": strategy_type,
            "suggested_type": "Bearish",
        },
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    """
    Ensure a QApplication exists for the test module.
    Returns the existing instance if one is already running (e.g., in CI).
    """
    app = QApplication.instance() or QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidationReportFixSignal:
    """
    Qt-level tests for ValidationReportWindow.fix_applied signal emission.

    Requires PyQt5 and pytest-qt. Both module-level importorskip guards skip
    this entire file when either dependency is absent.
    """

    def test_fix_applied_signal_emits_corrected_type(self, qtbot, qapp):
        """
        When _handle_fix_click() is called with a DIRECTION_001 issue:

          - fix_applied must be emitted exactly once.
          - The first argument (fix_type) must equal 'DIRECTION_001'.
          - The second argument (fix_data) must contain the 'issue' key
            whose value is the rule_name.
          - window.config.strategy_type must equal 'Bearish' (the corrected type).

        AutoFixConfirmDialog and QMessageBox are both mocked so no modal
        dialogs are shown during the test.
        """
        config = _make_bullish_config_with_bearish_signals()

        # Build a ValidationReport so the window can be constructed.
        validator = InstitutionalValidator()
        report = validator.validate(config)

        # Confirm DIRECTION_001 is present before we start (test setup sanity).
        pre_ids = [i.rule_id for i in report.critical_issues]
        assert "DIRECTION_001" in pre_ids, (
            "Test setup error: DIRECTION_001 not in report.critical_issues. "
            f"Critical issues: {pre_ids}"
        )

        direction_001_issue = _make_direction_001_issue(strategy_type="Bullish")

        # ----------------------------------------------------------------
        # Mock AutoFixConfirmDialog so it auto-confirms without showing UI.
        # ----------------------------------------------------------------
        mock_dialog_instance = MagicMock()
        mock_dialog_instance.user_confirmed = True
        mock_dialog_instance.user_options = {}
        mock_dialog_instance.exec_.return_value = 1  # QDialog.Accepted

        # ----------------------------------------------------------------
        # Mock QMessageBox to prevent success dialog from blocking.
        # ----------------------------------------------------------------
        mock_msgbox_instance = MagicMock()
        mock_msgbox_instance.exec_.return_value = 0

        with (
            patch(
                "src.strategy_builder.ui.validation_report_window.AutoFixConfirmDialog",
                return_value=mock_dialog_instance,
            ),
            patch(
                "src.strategy_builder.ui.validation_report_window.QMessageBox",
                return_value=mock_msgbox_instance,
            ),
        ):
            window = ValidationReportWindow(report=report, config=config)
            qtbot.addWidget(window)

            # Collect emitted signals.
            emitted: list = []
            window.fix_applied.connect(lambda ft, fd: emitted.append((ft, fd)))

            # Trigger the fix handler directly.
            window._handle_fix_click(direction_001_issue)

        # ----------------------------------------------------------------
        # Assertions
        # ----------------------------------------------------------------
        assert len(emitted) == 1, (
            f"Expected fix_applied to be emitted exactly once, got {len(emitted)} emission(s)."
        )

        fix_type, fix_data = emitted[0]

        assert fix_type == "DIRECTION_001", (
            f"Expected fix_type='DIRECTION_001', got '{fix_type}'"
        )
        assert "issue" in fix_data, (
            f"fix_data must contain 'issue' key. Got: {fix_data}"
        )
        assert fix_data["issue"] == direction_001_issue.rule_name, (
            f"fix_data['issue'] should be the rule_name. "
            f"Expected '{direction_001_issue.rule_name}', got '{fix_data['issue']}'"
        )
        assert window.config.strategy_type == "Bearish", (
            f"Expected window.config.strategy_type='Bearish' after fix, "
            f"got '{window.config.strategy_type}'"
        )

    def test_fix_not_emitted_when_dialog_cancelled(self, qtbot, qapp):
        """
        When the user cancels the AutoFixConfirmDialog, fix_applied must NOT
        be emitted and the config must remain unchanged.
        """
        config = _make_bullish_config_with_bearish_signals()
        validator = InstitutionalValidator()
        report = validator.validate(config)

        direction_001_issue = _make_direction_001_issue()

        # Dialog cancelled (user_confirmed=False).
        mock_dialog_instance = MagicMock()
        mock_dialog_instance.user_confirmed = False
        mock_dialog_instance.user_options = {}
        mock_dialog_instance.exec_.return_value = 0  # QDialog.Rejected

        with patch(
            "src.strategy_builder.ui.validation_report_window.AutoFixConfirmDialog",
            return_value=mock_dialog_instance,
        ):
            window = ValidationReportWindow(report=report, config=config)
            qtbot.addWidget(window)

            emitted: list = []
            window.fix_applied.connect(lambda ft, fd: emitted.append((ft, fd)))

            window._handle_fix_click(direction_001_issue)

        assert len(emitted) == 0, (
            "fix_applied must NOT be emitted when the confirmation dialog is cancelled."
        )
        assert window.config.strategy_type == "Bullish", (
            "Config must remain unchanged when the dialog is cancelled."
        )

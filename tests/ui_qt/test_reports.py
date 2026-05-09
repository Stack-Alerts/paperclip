"""
E2E tests for report generation — ValidationReportWindow renders without
exceptions for both clean strategies and strategies with issues.

Happy-path: window opens, tabs exist, no crash on empty report.
Error-path: report with blocking issues renders and exposes correct state.

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/ui_qt/test_reports.py -v
"""

import pytest
from datetime import datetime

from PyQt5.QtWidgets import QTabWidget, QPushButton, QTableWidget

from src.strategy_builder.ui.validation_report_window import ValidationReportWindow
from src.optimizer_v3.validation.institutional_validator import (
    ValidationReport,
    ValidationIssue,
    ValidationSeverity,
)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def _empty_report():
    """ValidationReport with no issues — represents a fully valid strategy."""
    return ValidationReport(
        timestamp=datetime.now().isoformat(),
        is_valid=True,
        validation_level="FULL",
    )


def _report_with_warning():
    """ValidationReport with one WARNING — valid but should be reviewed."""
    issue = ValidationIssue(
        severity=ValidationSeverity.WARNING,
        category="STRUCTURAL",
        rule_id="STRUCTURAL_001",
        rule_name="Missing exit condition",
        message="Strategy has no exit condition defined.",
        location="strategy-level",
        suggestion="Add a take-profit or stop-loss block.",
    )
    return ValidationReport(
        timestamp=datetime.now().isoformat(),
        is_valid=True,
        validation_level="FULL",
        warnings=[issue],
    )


def _report_with_error():
    """ValidationReport with one ERROR — blocks backtest execution."""
    issue = ValidationIssue(
        severity=ValidationSeverity.ERROR,
        category="STRUCTURAL",
        rule_id="STRUCTURAL_002",
        rule_name="No entry signal",
        message="Strategy has no entry signal configured.",
        location="block::EntryBlock",
    )
    return ValidationReport(
        timestamp=datetime.now().isoformat(),
        is_valid=False,
        validation_level="FULL",
        errors=[issue],
    )


def _report_with_critical():
    """ValidationReport with one CRITICAL issue."""
    issue = ValidationIssue(
        severity=ValidationSeverity.CRITICAL,
        category="STRUCTURAL",
        rule_id="STRUCTURAL_003",
        rule_name="Conflicting exit conditions",
        message="Multiple conflicting exit conditions are active simultaneously.",
        location="strategy-level",
    )
    return ValidationReport(
        timestamp=datetime.now().isoformat(),
        is_valid=False,
        validation_level="FULL",
        critical_issues=[issue],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.qt_real
def test_report_window_renders_clean_strategy(qtbot):
    """
    Happy path: ValidationReportWindow opens without raising for a zero-issue
    ValidationReport.  This is the baseline sanity gate.
    """
    window = ValidationReportWindow(report=_empty_report(), config=None)
    qtbot.addWidget(window)

    assert window.windowTitle() != "", "Window must have a non-empty title"


@pytest.mark.qt_real
def test_report_window_has_central_widget(qtbot):
    """QMainWindow must set a central widget (required for layout to work)."""
    window = ValidationReportWindow(report=_empty_report(), config=None)
    qtbot.addWidget(window)

    assert window.centralWidget() is not None, "centralWidget() must not be None"


@pytest.mark.qt_real
def test_report_window_contains_tab_widget(qtbot):
    """Report window must contain a QTabWidget with at least 3 tabs."""
    window = ValidationReportWindow(report=_empty_report(), config=None)
    qtbot.addWidget(window)

    tab = window.centralWidget().findChild(QTabWidget)
    assert tab is not None, "No QTabWidget found inside ValidationReportWindow"
    assert tab.count() >= 3, (
        f"Expected ≥3 tabs (Summary, Issues, Metrics), found {tab.count()}"
    )


@pytest.mark.qt_real
def test_report_window_warning_populates_issues_table(qtbot):
    """
    Happy path: A WARNING issue must produce at least one row in the Issues
    table so operators can see and act on validation findings.
    """
    window = ValidationReportWindow(report=_report_with_warning(), config=None)
    qtbot.addWidget(window)

    issues_table = window.centralWidget().findChild(QTableWidget)
    assert issues_table is not None, "Issues QTableWidget not found in report window"
    assert issues_table.rowCount() >= 1, (
        "Issues table should have ≥1 row when report contains a WARNING"
    )


@pytest.mark.qt_real
def test_report_window_error_sets_blocking_issue_count(qtbot):
    """
    Error path: ValidationReport.blocking_issues() reflects ERROR severity.
    The window must open without crashing even when the strategy is blocked.
    """
    report = _report_with_error()
    window = ValidationReportWindow(report=report, config=None)
    qtbot.addWidget(window)

    assert report.is_valid is False
    assert report.blocking_issues() == 1
    # Window must stay functional after rendering blocking issues
    assert window.centralWidget() is not None


@pytest.mark.qt_real
def test_report_window_critical_issue_opens_without_crash(qtbot):
    """
    Error path: CRITICAL issue (blocks live deployment) must not crash the
    window.  Operator must be able to read the report and act on it.
    """
    report = _report_with_critical()
    window = ValidationReportWindow(report=report, config=None)
    qtbot.addWidget(window)

    assert report.blocking_issues() == 1
    tab = window.centralWidget().findChild(QTabWidget)
    assert tab is not None


@pytest.mark.qt_real
def test_report_window_has_close_or_action_button(qtbot):
    """Report window must expose a Close/Done button in the footer."""
    window = ValidationReportWindow(report=_empty_report(), config=None)
    qtbot.addWidget(window)

    buttons = window.centralWidget().findChildren(QPushButton)
    button_texts = [b.text().lower() for b in buttons]
    has_close = any(
        kw in t for t in button_texts for kw in ("close", "done", "cancel", "ok")
    )
    assert has_close, (
        f"No close/done/cancel/ok button found; available: {button_texts}"
    )

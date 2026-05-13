"""
Regression tests for BTCAAAAA-2118: wire ValidationDialog into step 1 as modal
for Generate Code access.

Issue: BTCAAAAA-2118
Fixed in commit: fff30a1d
Component: src/strategy_builder/ui/strategy_builder_main_window.py

Root cause: Step 1 Validate handler opened ValidationReportWindow + non-modal
ValidationDialog, but the "Generate Nautilus Code" button in ValidationPanel
was unreachable because ValidationReportWindow obscured it.

Fix: Replace with a single modal ValidationDialog that wraps ValidationPanel.
- ValidationDialog auto-validates on open, enables Generate Code on pass
- Save and Run Backtest signals connected to main window handlers
- Stepper updated from last_validation_result after dialog closes
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-2118"),
    pytest.mark.regression,
]


class MockValidationResult:
    """Minimal stand-in for a validation result object."""
    def __init__(self, success: bool = True):
        self.success = success
        self.warnings = []
        self.validation_errors = []
        self.errors = []


class MockConfig:
    """Minimal stand-in for a config with validation_status attr."""
    def __init__(self):
        self.validation_status = None
        self.blocks = []
        self.exit_conditions = None


class MockConfigEngine:
    def __init__(self):
        self.config = MockConfig()


class MockOrchestrator:
    def __init__(self):
        self.config_engine = MockConfigEngine()


def _make_window(**overrides):
    """Build a minimal MagicMock window with required attributes for step 1."""
    window = MagicMock()
    window._check_validation_prerequisites.return_value = True
    window.validation_dialog = None
    window.orchestrator = MockOrchestrator()
    window.validation_passed = False
    for k, v in overrides.items():
        setattr(window, k, v)
    return window


class TestStep1HandlerPrerequisitesGate:
    """_on_step_clicked(1) must gate on prerequisites."""

    def test_returns_when_prerequisites_fail(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = MagicMock()
        window._check_validation_prerequisites.return_value = False

        StrategyBuilderMainWindow._on_step_clicked(window, 1)

        window._check_validation_prerequisites.assert_called_once()
        window.stepper.set_current_step.assert_not_called()

    def test_sets_step_when_prerequisites_pass(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        window.stepper.set_current_step.assert_called_once_with(1)


class TestStep1HandlerDialogAlreadyVisible:
    """When a ValidationDialog is already shown, raise it and return early."""

    def test_raises_existing_dialog(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        existing_dialog = MagicMock()
        existing_dialog.isVisible.return_value = True
        window = _make_window(validation_dialog=existing_dialog)

        StrategyBuilderMainWindow._on_step_clicked(window, 1)

        existing_dialog.raise_.assert_called_once()
        existing_dialog.activateWindow.assert_called_once()

    def test_skips_new_dialog_when_already_visible(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        existing_dialog = MagicMock()
        existing_dialog.isVisible.return_value = True
        window = _make_window(validation_dialog=existing_dialog)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_cls:
            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        mock_cls.assert_not_called()


class TestStep1HandlerDialogCreation:
    """A new ValidationDialog is created with correct args and signal wiring."""

    def test_creates_dialog_with_orchestrator_and_parent(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        mock_dialog_cls.assert_called_once_with(window.orchestrator, window)

    def test_stores_dialog_reference(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        assert window.validation_dialog is dialog_instance

    def test_destroyed_signal_clears_reference(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

            destroyed_conn = dialog_instance.destroyed.connect
            destroyed_conn.assert_called_once()

            handler = destroyed_conn.call_args[0][0]
            handler()

        assert window.validation_dialog is None

    def test_wires_save_requested_signal(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        dialog_instance.validation_panel.save_requested.connect.assert_called_once_with(
            window._on_save_strategy
        )

    def test_wires_run_test_requested_signal(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        dialog_instance.validation_panel.run_test_requested.connect.assert_called_once_with(
            window._on_run_backtest
        )

    def test_calls_exec_on_dialog(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        dialog_instance.exec_.assert_called_once()


class TestStep1HandlerSuccessPath:
    """Post-dialog behavior when validation passes."""

    def test_validation_passed_flag_set(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window(validation_passed=False)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        assert window.validation_passed is True

    def test_marks_step_complete_on_success(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        window.stepper.mark_step_complete.assert_called_once_with(1)

    def test_saves_pass_to_db_on_success(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        window._save_validation_status_to_db.assert_called_once_with('Pass')

    def test_updates_config_validation_status_on_success(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        config = MockConfig()
        engine = MockConfigEngine()
        engine.config = config
        window = _make_window()
        window.orchestrator = MagicMock()
        window.orchestrator.config_engine = engine

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        assert config.validation_status == 'passed'

    def test_updates_status_message_on_success(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        window._update_status.assert_called_with('Strategy validated successfully')


class TestStep1HandlerFailurePath:
    """Post-dialog behavior when validation fails."""

    def test_validation_failed_flag_cleared(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window(validation_passed=True)

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=False)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        assert window.validation_passed is False

    def test_marks_step_error_on_failure(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=False)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        window.stepper.mark_step_error.assert_called_once_with(1)

    def test_saves_fail_to_db_on_failure(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            mock_panel = MagicMock()
            mock_panel.last_validation_result = MockValidationResult(success=False)
            dialog_instance.validation_panel = mock_panel
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        window._save_validation_status_to_db.assert_called_once_with('Fail')

    def test_clears_config_validation_status_on_failure(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        config = MockConfig()
        config.validation_status = 'passed'
        engine = MockConfigEngine()
        engine.config = config
        window = _make_window()
        window.orchestrator = MagicMock()
        window.orchestrator.config_engine = engine

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            mock_panel = MagicMock()
            mock_panel.last_validation_result = MockValidationResult(success=False)
            dialog_instance.validation_panel = mock_panel
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        assert not hasattr(config, 'validation_status')

    def test_updates_status_message_on_failure(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            mock_panel = MagicMock()
            mock_panel.last_validation_result = MockValidationResult(success=False)
            dialog_instance.validation_panel = mock_panel
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        window._update_status.assert_called_with('Strategy validation failed')


class TestStep1HandlerExceptionPath:
    """Exception during post-dialog processing must not crash."""

    def test_marks_step_error_on_exception(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window()
        window._save_validation_status_to_db.side_effect = RuntimeError("DB error")

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        window.stepper.mark_step_error.assert_called_once_with(1)

    def test_clears_validation_passed_on_exception(self):
        from src.strategy_builder.ui.strategy_builder_main_window import (
            StrategyBuilderMainWindow,
        )
        window = _make_window(validation_passed=True)
        window._save_validation_status_to_db.side_effect = RuntimeError("DB error")

        with patch(
            "src.strategy_builder.ui.strategy_builder_main_window.ValidationDialog"
        ) as mock_dialog_cls:
            dialog_instance = MagicMock()
            dialog_instance.validation_panel = MagicMock()
            dialog_instance.validation_panel.last_validation_result = (
                MockValidationResult(success=True)
            )
            mock_dialog_cls.return_value = dialog_instance

            StrategyBuilderMainWindow._on_step_clicked(window, 1)

        assert window.validation_passed is False

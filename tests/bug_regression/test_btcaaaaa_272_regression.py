"""
Regression tests for BTCAAAAA-272: Rename Automated Trainer to Calibrate + UX improvements.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-272

This test suite verifies:
  1. TrainingPanelUI imports and constructs without error
  2. Panel header uses "Signal Calibration" title (not "Automated Trainer")
  3. Group box titles use "Calibration" naming convention
  4. Button labels use "Calibration" instead of "Training"
  5. Timeframe selection uses QCheckBox controls (post-BTCAAAAA-338 design)
  6. No hardcoded hex color strings or QFont() in UI setup paths
  7. Tooltips present on key controls (mode, lookback, timeframe, start)
  8. Styles imported from centralized styles module (create_font, get_color)
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-272"),
    pytest.mark.regression,
]


@pytest.fixture
def panel(qapp):
    """Return a TrainingPanelUI instance with mocked orchestrator."""
    with (
        patch("src.optimizer_v3.ui.training_panel.calibration_cache") as mock_cache,
        patch("src.optimizer_v3.ui.training_panel.get_training_config") as mock_config,
    ):
        mock_cache.load_cache.return_value = (None, None)
        mock_config.return_value = {
            "training": {"max_lookback": 180},
            "other": {},
        }
        from src.optimizer_v3.ui.training_panel import TrainingPanelUI

        orchestrator = MagicMock()
        orchestrator.get_current_config.return_value = None
        inst = TrainingPanelUI(orchestrator=orchestrator)
        return inst


class TestTrainingPanelUIConstruction:
    """TrainingPanelUI must import and construct without error."""

    def test_module_imports(self):
        from src.optimizer_v3.ui.training_panel import TrainingPanelUI

        assert TrainingPanelUI is not None

    def test_constructs_with_orchestrator(self, panel):
        assert panel is not None
        assert panel.orchestrator is not None

    def test_constructs_without_orchestrator(self):
        with (
            patch("src.optimizer_v3.ui.training_panel.calibration_cache") as mock_cache,
            patch("src.optimizer_v3.ui.training_panel.get_training_config") as mock_config,
        ):
            mock_cache.load_cache.return_value = (None, None)
            mock_config.return_value = {"training": {"max_lookback": 180}}
            from src.optimizer_v3.ui.training_panel import TrainingPanelUI

            inst = TrainingPanelUI()
            assert inst is not None

    def test_default_mode_is_testing(self, panel):
        assert panel.mode_combo.currentIndex() == 0
        assert "Testing" in panel.mode_combo.currentText()

    def test_default_period_days(self, panel):
        assert panel.period_spin.value() == 180


class TestHeaderNaming:
    """Header must use 'Calibration' naming (not 'Training' / 'Automated Trainer')."""

    def test_header_title_uses_calibration(self, panel):
        from PyQt5.QtWidgets import QLabel

        title = panel.findChild(QLabel, "")
        assert title is not None
        text = title.text()
        assert "Calibration" in text
        assert "Automated" not in text
        assert "Trainer" not in text


class TestGroupBoxNaming:
    """Group box titles must use 'Calibration' naming convention."""

    def test_config_group_box_title(self, panel):
        from PyQt5.QtWidgets import QGroupBox

        groups = panel.findChildren(QGroupBox)
        titles = [g.title() for g in groups]
        assert any("Calibration" in t for t in titles)
        assert not any("Training" in t for t in titles), (
            "Group box titles should not contain 'Training'"
        )


class TestButtonLabels:
    """Button labels must use 'Calibration' naming."""

    def test_start_button_label(self, panel):
        assert "Calibration" in panel.start_btn.text()
        assert "Training" not in panel.start_btn.text()

    def test_stop_button_label(self, panel):
        assert "Calibration" in panel.stop_btn.text()
        assert "Training" not in panel.stop_btn.text()

    def test_export_button_label(self, panel):
        assert "Calibration" in panel.export_btn.text()
        assert "Training" not in panel.export_btn.text()

    def test_export_button_disabled_initially(self, panel):
        assert panel.export_btn.isEnabled() is False


class TestTimeframeSelection:
    """Timeframe selection uses QCheckBox controls with 15m default checked."""

    def test_timeframe_checkboxes_exist(self, panel):
        assert len(panel.timeframe_checkboxes) > 0

    def test_expected_timeframes_present(self, panel):
        expected = {"5m", "15m", "1h", "4h"}
        assert set(panel.timeframe_checkboxes.keys()) == expected

    def test_fifteen_minute_checked_by_default(self, panel):
        assert panel.timeframe_checkboxes["15m"].isChecked() is True

    def test_other_timeframes_unchecked_by_default(self, panel):
        for tf in ("5m", "1h", "4h"):
            assert panel.timeframe_checkboxes[tf].isChecked() is False

    def test_get_selected_timeframes_returns_checked(self, panel):
        selected = panel._get_selected_timeframes()
        assert selected == ["15m"]

    def test_timeframe_checkboxes_have_tooltips(self, panel):
        for tf, cb in panel.timeframe_checkboxes.items():
            assert cb.toolTip(), f"Checkbox for {tf} is missing tooltip"


class TestTooltips:
    """Key controls must have tooltips (added by BTCAAAAA-272)."""

    def test_mode_combo_has_tooltip(self, panel):
        assert panel.mode_combo.toolTip(), "Mode combo is missing tooltip"

    def test_period_spin_has_tooltip(self, panel):
        assert panel.period_spin.toolTip(), "Period spin is missing tooltip"

    def test_start_button_has_tooltip(self, panel):
        assert panel.start_btn.toolTip(), "Start button is missing tooltip"


class TestStyleCompliance:
    """UI must not use hardcoded hex colors or QFont() -- uses centralized styles."""

    def test_no_hardcoded_hex_colors_in_source(self):
        from src.optimizer_v3.ui.training_panel import TrainingPanelUI

        source_file = inspect.getfile(TrainingPanelUI)
        source = Path(source_file).read_text(encoding="utf-8")
        hardcoded_hex = re.findall(r'#[0-9A-Fa-f]{6}', source)
        assert len(hardcoded_hex) == 0, (
            f"Found {len(hardcoded_hex)} hardcoded hex colors: {hardcoded_hex[:5]}"
        )

    def test_no_qfont_in_ui_setup(self):
        from src.optimizer_v3.ui.training_panel import TrainingPanelUI

        source_file = inspect.getfile(TrainingPanelUI)
        source = Path(source_file).read_text(encoding="utf-8")
        assert "QFont(" not in source, "Source must not use QFont() directly"

    def test_create_font_used(self):
        from src.optimizer_v3.ui.training_panel import TrainingPanelUI

        source_file = inspect.getfile(TrainingPanelUI)
        source = Path(source_file).read_text(encoding="utf-8")
        assert "create_font(" in source, "Source must use create_font() from styles"

    def test_get_color_used_in_stylesheets(self):
        from src.optimizer_v3.ui.training_panel import TrainingPanelUI

        source_file = inspect.getfile(TrainingPanelUI)
        source = Path(source_file).read_text(encoding="utf-8")
        assert "get_color(" in source, "Source must use get_color() from styles"

"""
Regression tests for BTCAAAAA-354: AI Recommendations Panel — P4 regression
that hid the Request Preview by default.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-354
Component: src/optimizer_v3/ui/ai_recommendations_panel.py

Root cause: Commit 692bf00 changed the following in
AIRecommendationsPanel.__init__:

  1. preview_container.setVisible(False) — hid the Request Preview by default
  2. Button label "Show Request Preview" — implied collapsed state
  3. Comment: "Hidden by default" / "collapsed by default"

The fix (BTCAAAAA-355, commits e8a60286 / 132be884) reverted to:

  1. preview_container.setVisible(True) — visible by default
  2. Button label "Hide Request Preview" — matches expanded state
  3. Comment: "Visible by default" / "collapsible, visible by default"

This file validates source-level contracts that prevent the P4 regression from
reoccurring.  All 5 original preview sections and the _toggle_request_preview
method must remain intact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-354"),
    pytest.mark.regression,
]

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src" / "optimizer_v3" / "ui" / "ai_recommendations_panel.py"
SOURCE_TEXT = SOURCE.read_text()


# ============================================================================
# Request Preview visibility — must be visible by default
# ============================================================================


class TestPreviewContainerVisibleByDefault:
    """BTCAAAAA-354: preview_container must be visible by default."""

    def test_setVisible_true_not_false(self):
        """setVisible(True) must appear for preview_container, not False."""
        assert "self.preview_container.setVisible(True)" in SOURCE_TEXT, (
            "preview_container.setVisible must be True by default"
        )
        assert "self.preview_container.setVisible(False)" not in SOURCE_TEXT, (
            "preview_container.setVisible must NOT be False — that was the P4 regression"
        )

    def test_no_stale_p4_comment(self):
        """The setVisible(True) line has comment '# Visible by default'."""
        lines = SOURCE_TEXT.split("\n")
        found = False
        for line in lines:
            if "self.preview_container.setVisible(True)" in line:
                assert "Hidden by default" not in line, (
                    "P4 'Hidden by default' comment must not exist on preview_container line"
                )
                assert "Visible by default" in line, (
                    "Comment must state 'Visible by default' on preview_container line"
                )
                found = True
        assert found, "self.preview_container.setVisible(True) must exist in source"

    def test_visible_by_default_in_comment_block(self):
        """Comment for the section says 'visible by default'."""
        assert "# Visible by default" in SOURCE_TEXT, (
            "Source must contain '# Visible by default'"
        )

    def test_collapsible_comment_correct(self):
        """Section comment says 'visible by default', not 'collapsed by default'."""
        assert "collapsible, visible by default" in SOURCE_TEXT, (
            "Section comment must say 'collapsible, visible by default'"
        )
        assert "collapsed by default" not in SOURCE_TEXT, (
            "'collapsed by default' must not appear — that was the P4 regression"
        )


# ============================================================================
# Toggle button label — must say "Hide Request Preview" by default
# ============================================================================


class TestToggleButtonLabel:
    """BTCAAAAA-354: toggle button must say 'Hide Request Preview' by default,
    matching the expanded (visible-by-default) state."""

    def test_button_text_is_hide(self):
        """Button text in __init__ is 'Hide Request Preview'."""
        assert 'QPushButton("Hide Request Preview")' in SOURCE_TEXT, (
            "Button must say 'Hide Request Preview' to match visible-by-default state"
        )
        assert 'QPushButton("Show Request Preview")' not in SOURCE_TEXT, (
            "Button must NOT say 'Show Request Preview' — that was the P4 regression"
        )

    def test_button_assigned_to_correct_attribute(self):
        """preview_toggle_btn attribute holds the toggle QPushButton."""
        assert "self.preview_toggle_btn = QPushButton" in SOURCE_TEXT, (
            "preview_toggle_btn attribute must be assigned the toggle button"
        )

    def test_button_has_secondary_style(self):
        """Toggle button uses get_secondary_button_stylesheet()."""
        lines = SOURCE_TEXT.split("\n")
        in_toggle_btn = False
        found = False
        for line in lines:
            if "self.preview_toggle_btn" in line and "QPushButton" in line:
                in_toggle_btn = True
                continue
            if in_toggle_btn and "get_secondary_button_stylesheet" in line:
                found = True
                break
        assert found, (
            "preview_toggle_btn must use get_secondary_button_stylesheet()"
        )


# ============================================================================
# _toggle_request_preview method — must toggle visibility + button label
# ============================================================================


class TestToggleRequestPreviewMethod:
    """BTCAAAAA-354: _toggle_request_preview must correctly toggle visibility
    and keep the button label synchronized with the container state."""

    def test_method_defined(self):
        """_toggle_request_preview method must exist."""
        assert "def _toggle_request_preview" in SOURCE_TEXT, (
            "_toggle_request_preview method must be defined"
        )

    def test_method_connected_to_button(self):
        """Toggle button click connects to _toggle_request_preview."""
        assert (
            "self.preview_toggle_btn.clicked.connect(self._toggle_request_preview)"
            in SOURCE_TEXT
        ), (
            "preview_toggle_btn.clicked must connect to _toggle_request_preview"
        )

    def test_uses_isVisible_for_toggle(self):
        """_toggle_request_preview checks preview_container.isVisible()."""
        lines = SOURCE_TEXT.split("\n")
        in_method = False
        found = False
        for line in lines:
            if "def _toggle_request_preview" in line:
                in_method = True
                continue
            if in_method and "self.preview_container.isVisible()" in line:
                found = True
                break
            if in_method and line.strip().startswith("def "):
                break
        assert found, (
            "Must use self.preview_container.isVisible() to determine current state"
        )

    def test_sets_button_to_show_when_hiding(self):
        """When visible→hidden: setText('Show Request Preview')."""
        lines = SOURCE_TEXT.split("\n")
        in_method = False
        found = False
        for line in lines:
            if "def _toggle_request_preview" in line:
                in_method = True
                continue
            if in_method and line.strip().startswith("def "):
                break
            if in_method and '"Show Request Preview"' in line:
                found = True
                break
        assert found, (
            "setText('Show Request Preview') must exist in _toggle_request_preview"
        )

    def test_sets_button_to_hide_when_showing(self):
        """When hidden→visible: setText('Hide Request Preview')."""
        lines = SOURCE_TEXT.split("\n")
        in_method = False
        found_hide = False
        for line in lines:
            if "def _toggle_request_preview" in line:
                in_method = True
                continue
            if in_method and line.strip().startswith("def "):
                break
            if in_method and '"Hide Request Preview"' in line:
                found_hide = True
                break
        assert found_hide, (
            "setText('Hide Request Preview') must exist in _toggle_request_preview"
        )

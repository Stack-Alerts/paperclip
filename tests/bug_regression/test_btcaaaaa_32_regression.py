"""
Regression tests for BTCAAAAA-32: DataVerifyDialog table auto-size to show
all 3 rows without scrolling.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-32
Fixed in commit: b3407a85
Component: src/strategy_builder/ui/data_verify_dialog.py

Root cause: The results table in DataVerifyDialog had a static
setMinimumHeight(200) and never grew to fit its row content after
_populate_table() inserted rows, forcing the user to scroll to see all three
timeframes (15m, 1h, 1d).

Fix: After resizeRowsToContents(), compute total row height + header height
and call setMinimumHeight() so the table fits its content exactly while still
allowing the layout to distribute extra vertical space on window resize.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-32"),
    pytest.mark.regression,
]

SOURCE = Path(__file__).resolve().parents[2] / "src" / "strategy_builder" / "ui" / "data_verify_dialog.py"
SOURCE_TEXT = SOURCE.read_text()


class TestAutoSizeRows:
    """Verify the auto-sizing fix in DataVerifyDialog._populate_table."""

    def test_resize_rows_to_contents_called(self):
        assert "resizeRowsToContents()" in SOURCE_TEXT, (
            "_populate_table must call resizeRowsToContents() after inserting rows"
        )

    def test_row_height_computed(self):
        assert "rowHeight" in SOURCE_TEXT, (
            "Must compute total row height after population via rowHeight()"
        )

    def test_header_height_added(self):
        assert "horizontalHeader().height()" in SOURCE_TEXT, (
            "Must include header height in the minimum-height calculation"
        )

    def test_set_minimum_height_dynamic(self):
        assert "setMinimumHeight(total_row_height + header_height" in SOURCE_TEXT, (
            "setMinimumHeight must use computed total_row_height + header_height"
        )

    def test_viewport_update_called(self):
        assert "viewport().update()" in SOURCE_TEXT, (
            "Must call viewport().update() to force Qt repaint after row insertion"
        )

    def test_dynamic_sizing_overrides_static(self):
        has_static = "self._table.setMinimumHeight(200)" in SOURCE_TEXT
        has_dynamic = "setMinimumHeight(total_row_height + header_height" in SOURCE_TEXT
        assert not has_static or has_dynamic, (
            "If static 200px minimum still exists, dynamic auto-sizing must also exist"
        )


class TestPopulateTableSignature:
    """Verify _populate_table exists on DataVerifyDialog."""

    def test_populate_table_method_exists(self):
        assert "def _populate_table" in SOURCE_TEXT, (
            "DataVerifyDialog must have _populate_table method"
        )

    def test_populate_table_accepts_report_dict(self):
        assert "def _populate_table(self, report" in SOURCE_TEXT, (
            "_populate_table must accept report parameter"
        )

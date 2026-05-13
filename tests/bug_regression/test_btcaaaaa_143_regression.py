"""
Regression tests for BTCAAAAA-143: Sequence data-update modal BEFORE auto-update
system at startup to eliminate race condition on parquet file writes.

Issue: BTCAAAAA-143
Component: src/strategy_builder/ui/strategy_builder_main_window.py

Root cause: _start_auto_update_system() was started via QTimer at t+1500ms while
_show_data_update_modal() started at t+2000ms. Since auto-update is non-blocking,
both threads could write the same parquet file concurrently and the stale bar
would win.

Fix:
  1. Collapse two timers into one: QTimer.singleShot(2000, self._on_app_start)
  2. _on_app_start() calls _show_data_update_modal() first (exec_() blocks),
     then _start_auto_update_system() only after modal completes.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-143"),
    pytest.mark.regression,
]

MAIN_PATH = pathlib.Path(
    "src/strategy_builder/ui/strategy_builder_main_window.py"
)


class TestOnAppStartSequencing:
    """Validate that _on_app_start sequences modal before auto-update."""

    ON_APP_START = "_on_app_start"

    def _get_method_lines(self) -> list[str]:
        source = MAIN_PATH.read_text()
        tree = ast.parse(source, str(MAIN_PATH))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.ON_APP_START:
                srclines = source.splitlines()
                return srclines[node.lineno - 1 : node.end_lineno]
        pytest.fail(f"{self.ON_APP_START} method not found in {MAIN_PATH}")

    def test_on_app_start_method_exists(self):
        """_on_app_start method must exist."""
        source = MAIN_PATH.read_text()
        tree = ast.parse(source, str(MAIN_PATH))
        method_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        assert self.ON_APP_START in method_names, (
            f"{self.ON_APP_START} method not found in {MAIN_PATH}"
        )

    def test_calls_show_data_update_modal_first(self):
        """_on_app_start must call _show_data_update_modal()."""
        body = self._get_method_lines()
        body_text = "\n".join(body)
        assert "self._show_data_update_modal()" in body_text, (
            "_on_app_start must call self._show_data_update_modal()"
        )

    def test_calls_start_auto_update_system_after_modal(self):
        """_on_app_start must call _start_auto_update_system()."""
        body = self._get_method_lines()
        body_text = "\n".join(body)
        assert "self._start_auto_update_system()" in body_text, (
            "_on_app_start must call self._start_auto_update_system()"
        )

    def test_modal_before_auto_update_order(self):
        """_show_data_update_modal() must appear BEFORE _start_auto_update_system()."""
        body = self._get_method_lines()

        modal_line = None
        auto_update_line = None
        for i, line in enumerate(body):
            stripped = line.strip()
            if "self._show_data_update_modal()" in stripped:
                modal_line = i
            if "self._start_auto_update_system()" in stripped:
                auto_update_line = i

        assert modal_line is not None, "_show_data_update_modal() not found"
        assert auto_update_line is not None, "_start_auto_update_system() not found"
        assert modal_line < auto_update_line, (
            "_show_data_update_modal() must appear BEFORE _start_auto_update_system() "
            f"(modal at line offset {modal_line}, auto-update at {auto_update_line})"
        )


class TestNoOldTimerPattern:
    """Validate the old two-timer race pattern has been removed."""

    def test_no_old_auto_update_timer_before_modal(self):
        """Old pattern: _start_auto_update_system must NOT be called via timer before modal."""
        source = MAIN_PATH.read_text()
        tree = ast.parse(source, str(MAIN_PATH))
        srclines = source.splitlines()

        timer_calls_before_startup = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node.func, "attr"):
                if node.func.attr == "singleShot" and hasattr(node, "args"):
                    for arg in node.args:
                        if isinstance(arg, ast.Call) and hasattr(arg.func, "attr"):
                            if arg.func.attr == "_start_auto_update_system":
                                timer_calls_before_startup.append(
                                    srclines[node.lineno - 1]
                                )

        found_outside_on_app_start = False
        for line in timer_calls_before_startup:
            if "_on_app_start" not in line:
                found_outside_on_app_start = True

        assert not found_outside_on_app_start, (
            "Old race pattern detected: _start_auto_update_system is still called "
            "via QTimer.singleShot outside of _on_app_start"
        )


class TestReferenceComments:
    """Validate the BTCAAAAA-143 reference comment exists."""

    def test_btcaaaaa_143_comment_in_source(self):
        """The BTCAAAAA-143 reference comment must exist."""
        source = MAIN_PATH.read_text()
        assert "BTCAAAAA-143" in source, (
            "BTCAAAAA-143 reference comment must exist in strategy_builder_main_window.py"
        )

    def test_startup_sequencing_comment_exists(self):
        """The startup sequencing explanation comment must exist."""
        source = MAIN_PATH.read_text()
        assert "RC2 FIX" in source or "Sequence modal BEFORE auto-update" in source, (
            "The RC2 FIX startup sequencing comment must exist in the source"
        )

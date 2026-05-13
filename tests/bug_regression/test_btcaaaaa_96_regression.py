"""
Regression tests for BTCAAAAA-96: Extend runtime auto-update to cover 15m AND 1h timeframes.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-96
Component: src/strategy_builder/ui/strategy_builder_main_window.py

Root cause: The _check_and_update_data loop only ever downloaded 15m klines
and saved them via an ad-hoc path that bypassed UnifiedDataManager entirely.
1h (and any future) timeframe was never written to disk during runtime,
causing fresh gaps on every restart.

Fix:
- Add _RuntimeCandleUpdateThread (QThread) that calls
  UnifiedDataManager.verify_and_repair(timeframes=['15m','1h']) with a
  2-hour lookback, covering all managed timeframes in one pass.
- Replace the blocking, 15m-only klines download block in
  _check_and_update_data with a non-blocking thread launch + finished slot.
- Add _on_runtime_update_finished slot: updates status bar, handles
  quick-retry guard on failure (same semantics as before).
- Guard against overlapping cycles: skip launch if previous thread is
  still running.
- Add QThread, pyqtSignal to PyQt5.QtCore imports.
- Track _runtime_update_thread instance on the window for lifecycle control.
"""

from __future__ import annotations

import ast
import pathlib
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-96"),
    pytest.mark.regression,
]

SOURCE_PATH = pathlib.Path("src/strategy_builder/ui/strategy_builder_main_window.py")


# ---------------------------------------------------------------------------
# Source-level checks -- _RuntimeCandleUpdateThread class
# ---------------------------------------------------------------------------


class TestRuntimeCandleUpdateThreadClass:
    """The _RuntimeCandleUpdateThread class must exist and be well-formed."""

    def test_class_exists(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        found = any(
            isinstance(node, ast.ClassDef)
            and node.name == "_RuntimeCandleUpdateThread"
            for node in ast.walk(tree)
        )
        assert found, (
            "_RuntimeCandleUpdateThread class not found in "
            "strategy_builder_main_window.py (BTCAAAAA-96)."
        )

    def test_inherits_from_qthread(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "_RuntimeCandleUpdateThread":
                bases = [b.id if isinstance(b, ast.Name) else None for b in node.bases]
                assert "QThread" in bases, (
                    "_RuntimeCandleUpdateThread must inherit from QThread (BTCAAAAA-96)."
                )
                return
        pytest.fail("_RuntimeCandleUpdateThread class not found (BTCAAAAA-96).")

    def test_has_finished_signal(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "_RuntimeCandleUpdateThread":
                body_source = ast.get_source_segment(source, node) or ""
                assert "finished = pyqtSignal(bool, str)" in body_source, (
                    "_RuntimeCandleUpdateThread must define "
                    "finished = pyqtSignal(bool, str) (BTCAAAAA-96)."
                )
                return
        pytest.fail("_RuntimeCandleUpdateThread class not found (BTCAAAAA-96).")

    def test_has_run_method(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "_RuntimeCandleUpdateThread":
                run_fn = next(
                    (m for m in node.body if isinstance(m, ast.FunctionDef) and m.name == "run"),
                    None,
                )
                assert run_fn is not None, (
                    "_RuntimeCandleUpdateThread must define a run() method (BTCAAAAA-96)."
                )
                return
        pytest.fail("_RuntimeCandleUpdateThread class not found (BTCAAAAA-96).")

    def test_run_calls_verify_and_repair_with_both_timeframes(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "_RuntimeCandleUpdateThread":
                run_fn = next(
                    (m for m in node.body if isinstance(m, ast.FunctionDef) and m.name == "run"),
                    None,
                )
                assert run_fn is not None, "run() method not found"
                run_source = ast.get_source_segment(source, run_fn) or ""
                assert "verify_and_repair" in run_source, (
                    "run() must call UnifiedDataManager.verify_and_repair() (BTCAAAAA-96)."
                )
                assert "'15m'" in run_source, (
                    "verify_and_repair must be called with timeframes containing '15m' (BTCAAAAA-96)."
                )
                assert "'1h'" in run_source, (
                    "verify_and_repair must be called with timeframes containing '1h' (BTCAAAAA-96)."
                )
                return
        pytest.fail("_RuntimeCandleUpdateThread class not found (BTCAAAAA-96).")

    def test_run_timeout_guard_exists(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "_RuntimeCandleUpdateThread":
                body_source = ast.get_source_segment(source, node) or ""
                assert "TIMEOUT_SECONDS" in body_source, (
                    "_RuntimeCandleUpdateThread must define TIMEOUT_SECONDS guard (BTCAAAAA-96)."
                )
                return
        pytest.fail("_RuntimeCandleUpdateThread class not found (BTCAAAAA-96).")


# ---------------------------------------------------------------------------
# Source-level checks -- _check_and_update_data method
# ---------------------------------------------------------------------------


class TestCheckAndUpdateDataMethod:
    """_check_and_update_data must use _RuntimeCandleUpdateThread."""

    def test_creates_runtime_update_thread(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_and_update_data":
                body_source = ast.get_source_segment(source, node) or ""
                assert "_RuntimeCandleUpdateThread(" in body_source, (
                    "_check_and_update_data must create a _RuntimeCandleUpdateThread "
                    "instance (BTCAAAAA-96)."
                )
                assert "session_start_time" in body_source, (
                    "Must pass session_start_time to _RuntimeCandleUpdateThread (BTCAAAAA-96)."
                )
                return
        pytest.fail("_check_and_update_data method not found (BTCAAAAA-96).")

    def test_has_overlap_guard(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_and_update_data":
                body_source = ast.get_source_segment(source, node) or ""
                assert "isRunning()" in body_source, (
                    "_check_and_update_data must have an overlap guard using "
                    "isRunning() (BTCAAAAA-96)."
                )
                return
        pytest.fail("_check_and_update_data method not found (BTCAAAAA-96).")

    def test_connects_finished_signal(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_and_update_data":
                body_source = ast.get_source_segment(source, node) or ""
                assert "finished.connect" in body_source, (
                    "_check_and_update_data must connect the thread's "
                    "finished signal to a slot (BTCAAAAA-96)."
                )
                assert "_on_runtime_update_finished" in body_source, (
                    "Finished signal must connect to _on_runtime_update_finished (BTCAAAAA-96)."
                )
                return
        pytest.fail("_check_and_update_data method not found (BTCAAAAA-96).")


# ---------------------------------------------------------------------------
# Source-level checks -- _on_runtime_update_finished slot
# ---------------------------------------------------------------------------


class TestOnRuntimeUpdateFinished:
    """_on_runtime_update_finished must handle success and failure."""

    def test_slot_exists(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        found = any(
            isinstance(node, ast.FunctionDef)
            and node.name == "_on_runtime_update_finished"
            for node in ast.walk(tree)
        )
        assert found, (
            "_on_runtime_update_finished slot not found (BTCAAAAA-96)."
        )

    def test_slot_accepts_success_and_message(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_on_runtime_update_finished":
                arg_names = [a.arg for a in node.args.args]
                assert "success" in arg_names, (
                    "Slot must accept 'success' parameter (BTCAAAAA-96)."
                )
                assert "message" in arg_names, (
                    "Slot must accept 'message' parameter (BTCAAAAA-96)."
                )
                return
        pytest.fail("_on_runtime_update_finished not found (BTCAAAAA-96).")

    def test_slot_updates_status_bar_on_success(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_on_runtime_update_finished":
                body_source = ast.get_source_segment(source, node) or ""
                assert "last_update_time" in body_source, (
                    "Slot must update last_update_time on success (BTCAAAAA-96)."
                )
                assert "_update_status(" in body_source, (
                    "Slot must update the status bar (BTCAAAAA-96)."
                )
                return
        pytest.fail("_on_runtime_update_finished not found (BTCAAAAA-96).")

    def test_slot_handles_quick_retry_on_failure(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_on_runtime_update_finished":
                body_source = ast.get_source_segment(source, node) or ""
                assert "_in_quick_retry" in body_source, (
                    "Slot must use _in_quick_retry guard (BTCAAAAA-96)."
                )
                assert "singleShot" in body_source, (
                    "Slot must schedule a quick retry via QTimer.singleShot (BTCAAAAA-96)."
                )
                return
        pytest.fail("_on_runtime_update_finished not found (BTCAAAAA-96).")


# ---------------------------------------------------------------------------
# Source-level checks -- QThread and pyqtSignal imports
# ---------------------------------------------------------------------------


class TestImports:
    """QThread and pyqtSignal must be imported from PyQt5.QtCore."""

    def test_qthread_imported(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        import_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "PyQt5.QtCore":
                names = [a.name for a in node.names]
                if "QThread" in names:
                    import_found = True
                    break
        assert import_found, (
            "QThread must be imported from PyQt5.QtCore (BTCAAAAA-96)."
        )

    def test_pyqtsignal_imported(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        import_found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "PyQt5.QtCore":
                names = [a.name for a in node.names]
                if "pyqtSignal" in names:
                    import_found = True
                    break
        assert import_found, (
            "pyqtSignal must be imported from PyQt5.QtCore (BTCAAAAA-96)."
        )


# ---------------------------------------------------------------------------
# Runtime-level checks -- instance tracking
# ---------------------------------------------------------------------------


class TestRuntimeUpdateInstanceTracking:
    """_runtime_update_thread instance tracking."""

    def test_instance_variable_exists(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "StrategyBuilderMainWindow":
                init_fn = next(
                    (m for m in node.body if isinstance(m, ast.FunctionDef) and m.name == "__init__"),
                    None,
                )
                assert init_fn is not None, "__init__ not found"
                init_source = ast.get_source_segment(source, init_fn) or ""
                assert "_runtime_update_thread" in init_source, (
                    "__init__ must declare _runtime_update_thread instance variable (BTCAAAAA-96)."
                )
                return
        pytest.fail("StrategyBuilderMainWindow class not found (BTCAAAAA-96).")

    def test_thread_assigned_and_started(self):
        source = SOURCE_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_check_and_update_data":
                body_source = ast.get_source_segment(source, node) or ""
                assert "self._runtime_update_thread = thread" in body_source, (
                    "_check_and_update_data must assign the thread to "
                    "self._runtime_update_thread (BTCAAAAA-96)."
                )
                assert "thread.start()" in body_source, (
                    "_check_and_update_data must call thread.start() (BTCAAAAA-96)."
                )
                return
        pytest.fail("_check_and_update_data not found (BTCAAAAA-96).")

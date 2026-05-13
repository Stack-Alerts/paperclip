"""
Regression tests for BTCAAAAA-1096 — TrainingPanel cache gate.

Bug: Manual TrainingPanel._execute_training had no caching layer. Each
calibration request unconditionally spawned a TrainingThread, even when
the same block set / timeframe / period / mode had already been calibrated
in the current session or persisted to disk.

Fix: src/optimizer_v3/ui/training_panel.py — _execute_training now computes a
fingerprint and checks it against `_calibration_fingerprint`. On cache hit a
dialog offers "Use Cached" (skip TrainingThread) or "Re-calibrate" (re-run and
update cache). Cross-pollination with BacktestConfigPanel is via the shared
`calibration_cache` disk store.

Acceptance criteria tested here:
  AC1  Dialog appears when cache fingerprint matches (cache hit).
  AC2  "Use cached" path: delay_map applied, TrainingThread NOT spawned.
  AC3  "Re-calibrate" path: TrainingThread spawned, shared cache updated.
  AC5  Different block-set: no dialog, TrainingThread runs normally.
"""

from __future__ import annotations

import hashlib
import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1096"),
    pytest.mark.regression,
]

from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def _make_fingerprint(block_names, timeframe="15m", period_days=180, mode="production"):
    payload = {
        "block_names": sorted(block_names),
        "timeframe": timeframe,
        "period_days": period_days,
        "mode": mode,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _make_training_stub():
    from src.optimizer_v3.ui.training_panel import TrainingPanelUI

    stub = MagicMock()
    stub.results_text = MagicMock()
    stub.status_label = MagicMock()
    stub.export_btn = MagicMock()
    stub.start_btn = MagicMock()
    stub.stop_btn = MagicMock()
    stub.progress_bar = MagicMock()
    stub.eta_label = MagicMock()
    stub.training_running = False
    stub.block_checkboxes = []
    stub.timeframe_checkboxes = {}
    stub.mode_combo = MagicMock()
    stub.period_spin = MagicMock()
    stub.training_thread = None

    stub._calibration_fingerprint = None
    stub._calibration_cache = None
    stub._calibration_cache_from_disk = False
    stub._pending_fingerprint = None

    stub._execute_training = types.MethodType(TrainingPanelUI._execute_training, stub)
    stub._on_training_complete = types.MethodType(TrainingPanelUI._on_training_complete, stub)
    stub._reset_ui_state = types.MethodType(TrainingPanelUI._reset_ui_state, stub)

    return stub


def _make_mock_thread():
    mt = MagicMock()
    mt.isRunning.return_value = False
    mt.is_simulation_mode = False
    return mt


# ---------------------------------------------------------------------------
# AC1 — Cache hit -> dialog appears
# ---------------------------------------------------------------------------

class TestAc1DialogOnCacheHit:
    """AC1: Cache hit -> 'Cached calibration results available' dialog shown."""

    def test_dialog_appears_on_cache_hit(self, qapp):
        """When fingerprint matches cached data, QMessageBox must be created."""
        stub = _make_training_stub()
        fp = _make_fingerprint(["Alpha", "Beta"])
        stub._calibration_fingerprint = fp
        stub._calibration_cache = {"Alpha": 3, "Beta": 5}
        stub._calibration_cache_from_disk = True

        dialog_created = []

        class DialogTracker(MagicMock):
            def __call__(self, *args, **kwargs):
                dialog_created.append(True)
                msg_box = MagicMock()
                msg_box.addButton.return_value = object()
                msg_box.exec_.return_value = None
                msg_box.clickedButton.return_value = object()
                return msg_box

        mock_qmb = DialogTracker()
        mock_qmb.AcceptRole = MagicMock()
        mock_qmb.DestructiveRole = MagicMock()

        config = {
            "blocks": ["Alpha", "Beta"],
            "timeframes": ["15m"],
            "period_days": 180,
            "mode": "production",
            "config": {},
        }

        with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb):
            stub._execute_training(config)

        assert dialog_created, "AC1: QMessageBox was NOT created on cache hit"

    def test_no_dialog_on_cache_miss(self, qapp):
        """When fingerprint does NOT match cache, no dialog should appear."""
        stub = _make_training_stub()
        fp = _make_fingerprint(["Alpha", "Beta"])
        stub._calibration_fingerprint = fp
        stub._calibration_cache = {"Alpha": 3}

        dialog_created = []

        class DialogTracker(MagicMock):
            def __call__(self, *args, **kwargs):
                dialog_created.append(True)
                msg_box = MagicMock()
                msg_box.addButton.return_value = object()
                msg_box.exec_.return_value = None
                msg_box.clickedButton.return_value = object()
                return msg_box

        mock_qmb = DialogTracker()
        mock_qmb.AcceptRole = MagicMock()
        mock_qmb.DestructiveRole = MagicMock()

        config = {
            "blocks": ["Gamma"],
            "timeframes": ["15m"],
            "period_days": 180,
            "mode": "production",
            "config": {},
        }

        mock_thread = _make_mock_thread()
        with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb), \
             patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_thread):
            stub._execute_training(config)

        assert not dialog_created, "AC1: Dialog appeared on cache miss - should NOT have"


# ---------------------------------------------------------------------------
# AC2 -- "Use cached" -> delay_map applied, TrainingThread NOT spawned
# ---------------------------------------------------------------------------

class TestAc2UseCachedPath:
    """AC2: 'Use cached' must skip TrainingThread and display cached delay_map."""

    def test_training_thread_not_started(self, qapp):
        """When user clicks 'Use Cached', TrainingThread.start() must NOT be called."""
        stub = _make_training_stub()
        fp = _make_fingerprint(["Alpha"])
        stub._calibration_fingerprint = fp
        stub._calibration_cache = {"Alpha": 7}
        stub._calibration_cache_from_disk = False

        use_btn = object()
        mock_msg_box = MagicMock()
        mock_msg_box.addButton.side_effect = lambda label, role: use_btn if "Use Cached" in str(label) else object()
        mock_msg_box.exec_.return_value = None
        mock_msg_box.clickedButton.return_value = use_btn
        mock_qmb = MagicMock(return_value=mock_msg_box)
        mock_qmb.AcceptRole = MagicMock()
        mock_qmb.DestructiveRole = MagicMock()

        config = {
            "blocks": ["Alpha"],
            "timeframes": ["15m"],
            "period_days": 180,
            "mode": "production",
            "config": {},
        }

        mock_thread = _make_mock_thread()
        with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb), \
             patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_thread):
            stub._execute_training(config)

        mock_thread.start.assert_not_called()

    def test_cached_delay_map_displayed(self, qapp):
        """results_text must show cached delay_map when using cached path."""
        stub = _make_training_stub()
        fp = _make_fingerprint(["Alpha"])
        stub._calibration_fingerprint = fp
        stub._calibration_cache = {"Alpha": 7}
        stub._calibration_cache_from_disk = False

        use_btn = object()
        mock_msg_box = MagicMock()
        mock_msg_box.addButton.side_effect = lambda label, role: use_btn if "Use Cached" in str(label) else object()
        mock_msg_box.exec_.return_value = None
        mock_msg_box.clickedButton.return_value = use_btn
        mock_qmb = MagicMock(return_value=mock_msg_box)
        mock_qmb.AcceptRole = MagicMock()
        mock_qmb.DestructiveRole = MagicMock()

        config = {
            "blocks": ["Alpha"],
            "timeframes": ["15m"],
            "period_days": 180,
            "mode": "production",
            "config": {},
        }

        with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb):
            stub._execute_training(config)

        call_text = stub.results_text.setPlainText.call_args[0][0]
        assert "Cached calibration results applied" in call_text, \
            f"Expected cached result message, got: {call_text!r}"


# ---------------------------------------------------------------------------
# AC3 -- "Re-calibrate" -> TrainingThread spawned, cache updated
# ---------------------------------------------------------------------------

class TestAc3RecalibratePath:
    """AC3: 'Re-calibrate' must spawn TrainingThread and update cache on completion."""

    def test_training_thread_started(self, qapp):
        """When user clicks 'Re-calibrate', TrainingThread.start() must be called."""
        stub = _make_training_stub()
        fp = _make_fingerprint(["Alpha"])
        stub._calibration_fingerprint = fp
        stub._calibration_cache = {"Alpha": 3}
        stub._calibration_cache_from_disk = False

        recal_btn = object()
        mock_msg_box = MagicMock()
        mock_msg_box.addButton.side_effect = lambda label, role: object() if "Use Cached" in str(label) else recal_btn
        mock_msg_box.exec_.return_value = None
        mock_msg_box.clickedButton.return_value = recal_btn
        mock_qmb = MagicMock(return_value=mock_msg_box)
        mock_qmb.AcceptRole = MagicMock()
        mock_qmb.DestructiveRole = MagicMock()

        config = {
            "blocks": ["Alpha"],
            "timeframes": ["15m"],
            "period_days": 180,
            "mode": "production",
            "config": {},
        }

        mock_thread = _make_mock_thread()
        with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb), \
             patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_thread):
            stub._execute_training(config)

        mock_thread.start.assert_called_once()

    def test_pending_fingerprint_set_before_thread(self, qapp):
        """_pending_fingerprint must be set before TrainingThread starts."""
        stub = _make_training_stub()
        fp = _make_fingerprint(["Alpha"])
        stub._calibration_fingerprint = fp
        stub._calibration_cache = {"Alpha": 3}

        recal_btn = object()
        mock_msg_box = MagicMock()
        mock_msg_box.addButton.side_effect = lambda label, role: object() if "Use Cached" in str(label) else recal_btn
        mock_msg_box.exec_.return_value = None
        mock_msg_box.clickedButton.return_value = recal_btn
        mock_qmb = MagicMock(return_value=mock_msg_box)
        mock_qmb.AcceptRole = MagicMock()
        mock_qmb.DestructiveRole = MagicMock()

        config = {
            "blocks": ["Alpha"],
            "timeframes": ["15m"],
            "period_days": 180,
            "mode": "production",
            "config": {},
        }

        mock_thread = _make_mock_thread()
        with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb), \
             patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_thread):
            stub._execute_training(config)

        assert stub._pending_fingerprint is not None


# ---------------------------------------------------------------------------
# AC5 -- Different block-set -> no dialog, TrainingThread runs
# ---------------------------------------------------------------------------

class TestAc5CacheMissRunsTraining:
    """AC5: Different block-set must NOT show dialog and must run TrainingThread."""

    def test_no_dialog_on_fingerprint_mismatch(self, qapp):
        """When cached fingerprint differs from current, no dialog should appear."""
        stub = _make_training_stub()
        fp = _make_fingerprint(["Alpha", "Beta"])
        stub._calibration_fingerprint = fp
        stub._calibration_cache = {"Alpha": 3, "Beta": 5}
        stub._calibration_cache_from_disk = True

        dialog_created = []

        class DialogTracker(MagicMock):
            def __call__(self, *args, **kwargs):
                dialog_created.append(True)
                return MagicMock()

        mock_qmb = DialogTracker()
        mock_qmb.AcceptRole = MagicMock()
        mock_qmb.DestructiveRole = MagicMock()

        config = {
            "blocks": ["Gamma"],
            "timeframes": ["15m"],
            "period_days": 180,
            "mode": "production",
            "config": {},
        }

        mock_thread = _make_mock_thread()
        with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb), \
             patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_thread):
            stub._execute_training(config)

        assert not dialog_created, "AC5: Dialog appeared for different block-set"
        mock_thread.start.assert_called_once()

    def test_no_cache_skips_dialog(self, qapp):
        """When _calibration_fingerprint is None, no dialog and TrainingThread runs."""
        stub = _make_training_stub()
        dialog_created = []

        class DialogTracker(MagicMock):
            def __call__(self, *args, **kwargs):
                dialog_created.append(True)
                return MagicMock()

        mock_qmb = DialogTracker()
        mock_qmb.AcceptRole = MagicMock()
        mock_qmb.DestructiveRole = MagicMock()

        config = {
            "blocks": ["Alpha"],
            "timeframes": ["15m"],
            "period_days": 180,
            "mode": "production",
            "config": {},
        }

        mock_thread = _make_mock_thread()
        with patch("src.optimizer_v3.ui.training_panel.QMessageBox", mock_qmb), \
             patch("src.optimizer_v3.core.training_thread.TrainingThread", return_value=mock_thread):
            stub._execute_training(config)

        assert not dialog_created, "No dialog should appear when no cache exists"
        mock_thread.start.assert_called_once()


# ---------------------------------------------------------------------------
# Cache write on _on_training_complete
# ---------------------------------------------------------------------------

class TestCacheWriteOnTrainingComplete:
    """_on_training_complete must write cache when _pending_fingerprint is set."""

    def test_cache_written_on_complete(self, qapp):
        """After _on_training_complete, fingerprint and delay_map must be stored."""
        stub = _make_training_stub()
        fp = _make_fingerprint(["Alpha"])
        stub._pending_fingerprint = fp

        results = [{"signal_name": "Alpha", "optimal_delay": 5}]

        with patch("src.optimizer_v3.ui.training_panel.calibration_cache.save_cache") as mock_save:
            stub._on_training_complete(results)

        assert stub._calibration_fingerprint == fp
        assert stub._calibration_cache == {"Alpha": 5}
        mock_save.assert_called_once_with(fp, {"Alpha": 5})

    def test_pending_fingerprint_cleared_on_complete(self, qapp):
        """After _on_training_complete, _pending_fingerprint must be reset to None."""
        stub = _make_training_stub()
        stub._pending_fingerprint = _make_fingerprint(["Alpha"])

        results = [{"signal_name": "Alpha", "optimal_delay": 5}]

        with patch("src.optimizer_v3.ui.training_panel.calibration_cache.save_cache"):
            stub._on_training_complete(results)

        assert stub._pending_fingerprint is None

    def test_cache_not_written_when_pending_none(self, qapp):
        """When _pending_fingerprint is None, no cache write should occur."""
        stub = _make_training_stub()
        stub._pending_fingerprint = None

        results = [{"signal_name": "Alpha", "optimal_delay": 5}]

        with patch("src.optimizer_v3.ui.training_panel.calibration_cache.save_cache") as mock_save:
            stub._on_training_complete(results)

        assert stub._calibration_fingerprint is None
        assert stub._calibration_cache is None
        mock_save.assert_not_called()

    def test_cache_not_written_when_delay_map_empty(self, qapp):
        """When no results have valid signal_name/optimal_delay, cache is not updated."""
        stub = _make_training_stub()
        stub._pending_fingerprint = _make_fingerprint(["Alpha"])

        results = [{"foo": "bar"}]

        with patch("src.optimizer_v3.ui.training_panel.calibration_cache.save_cache") as mock_save:
            stub._on_training_complete(results)

        assert stub._calibration_fingerprint is None
        assert stub._calibration_cache is None
        mock_save.assert_not_called()

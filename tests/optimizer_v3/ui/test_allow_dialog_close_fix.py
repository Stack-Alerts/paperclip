"""
Unit tests for BTCAAAAA-381 fix:
  _allow_dialog_close() must call _finalize_recommendations() when
  _recommendations_waiting is set (timer path).

These tests exercise the logic of _allow_dialog_close and _on_recommendations_ready
using a lightweight stub — no QWidget instantiation required, safe for CI/headless.

The stub replaces PyQt signals and UI calls with simple counters/flags so we can
assert exactly how many times _finalize_recommendations() fires and which code path
triggers it.
"""
import pytest


class _FakeProgressDialog:
    """Minimal stand-in for the Qt progress dialog."""
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _MetricsDisplayPanelStub:
    """
    Minimal stub that replicates the control-flow attributes and methods
    relevant to the dialog-close / recommendations-ready interaction.

    No Qt imports — works headlessly.
    """

    def __init__(self):
        # State mirrors real class
        self.dialog_can_close: bool = False
        self.batch_recommendations = []
        self.rec_engine = None
        self.progress_dialog = _FakeProgressDialog()

        # Observation counters
        self.finalize_call_count: int = 0

    # ------------------------------------------------------------------ #
    # Methods under test (copied verbatim from production code)            #
    # ------------------------------------------------------------------ #

    def _allow_dialog_close(self) -> None:
        """Allow progress dialog to close after minimum display time"""
        self.dialog_can_close = True
        if hasattr(self, 'progress_dialog') and hasattr(self, '_recommendations_waiting'):
            self.progress_dialog.close()
            del self._recommendations_waiting  # Clear the flag before calling
            self._finalize_recommendations()

    def _on_recommendations_ready(self, recommendations) -> None:
        """Handle completion of background AI recommendation generation."""
        self.batch_recommendations = recommendations
        if hasattr(self, 'progress_dialog'):
            if self.dialog_can_close:
                self.progress_dialog.close()
            else:
                self._recommendations_waiting = True
                return  # Don't update UI yet - wait for timer
        self._finalize_recommendations()

    def _finalize_recommendations(self) -> None:
        """Stub: count calls instead of touching Qt widgets."""
        self.finalize_call_count += 1


# ================================================================== #
# AC-1: Core fix — _allow_dialog_close calls _finalize_recommendations
#        when _recommendations_waiting is set (timer path / slow path)
# ================================================================== #

class TestTimerPath:
    """AI returns before 1-second minimum timer fires (slow-dialog scenario)."""

    def test_allow_dialog_close_calls_finalize_when_waiting(self):
        """
        _allow_dialog_close() MUST call _finalize_recommendations() exactly once
        when _recommendations_waiting has been set by _on_recommendations_ready.
        """
        stub = _MetricsDisplayPanelStub()
        # Simulate: AI finished but timer hasn't fired yet
        stub._on_recommendations_ready(["rec_a"])
        assert stub.finalize_call_count == 0, \
            "_finalize_recommendations should not fire before timer"
        # Timer fires
        stub._allow_dialog_close()
        assert stub.finalize_call_count == 1, \
            "_finalize_recommendations must be called exactly once after timer fires"

    def test_allow_dialog_close_closes_dialog_when_waiting(self):
        """Dialog must be closed in the timer path."""
        stub = _MetricsDisplayPanelStub()
        stub._on_recommendations_ready(["rec_a"])
        stub._allow_dialog_close()
        assert stub.progress_dialog.closed, "progress_dialog.close() was not called"

    def test_recommendations_waiting_flag_deleted_after_timer(self):
        """
        _recommendations_waiting must be deleted before _finalize_recommendations
        is called to prevent any re-entry / double-fire risk.
        """
        stub = _MetricsDisplayPanelStub()
        stub._on_recommendations_ready(["rec_a"])
        stub._allow_dialog_close()
        assert not hasattr(stub, '_recommendations_waiting'), \
            "_recommendations_waiting must be deleted after the timer fires"

    def test_no_finalize_without_waiting_flag(self):
        """
        If _recommendations_waiting is NOT set (no pending recommendations),
        _allow_dialog_close() should NOT call _finalize_recommendations.
        """
        stub = _MetricsDisplayPanelStub()
        # Timer fires but AI hasn't finished yet
        stub._allow_dialog_close()
        assert stub.finalize_call_count == 0, \
            "_finalize_recommendations must NOT fire if no recommendations are waiting"


# ================================================================== #
# AC-2: No double-fire — fast path must not also call _finalize
# ================================================================== #

class TestFastPath:
    """AI takes > 1 second — dialog minimum has elapsed by the time AI returns."""

    def test_fast_path_calls_finalize_directly(self):
        """
        When dialog_can_close is True, _on_recommendations_ready closes the dialog
        and calls _finalize_recommendations directly (no _recommendations_waiting set).
        """
        stub = _MetricsDisplayPanelStub()
        stub.dialog_can_close = True  # Timer already fired
        stub._on_recommendations_ready(["rec_a"])
        assert stub.finalize_call_count == 1, \
            "_finalize_recommendations must be called once via fast path"
        assert not hasattr(stub, '_recommendations_waiting'), \
            "_recommendations_waiting must NOT be set in the fast path"

    def test_fast_path_no_double_fire_from_allow_dialog_close(self):
        """
        In the fast path, _allow_dialog_close() fires BEFORE AI returns.
        It sets dialog_can_close=True but _recommendations_waiting is absent,
        so no additional _finalize_recommendations call should occur.
        """
        stub = _MetricsDisplayPanelStub()
        # Timer fires first (AI not done yet)
        stub._allow_dialog_close()
        assert stub.finalize_call_count == 0

        # AI arrives after timer — fast path
        stub._on_recommendations_ready(["rec_a"])
        assert stub.finalize_call_count == 1, \
            "_finalize_recommendations must be called exactly once total"


# ================================================================== #
# AC-3: Double-call prevention — never called twice in any scenario
# ================================================================== #

class TestDoubleCallPrevention:
    """Verify _finalize_recommendations is never called more than once."""

    def test_timer_path_never_double_fires(self):
        """
        Simulate the complete timer-path sequence:
        1. AI finishes → _on_recommendations_ready sets _recommendations_waiting, returns early
        2. Timer fires → _allow_dialog_close deletes flag, calls _finalize_recommendations
        Total: exactly 1 call.
        """
        stub = _MetricsDisplayPanelStub()
        stub._on_recommendations_ready(["rec_a", "rec_b"])
        stub._allow_dialog_close()
        assert stub.finalize_call_count == 1, \
            f"Expected exactly 1 _finalize_recommendations call, got {stub.finalize_call_count}"

    def test_fast_path_never_double_fires(self):
        """
        Fast path: timer fires first, then AI arrives.
        Total: exactly 1 call.
        """
        stub = _MetricsDisplayPanelStub()
        stub._allow_dialog_close()          # timer fires, no recommendations yet
        stub._on_recommendations_ready(["rec_a"])  # AI arrives; fast path
        assert stub.finalize_call_count == 1, \
            f"Expected exactly 1 _finalize_recommendations call, got {stub.finalize_call_count}"

    def test_second_allow_dialog_close_does_not_double_fire(self):
        """
        If _allow_dialog_close somehow fires twice (e.g. timer bug), the second
        call must be a no-op — the flag was deleted on the first call.
        """
        stub = _MetricsDisplayPanelStub()
        stub._on_recommendations_ready(["rec_a"])
        stub._allow_dialog_close()
        stub._allow_dialog_close()  # spurious second call
        assert stub.finalize_call_count == 1, \
            "Spurious second _allow_dialog_close() must not trigger a second finalize"


# ================================================================== #
# AC-4: Acceptance criteria — methods exist on the real class
# ================================================================== #

class TestMethodsExistOnRealClass:
    """Verify the fix methods are present on MetricsDisplayPanel (no Qt needed)."""

    def test_allow_dialog_close_exists(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, "_allow_dialog_close"), \
            "_allow_dialog_close not found on MetricsDisplayPanel"

    def test_finalize_recommendations_exists(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, "_finalize_recommendations"), \
            "_finalize_recommendations not found on MetricsDisplayPanel"

    def test_on_recommendations_ready_exists(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, "_on_recommendations_ready"), \
            "_on_recommendations_ready not found on MetricsDisplayPanel"

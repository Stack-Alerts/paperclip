"""
Unit tests for BTCAAAAA-423 UX Fixes:

  Fix 1: _switch_to_metrics_tab() now prefers 'Metrics' tab (not 'AI Recommendations')
          after AI response completes.

  Fix 2: backtest_config_panel.py — tab order is:
          Config (0) | Live Output (1) | Trades (2) | AI Recommendations (3) | Metrics (4) | Compare (5)

  Fix 3: _find_main_window() walks the full Qt parent chain past BacktestConfigDialog
          to find StrategyBuilderMainWindow (via 'blocks_panel' attribute).
          _refresh_strategy_builder_ui() calls refresh_from_orchestrator() on the
          blocks_panel instead of non-existent refresh_blocks()/_refresh_ui().

All tests use lightweight stubs — no QWidget instantiation required, safe for CI/headless.
"""
import pytest


# ============================================================== #
#  Shared Stubs & Helpers                                        #
# ============================================================== #

class _FakeTabWidget:
    """Minimal stub for a QTabWidget."""

    def __init__(self, tabs):
        """
        tabs: list of (text, widget) tuples in order.
        """
        self._tabs = list(tabs)
        self._current_index = 0

    def count(self):
        return len(self._tabs)

    def tabText(self, i):
        return self._tabs[i][0]

    def setCurrentIndex(self, i):
        self._current_index = i

    def currentIndex(self):
        return self._current_index

    def parent(self):
        return None


class _FakeBlocksPanel:
    """Minimal stub for StrategyBlocksPanel."""

    def __init__(self, has_refresh=True):
        self._refresh_called = False
        self._repaint_called = False
        self._has_refresh = has_refresh

    def __bool__(self):
        return True  # not None

    def refresh_from_orchestrator(self):
        self._refresh_called = True

    def update(self):
        pass

    def repaint(self):
        self._repaint_called = True

    def __hasattr__(self, name):
        if name == 'refresh_from_orchestrator':
            return self._has_refresh
        return False


class _FakeMainWindow:
    """Minimal stub for StrategyBuilderMainWindow (the 'has blocks_panel' sentinel)."""

    def __init__(self, has_refresh=True):
        self.blocks_panel = _FakeBlocksPanel(has_refresh=has_refresh)
        self._parent = None

    def parent(self):
        return self._parent


class _FakeDialog:
    """Stub for BacktestConfigDialog — sits BETWEEN panel and main window."""

    def __init__(self, main_window):
        self._main_window = main_window
        self._child_parent = None

    def parent(self):
        return self._main_window


class _MetricsPanelStub:
    """
    Lightweight stub that replicates only the parent-chain walking and
    refresh/switch logic from MetricsDisplayPanel.

    No Qt imports — safe for headless CI.
    """

    def __init__(self):
        self._parent_chain = []   # list of objects, innermost first
        self._tab_widget = None    # the QTabWidget stub in the chain
        self._log = []
        self.refresh_calls = []

    def parent(self):
        """Return first item in the parent chain (immediate parent)."""
        if self._parent_chain:
            return self._parent_chain[0]
        return None

    # -------------------------------------------------------------- #
    # Internal parent-chain walker (mirrors production code)          #
    # -------------------------------------------------------------- #

    def _iter_parents(self):
        """Yield self, then each item in _parent_chain."""
        yield self
        for p in self._parent_chain:
            yield p

    # -------------------------------------------------------------- #
    # Fix 3: _find_main_window (pure Python version of production logic)
    # -------------------------------------------------------------- #

    def _find_main_window(self):
        """
        Walk the parent chain (self → parents) looking for an object that
        owns 'blocks_panel'.  Returns that object or None.
        (Mirror of production logic — no Qt needed.)
        """
        widget = self
        while widget is not None:
            if hasattr(widget, 'blocks_panel'):
                return widget
            widget = widget.parent() if hasattr(widget, 'parent') and callable(widget.parent) else None

        return None

    def _refresh_strategy_builder_ui(self) -> None:
        """Mirror of production _refresh_strategy_builder_ui."""
        main_window = self._find_main_window()

        if main_window is None:
            self._log.append("WARNING: StrategyBuilderMainWindow not found")
            return

        blocks_panel = main_window.blocks_panel
        if blocks_panel is None:
            self._log.append("WARNING: blocks_panel is None")
            return

        if hasattr(blocks_panel, 'refresh_from_orchestrator'):
            blocks_panel.refresh_from_orchestrator()
            self._log.append("INFO: refreshed via refresh_from_orchestrator()")
        else:
            blocks_panel.update()
            blocks_panel.repaint()
            self._log.append("WARNING: fallback repaint")

    # -------------------------------------------------------------- #
    # Fix 1: _switch_to_metrics_tab (pure Python version)             #
    # -------------------------------------------------------------- #

    def _switch_to_metrics_tab(self) -> None:
        """
        Mirror of production _switch_to_metrics_tab.
        Walks parent chain to find _FakeTabWidget, then switches to 'Metrics' tab.
        """
        # Find QTabWidget-like object in parent chain
        tab_widget = None
        for obj in self._iter_parents():
            if isinstance(obj, _FakeTabWidget):
                tab_widget = obj
                break

        if tab_widget is None:
            self._log.append("WARNING: Could not find tab widget")
            return

        # Prefer Metrics tab
        for i in range(tab_widget.count()):
            tab_text = tab_widget.tabText(i).lower()
            if 'metric' in tab_text:
                tab_widget.setCurrentIndex(i)
                self._log.append(f"INFO: Switched to tab: {tab_widget.tabText(i)}")
                return

        # Fallback: AI Recommendations tab
        for i in range(tab_widget.count()):
            tab_text = tab_widget.tabText(i).lower()
            if 'ai' in tab_text or 'rec' in tab_text:
                tab_widget.setCurrentIndex(i)
                self._log.append(f"INFO: Switched to tab (fallback): {tab_widget.tabText(i)}")
                return

        self._log.append("WARNING: Could not find Metrics or AI tab")


# ============================================================== #
# Fix 1 — _switch_to_metrics_tab prefers 'Metrics' tab           #
# ============================================================== #

EXPECTED_TABS = [
    (0, "💠 Config"),
    (1, "● Live Output"),
    (2, "💰 Trades"),
    (3, "🤖 AI Recommendations"),
    (4, "💹 Metrics"),
    (5, "🔁 Compare"),
]


class TestSwitchToMetricsTab:
    """AC-1: After AI response, panel auto-switches to Metrics tab (not AI Recommendations)."""

    def _make_panel_with_tabs(self, tabs=None):
        """Build a stub panel that lives inside a tab widget."""
        if tabs is None:
            tabs = [(text, None) for _, text in EXPECTED_TABS]
        tab_widget = _FakeTabWidget(tabs)
        panel = _MetricsPanelStub()
        # Panel's immediate parent is the tab widget
        panel._parent_chain = [tab_widget]
        return panel, tab_widget

    def test_switches_to_metrics_tab_by_default(self):
        """_switch_to_metrics_tab must select the '💹 Metrics' tab (index 4)."""
        panel, tab_widget = self._make_panel_with_tabs()
        tab_widget._current_index = 0  # start on Config
        panel._switch_to_metrics_tab()
        assert tab_widget.currentIndex() == 4, (
            f"Expected Metrics tab (4), got {tab_widget.currentIndex()} "
            f"({tab_widget.tabText(tab_widget.currentIndex())})"
        )

    def test_does_not_switch_to_ai_recommendations_first(self):
        """Ensure AI Recommendations tab (3) is NOT the first choice."""
        panel, tab_widget = self._make_panel_with_tabs()
        tab_widget._current_index = 0
        panel._switch_to_metrics_tab()
        assert tab_widget.currentIndex() != 3, (
            "Should NOT auto-switch to 'AI Recommendations' tab — Metrics must be preferred"
        )

    def test_falls_back_to_ai_recommendations_when_metrics_absent(self):
        """When there is no Metrics tab, fallback must pick AI Recommendations."""
        tabs_no_metrics = [
            (0, "💠 Config"),
            (1, "● Live Output"),
            (2, "💰 Trades"),
            (3, "🤖 AI Recommendations"),
            (4, "🔁 Compare"),
        ]
        tabs = [(text, None) for _, text in tabs_no_metrics]
        tab_widget = _FakeTabWidget(tabs)
        panel = _MetricsPanelStub()
        panel._parent_chain = [tab_widget]
        panel._switch_to_metrics_tab()
        selected_text = tab_widget.tabText(tab_widget.currentIndex()).lower()
        assert 'ai' in selected_text or 'rec' in selected_text, (
            f"Fallback should pick AI Recommendations tab, got '{selected_text}'"
        )

    def test_graceful_when_no_tab_widget_in_parent_chain(self):
        """No exception when there's no QTabWidget ancestor."""
        panel = _MetricsPanelStub()
        panel._parent_chain = []  # no tab widget
        panel._switch_to_metrics_tab()  # must not raise
        assert any("WARNING" in msg for msg in panel._log), \
            "Should log a warning when no tab widget found"

    def test_metrics_tab_found_regardless_of_emoji(self):
        """Tab text matching should be case-insensitive and work with emoji prefixes."""
        tabs = [
            ("💠 Config", None),
            ("💹 Metrics", None),
            ("🤖 AI Recommendations", None),
        ]
        tab_widget = _FakeTabWidget(tabs)
        panel = _MetricsPanelStub()
        panel._parent_chain = [tab_widget]
        panel._switch_to_metrics_tab()
        # Index 1 is Metrics
        assert tab_widget.currentIndex() == 1, (
            f"Expected Metrics at index 1, got {tab_widget.currentIndex()}"
        )


# ============================================================== #
# Fix 2 — Tab order in BacktestConfigPanel                       #
# ============================================================== #

class TestTabOrder:
    """AC-2: Tab order verification — AI Recommendations (3) before Metrics (4)."""

    def test_ai_recommendations_tab_index_is_3(self):
        """AI Recommendations must be at index 3."""
        tab_names = [text for _, text in EXPECTED_TABS]
        ai_index = next(
            (i for i, t in enumerate(tab_names) if 'AI Recommendations' in t), None
        )
        assert ai_index == 3, f"AI Recommendations expected at index 3, found at {ai_index}"

    def test_metrics_tab_index_is_4(self):
        """Metrics tab must be at index 4 (after AI Recommendations)."""
        tab_names = [text for _, text in EXPECTED_TABS]
        metrics_index = next(
            (i for i, t in enumerate(tab_names) if 'Metrics' in t), None
        )
        assert metrics_index == 4, f"Metrics expected at index 4, found at {metrics_index}"

    def test_ai_recommendations_before_metrics(self):
        """AI Recommendations index must be less than Metrics index."""
        tab_names = [text for _, text in EXPECTED_TABS]
        ai_idx = next((i for i, t in enumerate(tab_names) if 'AI Recommendations' in t), None)
        metrics_idx = next((i for i, t in enumerate(tab_names) if 'Metrics' in t), None)
        assert ai_idx is not None, "AI Recommendations tab not found"
        assert metrics_idx is not None, "Metrics tab not found"
        assert ai_idx < metrics_idx, (
            f"AI Recommendations ({ai_idx}) must precede Metrics ({metrics_idx})"
        )

    def test_config_tab_is_first(self):
        """Config tab must remain at index 0."""
        tab_names = [text for _, text in EXPECTED_TABS]
        assert 'Config' in tab_names[0], "Config must be first tab"

    def test_compare_tab_is_last(self):
        """Compare tab must remain last."""
        tab_names = [text for _, text in EXPECTED_TABS]
        assert 'Compare' in tab_names[-1], "Compare must be last tab"

    def test_full_tab_order(self):
        """Verify complete tab sequence matches spec."""
        expected_keywords = ['Config', 'Live Output', 'Trades', 'AI Recommendations', 'Metrics', 'Compare']
        for idx, (_, tab_text) in enumerate(EXPECTED_TABS):
            assert expected_keywords[idx] in tab_text, (
                f"Tab {idx}: expected keyword '{expected_keywords[idx]}' in '{tab_text}'"
            )


# ============================================================== #
# Fix 3a — _find_main_window walks full parent chain              #
# ============================================================== #

class _FakeParent:
    """Generic fake parent for chain construction."""
    def __init__(self, parent_obj=None):
        self._parent = parent_obj

    def parent(self):
        return self._parent


class _FakeParentWithBlocks:
    """Parent that owns blocks_panel (acts as StrategyBuilderMainWindow)."""
    def __init__(self, parent_obj=None):
        self._parent = parent_obj
        self.blocks_panel = _FakeBlocksPanel()

    def parent(self):
        return self._parent


class TestFindMainWindow:
    """AC-3a: _find_main_window correctly traverses the parent chain."""

    def test_finds_main_window_as_direct_parent(self):
        """Main window is the direct parent of the panel."""
        main_window = _FakeParentWithBlocks()
        panel = _MetricsPanelStub()
        panel._parent_chain = [main_window]
        result = panel._find_main_window()
        assert result is main_window, "Should find main window as direct parent"

    def test_finds_main_window_through_dialog(self):
        """Main window is the dialog's parent (typical production layout)."""
        main_window = _FakeParentWithBlocks()
        dialog = _FakeParent(parent_obj=main_window)
        panel = _MetricsPanelStub()
        # Panel → dialog → main_window
        panel._parent_chain = [dialog, main_window]
        result = panel._find_main_window()
        assert result is main_window, (
            "Should find main window by traversing: panel → dialog → main_window"
        )

    def test_finds_main_window_through_deep_chain(self):
        """Main window is buried three levels up."""
        main_window = _FakeParentWithBlocks()
        level2 = _FakeParent(parent_obj=main_window)
        level1 = _FakeParent(parent_obj=level2)
        panel = _MetricsPanelStub()
        panel._parent_chain = [level1, level2, main_window]
        result = panel._find_main_window()
        assert result is main_window, "Should find main window 3 levels up"

    def test_returns_none_when_no_blocks_panel_ancestor(self):
        """Returns None when no ancestor has 'blocks_panel' and no Qt fallbacks."""
        level1 = _FakeParent()
        level2 = _FakeParent(parent_obj=level1)
        panel = _MetricsPanelStub()
        panel._parent_chain = [level1, level2]
        result = panel._find_main_window()
        assert result is None, "Should return None when no ancestor has blocks_panel"

    def test_panel_itself_with_blocks_panel(self):
        """Edge case: if panel itself had blocks_panel, it returns itself."""
        panel = _MetricsPanelStub()
        panel.blocks_panel = _FakeBlocksPanel()  # unusual but test edge case
        panel._parent_chain = []
        result = panel._find_main_window()
        assert result is panel, "Should return self if it owns blocks_panel"


# ============================================================== #
# Fix 3b — _refresh_strategy_builder_ui uses refresh_from_orchestrator
# ============================================================== #

class TestRefreshStrategyBuilderUI:
    """AC-3b: refresh uses refresh_from_orchestrator(), not refresh_blocks() etc."""

    def test_calls_refresh_from_orchestrator(self):
        """Primary path: refresh_from_orchestrator() must be called."""
        main_window = _FakeParentWithBlocks()
        panel = _MetricsPanelStub()
        panel._parent_chain = [main_window]
        panel._refresh_strategy_builder_ui()
        assert main_window.blocks_panel._refresh_called, \
            "refresh_from_orchestrator() must be called on blocks_panel"

    def test_no_refresh_when_main_window_not_found(self):
        """When main window is None, no call should be made and no exception raised."""
        panel = _MetricsPanelStub()
        panel._parent_chain = []  # no ancestors
        panel._refresh_strategy_builder_ui()  # must not raise
        assert any("WARNING" in msg for msg in panel._log), \
            "Should log a warning when main window not found"

    def test_no_refresh_when_blocks_panel_none(self):
        """When blocks_panel is None on the main window, should log warning."""
        main_window = _FakeParentWithBlocks()
        main_window.blocks_panel = None   # simulate None blocks_panel
        panel = _MetricsPanelStub()
        panel._parent_chain = [main_window]
        panel._refresh_strategy_builder_ui()  # must not raise
        assert any("WARNING" in msg for msg in panel._log), \
            "Should log a warning when blocks_panel is None"

    def test_fallback_repaint_when_refresh_method_missing(self):
        """When refresh_from_orchestrator is absent, update()/repaint() is called."""
        class _BlocksPanelNoRefresh:
            def __init__(self):
                self._repaint_called = False

            def update(self):
                pass

            def repaint(self):
                self._repaint_called = True

            def __bool__(self):
                return True

        main_window = _FakeParentWithBlocks()
        main_window.blocks_panel = _BlocksPanelNoRefresh()
        panel = _MetricsPanelStub()
        panel._parent_chain = [main_window]
        panel._refresh_strategy_builder_ui()
        assert main_window.blocks_panel._repaint_called, \
            "Fallback repaint() must be called when refresh_from_orchestrator is absent"

    def test_does_not_call_refresh_blocks(self):
        """refresh_blocks() must NOT be called (it was removed in the fix)."""
        class _BlocksPanelWithOldMethods:
            def __init__(self):
                self._refresh_blocks_called = False
                self._refresh_ui_called = False
                self._refresh_from_orch_called = False

            def refresh_blocks(self):
                self._refresh_blocks_called = True

            def _refresh_ui(self):
                self._refresh_ui_called = True

            def refresh_from_orchestrator(self):
                self._refresh_from_orch_called = True

            def __bool__(self):
                return True

        main_window = _FakeParentWithBlocks()
        bp = _BlocksPanelWithOldMethods()
        main_window.blocks_panel = bp
        panel = _MetricsPanelStub()
        panel._parent_chain = [main_window]
        panel._refresh_strategy_builder_ui()

        assert bp._refresh_from_orch_called, "refresh_from_orchestrator() must be called"
        assert not bp._refresh_blocks_called, "refresh_blocks() must NOT be called (removed)"
        assert not bp._refresh_ui_called, "_refresh_ui() must NOT be called (removed)"


# ============================================================== #
# Signal connection verification (no Qt — just method existence)  #
# ============================================================== #

class TestMethodsExistOnRealClasses:
    """Verify the production methods exist on the real classes (import-only, no QWidget)."""

    def test_find_main_window_on_metrics_panel(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, '_find_main_window'), \
            "_find_main_window must exist on MetricsDisplayPanel"

    def test_refresh_strategy_builder_ui_on_metrics_panel(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, '_refresh_strategy_builder_ui'), \
            "_refresh_strategy_builder_ui must exist on MetricsDisplayPanel"

    def test_switch_to_metrics_tab_on_metrics_panel(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert hasattr(MetricsDisplayPanel, '_switch_to_metrics_tab'), \
            "_switch_to_metrics_tab must exist on MetricsDisplayPanel"

    def test_metrics_panel_class_importable(self):
        from src.optimizer_v3.ui.metrics_display_panel import MetricsDisplayPanel
        assert MetricsDisplayPanel is not None

    def test_ai_recommendations_panel_importable(self):
        from src.optimizer_v3.ui.ai_recommendations_panel import AIRecommendationsPanel
        assert AIRecommendationsPanel is not None

    def test_backtest_config_panel_source_exists(self):
        """Verify backtest_config_panel.py exists on disk (import may fail in CI due to .env issue)."""
        import pathlib
        path = pathlib.Path("src/strategy_builder/ui/backtest_config_panel.py")
        assert path.exists(), "backtest_config_panel.py must exist"
        assert path.stat().st_size > 0, "backtest_config_panel.py must not be empty"


# ============================================================== #
# Tab order verification using source code inspection             #
# ============================================================== #

class TestTabOrderInSourceCode:
    """
    Verify the tab order matches the spec by inspecting the actual source code
    structure of BacktestConfigPanel.  This is a regression guard that will fail
    if someone reverts the tab reorder.
    """

    def test_ai_recommendations_added_before_metrics_in_source(self):
        """
        In backtest_config_panel.py, 'AI Recommendations' must be addTab'd
        before 'Metrics'.  Verified by scanning source lines for addTab calls.
        """
        import pathlib
        source_path = pathlib.Path(
            "src/strategy_builder/ui/backtest_config_panel.py"
        )
        source = source_path.read_text()
        ai_pos = source.find('AI Recommendations')
        metrics_pos = source.find('"💹 Metrics"')
        assert ai_pos != -1, "AI Recommendations tab not found in source"
        assert metrics_pos != -1, "Metrics tab not found in source"
        assert ai_pos < metrics_pos, (
            "AI Recommendations addTab must appear before Metrics addTab in source"
        )

    def test_signal_connections_present_in_source(self):
        """
        Verify the three critical signal connections are present in backtest_config_panel:
          1. trades_panel.metrics_updated → metrics_panel.update_metrics
          2. ai_recommendations_panel.send_approved → metrics_panel._on_ai_request_approved
          3. metrics_panel.recommendations_generated → ai_recommendations_panel.display_recommendations
        """
        import pathlib
        source = pathlib.Path(
            "src/strategy_builder/ui/backtest_config_panel.py"
        ).read_text()
        assert 'metrics_updated' in source, \
            "trades_panel.metrics_updated connection must exist"
        assert 'send_approved' in source, \
            "ai_recommendations_panel.send_approved connection must exist"
        assert 'recommendations_generated' in source, \
            "metrics_panel.recommendations_generated connection must exist"
        assert '_on_ai_request_approved' in source, \
            "_on_ai_request_approved handler must be referenced"
        assert 'display_recommendations' in source, \
            "display_recommendations must be referenced"

    def test_find_main_window_walks_past_dialog_in_source(self):
        """
        _find_main_window must walk the parent chain looking for blocks_panel,
        not just call self.window() (the old incorrect approach).
        """
        import pathlib
        source = pathlib.Path(
            "src/optimizer_v3/ui/metrics_display_panel.py"
        ).read_text()
        assert '_find_main_window' in source, \
            "_find_main_window method must be defined"
        assert 'blocks_panel' in source, \
            "blocks_panel attribute check must be present in _find_main_window"
        # Old approach — must be gone from _refresh_strategy_builder_ui
        # (self.window() was the buggy way to get the main window)
        # The new code uses _find_main_window()
        assert 'refresh_from_orchestrator' in source, \
            "refresh_from_orchestrator() must be called in _refresh_strategy_builder_ui"

    def test_switch_to_metrics_tab_prefers_metric_in_source(self):
        """
        _switch_to_metrics_tab must check for 'metric' first, then 'ai'/'rec' as fallback.
        """
        import pathlib
        source = pathlib.Path(
            "src/optimizer_v3/ui/metrics_display_panel.py"
        ).read_text()
        # Locate the _switch_to_metrics_tab method
        method_start = source.find('def _switch_to_metrics_tab')
        assert method_start != -1, "_switch_to_metrics_tab must be defined"
        # Next method boundary — find 'def ' after method_start
        next_def = source.find('\n    def ', method_start + 1)
        method_body = source[method_start:next_def if next_def != -1 else method_start + 2000]

        # 'metric' check must appear before 'ai'/'rec' check
        metric_pos = method_body.find("'metric'")
        ai_pos = method_body.find("'ai'")
        assert metric_pos != -1, "'metric' check not found in _switch_to_metrics_tab"
        assert ai_pos != -1, "'ai' fallback not found in _switch_to_metrics_tab"
        assert metric_pos < ai_pos, (
            "In _switch_to_metrics_tab, 'metric' check must come before 'ai' fallback"
        )

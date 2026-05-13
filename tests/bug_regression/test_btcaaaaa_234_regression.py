"""
Regression tests for BTCAAAAA-234: Replace remaining "BTC Engine v3" references
with "BTC Trade Engine" across the codebase.

Issue: BTCAAAAA-234
Fix commit: 7f3bdf04

Scope:
  - src/data_manager/__init__.py (docstring + __author__)
  - src/optimizer_v3/core/ai_recommendation_enhancer.py (X-Title header)
  - src/optimizer_v3/core/data_cache_manager.py (docstring author)
  - src/optimizer_v3/database/__init__.py (__author__)
  - src/utils/Strategy_Builder/qt_gui/main_window.py → refactored to
    src/strategy_builder/ui/strategy_builder_main_window.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-234"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestDataManagerIdentity:
    """src/data_manager/__init__.py must carry the correct name."""

    def test_data_manager_init_importable(self):
        from src.data_manager import __doc__ as d

        assert d is not None

    def test_data_manager_docstring_uses_new_name(self):
        from src.data_manager import __doc__ as d

        assert "BTC Trade Engine" in (d or "")

    def test_data_manager_author_uses_new_name(self):
        from src.data_manager import __author__ as a

        assert "BTC Trade Engine" in a

    def test_data_manager_no_stale_name(self):
        from src.data_manager import __doc__ as d
        from src.data_manager import __author__ as a

        assert "BTC Engine v3" not in (d or "")
        assert "BTC Engine v3" not in a


class TestAiRecommendationEnhancer:
    """X-Title header must use the correct application name."""

    def test_module_has_x_title_header(self):
        import inspect
        from src.optimizer_v3.core import ai_recommendation_enhancer as mod

        src = inspect.getsource(mod)
        assert "X-Title" in src

    def test_x_title_uses_new_name(self):
        import inspect
        from src.optimizer_v3.core import ai_recommendation_enhancer as mod

        src = inspect.getsource(mod)
        assert "BTC Trade Engine" in src
        assert "BTC Engine v3" not in src


class TestDataCacheManager:
    """src/optimizer_v3/core/data_cache_manager.py must use the correct name."""

    def test_docstring_author_uses_new_name(self):
        import inspect
        from src.optimizer_v3.core import data_cache_manager as mod

        src = inspect.getsource(mod)
        assert "BTC Trade Engine" in src
        assert "BTC Engine v3" not in src


class TestOptimizerDatabaseInit:
    """src/optimizer_v3/database/__init__.py __author__ must use new name."""

    def test_database_init_importable(self):
        from src.optimizer_v3.database import __doc__ as d

        assert d is not None

    def test_database_author_uses_new_name(self):
        from src.optimizer_v3.database import __author__ as a

        assert "BTC Trade Engine" in a

    def test_database_author_no_stale_name(self):
        from src.optimizer_v3.database import __author__ as a

        assert "BTC Engine v3" not in a


class TestMainWindowTitle:
    """The strategy builder main window must use the correct application name."""

    def test_main_window_file_exists(self):
        path = REPO_ROOT / "src" / "strategy_builder" / "ui" / "strategy_builder_main_window.py"
        assert path.exists()

    def test_main_window_title_contains_new_name(self):
        path = REPO_ROOT / "src" / "strategy_builder" / "ui" / "strategy_builder_main_window.py"
        text = path.read_text(encoding="utf-8")
        assert "BTC Trade Engine" in text

    def test_main_window_no_stale_name(self):
        path = REPO_ROOT / "src" / "strategy_builder" / "ui" / "strategy_builder_main_window.py"
        text = path.read_text(encoding="utf-8")
        assert "BTC Engine v3" not in text


class TestCodebaseNoStaleReferences:
    """Ensure no stale 'BTC Engine v3' references exist in the affected modules."""

    AFFECTED_PATHS = [
        "src/data_manager/__init__.py",
        "src/optimizer_v3/core/ai_recommendation_enhancer.py",
        "src/optimizer_v3/core/data_cache_manager.py",
        "src/optimizer_v3/database/__init__.py",
        "src/strategy_builder/ui/strategy_builder_main_window.py",
    ]

    @pytest.mark.parametrize("rel_path", AFFECTED_PATHS)
    def test_no_stale_reference_in_module(self, rel_path: str):
        path = REPO_ROOT / rel_path
        if not path.exists():
            pytest.skip(f"{rel_path} no longer exists — code may have been refactored")
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "BTC Engine v3" not in text, (
            f"Stale 'BTC Engine v3' reference found in {rel_path}"
        )

    @pytest.mark.parametrize("rel_path", AFFECTED_PATHS)
    def test_new_name_present_in_module(self, rel_path: str):
        path = REPO_ROOT / rel_path
        if not path.exists():
            pytest.skip(f"{rel_path} no longer exists — code may have been refactored")
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "BTC Trade Engine" in text, (
            f"'BTC Trade Engine' not found in {rel_path}"
        )

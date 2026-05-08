"""
conftest.py — test isolation fixtures for tests/strategy_builder/ui/

Provides:
  - A single shared ``qapp`` fixture (module-scoped) so every test module in
    this directory gets the same QApplication instance without creating
    redundant per-file fixture definitions.
  - A ``sys_modules_mock_guard`` autouse fixture (function-scoped) that detects
    when a test replaces a real module in ``sys.modules`` with a MagicMock and
    restores the original after the test completes.  Newly-imported real modules
    are NOT removed — only mock substitutions are reversed.

Background (BTCAAAAA-591):
  Earlier test files patched PyQt5 internals at session/module scope without
  proper teardown.  The leaked mocks caused 11 of 24 calibration-gate tests
  to fail when the full UI suite was run together, while the same 24 tests
  passed in isolation.  The conftest fixtures below ensure this can never
  happen again regardless of test-collection order.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock
import pytest

from PyQt5.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Shared QApplication fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def qapp():
    """Return (or create) the single QApplication for this test module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # QApplication must outlive all widgets — do NOT delete it here.


# ---------------------------------------------------------------------------
# sys.modules mock-substitution guard — prevents mock pollution between tests
# ---------------------------------------------------------------------------

def _is_mock(obj: object) -> bool:
    """Return True if *obj* looks like a unittest.mock object or a MagicMock-backed stub."""
    return isinstance(obj, MagicMock) or (
        isinstance(obj, types.ModuleType)
        and getattr(obj, "__spec__", None) is None
        and not hasattr(obj, "__file__")
        and type(obj).__name__ == "MagicMock"
    )


@pytest.fixture(autouse=True)
def sys_modules_mock_guard():
    """
    Restore sys.modules entries that are replaced with mock objects during a test.

    Strategy:
    - Before each test, snapshot the set of keys and their identity.
    - After the test, find any key whose value changed to a MagicMock (or
      mock-backed stub module) and restore the original value.
    - Newly added real-module entries are left in place (normal import side effects).
    - Newly added mock entries (key didn't exist before, now holds a mock) are removed.

    This guards against the class of bugs where a test does:
        sys.modules["PyQt5.QtCore"] = MagicMock(...)
    outside a ``patch.dict`` context manager and never restores the original.
    """
    # Snapshot: key -> (existed, original_value)
    snapshot: dict[str, tuple[bool, object]] = {
        key: (True, mod) for key, mod in sys.modules.items()
    }

    yield

    for key, mod in list(sys.modules.items()):
        if key in snapshot:
            existed, original = snapshot[key]
            if mod is not original and _is_mock(mod):
                # Real module was replaced with a mock — restore
                sys.modules[key] = original  # type: ignore[assignment]
        else:
            # Key did not exist before — if it's a mock, remove it
            if _is_mock(mod):
                del sys.modules[key]

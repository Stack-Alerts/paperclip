"""
Regression tests for BTCAAAAA-240: SettingsDialog must allow maximize and
must NOT set a fixed maximum size — the window must be freely resizable.

Issue: BTCAAAAA-240
Components:
  - src/strategy_builder/ui/settings_dialog.py

Fix:
1. Use Qt.Window (not Qt.Dialog / Qt.Tool) so the Settings window is an
   independent top-level window with a full OS title bar.
2. Add Qt.WindowMaximizeButtonHint explicitly for platforms that require it.
3. Do NOT call setMaximumSize — the window must be freely resizable so it
   can maximise to fill the screen on any monitor size.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-240"),
    pytest.mark.regression,
]

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[1]


def _settings_class_body() -> str:
    """Return the full SettingsDialog class body from source."""
    path = _REPO_ROOT / "src/strategy_builder/ui/settings_dialog.py"
    source = path.read_text(encoding="utf-8")
    cls_idx = source.index("class SettingsDialog(")
    end_idx = len(source)
    for kw in ("\nclass ", "\ndef ", "\nimport ", "\nfrom "):
        pos = source.find(kw, cls_idx + 1)
        if pos > 0 and pos < end_idx:
            end_idx = pos
    return source[cls_idx:end_idx]


def _super_init_block() -> str:
    """Extract the super().__init__(...) call block (may span multiple lines).

    The search skips past the ``super()`` call inside ``super().__init__``
    by starting the parenthesis-count from the ``__init__(`` paren.
    """
    body = _settings_class_body()
    # Find the opening paren of the __init__ call (after "super().__init__(")
    marker = "super().__init__("
    init_paren_idx = body.index(marker) + len(marker) - 1  # points to the '('
    # Walk forward counting paren depth starting from this paren
    depth = 0
    for i in range(init_paren_idx, len(body)):
        ch = body[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return body[init_paren_idx:i + 1]
    return body[init_paren_idx:]


class TestSettingsDialogWindowFlags:
    """Verify SettingsDialog uses Qt.Window with maximize button."""

    def test_uses_qt_window_not_dialog(self):
        block = _super_init_block()
        assert "Qt.Window" in block, "super().__init__ must use Qt.Window flag"
        assert "Qt.Dialog" not in block, (
            "super().__init__ must NOT use Qt.Dialog flag"
        )

    def test_has_windowmaximizebuttonhint(self):
        block = _super_init_block()
        assert "Qt.WindowMaximizeButtonHint" in block

    def test_has_windowminimizebuttonhint(self):
        block = _super_init_block()
        assert "Qt.WindowMinimizeButtonHint" in block

    def test_has_windowclosebuttonhint(self):
        block = _super_init_block()
        assert "Qt.WindowCloseButtonHint" in block

    def test_no_setmaximumsize_call(self):
        body = _settings_class_body()
        lines = body.split("\n")
        calls = [l.strip() for l in lines if ".setMaximumSize(" in l and not l.strip().startswith("#")]
        assert not calls, f"SettingsDialog must not call setMaximumSize(); found: {calls}"

    def test_no_setfixedsize_call(self):
        body = _settings_class_body()
        lines = body.split("\n")
        calls = [l.strip() for l in lines if ".setFixedSize(" in l and not l.strip().startswith("#")]
        assert not calls, f"SettingsDialog must not call setFixedSize(); found: {calls}"

    def test_uses_setminimumwidth(self):
        body = _settings_class_body()
        assert "self.setMinimumWidth(" in body

    def test_uses_setminimumheight(self):
        body = _settings_class_body()
        assert "self.setMinimumHeight(" in body

    def test_parent_is_none(self):
        block = _super_init_block()
        assert "None," in block or "None)" in block, (
            "super().__init__ must pass None as parent"
        )

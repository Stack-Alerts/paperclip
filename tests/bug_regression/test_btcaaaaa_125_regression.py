"""
Regression tests for BTCAAAAA-125: fix order of operations in auto-fix flow to
prevent duplicate dialogs and spurious "No Changes" save early-return.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-125
Components:
  - src/strategy_builder/ui/validation_report_window.py
  - src/strategy_builder/ui/strategy_builder_main_window.py

Root cause (dual):
  1. _handle_fix_click in validation_report_window emitted fix_applied signal
     BEFORE showing the success dialog. The signal synchronously called
     _on_save_strategy in the parent window, which could show its own
     "No Changes" dialog -- resulting in two sequential message boxes for
     the user.
  2. _on_validation_fix_applied in strategy_builder_main_window did not set
     self.is_modified = True before calling _on_save_strategy, causing it
     to short-circuit at the "No Changes" guard (line 1072-1079) and return
     early without persisting.

Fix:
  1. Show success dialog BEFORE emitting fix_applied signal
  2. Set self.is_modified = True before calling _on_save_strategy so the
     "No Changes" early-return path is not taken.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-125"),
    pytest.mark.regression,
]

REPORT_PATH = pathlib.Path("src/strategy_builder/ui/validation_report_window.py")
MAIN_PATH = pathlib.Path("src/strategy_builder/ui/strategy_builder_main_window.py")


class TestValidationReportDialogOrder:
    """Validate that _handle_fix_click shows dialog BEFORE emitting fix_applied."""

    HANDLE_FIX_CLICK = "_handle_fix_click"

    def _get_method_body_lines(self, path: pathlib.Path, method: str) -> list[str]:
        source = path.read_text()
        tree = ast.parse(source, str(path))
        srclines = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == method:
                return srclines[node.lineno - 1 : node.end_lineno]
        pytest.fail(f"{method} not found in {path}")

    def test_success_dialog_before_fix_applied_emit(self):
        """The dialog exec_ call must precede fix_applied.emit."""
        body = self._get_method_body_lines(REPORT_PATH, self.HANDLE_FIX_CLICK)
        body_text = "\n".join(body)

        emit_idx = None
        msg_idx = None
        for i, line in enumerate(body):
            if "fix_applied.emit" in line:
                emit_idx = i
            if "exec_()" in line:
                msg_idx = i

        assert msg_idx is not None, (
            "exec_() call must exist in _handle_fix_click"
        )
        assert emit_idx is not None, (
            "fix_applied.emit() must exist in _handle_fix_click"
        )
        assert msg_idx < emit_idx, (
            "dialog exec_() must appear BEFORE fix_applied.emit() -- "
            f"found msg at line offset {msg_idx}, emit at {emit_idx}"
        )

    def test_success_dialog_title_contains_check(self):
        """The success dialog window title should indicate success."""
        body_text = "\n".join(self._get_method_body_lines(REPORT_PATH, self.HANDLE_FIX_CLICK))
        assert "Fix Applied Successfully" in body_text, (
            "Success dialog title must indicate the fix was applied"
        )

    def test_emit_after_dialog_block(self):
        """The fix_applied.emit should be in the same 'if success:' block
        and placed after the dialog exec_ call."""
        body = self._get_method_body_lines(REPORT_PATH, self.HANDLE_FIX_CLICK)
        body_text = "\n".join(body)
        lines = body_text.splitlines()

        success_block_start = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "if success:":
                success_block_start = i
                break

        assert success_block_start is not None, "Must have 'if success:' block"
        exec_line = None
        emit_line = None
        for i in range(success_block_start + 1, len(lines)):
            if "exec_()" in lines[i]:
                exec_line = i
            if "fix_applied.emit" in lines[i]:
                emit_line = i

        assert exec_line is not None, "exec_() call must exist in success block"
        assert emit_line is not None, "fix_applied.emit must exist in success block"
        assert exec_line < emit_line, (
            "Dialog exec_() must be before fix_applied.emit() in the success block"
        )


class TestMainWindowIsModifiedGuard:
    """Validate that _on_validation_fix_applied sets is_modified before saving."""

    ON_VALIDATION_FIX_APPLIED = "_on_validation_fix_applied"

    def _get_method_body(self, path: pathlib.Path, method: str) -> str:
        source = path.read_text()
        tree = ast.parse(source, str(path))
        srclines = source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == method:
                return "\n".join(srclines[node.lineno - 1 : node.end_lineno])
        pytest.fail(f"{method} not found in {path}")

    def test_is_modified_set_before_save_call(self):
        """self.is_modified = True must appear before self._on_save_strategy()."""
        body = self._get_method_body(MAIN_PATH, self.ON_VALIDATION_FIX_APPLIED)
        lines = body.splitlines()

        modified_line = None
        save_call_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "self.is_modified = True" in stripped or "self.is_modified=True" in stripped:
                modified_line = i
            if "self._on_save_strategy()" in stripped:
                save_call_line = i

        assert modified_line is not None, (
            "self.is_modified = True must be set in _on_validation_fix_applied"
        )
        assert save_call_line is not None, (
            "self._on_save_strategy() must be called in _on_validation_fix_applied"
        )
        assert modified_line < save_call_line, (
            "self.is_modified = True must appear BEFORE self._on_save_strategy() -- "
            f"found modified at line offset {modified_line}, save at {save_call_line}"
        )

    def test_is_modified_assignment_exists(self):
        """Direct AST check for the assignment node."""
        source = MAIN_PATH.read_text()
        tree = ast.parse(source, str(MAIN_PATH))
        method_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.ON_VALIDATION_FIX_APPLIED:
                method_node = node
                break
        assert method_node is not None, f"{self.ON_VALIDATION_FIX_APPLIED} not found"

        found = False
        for node in ast.walk(method_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                        and target.attr == "is_modified"
                    ):
                        if isinstance(node.value, ast.Constant) and node.value.value is True:
                            found = True
        assert found, "self.is_modified = True assignment not found in method"

    def test_on_save_strategy_call_exists(self):
        """Direct AST check for _on_save_strategy call (as assignment or expr)."""
        source = MAIN_PATH.read_text()
        tree = ast.parse(source, str(MAIN_PATH))
        method_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.ON_VALIDATION_FIX_APPLIED:
                method_node = node
                break
        assert method_node is not None, f"{self.ON_VALIDATION_FIX_APPLIED} not found"

        def _is_on_save_strategy_call(node: ast.AST) -> bool:
            """Check if a node is a call to self._on_save_strategy."""
            if isinstance(node, ast.Call):
                func = node.func
                return (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "self"
                    and func.attr == "_on_save_strategy"
                )
            return False

        found = False
        for node in ast.walk(method_node):
            if _is_on_save_strategy_call(node):
                found = True
                break
            if isinstance(node, ast.Assign):
                if _is_on_save_strategy_call(node.value):
                    found = True
                    break
        assert found, "self._on_save_strategy() call not found in method"


class TestNoChangesGuard:
    """Validate that _on_save_strategy has the 'No Changes' early-return guard."""

    ON_SAVE_STRATEGY = "_on_save_strategy"

    def test_no_changes_guard_exists(self):
        """The 'No Changes' early-return must exist for context."""
        source = MAIN_PATH.read_text()
        tree = ast.parse(source, str(MAIN_PATH))
        method_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.ON_SAVE_STRATEGY:
                method_node = node
                break
        assert method_node is not None, f"{self.ON_SAVE_STRATEGY} not found"

        source_lines = source.splitlines()
        body = "\n".join(
            source_lines[method_node.lineno - 1 : method_node.end_lineno]
        )

        assert "if not self.is_modified:" in body, (
            "Must have 'if not self.is_modified:' guard"
        )
        assert "No Changes" in body, (
            "Guard must reference 'No Changes' dialog"
        )
        assert "return True" in body, (
            "Guard must have return True (early-return, not error)"
        )

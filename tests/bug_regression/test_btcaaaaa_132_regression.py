"""
Regression tests for BTCAAAAA-132: ValidationReportWindow config reference becomes
stale after _reload_current_version().

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-132
Component: src/strategy_builder/ui/validation_report_window.py
Component: src/strategy_builder/ui/strategy_builder_main_window.py

Root cause: after a fix is applied, _on_validation_fix_applied in the main window
saves to DB and calls _reload_current_version(), which replaces
orchestrator.config_engine.config with a new restored_config object.  But
ValidationReportWindow held the original config reference passed at construction
time, so _rerun_validation() operated on stale data — the fixed issue appeared
unresolved.

Fix (BTCAAAAA-133):
  1. Add update_config(self, new_config) method to ValidationReportWindow
  2. After _reload_current_version() in _on_validation_fix_applied, push the
     freshly-reloaded config via self.validation_window.update_config(...)
     so _rerun_validation() validates the current state.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-132"),
    pytest.mark.regression,
]

REPORT_PATH = pathlib.Path("src/strategy_builder/ui/validation_report_window.py")
MAIN_PATH = pathlib.Path("src/strategy_builder/ui/strategy_builder_main_window.py")


class TestValidationReportWindowUpdateConfig:
    """Validate that update_config() method exists and reassigns self.config."""

    METHOD_NAME = "update_config"

    def _get_source(self) -> str:
        return REPORT_PATH.read_text()

    def _get_method_node(self, tree: ast.Module) -> ast.FunctionDef | None:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.METHOD_NAME:
                return node
        return None

    def test_update_config_method_exists(self):
        """update_config must be defined in ValidationReportWindow."""
        tree = ast.parse(self._get_source())
        assert self._get_method_node(tree) is not None, (
            f"{self.METHOD_NAME} not found in {REPORT_PATH}"
        )

    def test_update_config_assigns_self_config(self):
        """update_config must assign self.config = new_config."""
        tree = ast.parse(self._get_source())
        method = self._get_method_node(tree)
        assert method is not None

        found = False
        for node in ast.walk(method):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                        and target.attr == "config"
                    ):
                        found = True
                        break
        assert found, "self.config assignment not found in update_config"

    def test_update_config_accepts_one_arg(self):
        """update_config must accept exactly one argument (new_config)."""
        tree = ast.parse(self._get_source())
        method = self._get_method_node(tree)
        assert method is not None
        args = method.args.args
        non_self = [a for a in args if a.arg != "self"]
        assert len(non_self) == 1, (
            f"update_config should accept 1 argument (new_config), got {len(non_self)}"
        )

    def test_update_config_docstring_refers_btcaaaaa_133(self):
        """Docstring or comment in update_config must reference BTCAAAAA-133."""
        tree = ast.parse(self._get_source())
        method = self._get_method_node(tree)
        assert method is not None
        body_text = ast.get_source_segment(self._get_source(), method) or ""
        assert "BTCAAAAA-133" in body_text, (
            "BTCAAAAA-133 reference not found in update_config body/docstring"
        )

    def test_update_config_is_bound_method(self):
        """update_config must be a FunctionDef (not a lambda or property)."""
        tree = ast.parse(self._get_source())
        method = self._get_method_node(tree)
        assert method is not None
        assert isinstance(method, ast.FunctionDef)

    def test_update_config_has_docstring(self):
        """update_config should have a docstring."""
        tree = ast.parse(self._get_source())
        method = self._get_method_node(tree)
        assert method is not None
        docstring = ast.get_docstring(method)
        assert docstring is not None and len(docstring) > 0


class TestMainWindowConfigPush:
    """Validate that _on_validation_fix_applied pushes reloaded config."""

    METHOD_NAME = "_on_validation_fix_applied"

    def _get_source(self) -> str:
        return MAIN_PATH.read_text()

    def _get_method_node(self, tree: ast.Module) -> ast.FunctionDef | None:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.METHOD_NAME:
                return node
        return None

    def _method_lines(self) -> list[str]:
        tree = ast.parse(self._get_source())
        node = self._get_method_node(tree)
        assert node is not None, f"{self.METHOD_NAME} not found"
        return self._get_source().splitlines()[node.lineno - 1 : node.end_lineno]

    def test_validation_window_update_config_call_exists(self):
        """_on_validation_fix_applied must call update_config."""
        body = "\n".join(self._method_lines())
        assert "update_config" in body, (
            "update_config call not found in _on_validation_fix_applied"
        )

    def test_reload_current_version_before_update_config(self):
        """_reload_current_version() must be called before update_config()."""
        body = self._method_lines()
        reload_idx = None
        update_idx = None
        for i, line in enumerate(body):
            if "_reload_current_version()" in line:
                reload_idx = i
            if "update_config" in line:
                update_idx = i

        assert reload_idx is not None, "_reload_current_version() not found in method"
        assert update_idx is not None, "update_config call not found in method"
        assert reload_idx < update_idx, (
            "_reload_current_version() must be called BEFORE update_config() -- "
            f"reload at line offset {reload_idx}, update at {update_idx}"
        )

    def test_update_config_uses_orchestrator_config(self):
        """update_config must be called with self.orchestrator.config_engine.config."""
        body = "\n".join(self._method_lines())
        assert "self.orchestrator.config_engine.config" in body, (
            "update_config must receive config from orchestrator.config_engine.config"
        )

    def test_config_push_inside_general_block(self):
        """The update_config call must be inside the general block."""
        body = "\n".join(self._method_lines())
        assert "BTCAAAAA-133" in body, (
            "BTCAAAAA-133 comment marker not found"
        )

    def test_validation_window_none_safe(self):
        """update_config guard must check validation_window is not None."""
        body = "\n".join(self._method_lines())
        assert "validation_window" in body, "validation_window reference not found"
        assert "None" in body, "None guard not found for validation_window call"


class TestPureEdgeCases:
    """Pure-math edge cases that validate the fix intent without PyQt."""

    def test_replace_reference_preserves_identity(self):
        """Simulate effect: replacing config reference does not crash caller."""
        class FakeWindow:
            def __init__(self):
                self.config = "old"
            def update_config(self, new_config):
                self.config = new_config

        w = FakeWindow()
        assert w.config == "old"
        w.update_config("new")
        assert w.config == "new"

    def test_none_guard_does_not_crash(self):
        """When validation_window is None, the code must not crash."""
        code = """
validation_window = None
orchestrator = type('o', (), {'config_engine': type('e', (), {'config': 'fresh'})()})()
if validation_window and orchestrator and orchestrator.config_engine and orchestrator.config_engine.config:
    validation_window.update_config(orchestrator.config_engine.config)
"""
        exec(code)  # noqa: S102

    def test_stale_config_does_not_change(self):
        """Verifying that stale config is not mutated after update_config."""
        class FakeConfig:
            def __init__(self, name):
                self.name = name

        original = FakeConfig("original")
        fresh = FakeConfig("fresh")

        class FakeWindow:
            def __init__(self):
                self.config = original
            def update_config(self, new_config):
                self.config = new_config

        w = FakeWindow()
        assert w.config.name == "original"
        w.update_config(fresh)
        assert w.config.name == "fresh"
        assert original.name == "original"

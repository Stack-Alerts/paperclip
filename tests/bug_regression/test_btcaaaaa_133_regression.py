"""
Regression tests for BTCAAAAA-133: Push freshly-reloaded config to
ValidationReportWindow so _rerun_validation does not use stale reference.

Issue: BTCAAAAA-133
Components:
  - src/strategy_builder/ui/validation_report_window.py (update_config)
  - src/strategy_builder/ui/strategy_builder_main_window.py
    (_on_validation_fix_applied update_config call after _reload_current_version)

Root cause: After _reload_current_version() replaces orchestrator.config_engine.config
with a freshly-restored object from the database, ValidationReportWindow still held
the old config reference. Subsequent _rerun_validation() would validate stale data
and the fixed issue would appear not to have been resolved.

Fix:
  1. Add ValidationReportWindow.update_config(new_config) method
  2. Call it from _on_validation_fix_applied after _reload_current_version()
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-133"),
    pytest.mark.regression,
]

REPORT_PATH = pathlib.Path("src/strategy_builder/ui/validation_report_window.py")
MAIN_PATH = pathlib.Path("src/strategy_builder/ui/strategy_builder_main_window.py")


class TestUpdateConfigMethod:
    """Validate that ValidationReportWindow.update_config exists and works."""

    UPDATE_CONFIG = "update_config"

    def test_update_config_method_exists(self):
        """update_config must be a method on ValidationReportWindow."""
        source = REPORT_PATH.read_text()
        tree = ast.parse(source, str(REPORT_PATH))
        method_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        assert self.UPDATE_CONFIG in method_names, (
            f"{self.UPDATE_CONFIG} method not found in {REPORT_PATH}"
        )

    def test_update_config_sets_self_config(self):
        """update_config must assign new_config to self.config."""
        source = REPORT_PATH.read_text()
        tree = ast.parse(source, str(REPORT_PATH))
        method_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.UPDATE_CONFIG:
                method_node = node
                break
        assert method_node is not None, f"{self.UPDATE_CONFIG} not found"

        has_self_config_assign = False
        for node in ast.walk(method_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                        and target.attr == "config"
                    ):
                        has_self_config_assign = True
                        break
        assert has_self_config_assign, (
            "update_config must assign self.config = new_config"
        )

    def test_update_config_accepts_one_arg(self):
        """update_config(self, new_config) must accept exactly one arg besides self."""
        source = REPORT_PATH.read_text()
        tree = ast.parse(source, str(REPORT_PATH))
        method_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.UPDATE_CONFIG:
                method_node = node
                break
        assert method_node is not None
        assert len(method_node.args.args) == 2, (
            f"update_config should have exactly 2 args (self, new_config), "
            f"got {len(method_node.args.args)}"
        )
        assert method_node.args.args[1].arg == "new_config", (
            f"Second parameter should be named 'new_config', "
            f"got '{method_node.args.args[1].arg}'"
        )


class TestMainWindowUpdateConfigCall:
    """Validate that _on_validation_fix_applied calls update_config after reload."""

    ON_VALIDATION_FIX_APPLIED = "_on_validation_fix_applied"

    def test_update_config_called_after_reload(self):
        """update_config must be called after _reload_current_version()."""
        source = MAIN_PATH.read_text()
        tree = ast.parse(source, str(MAIN_PATH))
        method_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.ON_VALIDATION_FIX_APPLIED:
                method_node = node
                break
        assert method_node is not None, f"{self.ON_VALIDATION_FIX_APPLIED} not found"

        srclines = source.splitlines()
        body = srclines[method_node.lineno - 1 : method_node.end_lineno]

        reload_line = None
        update_config_line = None
        for i, line in enumerate(body):
            stripped = line.strip()
            if "_reload_current_version()" in stripped:
                reload_line = i
            if "update_config(" in stripped:
                update_config_line = i

        assert reload_line is not None, (
            "_reload_current_version() must be called in _on_validation_fix_applied"
        )
        assert update_config_line is not None, (
            "update_config() must be called in _on_validation_fix_applied"
        )
        assert reload_line < update_config_line, (
            "update_config() must appear AFTER _reload_current_version() -- "
            f"found reload at line offset {reload_line}, "
            f"update_config at {update_config_line}"
        )

    def test_update_config_receives_orchestrator_config(self):
        """update_config must receive orchestrator.config_engine.config."""
        source = MAIN_PATH.read_text()
        tree = ast.parse(source, str(MAIN_PATH))
        method_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.ON_VALIDATION_FIX_APPLIED:
                method_node = node
                break
        assert method_node is not None

        source_lines = source.splitlines()
        body = "\n".join(source_lines[method_node.lineno - 1 : method_node.end_lineno])
        assert "self.orchestrator.config_engine.config" in body, (
            "update_config must receive orchestrator.config_engine.config as argument"
        )

    def test_update_config_inside_guard_block(self):
        """The update_config call must be inside the 'if success:' body."""
        source = MAIN_PATH.read_text()
        tree = ast.parse(source, str(MAIN_PATH))
        method_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.ON_VALIDATION_FIX_APPLIED:
                method_node = node
                break
        assert method_node is not None

        srclines = source.splitlines()
        body_lines = srclines[method_node.lineno - 1 : method_node.end_lineno]

        success_block_start = None
        for i, line in enumerate(body_lines):
            stripped = line.strip()
            if stripped == "if success:":
                success_block_start = i
                break

        assert success_block_start is not None, "Must have 'if success:' block"

        found_reload = False
        found_update_config = False
        for i in range(success_block_start + 1, len(body_lines)):
            stripped = body_lines[i].strip()
            if "_reload_current_version()" in stripped:
                found_reload = True
            if "update_config(" in stripped:
                found_update_config = True

        assert found_reload, (
            "_reload_current_version() must be in the success block"
        )
        assert found_update_config, (
            "update_config() must be in the success block"
        )

    def test_btcaaaaa_133_comment_ref_in_source(self):
        """The BTCAAAAA-133 reference comment must exist in the source."""
        source = MAIN_PATH.read_text()
        assert "BTCAAAAA-133" in source, (
            "BTCAAAAA-133 reference comment must exist in strategy_builder_main_window.py"
        )

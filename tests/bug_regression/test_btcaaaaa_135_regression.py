"""
Regression tests for BTCAAAAA-135: Sync the full fixed config from
validation_window into orchestrator for ALL fix types.

Issue: BTCAAAAA-135
Components:
  - src/strategy_builder/ui/strategy_builder_main_window.py
    (_on_validation_fix_applied)

Root cause: _on_validation_fix_applied only synced the config for
DIRECTION_001 fix type.  For other fix types (EXIT_009, LOGIC_003,
TIMING_004) the orchestrator still held stale config, so _on_save_strategy()
would persist the unfixed version.

Fix:
  1. Unconditionally sync orchestrator.config_engine.config from
     self.validation_window.config for ALL fix types.
  2. Sync strategy_type to info_panel so UI reflects the change.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-135"),
    pytest.mark.regression,
]

MAIN_PATH = pathlib.Path("src/strategy_builder/ui/strategy_builder_main_window.py")

ON_VALIDATION_FIX_APPLIED = "_on_validation_fix_applied"


def _get_method_body_lines(path: pathlib.Path, method: str) -> list[str]:
    source = path.read_text()
    tree = ast.parse(source, str(path))
    srclines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method:
            return srclines[node.lineno - 1 : node.end_lineno]
    pytest.fail(f"{method} not found in {path}")


class TestConfigSyncExists:
    """Validate the orchestrator config sync block exists in _on_validation_fix_applied."""

    def test_btcaaaaa_135_comment_ref_exists(self):
        """The BTCAAAAA-135 reference comment must exist in the source."""
        source = MAIN_PATH.read_text()
        assert "BTCAAAAA-135" in source, (
            "BTCAAAAA-135 reference comment must exist in strategy_builder_main_window.py"
        )

    def test_orchestrator_config_sync_guard_exists(self):
        """The guard condition for the sync block must check validation_window and orchestrator."""
        body = _get_method_body_lines(MAIN_PATH, ON_VALIDATION_FIX_APPLIED)
        body_text = "\n".join(body)
        assert "self.validation_window" in body_text, (
            "Must reference self.validation_window in the sync block"
        )
        assert "self.orchestrator" in body_text, (
            "Must reference self.orchestrator in the sync block"
        )
        assert "self.orchestrator.config_engine" in body_text, (
            "Must reference self.orchestrator.config_engine in the sync block"
        )

    def test_config_assign_via_orchestrator(self):
        """The sync must assign orchestrator.config_engine.config = fixed_config."""
        body = _get_method_body_lines(MAIN_PATH, ON_VALIDATION_FIX_APPLIED)
        body_text = "\n".join(body)
        assert "self.orchestrator.config_engine.config" in body_text, (
            "Must assign orchestrator.config_engine.config in the sync block"
        )
        assert "self.validation_window.config" in body_text, (
            "Config must come from self.validation_window.config"
        )

    def test_strategy_type_synced_to_info_panel(self):
        """The sync must set strategy_type on info_panel."""
        body = _get_method_body_lines(MAIN_PATH, ON_VALIDATION_FIX_APPLIED)
        body_text = "\n".join(body)
        assert "self.info_panel.set_strategy_type(fixed_type)" in body_text, (
            "Must call info_panel.set_strategy_type with the synced type"
        )

    def test_fixed_type_uses_getattr(self):
        """The strategy_type must be extracted via getattr."""
        body = _get_method_body_lines(MAIN_PATH, ON_VALIDATION_FIX_APPLIED)
        body_text = "\n".join(body)
        assert "getattr(fixed_config, 'strategy_type', None)" in body_text, (
            "Must use getattr to safely extract strategy_type from fixed_config"
        )

    def test_config_sync_before_save_call(self):
        """The config sync block must appear BEFORE self._on_save_strategy()."""
        body = _get_method_body_lines(MAIN_PATH, ON_VALIDATION_FIX_APPLIED)
        lines = body

        guard_start = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "self.orchestrator.config_engine.config" in stripped:
                guard_start = i
                break

        save_call_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "self._on_save_strategy()" in stripped:
                save_call_line = i
                break

        assert guard_start is not None, (
            "orchestrator config assignment must exist in the method"
        )
        assert save_call_line is not None, (
            "self._on_save_strategy() must exist in the method"
        )
        assert guard_start < save_call_line, (
            "Config sync block must appear BEFORE _on_save_strategy() -- "
            f"config sync at line offset {guard_start}, "
            f"save call at {save_call_line}"
        )

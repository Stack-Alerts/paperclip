"""
Regression tests for BTCAAAAA-146: Stale-version display in Strategy Browser.

Issue: BTCAAAAA-146
Components:
  - src/strategy_builder/ui/strategy_browser_dialog.py (_on_table_version_changed)
  - src/optimizer_v3/database/strategy_manager.py (get_strategy_version)
  - src/strategy_builder/ui/strategy_builder_main_window.py (_on_save_strategy, _on_save_strategy_as)

Root cause (triple bug):
  1. _on_table_version_changed used table.currentRow() which returns -1 when the
     combo popup steals table focus. Fixed: use selectedItems() and unconditionally
     refresh the details panel.
  2. get_strategy_version() did not expire the ORM identity-map, returning stale
     cached data. Fixed: call session.expire_all() so SQLAlchemy issues a fresh SELECT.
     (rollback is only in the except handler for error recovery, not the happy path.)
  3. Both _on_save_strategy and _on_save_strategy_as passed bare references from
     config_dict into version_data, allowing in-place mutation of saved version rows
     via the SQLAlchemy session. Fixed: use copy.deepcopy() for JSONB fields.
     _on_save_strategy_as also saved exit_conditions as {} instead of reading from
     config_dict. Fixed: deepcopy config_dict.get('exit_conditions', []).
"""

from __future__ import annotations

import ast
import pathlib

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-146"),
    pytest.mark.regression,
]

BROWSER_PATH = pathlib.Path("src/strategy_builder/ui/strategy_browser_dialog.py")
MANAGER_PATH = pathlib.Path("src/optimizer_v3/database/strategy_manager.py")
MAIN_PATH = pathlib.Path("src/strategy_builder/ui/strategy_builder_main_window.py")

ON_TABLE_VERSION_CHANGED = "_on_table_version_changed"
GET_STRATEGY_VERSION = "get_strategy_version"
ON_SAVE_STRATEGY = "_on_save_strategy"
ON_SAVE_STRATEGY_AS = "_on_save_strategy_as"


def _get_method_body_lines(path: pathlib.Path, method: str) -> list[str]:
    source = path.read_text()
    tree = ast.parse(source, str(path))
    srclines = source.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method:
            return srclines[node.lineno - 1 : node.end_lineno]
    pytest.fail(f"{method} not found in {path}")


def _strip_comments(line: str) -> str:
    idx = line.find("#")
    if idx == -1:
        return line
    return line[:idx]


# ---------------------------------------------------------------------------
# Bug 1: _on_table_version_changed — selectedItems() vs currentRow()
# ---------------------------------------------------------------------------

class TestBrowserVersionChangedSelectedItems:
    """Validate _on_table_version_changed uses selectedItems() instead of currentRow()."""

    def test_uses_selected_items_not_current_row(self):
        """The method must use selectedItems() rather than currentRow() in code (comments ok)."""
        body = _get_method_body_lines(BROWSER_PATH, ON_TABLE_VERSION_CHANGED)
        code_lines = [_strip_comments(l) for l in body]
        code_text = "\n".join(code_lines)
        assert "selectedItems()" in code_text
        assert "currentRow()" not in code_text

    def test_selected_rows_set_comprehension(self):
        """The selected_rows must be built from a set comprehension over selectedItems()."""
        body = _get_method_body_lines(BROWSER_PATH, ON_TABLE_VERSION_CHANGED)
        body_text = "\n".join(body)
        assert "{item.row() for item in self.table.selectedItems()}" in body_text

    def test_unconditional_details_panel_refresh(self):
        """_populate_details_panel must be called for BOTH selected and non-selected rows."""
        body = _get_method_body_lines(BROWSER_PATH, ON_TABLE_VERSION_CHANGED)
        body_text = "\n".join(body)
        count = body_text.count("self._populate_details_panel(version_id)")
        assert count >= 2

    def test_selected_version_id_only_updated_when_selected(self):
        """selected_version_id must only be updated when the row is selected."""
        body = _get_method_body_lines(BROWSER_PATH, ON_TABLE_VERSION_CHANGED)
        assign_lines = [
            i for i, l in enumerate(body)
            if "self.selected_version_id" in _strip_comments(l) and "=" in _strip_comments(l)
        ]
        assert len(assign_lines) == 1
        if_block_line = assign_line = None
        for i, l in enumerate(body):
            stripped = _strip_comments(l)
            if stripped.strip().startswith("if ") and "row_is_selected" in stripped:
                if_block_line = i
            if "self.selected_version_id" in stripped and "=" in stripped:
                assign_line = i
        assert if_block_line is not None
        assert assign_line is not None
        assert assign_line > if_block_line


# ---------------------------------------------------------------------------
# Bug 2: strategy_manager get_strategy_version — expire_all() for fresh SELECT
# ---------------------------------------------------------------------------

class TestGetStrategyVersionExpireAll:
    """Validate get_strategy_version uses expire_all() to avoid stale ORM cache."""

    def test_expire_all_called_before_query(self):
        """expire_all() must be called before the ORM SELECT in get_strategy_version."""
        body = _get_method_body_lines(MANAGER_PATH, GET_STRATEGY_VERSION)
        expire_line = query_line = None
        for i, line in enumerate(body):
            stripped = _strip_comments(line)
            if "self.session.expire_all()" in stripped:
                expire_line = i
            if "self.session.query" in stripped or ".query(" in stripped:
                query_line = i
        assert expire_line is not None
        assert query_line is not None
        assert expire_line < query_line

    def test_expire_all_replaces_unconditional_rollback(self):
        """The happy path must use expire_all(), not rollback() (rollback only in except)."""
        body = _get_method_body_lines(MANAGER_PATH, GET_STRATEGY_VERSION)
        code_lines = [_strip_comments(l) for l in body]
        # Find the try block
        try_line = None
        except_line = None
        for i, line in enumerate(code_lines):
            if line.strip() == "try:":
                try_line = i
            if line.strip().startswith("except "):
                except_line = i
        assert try_line is not None, "try block must exist"
        assert except_line is not None, "except block must exist"
        # Rollback in except-handler is OK (error recovery)
        # But rollback must NOT appear in the happy path (before the except)
        for i in range(except_line):
            if "self.session.rollback()" in code_lines[i]:
                pytest.fail(
                    "self.session.rollback() must NOT appear before the except block — "
                    "only expire_all() should be in the happy path"
                )

    def test_expire_all_comment_exists(self):
        """The comment explaining expire_all() must be present."""
        source = MANAGER_PATH.read_text()
        assert "expire_all" in source


# ---------------------------------------------------------------------------
# Bug 3: _on_save_strategy / _on_save_strategy_as — deepcopy + exit_conditions
# ---------------------------------------------------------------------------

class TestOnSaveStrategyDeepcopy:
    """Validate _on_save_strategy uses copy.deepcopy() for JSONB fields."""

    def test_deepcopy_import_exists(self):
        """copy.deepcopy must be importable in strategy_builder_main_window.py."""
        source = MAIN_PATH.read_text()
        tree = ast.parse(source, str(MAIN_PATH))
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "copy":
                for alias in node.names:
                    if alias.name == "deepcopy":
                        found = True
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "copy":
                        found = True
        assert found

    def test_blocks_deepcopy_in_on_save_strategy(self):
        """blocks must be deepcopied in _on_save_strategy version_data."""
        body = _get_method_body_lines(MAIN_PATH, ON_SAVE_STRATEGY)
        body_text = "\n".join(body)
        assert "copy.deepcopy(config_dict.get('blocks', []))" in body_text

    def test_exit_conditions_deepcopy_in_on_save_strategy(self):
        """exit_conditions must be deepcopied in _on_save_strategy version_data."""
        body = _get_method_body_lines(MAIN_PATH, ON_SAVE_STRATEGY)
        body_text = "\n".join(body)
        assert "copy.deepcopy(config_dict.get('exit_conditions', []))" in body_text


class TestOnSaveStrategyAsDeepcopy:
    """Validate _on_save_strategy_as uses copy.deepcopy() for JSONB fields."""

    def test_blocks_deepcopy_in_on_save_strategy_as(self):
        """blocks must be deepcopied in _on_save_strategy_as version_data."""
        body = _get_method_body_lines(MAIN_PATH, ON_SAVE_STRATEGY_AS)
        body_text = "\n".join(body)
        assert "copy.deepcopy(config_dict.get('blocks', []))" in body_text

    def test_exit_conditions_deepcopy_in_on_save_strategy_as(self):
        """exit_conditions must be deepcopied (not {}) in _on_save_strategy_as."""
        body = _get_method_body_lines(MAIN_PATH, ON_SAVE_STRATEGY_AS)
        body_text = "\n".join(body)
        assert "copy.deepcopy(config_dict.get('exit_conditions', []))" in body_text

    def test_exit_conditions_not_empty_dict(self):
        """exit_conditions must NOT be assigned as {} in _on_save_strategy_as."""
        body = _get_method_body_lines(MAIN_PATH, ON_SAVE_STRATEGY_AS)
        code_lines = [_strip_comments(l) for l in body]
        for line in code_lines:
            if "'exit_conditions': {}" in line or '"exit_conditions": {}' in line:
                pytest.fail("exit_conditions must NOT be {} in _on_save_strategy_as")

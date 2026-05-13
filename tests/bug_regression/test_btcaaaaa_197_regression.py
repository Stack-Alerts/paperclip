"""
Regression tests for BTCAAAAA-197: Replace datetime.utcnow() with datetime.now(timezone.utc).

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-197
Component: Multiple files across src/ (7 files, 13 occurrences)

Root cause: 13 deprecated datetime.utcnow() calls across 7 files would emit
DeprecationWarning under Python 3.12+ and could cause subtle comparison bugs
with timezone-aware datetimes. All were migrated to datetime.now(timezone.utc).

The fix also added ruff rule DTZ003 to pyproject.toml to gate reintroduction
in CI.

This regression test:
1. Verifies the DTZ003 ruff rule is still present in pyproject.toml
2. Scans the 7 files that were part of the fix for any reintroduced
   datetime.utcnow() calls using AST analysis
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-197"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT_TOML = REPO_ROOT / "pyproject.toml"

# The 7 source files that were part of the BTCAAAAA-197 fix.
# These should never re-introduce datetime.utcnow().
FIXED_FILES = [
    REPO_ROOT / "src" / "data_manager" / "binance" / "rest_client.py",
    REPO_ROOT / "src" / "optimizer_v3" / "database" / "ai_recommendations_manager.py",
    REPO_ROOT / "src" / "optimizer_v3" / "database" / "manager.py",
    REPO_ROOT / "src" / "optimizer_v3" / "database" / "strategy_manager.py",
    REPO_ROOT / "src" / "strategy_builder" / "ui" / "data_verify_dialog.py",
    REPO_ROOT / "src" / "strategy_builder" / "ui" / "strategy_builder_main_window.py",
    REPO_ROOT / "src" / "strategy_builder" / "ui" / "validation_panel.py",
]


class TestDTZ003RuffRule:
    """The CI gate — DTZ003 must be in pyproject.toml's ruff select list."""

    def _read_pyproject(self) -> str:
        return PYPROJECT_TOML.read_text(encoding="utf-8")

    def test_dtz003_in_ruff_select(self):
        content = self._read_pyproject()
        assert "DTZ003" in content, (
            "DTZ003 missing from pyproject.toml — the CI gate that prevents "
            "reintroduction of datetime.utcnow() has been removed. "
            "See BTCAAAAA-197 for context."
        )


class TestNoUtcnowInFixedFiles:
    """The 7 files fixed by BTCAAAAA-197 must not regress."""

    def _find_utcnow_calls(self, filepath: Path) -> list[tuple[int, str]]:
        violations: list[tuple[int, str]] = []
        try:
            text = filepath.read_text(encoding="utf-8")
        except Exception:
            return violations

        lines = text.split("\n")

        if "utcnow" not in text:
            return violations

        try:
            tree = ast.parse(text, filename=str(filepath))
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            attr = None

            if isinstance(func, ast.Attribute) and func.attr == "utcnow":
                attr = func.attr
            elif isinstance(func, ast.Name) and func.id == "utcnow":
                attr = func.id

            if attr is None:
                continue

            lineno = node.lineno
            if lineno < 1 or lineno > len(lines):
                continue
            line = lines[lineno - 1]

            if "# noqa: DTZ003" in line:
                continue

            violations.append((lineno, line.strip()))

        return violations

    def test_no_datetime_utcnow_in_fixed_files(self):
        all_violations: list[tuple[str, int, str]] = []

        for filepath in FIXED_FILES:
            if not filepath.exists():
                continue
            violations = self._find_utcnow_calls(filepath)
            for lineno, line in violations:
                rel = str(filepath.relative_to(REPO_ROOT))
                all_violations.append((rel, lineno, line))

        if all_violations:
            msg_lines = [
                f"Found {len(all_violations)} datetime.utcnow() call(s) in files "
                "fixed by BTCAAAAA-197:",
                "",
            ]
            for fp, ln, line in all_violations:
                msg_lines.append(f"  {fp}:{ln}: {line}")
            msg_lines.append(
                "\nBTCAAAAA-197 replaced all datetime.utcnow() with "
                "datetime.now(timezone.utc) in these files. "
                "Use datetime.now(timezone.utc) instead, or add "
                "'# noqa: DTZ003' to exempt an intentional call."
            )
            pytest.fail("\n".join(msg_lines))

"""
Regression tests for BTCAAAAA-197: Replace datetime.utcnow() with datetime.now(timezone.utc).

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-197
Component: Multiple files across src/ (7 files, 13 occurrences)

Root cause: 13 deprecated datetime.utcnow() calls across 7 files would emit
DeprecationWarning under Python 3.12+ and could cause subtle comparison bugs
with timezone-aware datetimes. All were migrated to datetime.now(timezone.utc).

The fix also added ruff rule DTZ003 to pyproject.toml to gate reintroduction.

This regression test suite (10+ tests, impact gate bar):
1. Verifies ruff DTZ003 rule is present in pyproject.toml
2. Scans the 7 fixed files for reintroduced deprecated datetime calls (utcnow, utcfromtimestamp)
3. Verifies datetime.now() calls in fixed files pass timezone
4. Scans entire src/ tree for datetime.utcnow() reintroduction
5. Checks test files for deprecated datetime usage
6. Validates timezone-aware patterns in the 7 fixed files
"""
from __future__ import annotations

import ast
from pathlib import Path
from datetime import timezone

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-197"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT_TOML = REPO_ROOT / "pyproject.toml"
SRC_DIR = REPO_ROOT / "src"
TEST_DIR = REPO_ROOT / "tests"

FIXED_FILES = [
    REPO_ROOT / "src" / "data_manager" / "binance" / "rest_client.py",
    REPO_ROOT / "src" / "optimizer_v3" / "database" / "ai_recommendations_manager.py",
    REPO_ROOT / "src" / "optimizer_v3" / "database" / "manager.py",
    REPO_ROOT / "src" / "optimizer_v3" / "database" / "strategy_manager.py",
    REPO_ROOT / "src" / "strategy_builder" / "ui" / "data_verify_dialog.py",
    REPO_ROOT / "src" / "strategy_builder" / "ui" / "strategy_builder_main_window.py",
    REPO_ROOT / "src" / "strategy_builder" / "ui" / "validation_panel.py",
]


def _read_pyproject() -> str:
    return PYPROJECT_TOML.read_text(encoding="utf-8")


def _ast_find_calls(
    filepath: Path,
    attr_names: set[str],
    noqa_tag: str | None = None,
) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return violations

    lines = text.split("\n")
    if not any(name in text for name in attr_names):
        return violations

    try:
        tree = ast.parse(text, filename=str(filepath))
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        matched = None
        if isinstance(func, ast.Attribute) and func.attr in attr_names:
            matched = func.attr
        elif isinstance(func, ast.Name) and func.id in attr_names:
            matched = func.id
        if matched is None:
            continue
        lineno = node.lineno
        if lineno < 1 or lineno > len(lines):
            continue
        line = lines[lineno - 1]
        if noqa_tag and noqa_tag in line:
            continue
        violations.append((lineno, line.strip()))

    return violations


def _collect_violations(
    files: list[Path],
    attr_names: set[str],
    noqa_tag: str | None = None,
) -> list[tuple[str, int, str]]:
    results: list[tuple[str, int, str]] = []
    for filepath in files:
        if not filepath.exists():
            continue
        violations = _ast_find_calls(filepath, attr_names, noqa_tag)
        for lineno, line in violations:
            rel = str(filepath.relative_to(REPO_ROOT))
            results.append((rel, lineno, line))
    return results


def _all_py_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.py"))


def _fail_violations(
    violations: list[tuple[str, int, str]],
    pattern_name: str,
    fix_advice: str,
) -> None:
    msg_lines = [
        f"Found {len(violations)} {pattern_name} call(s):",
        "",
    ]
    for fp, ln, line in violations:
        msg_lines.append(f"  {fp}:{ln}: {line}")
    msg_lines.append("")
    msg_lines.append(fix_advice)
    pytest.fail("\n".join(msg_lines))


# ---------------------------------------------------------------------------
# RUFF DTZ003 rule gate
# ---------------------------------------------------------------------------


class TestDTZ003RuffRule:
    """DTZ003 must be in pyproject.toml's ruff select list."""

    def test_dtz003_in_ruff_select(self) -> None:
        content = _read_pyproject()
        assert "DTZ003" in content, (
            "DTZ003 missing from pyproject.toml - the CI gate that prevents "
            "reintroduction of datetime.utcnow() has been removed. "
            "See BTCAAAAA-197 for context."
        )

    def test_ruff_config_comments_reference_utcnow_ban(self) -> None:
        """The pyproject.toml comments about DTZ003 should remain descriptive."""
        content = _read_pyproject()
        assert "utcnow" in content.lower(), (
            "pyproject.toml ruff config comment should mention utcnow to "
            "document why DTZ003 exists."
        )

    def test_t201_rule_still_present(self) -> None:
        """T201 (ban print()) should still be in ruff select alongside DTZ003."""
        content = _read_pyproject()
        assert "T201" in content, (
            "T201 missing from pyproject.toml ruff select. "
            "This was added alongside DTZ003 as part of the CI lint gate."
        )


# ---------------------------------------------------------------------------
# AST scans of the 7 fixed files
# ---------------------------------------------------------------------------


class TestNoDeprecatedUtcInFixedFiles:
    """The 7 files fixed by BTCAAAAA-197 must not regress."""

    def test_no_datetime_utcnow_in_fixed_files(self) -> None:
        all_violations = _collect_violations(
            FIXED_FILES, {"utcnow"}, noqa_tag="DTZ003"
        )
        if all_violations:
            _fail_violations(
                all_violations,
                "datetime.utcnow()",
                "Use datetime.now(timezone.utc) instead, or add "
                "'# noqa: DTZ003' to exempt an intentional call.",
            )

    def test_no_utcfromtimestamp_in_fixed_files(self) -> None:
        all_violations = _collect_violations(FIXED_FILES, {"utcfromtimestamp"})
        if all_violations:
            _fail_violations(
                all_violations,
                "datetime.utcfromtimestamp()",
                "Use datetime.fromtimestamp(ts, tz=timezone.utc) instead.",
            )

    def test_fixed_files_use_now_with_timezone_arg(self) -> None:
        for filepath in FIXED_FILES:
            if not filepath.exists():
                continue
            text = filepath.read_text(encoding="utf-8")
            if "datetime.now" not in text:
                continue
            try:
                tree = ast.parse(text, filename=str(filepath))
            except SyntaxError:
                continue
            lines = text.split("\n")
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (isinstance(func, ast.Attribute) and func.attr == "now"):
                    continue
                if not node.args and not node.keywords:
                    lineno = node.lineno
                    line = lines[lineno - 1].strip() if 0 < lineno <= len(lines) else ""
                    pytest.fail(
                        f"{filepath.relative_to(REPO_ROOT)}:{lineno}: "
                        f"datetime.now() without timezone argument: {line}"
                    )

    def test_fixed_files_import_timezone(self) -> None:
        for filepath in FIXED_FILES:
            if not filepath.exists():
                continue
            text = filepath.read_text(encoding="utf-8")
            if "timezone" not in text and "utc" not in text:
                continue
            if "from datetime import" not in text:
                continue
            has_timezone = "timezone" in text
            has_utc_import = "timezone.utc" in text or "import timezone" in text
            assert has_timezone or has_utc_import, (
                f"{filepath.relative_to(REPO_ROOT)} uses timezone-related "
                f"code but may not import timezone properly."
            )

    def test_fixed_files_do_not_import_pytz_utc(self) -> None:
        for filepath in FIXED_FILES:
            if not filepath.exists():
                continue
            text = filepath.read_text(encoding="utf-8")
            if "pytz.utc" in text or "from pytz" in text:
                rel = filepath.relative_to(REPO_ROOT)
                pytest.fail(
                    f"{rel} imports pytz instead of using "
                    f"datetime.timezone.utc. pytz is an extra dependency; "
                    f"stdlib timezone.utc should be preferred."
                )


# ---------------------------------------------------------------------------
# Entire src/ tree scan
# ---------------------------------------------------------------------------


class TestNoUtcnowInSrcTree:
    """No datetime.utcnow() anywhere in src/."""

    def test_no_utcnow_in_src(self) -> None:
        src_files = _all_py_files(SRC_DIR)
        all_violations = _collect_violations(
            src_files, {"utcnow"}, noqa_tag="DTZ003"
        )
        if all_violations:
            _fail_violations(
                all_violations,
                "datetime.utcnow()",
                "datetime.utcnow() is forbidden in all src/ files. "
                "Use datetime.now(timezone.utc) instead.",
            )

    def test_no_utcfromtimestamp_in_src(self) -> None:
        src_files = _all_py_files(SRC_DIR)
        all_violations = _collect_violations(src_files, {"utcfromtimestamp"})
        if all_violations:
            _fail_violations(
                all_violations,
                "datetime.utcfromtimestamp()",
                "datetime.utcfromtimestamp() is deprecated. "
                "Use datetime.fromtimestamp(ts, tz=timezone.utc) instead.",
            )


# ---------------------------------------------------------------------------
# Test file scans
# ---------------------------------------------------------------------------


class TestNoDeprecatedUtcInTestFiles:
    """Test files should also avoid deprecated datetime utc functions."""

    def test_no_utcnow_in_bug_regression_tests(self) -> None:
        bug_dir = TEST_DIR / "bug_regression"
        if not bug_dir.exists():
            return
        files = list(bug_dir.rglob("*.py"))
        all_violations = _collect_violations(
            files, {"utcnow"}, noqa_tag="DTZ003"
        )
        if all_violations:
            _fail_violations(
                all_violations,
                "datetime.utcnow() in bug regression test file",
                "Test files should also use datetime.now(timezone.utc).",
            )

    def test_no_utcnow_in_unit_tests(self) -> None:
        unit_dir = TEST_DIR / "unit"
        if not unit_dir.exists():
            return
        files = list(unit_dir.rglob("*.py"))
        all_violations = _collect_violations(
            files, {"utcnow"}, noqa_tag="DTZ003"
        )
        if all_violations:
            _fail_violations(
                all_violations,
                "datetime.utcnow() in unit test",
                "Test files should also use datetime.now(timezone.utc).",
            )

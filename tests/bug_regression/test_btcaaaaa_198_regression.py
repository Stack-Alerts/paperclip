"""
Regression tests for BTCAAAAA-198: Migrate all print() calls to structured logging.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-198
Component: src/ (all Python modules)

Root cause: 1,783 bare print() calls across the codebase prevented structured
log collection, monitoring, and alerting.  All print() calls were migrated to
logging.getLogger(__name__).info/debug/warning/error.

This regression test scans src/ for any reintroduced print() calls (the T201
ruff rule equivalent, runnable without external tools).  Every print() found
must be accompanied by a # noqa: T201 comment or this test fails.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-198"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "src"


def _iter_source_files() -> list[Path]:
    files = []
    for path in SRC_DIR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return sorted(files)


def _find_print_violations(filepath: Path) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return violations

    lines = text.split("\n")

    if "print(" not in text:
        return violations

    try:
        tree = ast.parse(text, filename=str(filepath))
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == "print"):
            continue

        lineno = node.lineno
        if lineno < 1 or lineno > len(lines):
            continue
        line = lines[lineno - 1]

        if "# noqa: T201" in line:
            continue

        violations.append((lineno, line.strip()))

    return violations


class TestNoPrintRegression:
    def test_no_bare_print_in_source(self):
        all_violations: list[tuple[str, int, str]] = []

        for filepath in _iter_source_files():
            violations = _find_print_violations(filepath)
            for lineno, line in violations:
                all_violations.append((str(filepath.relative_to(REPO_ROOT)), lineno, line))

        if all_violations:
            msg_lines = [
                f"Found {len(all_violations)} print() call(s) without # noqa: T201:",
                "",
            ]
            for fp, ln, line in all_violations:
                msg_lines.append(f"  {fp}:{ln}: {line}")
            msg_lines.append(
                "\nBTCAAAAA-198 migrated all print() calls to structured logging.  "
                "Add a '# noqa: T201' comment to exempt intentional print() calls."
            )
            pytest.fail("\n".join(msg_lines))

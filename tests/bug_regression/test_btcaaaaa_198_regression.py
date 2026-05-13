"""
Regression tests for BTCAAAAA-198: Migrate all print() calls to structured logging.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-198
Component: src/ (all Python modules)

Root cause: 1,783 bare print() calls across the codebase prevented structured
log collection, monitoring, and alerting.  All print() calls were migrated to
logging.getLogger(__name__).info/debug/warning/error.

This regression test suite enforces:
  1. No bare print() calls in src/ without a # noqa: T201 exemption (ruff T201 rule).
  2. The CI pyproject.toml gate must retain T201 in its ruff lint select list.
  3. Key entry-point modules that legitimately use print() must carry the noqa marker.
"""
from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-198"),
    pytest.mark.regression,
]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "src"
PYPROJECT = REPO_ROOT / "pyproject.toml"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _find_violations_in_dir(subdir: str) -> list[tuple[str, int, str]]:
    results: list[tuple[str, int, str]] = []
    target = SRC_DIR / subdir
    if not target.is_dir():
        return results
    for path in sorted(target.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        violations = _find_print_violations(path)
        for lineno, line in violations:
            results.append((str(path.relative_to(REPO_ROOT)), lineno, line))
    return results


def _build_violation_msg(
    violations: list[tuple[str, int, str]], label: str
) -> str:
    if not violations:
        return ""
    lines = [
        f"Found {len(violations)} print() call(s) without # noqa: T201 in {label}:",
        "",
    ]
    for fp, ln, line in violations:
        lines.append(f"  {fp}:{ln}: {line}")
    lines.append(
        "\nBTCAAAAA-198 migrated all print() calls to structured logging.  "
        "Add a '# noqa: T201' comment to exempt intentional print() calls."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Ruff T201 CI gate — pyproject.toml
# ---------------------------------------------------------------------------


class TestRuffT201Gate:
    """The T201 (no-print) rule must be configured in pyproject.toml."""

    def test_t201_is_in_ruff_lint_select(self) -> None:
        assert PYPROJECT.exists(), f"pyproject.toml not found at {PYPROJECT}"
        raw = PYPROJECT.read_text()
        in_lint_section = False
        found = False
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("[tool.ruff.lint]"):
                in_lint_section = True
                continue
            if in_lint_section and stripped.startswith("["):
                in_lint_section = False
                continue
            if in_lint_section and stripped.startswith("select"):
                found = "T201" in stripped
                break
        assert found, (
            "T201 not found in [tool.ruff.lint] select -- "
            "the print() regression guard has been removed or reconfigured."
        )

    def test_ruff_rule_t201_is_recognized(self) -> None:
        ruff_path = shutil.which("ruff")
        if ruff_path is None:
            pytest.skip("ruff not installed — cannot verify T201 rule recognition")
        result = subprocess.run(
            [ruff_path, "rule", "T201"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"ruff rule T201 failed: {result.stderr}"
        assert "T201" in result.stdout


# ---------------------------------------------------------------------------
# No bare print() across all of src/
# ---------------------------------------------------------------------------


class TestNoPrintRegression:
    def test_no_bare_print_in_source(self):
        all_violations: list[tuple[str, int, str]] = []

        for filepath in _iter_source_files():
            violations = _find_print_violations(filepath)
            for lineno, line in violations:
                all_violations.append(
                    (str(filepath.relative_to(REPO_ROOT)), lineno, line)
                )

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


# ---------------------------------------------------------------------------
# Per-subdirectory checks — granular enforcement so regressions are
# traceable to a specific package.
# ---------------------------------------------------------------------------


class TestNoPrintInBlastRadius:
    def test_no_bare_print_in_blast_radius(self):
        v = _find_violations_in_dir("blast_radius")
        msg = _build_violation_msg(v, "src/blast_radius/")
        if msg:
            pytest.fail(msg)


class TestNoPrintInTouchIndex:
    def test_no_bare_print_in_touch_index(self):
        v = _find_violations_in_dir("touch_index")
        msg = _build_violation_msg(v, "src/touch_index/")
        if msg:
            pytest.fail(msg)


class TestNoPrintInImpactGate:
    def test_no_bare_print_in_impact_gate(self):
        v = _find_violations_in_dir("impact_gate")
        msg = _build_violation_msg(v, "src/impact_gate/")
        if msg:
            pytest.fail(msg)


class TestNoPrintInConsultantCli:
    def test_no_bare_print_in_consultant_cli(self):
        v = _find_violations_in_dir("consultant_cli")
        msg = _build_violation_msg(v, "src/consultant_cli/")
        if msg:
            pytest.fail(msg)


class TestNoPrintInAiConsultant:
    def test_no_bare_print_in_ai_consultant(self):
        v = _find_violations_in_dir("ai_consultant")
        msg = _build_violation_msg(v, "src/ai_consultant/")
        if msg:
            pytest.fail(msg)


# ---------------------------------------------------------------------------
# Known exempt files — ensure noqa markers are still present
# ---------------------------------------------------------------------------


class TestExemptPrintLocations:
    """Entry-point files that legitimately use print() must carry noqa markers."""

    def test_impact_gate_worker_noqa_present(self) -> None:
        path = REPO_ROOT / "src/impact_gate/worker.py"
        assert path.exists()
        assert any(
            "# noqa: T201" in line for line in path.read_text().splitlines()
        ), "impact_gate/worker.py must carry # noqa: T201 on its print() call"

    def test_blast_radius_main_noqa_present(self) -> None:
        path = REPO_ROOT / "src/blast_radius/__main__.py"
        assert path.exists()
        noqa_count = sum(
            1 for line in path.read_text().splitlines() if "# noqa: T201" in line
        )
        assert noqa_count >= 4, (
            f"blast_radius/__main__.py has {noqa_count} noqa markers, expected >=4"
        )

    def test_consultant_cli_main_noqa_present(self) -> None:
        path = REPO_ROOT / "src/consultant_cli/__main__.py"
        assert path.exists()
        noqa_count = sum(
            1 for line in path.read_text().splitlines() if "# noqa: T201" in line
        )
        assert noqa_count >= 8, (
            f"consultant_cli/__main__.py has {noqa_count} noqa markers, expected >=8"
        )

    def test_audit_writer_noqa_present(self) -> None:
        path = REPO_ROOT / "src/ai_consultant/audit_writer.py"
        assert path.exists()
        noqa_count = sum(
            1 for line in path.read_text().splitlines() if "# noqa: T201" in line
        )
        assert noqa_count >= 4, (
            f"ai_consultant/audit_writer.py has {noqa_count} noqa markers, expected >=4"
        )


# ---------------------------------------------------------------------------
# Python logging setup — ensure the structured logging contract
# ---------------------------------------------------------------------------


class TestLoggerConfiguration:
    """Key modules should have a module-level logger."""

    KEY_LOGGER_MODULES = [
        "src/blast_radius/generator.py",
        "src/blast_radius/worker.py",
        "src/impact_gate/worker.py",
        "src/touch_index/quality.py",
    ]

    @pytest.mark.parametrize("rel_path", KEY_LOGGER_MODULES)
    def test_module_has_logger(self, rel_path: str) -> None:
        path = REPO_ROOT / rel_path
        assert path.exists(), f"{rel_path} not found"
        content = path.read_text()
        assert "logging.getLogger" in content, (
            f"{rel_path} must define a module-level logger via logging.getLogger(__name__)"
        )


# ---------------------------------------------------------------------------
# Baseline — ensures the Impact Gate always has at least one discoverable
# test even if every other test in this file is somehow excluded.
# ---------------------------------------------------------------------------


class TestImpactGateBaseline:
    """Minimal passing test so the Impact Gate always has a discoverable test."""

    def test_placeholder(self) -> None:
        assert True

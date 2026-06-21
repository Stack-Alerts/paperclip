"""End-to-end tests for the deletion-touches-callers gate (BTCAAAAA-37737).

Each test builds a throw-away git repo so we exercise the real diff + ripgrep
plumbing, not just AST helpers. Synthetic PRs come straight from the issue's
acceptance criteria.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import textwrap

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "deletion_touches_callers.py"


def _git(repo: pathlib.Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )
    return proc.stdout


def _init_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    return repo


def _run_gate(repo: pathlib.Path, base: str = "main") -> tuple[int, dict]:
    env = os.environ.copy()
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--base-ref", base, "--json"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return proc.returncode, payload


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    return _init_repo(tmp_path)


def _has_rg() -> bool:
    return subprocess.run(["which", "rg"], capture_output=True).returncode == 0


pytestmark = pytest.mark.skipif(not _has_rg(), reason="ripgrep not installed")


def test_removed_def_with_live_caller_fails(repo: pathlib.Path) -> None:
    """Acceptance: synthetic PR removing a function with a live caller fails."""
    (repo / "src").mkdir()
    (repo / "src" / "db.py").write_text(textwrap.dedent("""
        class DatabaseManager:
            def scoped_managers(self):
                return {}
    """).lstrip())
    (repo / "src" / "app.py").write_text(textwrap.dedent("""
        from .db import DatabaseManager

        def handler(dm: DatabaseManager):
            return dm.scoped_managers()
    """).lstrip())
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "baseline")

    (repo / "src" / "db.py").write_text(textwrap.dedent("""
        class DatabaseManager:
            pass
    """).lstrip())
    _git(repo, "checkout", "-q", "-b", "pr")
    _git(repo, "commit", "-q", "-am", "drop scoped_managers")

    code, report = _run_gate(repo)
    assert code == 1
    names = [v["name"] for v in report["violations"]]
    assert "scoped_managers" in names
    callers = [c["file"] for v in report["violations"] for c in v["callers"]]
    assert any("app.py" in c for c in callers)


def test_removed_def_with_no_callers_passes(repo: pathlib.Path) -> None:
    """Acceptance: synthetic PR removing a fully-unreferenced function passes."""
    (repo / "src").mkdir()
    (repo / "src" / "util.py").write_text(textwrap.dedent("""
        def lonely_helper():
            return 42

        def kept():
            return 1
    """).lstrip())
    (repo / "src" / "consumer.py").write_text(textwrap.dedent("""
        from .util import kept

        def use():
            return kept()
    """).lstrip())
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "baseline")

    (repo / "src" / "util.py").write_text(textwrap.dedent("""
        def kept():
            return 1
    """).lstrip())
    _git(repo, "checkout", "-q", "-b", "pr")
    _git(repo, "commit", "-q", "-am", "drop lonely_helper")

    code, report = _run_gate(repo)
    assert code == 0, report
    assert report["violations"] == []


def test_test_only_caller_does_not_block(repo: pathlib.Path) -> None:
    """tests/** callers must not keep a deletion alive."""
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / "src" / "thing.py").write_text("def widget():\n    return 1\n")
    (repo / "tests" / "test_thing.py").write_text(
        "from src.thing import widget\n\n"
        "def test_w():\n    assert widget() == 1\n"
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "baseline")

    (repo / "src" / "thing.py").write_text("pass\n")
    _git(repo, "checkout", "-q", "-b", "pr")
    _git(repo, "commit", "-q", "-am", "drop widget")

    code, _ = _run_gate(repo)
    assert code == 0


def test_private_def_removal_ignored(repo: pathlib.Path) -> None:
    """Underscore-prefixed (private) defs are out of scope."""
    (repo / "src").mkdir()
    (repo / "src" / "m.py").write_text(
        "def _internal():\n    return 1\n\n"
        "def consumer():\n    return _internal()\n"
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "baseline")

    (repo / "src" / "m.py").write_text(
        "def consumer():\n    return 1\n"
    )
    _git(repo, "checkout", "-q", "-b", "pr")
    _git(repo, "commit", "-q", "-am", "drop private")

    code, _ = _run_gate(repo)
    assert code == 0

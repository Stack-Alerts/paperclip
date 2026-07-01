"""Regression tests for dependency-free .env loading in the deadman monitors.

BTCAAAAA-38803 (parent BTCAAAAA-38797): the systemd services run the host
/usr/bin/python3, which is PEP-668 externally-managed and has no python-dotenv.
The old code swallowed the ImportError, so a present-and-valid GH_TOKEN in
.env was never loaded and the monitor falsely reported gh_blind. Each monitor
now falls back to a minimal inline parser; these tests force the python-dotenv
import to fail and assert the token still loads.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

pytestmark = [pytest.mark.bug("BTCAAAAA-38803"), pytest.mark.regression]

MODULES = [
    "scripts.backup_deadman_switch_monitor",
    "scripts.deadman_switch_local_monitor",
    "scripts.backup_deadman_switch",
]


def _load_env_file(module_name):
    module = importlib.import_module(module_name)
    return module._load_env_file


@pytest.fixture
def force_dotenv_missing(monkeypatch):
    """Make `from dotenv import load_dotenv` raise ImportError."""
    monkeypatch.setitem(sys.modules, "dotenv", None)


@pytest.mark.parametrize("module_name", MODULES)
def test_loads_token_when_dotenv_import_fails(
    module_name, tmp_path, monkeypatch, force_dotenv_missing
):
    load_env_file = _load_env_file(module_name)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    env = tmp_path / ".env"
    env.write_text(
        "# leading comment\n"
        "\n"
        "GH_TOKEN=gho_fallbacktoken123\n"
        'export QUOTED="quoted-value"\n'
        "SINGLE='single-value'\n"
        "NOT_AN_ASSIGNMENT\n"
    )

    load_env_file(env, override=False)

    assert os.environ["GH_TOKEN"] == "gho_fallbacktoken123"
    assert os.environ["QUOTED"] == "quoted-value"
    assert os.environ["SINGLE"] == "single-value"
    assert "NOT_AN_ASSIGNMENT" not in os.environ


@pytest.mark.parametrize("module_name", MODULES)
def test_override_false_keeps_existing_value(
    module_name, tmp_path, monkeypatch, force_dotenv_missing
):
    load_env_file = _load_env_file(module_name)
    monkeypatch.setenv("GH_TOKEN", "preexisting-token")

    env = tmp_path / ".env"
    env.write_text("GH_TOKEN=gho_should_not_win\n")

    load_env_file(env, override=False)

    assert os.environ["GH_TOKEN"] == "preexisting-token"


@pytest.mark.parametrize("module_name", MODULES)
def test_missing_file_is_noop(
    module_name, tmp_path, monkeypatch, force_dotenv_missing
):
    load_env_file = _load_env_file(module_name)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    load_env_file(tmp_path / "does-not-exist.env", override=False)

    assert "GH_TOKEN" not in os.environ

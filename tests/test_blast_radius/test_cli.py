"""Unit tests for scripts/blast_radius_cli.py — thin wrapper delegation.

Verifies that the legacy CLI script correctly delegates to
blast_radius.__main__.main().
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# Insert both src/ and scripts/ so the CLI module can be loaded directly.
_SRC = Path(__file__).parents[2] / "src"
_SCRIPTS = Path(__file__).parents[2] / "scripts"
for p in (_SRC, _SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import importlib

_runner_path = _SCRIPTS / "blast_radius_cli.py"
_spec = importlib.util.spec_from_file_location("blast_radius_cli", _runner_path)
_cli = importlib.util.module_from_spec(_spec)
sys.modules["blast_radius_cli"] = _cli
_spec.loader.exec_module(_cli)

main = _cli.main


class TestMainDelegation:
    _CLEAN_ARGV = ["blast_radius_cli.py"]

    def test_delegates_to_unified_cli(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV)
        with patch("blast_radius.__main__.main", return_value=0) as mock_main:
            assert main() == 0
            mock_main.assert_called_once()

    def test_passes_return_code(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV)
        with patch("blast_radius.__main__.main", return_value=42):
            assert main() == 42

    def test_dry_run_forwarded(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", self._CLEAN_ARGV + ["--dry-run"])
        with patch("blast_radius.__main__.main", return_value=0) as mock_main:
            main()
            mock_main.assert_called_once()

"""
Tests for scripts/validate_testnet_env.py — BTCAAAAA-25616
===========================================================
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.validate_testnet_env import _check, main


@pytest.fixture(autouse=True)
def _clear_checks():
    from scripts import validate_testnet_env as m
    m._CHECKS.clear()


class TestEnvChecks:
    def test_paper_trading_default_passes(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(sys, "argv", ["validate_testnet_env.py"]):
                rc = main()

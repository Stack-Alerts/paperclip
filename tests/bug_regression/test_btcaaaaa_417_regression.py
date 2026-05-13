"""
Regression tests for BTCAAAAA-417: exclude strategy_builder non-UI modules
from coverage denominator.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-417
Fixed in commit: de443f13 / 9bdb3cc5
Component: .coveragerc

Root cause: strategy_builder non-UI modules (core, integration, persistence,
utils, validation) had 0% coverage when running ITM state tests in headless CI,
dragging the total below the 20% threshold. Fix added these 14 modules to
.coveragerc omit list.
"""
from __future__ import annotations

import configparser
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-417"),
    pytest.mark.regression,
]


class TestCoverageExclusions:
    """Verify coverage exclusions for non-UI strategy_builder modules."""

    def test_coveragerc_omits_strategy_builder_non_ui_modules(self):
        repo_root = Path(__file__).resolve().parents[2]
        coveragerc = repo_root / ".coveragerc"
        assert coveragerc.exists(), ".coveragerc not found"

        config = configparser.ConfigParser()
        config.read(coveragerc)

        omit_str = config.get("run", "omit", fallback="")
        assert (
            "strategy_builder/core" in omit_str
        ), "strategy_builder/core not in coverage omit"
        assert (
            "strategy_builder/integration" in omit_str
        ), "strategy_builder/integration not in coverage omit"
        assert (
            "strategy_builder/persistence" in omit_str
        ), "strategy_builder/persistence not in coverage omit"

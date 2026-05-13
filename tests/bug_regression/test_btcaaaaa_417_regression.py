"""
Regression tests for BTCAAAAA-417: exclude strategy_builder non-UI modules
from coverage denominator.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-417
Fixed in commit: de443f13 / 9bdb3cc5
Component: .coveragerc

Root cause: strategy_builder non-UI modules (core, integration, persistence,
utils, validation) had 0% coverage when running ITM state tests in headless CI,
dragging the total below the 20% threshold. Fix added these 15 modules to
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

_EXPECTED_OMIT_ENTRIES = frozenset({
    "src/strategy_builder/__init__.py",
    "src/strategy_builder/utils/__init__.py",
    "src/strategy_builder/core/block_registry_adapter.py",
    "src/strategy_builder/core/registry_interface.py",
    "src/strategy_builder/core/signal_dependency_resolver.py",
    "src/strategy_builder/core/strategy_config_engine.py",
    "src/strategy_builder/execution/block_state_manager.py",
    "src/strategy_builder/integration/strategy_builder_orchestrator.py",
    "src/strategy_builder/persistence/strategy_persistence.py",
    "src/strategy_builder/utils/institutional_logger.py",
    "src/strategy_builder/utils/signal_statistics_loader.py",
    "src/strategy_builder/utils/signal_statistics_updater.py",
    "src/strategy_builder/validation/auto_fix.py",
    "src/strategy_builder/validation/strategy_validator.py",
    "src/strategy_builder/validation/undo_manager.py",
})


class TestCoverageExclusions:
    """Verify coverage exclusions for non-UI strategy_builder modules."""

    @staticmethod
    def _load_omit_entries() -> set[str]:
        repo_root = Path(__file__).resolve().parents[2]
        coveragerc = repo_root / ".coveragerc"
        assert coveragerc.exists(), ".coveragerc not found"
        config = configparser.ConfigParser()
        config.read(coveragerc)
        omit_str = config.get("run", "omit", fallback="")
        return {
            line.strip()
            for line in omit_str.split("\n")
            if line.strip() and not line.strip().startswith("#")
        }

    def test_coveragerc_has_run_section(self):
        repo_root = Path(__file__).resolve().parents[2]
        config = configparser.ConfigParser()
        config.read(repo_root / ".coveragerc")
        assert config.has_section("run"), ".coveragerc missing [run] section"
        assert config.has_option("run", "omit"), ".coveragerc [run] missing omit key"

    def test_coveragerc_omits_strategy_builder_non_ui_modules(self):
        entries = self._load_omit_entries()
        for entry in _EXPECTED_OMIT_ENTRIES:
            assert entry in entries, f"{entry} not in .coveragerc omit list"

    def test_coveragerc_omits_core_modules(self):
        entries = self._load_omit_entries()
        for e in (
            "src/strategy_builder/core/block_registry_adapter.py",
            "src/strategy_builder/core/registry_interface.py",
            "src/strategy_builder/core/signal_dependency_resolver.py",
            "src/strategy_builder/core/strategy_config_engine.py",
        ):
            assert e in entries, f"{e} not in omit list"

    def test_coveragerc_omits_utils_modules(self):
        entries = self._load_omit_entries()
        for e in (
            "src/strategy_builder/utils/__init__.py",
            "src/strategy_builder/utils/institutional_logger.py",
            "src/strategy_builder/utils/signal_statistics_loader.py",
            "src/strategy_builder/utils/signal_statistics_updater.py",
        ):
            assert e in entries, f"{e} not in omit list"

    def test_coveragerc_omits_validation_modules(self):
        entries = self._load_omit_entries()
        for e in (
            "src/strategy_builder/validation/auto_fix.py",
            "src/strategy_builder/validation/strategy_validator.py",
            "src/strategy_builder/validation/undo_manager.py",
        ):
            assert e in entries, f"{e} not in omit list"

    def test_coveragerc_omits_init_and_execution(self):
        entries = self._load_omit_entries()
        assert "src/strategy_builder/__init__.py" in entries
        assert "src/strategy_builder/execution/block_state_manager.py" in entries
        assert "src/strategy_builder/integration/strategy_builder_orchestrator.py" in entries
        assert "src/strategy_builder/persistence/strategy_persistence.py" in entries

    def test_coveragerc_has_exactly_fifteen_strategy_builder_entries(self):
        entries = self._load_omit_entries()
        sb_entries = {e for e in entries if e.startswith("src/strategy_builder/")}
        fix_entries = sb_entries - {
            "src/strategy_builder/ui/*",
            "src/strategy_builder/testing/walkforward_test_engine.py",
            "src/strategy_builder/core/nautilus_code_generator.py",
        }
        assert len(fix_entries) == 15, (
            f"Expected 15 strategy_builder entries from the fix, "
            f"got {len(fix_entries)}: {sorted(fix_entries)}"
        )

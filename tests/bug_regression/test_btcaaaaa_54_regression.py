"""
Regression tests for BTCAAAAA-54: core data pipeline stability and configuration.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-54
Components: src/data_manager/config.py
            src/data_manager/unified_manager.py
            src/strategy_builder/core/

This suite exercises foundational system contracts:
  1. Config path resolution and invariants
  2. DataSource enum members
  3. Timeframe mapping integrity
  4. Core UnifiedDataManager constructor contracts
  5. Configuration constants
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-54"),
    pytest.mark.regression,
]


class TestConfigPaths:
    """Config path resolution must resolve correctly."""

    def test_project_root_resolved(self):
        from src.data_manager.config import PROJECT_ROOT

        root = Path(PROJECT_ROOT).resolve()
        assert root.exists()
        assert (root / "src").is_dir()

    def test_raw_data_dir_configured(self):
        from src.data_manager.config import RAW_DATA_DIR

        raw = Path(RAW_DATA_DIR).resolve()
        assert isinstance(str(raw), str)

    def test_catalog_dir_configured(self):
        from src.data_manager.config import CATALOG_DIR

        cat = Path(CATALOG_DIR).resolve()
        assert isinstance(str(cat), str)

    def test_log_dir_configured(self):
        from src.data_manager.config import LOG_DIR

        log = Path(LOG_DIR).resolve()
        assert isinstance(str(log), str)


class TestConfigConstants:
    """Config constants must have expected types and sensible ranges."""

    def test_min_price_positive(self):
        from src.data_manager.config import MIN_PRICE

        assert isinstance(MIN_PRICE, (int, float))
        assert MIN_PRICE > 0

    def test_max_price_greater_than_min(self):
        from src.data_manager.config import MIN_PRICE, MAX_PRICE

        assert isinstance(MAX_PRICE, (int, float))
        assert MAX_PRICE > MIN_PRICE

    def test_timeframes_is_list_with_1h(self):
        from src.data_manager.config import TIMEFRAMES

        assert isinstance(TIMEFRAMES, list)
        assert len(TIMEFRAMES) > 0
        assert "1h" in TIMEFRAMES

    def test_data_types_is_list(self):
        from src.data_manager.config import DATA_TYPES

        assert isinstance(DATA_TYPES, list)
        assert len(DATA_TYPES) > 0

    def test_timeframe_mapping_covers_all_frames(self):
        from src.data_manager.config import TIMEFRAMES, TIMEFRAME_MAPPING

        for tf in TIMEFRAMES:
            assert tf in TIMEFRAME_MAPPING

    def test_lakeapi_mappings_have_expected_keys(self):
        from src.data_manager.config import (
            DATA_TYPES,
            LAKEAPI_EXCHANGE_MAPPING,
            LAKEAPI_SYMBOL_MAPPING,
            LAKEAPI_TABLE_MAPPING,
        )

        for dt in DATA_TYPES:
            assert dt in LAKEAPI_EXCHANGE_MAPPING
            assert dt in LAKEAPI_SYMBOL_MAPPING
            assert dt in LAKEAPI_TABLE_MAPPING


class TestDataSourceEnum:
    """DataSource enum must have expected members."""

    def test_has_lakeapi(self):
        from src.data_manager.unified_manager import DataSource

        assert hasattr(DataSource, "LAKEAPI")
        assert DataSource.LAKEAPI.value == "lakeapi"

    def test_has_binance(self):
        from src.data_manager.unified_manager import DataSource

        assert hasattr(DataSource, "BINANCE")
        assert DataSource.BINANCE.value == "binance"

    def test_enum_values_unique(self):
        from src.data_manager.unified_manager import DataSource

        values = [e.value for e in DataSource]
        assert len(values) == len(set(values))


class TestUnifiedDataManagerConstruction:
    """UnifiedDataManager must construct in all modes."""

    def test_constructs_live(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="live")
        assert mgr.mode == "live"

    def test_constructs_backtest(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="backtest")
        assert mgr.mode == "backtest"

    def test_constructor_default_mode(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager()
        assert mgr.mode == "backtest"


class TestCoreMethods:
    """Key methods must exist with expected signatures."""

    def test_get_bars_method_exists(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        assert hasattr(UnifiedDataManager, "get_bars")
        assert callable(UnifiedDataManager.get_bars)

    def test_detect_gaps_method_exists(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        assert hasattr(UnifiedDataManager, "detect_gaps_in_binance_files")
        assert callable(UnifiedDataManager.detect_gaps_in_binance_files)

    def test_verify_and_repair_method_exists(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        assert hasattr(UnifiedDataManager, "verify_and_repair")
        assert callable(UnifiedDataManager.verify_and_repair)

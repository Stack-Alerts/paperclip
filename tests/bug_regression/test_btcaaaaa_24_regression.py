"""
Regression tests for BTCAAAAA-24: core data pipeline integrity and
data source routing in UnifiedDataManager.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-24

This test suite exercises foundational data pipeline contracts:
  1. DataSource enum values and behavior
  2. Core UnifiedDataManager constructor invariants
  3. Configuration path resolution
  4. Bar aggregation interface
  5. Gap detection signatures
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-24"),
    pytest.mark.regression,
]


class TestDataSourceEnum:
    """DataSource enum must have the expected members and string behavior."""

    def test_data_source_enum_has_lakeapi(self):
        from src.data_manager.unified_manager import DataSource

        assert hasattr(DataSource, "LAKEAPI")
        assert DataSource.LAKEAPI.value == "lakeapi"

    def test_data_source_enum_has_binance(self):
        from src.data_manager.unified_manager import DataSource

        assert hasattr(DataSource, "BINANCE")
        assert DataSource.BINANCE.value == "binance"

    def test_data_source_enum_values_are_unique(self):
        from src.data_manager.unified_manager import DataSource

        values = [e.value for e in DataSource]
        assert len(values) == len(set(values)), "DataSource enum values must be unique"


class TestConfigPaths:
    """Configuration path resolution must work correctly."""

    def test_project_root_is_resolved(self):
        from src.data_manager.config import PROJECT_ROOT

        root = Path(PROJECT_ROOT).resolve()
        assert root.exists(), f"PROJECT_ROOT {root} must exist"
        assert (root / "src").is_dir(), "PROJECT_ROOT must contain src/"

    def test_raw_data_dir_is_configured(self):
        from src.data_manager.config import RAW_DATA_DIR

        raw = Path(RAW_DATA_DIR).resolve()
        assert isinstance(str(raw), str)
        assert "data" in str(raw).lower() or "raw" in str(raw).lower()


class TestUnifiedDataManagerConstruction:
    """UnifiedDataManager must construct correctly in all modes."""

    def test_constructor_accepts_live_mode(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="live")
        assert mgr.mode == "live"

    def test_constructor_accepts_backtest_mode(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="backtest")
        assert mgr.mode == "backtest"

    def test_constructor_default_mode(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager()
        assert mgr.mode == "backtest"

    def test_constructor_sets_binance_dir(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="backtest")
        assert mgr.binance_dir is not None
        assert "binance" in str(mgr.binance_dir).lower()

    def test_constructor_sets_lakeapi_dir(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="backtest")
        assert mgr.lakeapi_dir is not None

    def test_startup_check_method_exists(self):
        from src.data_manager.unified_manager import UnifiedDataManager

        mgr = UnifiedDataManager(mode="backtest", startup_gap_check=False)
        assert hasattr(mgr, "startup_check")
        assert callable(mgr.startup_check)


class TestCoreMethods:
    """Key methods must exist and have expected signatures."""

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


class TestBarAggregation:
    """BarAggregator must be importable and instantiable."""

    def test_bar_aggregator_importable(self):
        from src.data_manager.processing.bar_aggregator import BarAggregator

        assert BarAggregator is not None

    def test_bar_aggregator_constructs(self):
        from src.data_manager.processing.bar_aggregator import BarAggregator

        agg = BarAggregator()
        assert agg is not None


class TestBinanceRestClient:
    """BinanceRestClient interface must remain stable."""

    def test_rest_client_importable(self):
        from src.data_manager.binance.rest_client import BinanceRestClient

        assert BinanceRestClient is not None

    def test_get_klines_signature_has_start_time(self):
        import inspect

        from src.data_manager.binance.rest_client import BinanceRestClient

        sig = inspect.signature(BinanceRestClient.get_klines)
        params = list(sig.parameters.keys())
        assert "start_time" in params or "startTime" in params

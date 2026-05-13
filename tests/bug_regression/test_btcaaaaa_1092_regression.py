"""
Regression tests for BTCAAAAA-1092: persist calibration fingerprint to disk
across restarts.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-1092
Component: src/strategy_builder/ui/backtest_config_panel.py,
           src/optimizer_v3/database/calibration_cache.py

BTCAAAAA-1092 added ``_load_calibration_disk_cache()`` and
``_save_calibration_disk_cache()`` to BacktestConfigPanel, backed by the
shared ``calibration_cache`` module.  The cache writes a schema-versioned,
TTL-guarded JSON blob to ``~/.paperclip/calibration_cache.json`` via an
atomic tmp+rename pattern so that identical calibration inputs can skip
recomputation across process restarts.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-1092"),
    pytest.mark.regression,
]

logging.disable(logging.CRITICAL)


# =========================================================================
# calibration_cache module — unit tests
# =========================================================================


class TestComputeFingerprint:
    """compute_fingerprint() must produce deterministic SHA-256 hex digests."""

    def test_deterministic_same_inputs(self):
        from src.optimizer_v3.database.calibration_cache import compute_fingerprint

        inp = ["Alpha", "Beta", "Gamma"]
        a = compute_fingerprint(inp, "15m", 180, "production")
        b = compute_fingerprint(inp, "15m", 180, "production")
        assert a == b
        assert isinstance(a, str)
        assert len(a) == 64

    def test_different_blocks_produce_different_fingerprints(self):
        from src.optimizer_v3.database.calibration_cache import compute_fingerprint

        a = compute_fingerprint(["Alpha"], "15m", 180, "production")
        b = compute_fingerprint(["Beta"], "15m", 180, "production")
        assert a != b

    def test_different_timeframe_produces_different_fingerprint(self):
        from src.optimizer_v3.database.calibration_cache import compute_fingerprint

        a = compute_fingerprint(["Alpha"], "15m", 180, "production")
        b = compute_fingerprint(["Alpha"], "1h", 180, "production")
        assert a != b

    def test_different_period_produces_different_fingerprint(self):
        from src.optimizer_v3.database.calibration_cache import compute_fingerprint

        a = compute_fingerprint(["Alpha"], "15m", 180, "production")
        b = compute_fingerprint(["Alpha"], "15m", 90, "production")
        assert a != b

    def test_different_mode_produces_different_fingerprint(self):
        from src.optimizer_v3.database.calibration_cache import compute_fingerprint

        a = compute_fingerprint(["Alpha"], "15m", 180, "production")
        b = compute_fingerprint(["Alpha"], "15m", 180, "simulation")
        assert a != b

    def test_block_order_independence(self):
        from src.optimizer_v3.database.calibration_cache import compute_fingerprint

        a = compute_fingerprint(["Gamma", "Alpha", "Beta"], "15m", 180, "production")
        b = compute_fingerprint(["Alpha", "Beta", "Gamma"], "15m", 180, "production")
        assert a == b

    def test_empty_blocks_list(self):
        from src.optimizer_v3.database.calibration_cache import compute_fingerprint

        fp = compute_fingerprint([], "15m", 180, "production")
        assert isinstance(fp, str)
        assert len(fp) == 64

    def test_fingerprint_is_sha256_hex(self):
        from src.optimizer_v3.database.calibration_cache import compute_fingerprint

        fp = compute_fingerprint(["A", "B"], "15m", 180, "production")
        expected = hashlib.sha256(
            json.dumps(
                {"block_names": ["A", "B"], "mode": "production",
                 "period_days": 180, "timeframe": "15m"},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        assert fp == expected


class TestSaveAndLoadCache:
    """save_cache() and load_cache() must round-trip correctly."""

    def test_round_trip(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        fp = hashlib.sha256(b"test").hexdigest()
        dm = {"Alpha": 3, "Beta": 5}

        with patch.object(calibration_cache, "get_cache_path", return_value=tmp_path / "calibration_cache.json"):
            calibration_cache.save_cache(fp, dm)
            loaded_fp, loaded_dm = calibration_cache.load_cache()

        assert loaded_fp == fp
        assert loaded_dm == dm

    def test_save_empty_delay_map(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        fp = hashlib.sha256(b"empty").hexdigest()

        with patch.object(calibration_cache, "get_cache_path", return_value=tmp_path / "calibration_cache.json"):
            calibration_cache.save_cache(fp, {})
            loaded_fp, loaded_dm = calibration_cache.load_cache()

        assert loaded_fp == fp
        assert loaded_dm == {}

    def test_load_when_file_missing(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        with patch.object(calibration_cache, "get_cache_path", return_value=tmp_path / "nonexistent.json"):
            fp, dm = calibration_cache.load_cache()

        assert fp is None
        assert dm is None

    def test_save_none_fingerprint_skips_write(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        with patch.object(calibration_cache, "get_cache_path", return_value=tmp_path / "calibration_cache.json"):
            calibration_cache.save_cache(None, {"A": 1})

        assert not (tmp_path / "calibration_cache.json").exists()

    def test_save_empty_string_fingerprint_skips_write(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        with patch.object(calibration_cache, "get_cache_path", return_value=tmp_path / "calibration_cache.json"):
            calibration_cache.save_cache("", {"A": 1})

        assert not (tmp_path / "calibration_cache.json").exists()

    def test_load_invalid_json_returns_none(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "calibration_cache.json"
        cache_file.write_text("{invalid json", encoding="utf-8")

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            fp, dm = calibration_cache.load_cache()

        assert fp is None
        assert dm is None

    def test_load_missing_structure_keys_returns_none(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "calibration_cache.json"
        cache_file.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            fp, dm = calibration_cache.load_cache()

        assert fp is None
        assert dm is None


class TestCacheSchemaVersion:
    """Cache files with an unknown schema_version must be ignored."""

    def test_schema_mismatch_returns_none(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "calibration_cache.json"
        payload = {
            "schema_version": 999,
            "fingerprint": "abc123",
            "delay_map": {"A": 1},
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            fp, dm = calibration_cache.load_cache()

        assert fp is None
        assert dm is None

    def test_missing_schema_version_returns_none(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "calibration_cache.json"
        payload = {
            "fingerprint": "abc123",
            "delay_map": {},
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            fp, dm = calibration_cache.load_cache()

        assert fp is None
        assert dm is None


class TestCacheTtl:
    """Cache entries older than 7 days must be ignored."""

    def test_expired_cache_returns_none(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "calibration_cache.json"
        stale_ts = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        payload = {
            "schema_version": 1,
            "fingerprint": "abc",
            "delay_map": {"A": 1},
            "stored_at": stale_ts,
        }
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            fp, dm = calibration_cache.load_cache()

        assert fp is None
        assert dm is None

    def test_fresh_cache_returns_values(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "calibration_cache.json"
        fresh_ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        payload = {
            "schema_version": 1,
            "fingerprint": "abc",
            "delay_map": {"A": 1},
            "stored_at": fresh_ts,
        }
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            fp, dm = calibration_cache.load_cache()

        assert fp == "abc"
        assert dm == {"A": 1}

    def test_missing_stored_at_is_tolerated(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "calibration_cache.json"
        payload = {
            "schema_version": 1,
            "fingerprint": "abc",
            "delay_map": {"B": 2},
        }
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            fp, dm = calibration_cache.load_cache()

        # missing stored_at skips TTL check but does NOT invalidate the cache
        assert fp == "abc"
        assert dm == {"B": 2}


class TestAtomicWrite:
    """save_cache must use tmp+rename to prevent partial-write corruption."""

    def test_tmp_file_created_then_renamed(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        cache_path = tmp_path / "calibration_cache.json"

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_path):
            calibration_cache.save_cache("fp123", {"A": 1})

        assert not cache_path.with_suffix(".json.tmp").exists()
        assert cache_path.exists()

    def test_consecutive_writes_no_corruption(self, tmp_path):
        from src.optimizer_v3.database import calibration_cache

        cache_path = tmp_path / "calibration_cache.json"

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_path):
            calibration_cache.save_cache("fp1", {"A": 1})
            calibration_cache.save_cache("fp2", {"B": 2})
            calibration_cache.save_cache("fp3", {"C": 3})

        with cache_path.open() as f:
            data = json.load(f)

        assert data["fingerprint"] == "fp3"
        assert data["delay_map"] == {"C": 3}


# =========================================================================
# BacktestConfigPanel — disk cache integration tests
# =========================================================================


class TestLoadCalibrationDiskCache:
    """BacktestConfigPanel._load_calibration_disk_cache() integration."""

    def test_load_populates_cache_attributes(self, tmp_path):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "calibration_cache.json"
        payload = {
            "schema_version": 1,
            "fingerprint": "abc_fp",
            "delay_map": {"Alpha": 3},
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            panel = MagicMock()
            panel._calibration_fingerprint = None
            panel._calibration_cache = None
            panel._calibration_cache_from_disk = False
            fn = BacktestConfigPanel._load_calibration_disk_cache
            bound = fn.__get__(panel, BacktestConfigPanel)
            bound()

        assert panel._calibration_fingerprint == "abc_fp"
        assert panel._calibration_cache == {"Alpha": 3}
        assert panel._calibration_cache_from_disk is True

    def test_load_when_no_cache_leaves_none(self, tmp_path):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "nonexistent_cache.json"

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            panel = MagicMock()
            panel._calibration_fingerprint = None
            panel._calibration_cache = None
            panel._calibration_cache_from_disk = False
            fn = BacktestConfigPanel._load_calibration_disk_cache
            bound = fn.__get__(panel, BacktestConfigPanel)
            bound()

        assert panel._calibration_fingerprint is None
        assert panel._calibration_cache is None
        assert panel._calibration_cache_from_disk is False


class TestSaveCalibrationDiskCache:
    """BacktestConfigPanel._save_calibration_disk_cache() integration."""

    def test_save_writes_current_cache(self, tmp_path):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "calibration_cache.json"

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            panel = MagicMock()
            panel._calibration_fingerprint = "test_fp"
            panel._calibration_cache = {"Beta": 7}
            fn = BacktestConfigPanel._save_calibration_disk_cache
            bound = fn.__get__(panel, BacktestConfigPanel)
            bound()

        assert cache_file.exists()
        with cache_file.open() as f:
            data = json.load(f)
        assert data["fingerprint"] == "test_fp"
        assert data["delay_map"] == {"Beta": 7}
        assert data["schema_version"] == 1

    def test_save_with_none_fingerprint_is_noop(self, tmp_path):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        from src.optimizer_v3.database import calibration_cache

        cache_file = tmp_path / "calibration_cache.json"

        with patch.object(calibration_cache, "get_cache_path", return_value=cache_file):
            panel = MagicMock()
            panel._calibration_fingerprint = None
            panel._calibration_cache = {"A": 1}
            fn = BacktestConfigPanel._save_calibration_disk_cache
            bound = fn.__get__(panel, BacktestConfigPanel)
            bound()

        assert not cache_file.exists()


class TestApplyCalibrationResults:
    """_apply_calibration_results must update block optimal_delay in-place."""

    def _call(self, blocks, delay_map):
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        stub = MagicMock()
        fn = BacktestConfigPanel._apply_calibration_results
        bound = fn.__get__(stub, BacktestConfigPanel)
        bound(blocks, delay_map)

    def test_applies_delays_from_map(self):
        blocks = [
            {"name": "Alpha", "optimal_delay": 0},
            {"name": "Beta", "optimal_delay": 0},
            {"name": "Gamma", "optimal_delay": 0},
        ]
        self._call(blocks, {"Alpha": 5, "Gamma": 3})
        assert blocks[0]["optimal_delay"] == 5
        assert blocks[1]["optimal_delay"] == 0
        assert blocks[2]["optimal_delay"] == 3

    def test_empty_delay_map_no_changes(self):
        blocks = [{"name": "Alpha", "optimal_delay": 2}]
        self._call(blocks, {})
        assert blocks[0]["optimal_delay"] == 2

    def test_unknown_block_names_ignored(self):
        blocks = [{"name": "Alpha", "optimal_delay": 0}]
        self._call(blocks, {"Unknown": 99})
        assert blocks[0]["optimal_delay"] == 0

    def test_fallback_to_block_name_key(self):
        blocks = [{"block_name": "Alpha", "optimal_delay": 0}]
        self._call(blocks, {"Alpha": 4})
        assert blocks[0]["optimal_delay"] == 4

    def test_empty_blocks_list(self):
        self._call([], {"A": 1})

    def test_blocks_without_name_or_block_name(self):
        blocks = [{"optimal_delay": 0}]
        self._call(blocks, {})
        assert blocks[0]["optimal_delay"] == 0

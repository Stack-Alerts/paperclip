"""
Unit tests for SignalCatalogService (BTCAAAAA-687)
===================================================

Tests catalog loading, context string generation, and search/lookup methods.
DB-augmentation is tested via mocking so these tests run without a live DB.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ai_consultant.signal_catalog import SignalCatalogService, CatalogEntry, SignalStats


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_entry(
    name: str,
    category: str = "PATTERNS",
    weight: int = 25,
    direction: str = "NEUTRAL",
    signals: list[str] | None = None,
    description: str = "",
) -> CatalogEntry:
    signals = signals or ["SIGNAL_A", "BULLISH", "BEARISH", "NEUTRAL"]
    tiers = {s: {"base_points": 25, "formula": "scaled"} for s in signals}
    return CatalogEntry(
        name=name,
        category=category,
        weight=weight,
        direction=direction,
        description=description,
        valid_signals=signals,
        signal_tiers=tiers,
        tags=[],
    )


def _loaded_service(entries: dict[str, CatalogEntry], stats: dict | None = None) -> SignalCatalogService:
    """Return a pre-loaded service with injected entries (no live DB)."""
    svc = SignalCatalogService(db_url=None)
    svc._entries = entries
    svc._signal_index = {}
    for name, entry in entries.items():
        for sig in entry.valid_signals:
            svc._signal_index.setdefault(sig, []).append(name)
    svc._global_stats = stats or {}
    svc._loaded = True
    svc._stats_source = "none"
    from datetime import datetime
    svc._loaded_at = datetime(2026, 5, 9, 12, 0, 0)
    return svc


# ---------------------------------------------------------------------------
# Registry loading tests
# ---------------------------------------------------------------------------

class TestRegistryLoading:
    def test_load_populates_entries(self):
        svc = SignalCatalogService()
        svc.load(with_live_stats=False)
        assert svc.block_count > 0, "Registry should have at least 1 block"

    def test_registry_has_83_plus_blocks(self):
        svc = SignalCatalogService()
        svc.load(with_live_stats=False)
        assert svc.block_count >= 83, f"Expected 83+ blocks, got {svc.block_count}"

    def test_signal_declarations_700_plus(self):
        """700+ refers to total signal declarations across all blocks (including duplicates)."""
        svc = SignalCatalogService()
        svc.load(with_live_stats=False)
        assert svc.total_signal_declarations >= 700, (
            f"Expected 700+ total signal declarations, got {svc.total_signal_declarations}"
        )

    def test_signal_index_has_unique_signals(self):
        svc = SignalCatalogService()
        svc.load(with_live_stats=False)
        assert svc.signal_count >= 50, f"Expected 50+ unique signals, got {svc.signal_count}"

    def test_all_blocks_have_dual_signals(self):
        svc = SignalCatalogService()
        svc.load(with_live_stats=False)
        for name, entry in svc._entries.items():
            assert "BULLISH" in entry.valid_signals, f"{name} missing BULLISH"
            assert "BEARISH" in entry.valid_signals, f"{name} missing BEARISH"
            assert "NEUTRAL" in entry.valid_signals, f"{name} missing NEUTRAL"

    def test_categories_are_populated(self):
        svc = SignalCatalogService()
        svc.load(with_live_stats=False)
        cats = svc.categories
        assert len(cats) >= 10, f"Expected 10+ categories, got {len(cats)}"
        assert "PATTERNS" in cats
        assert "OSCILLATORS" in cats

    def test_requires_load_before_use(self):
        svc = SignalCatalogService()
        with pytest.raises(RuntimeError, match="Call .load()"):
            svc.context_string()


# ---------------------------------------------------------------------------
# Context string tests
# ---------------------------------------------------------------------------

class TestContextString:
    def _make_service(self) -> SignalCatalogService:
        entries = {
            "cup_and_handle": _make_entry("cup_and_handle", "PATTERNS", 30, "BULLISH",
                                          ["BREAKOUT_CONFIRMED", "CUP_FORMING", "BULLISH", "BEARISH", "NEUTRAL"]),
            "rsi": _make_entry("rsi", "OSCILLATORS", 25, "NEUTRAL",
                               ["RSI_OVERSOLD", "RSI_OVERBOUGHT", "BULLISH", "BEARISH", "NEUTRAL"]),
        }
        return _loaded_service(entries)

    def test_context_string_returns_string(self):
        svc = self._make_service()
        ctx = svc.context_string()
        assert isinstance(ctx, str)
        assert len(ctx) > 100

    def test_context_string_contains_header(self):
        svc = self._make_service()
        ctx = svc.context_string()
        assert "SIGNAL CATALOG" in ctx
        assert "blocks" in ctx
        assert "signals" in ctx

    def test_context_string_contains_block_table(self):
        svc = self._make_service()
        ctx = svc.context_string()
        assert "BLOCKS" in ctx
        assert "cup_and_handle" in ctx
        assert "rsi" in ctx

    def test_context_string_fits_token_budget(self):
        """Context string must be ≤ ~5K tokens (rough estimate: 4 chars/token)."""
        svc = SignalCatalogService()
        svc.load(with_live_stats=False)
        ctx = svc.context_string()
        estimated_tokens = len(ctx) / 4
        assert estimated_tokens <= 5500, (
            f"Context string too long: ~{estimated_tokens:.0f} tokens "
            f"({len(ctx)} chars). Must fit ~5K token budget."
        )

    def test_context_string_contains_categories(self):
        svc = self._make_service()
        ctx = svc.context_string()
        assert "CATS:" in ctx
        assert "PATTERNS" in ctx
        assert "OSCILLATORS" in ctx

    def test_context_string_with_stats_shows_stats_table(self):
        entries = {"rsi": _make_entry("rsi", "OSCILLATORS", 25, "NEUTRAL",
                                      ["RSI_OVERSOLD", "BULLISH", "BEARISH", "NEUTRAL"])}
        stats = {
            "RSI_OVERSOLD": SignalStats("RSI_OVERSOLD", total_occurrences=500,
                                       trades_triggered=120, trigger_rate=0.24,
                                       win_rate=0.65, profit_factor=1.8),
        }
        svc = _loaded_service(entries, stats)
        ctx = svc.context_string()
        assert "SIGNAL STATS" in ctx
        assert "RSI_OVERSOLD" in ctx
        assert "500" in ctx

    def test_full_registry_context_string(self):
        svc = SignalCatalogService()
        svc.load(with_live_stats=False)
        ctx = svc.context_string()
        # Spot-check expected content
        assert "SIGNAL CATALOG" in ctx
        assert "BLOCKS" in ctx
        assert len(ctx) > 500


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------

class TestSearch:
    def _make_service(self) -> SignalCatalogService:
        entries = {
            "cup_and_handle": _make_entry("cup_and_handle", "PATTERNS", 30, "BULLISH",
                                          description="Cup and handle bullish continuation"),
            "rsi": _make_entry("rsi", "OSCILLATORS", 25, "NEUTRAL",
                               description="RSI oscillator momentum indicator"),
            "macd": _make_entry("macd", "OSCILLATORS", 25, "NEUTRAL",
                                description="MACD momentum crossover"),
        }
        return _loaded_service(entries)

    def test_search_by_block_name(self):
        svc = self._make_service()
        results = svc.search("rsi")
        names = [r["name"] for r in results]
        assert "rsi" in names

    def test_search_by_category(self):
        svc = self._make_service()
        results = svc.search("oscillators")
        names = [r["name"] for r in results]
        assert "rsi" in names
        assert "macd" in names

    def test_search_by_keyword_in_description(self):
        svc = self._make_service()
        results = svc.search("momentum")
        names = [r["name"] for r in results]
        assert "rsi" in names or "macd" in names

    def test_search_returns_dicts(self):
        svc = self._make_service()
        results = svc.search("rsi")
        assert all(isinstance(r, dict) for r in results)
        assert all("name" in r for r in results)
        assert all("signals" in r for r in results)

    def test_search_no_match_returns_empty(self):
        svc = self._make_service()
        results = svc.search("xxxxxxnonexistent")
        assert results == []

    def test_search_ranks_exact_name_first(self):
        svc = self._make_service()
        results = svc.search("cup_and_handle")
        assert results[0]["name"] == "cup_and_handle"


# ---------------------------------------------------------------------------
# get_signal_info tests
# ---------------------------------------------------------------------------

class TestGetSignalInfo:
    def _make_service(self) -> SignalCatalogService:
        entries = {
            "rsi": _make_entry("rsi", "OSCILLATORS", 25, "NEUTRAL",
                               ["RSI_OVERSOLD", "RSI_OVERBOUGHT", "BULLISH", "BEARISH", "NEUTRAL"]),
            "stoch": _make_entry("stoch", "OSCILLATORS", 20, "NEUTRAL",
                                 ["STOCH_OVERSOLD", "RSI_OVERSOLD", "BULLISH", "BEARISH", "NEUTRAL"]),
        }
        stats = {
            "RSI_OVERSOLD": SignalStats("RSI_OVERSOLD", total_occurrences=300, win_rate=0.6),
        }
        return _loaded_service(entries, stats)

    def test_get_signal_info_known_signal(self):
        svc = self._make_service()
        info = svc.get_signal_info("RSI_OVERSOLD")
        assert info is not None
        assert info["signal"] == "RSI_OVERSOLD"
        assert "rsi" in info["emitted_by"]
        assert "stoch" in info["emitted_by"]

    def test_get_signal_info_includes_stats(self):
        svc = self._make_service()
        info = svc.get_signal_info("RSI_OVERSOLD")
        assert info["stats"] is not None
        assert info["stats"]["occurrences"] == 300
        assert info["stats"]["win_rate"] == pytest.approx(0.6)

    def test_get_signal_info_unknown_signal(self):
        svc = self._make_service()
        assert svc.get_signal_info("UNKNOWN_SIGNAL_XYZ") is None

    def test_get_signal_info_case_insensitive(self):
        svc = self._make_service()
        info = svc.get_signal_info("rsi_oversold")
        assert info is not None
        assert info["signal"] == "RSI_OVERSOLD"


# ---------------------------------------------------------------------------
# list_signals_by_type tests
# ---------------------------------------------------------------------------

class TestListSignalsByType:
    def _make_service(self) -> SignalCatalogService:
        entries = {
            "rsi": _make_entry("rsi", "OSCILLATORS", 25, "NEUTRAL",
                               ["RSI_OVERSOLD", "RSI_OVERBOUGHT", "BULLISH", "BEARISH", "NEUTRAL"]),
            "cup_and_handle": _make_entry("cup_and_handle", "PATTERNS", 30, "BULLISH",
                                          ["BREAKOUT_CONFIRMED", "BULLISH", "BEARISH", "NEUTRAL"]),
        }
        return _loaded_service(entries)

    def test_list_by_category_oscillators(self):
        svc = self._make_service()
        results = svc.list_signals_by_type("OSCILLATORS")
        signals = [r["signal"] for r in results]
        assert "RSI_OVERSOLD" in signals
        assert "RSI_OVERBOUGHT" in signals

    def test_list_by_direction_bullish(self):
        svc = self._make_service()
        results = svc.list_signals_by_type("BULLISH")
        blocks = [r["block"] for r in results]
        assert "cup_and_handle" in blocks

    def test_list_by_unknown_type_returns_empty(self):
        svc = self._make_service()
        results = svc.list_signals_by_type("NONEXISTENT_TYPE")
        assert results == []

    def test_list_returns_dicts_with_signal_field(self):
        svc = self._make_service()
        results = svc.list_signals_by_type("OSCILLATORS")
        assert all("signal" in r for r in results)
        assert all("block" in r for r in results)


# ---------------------------------------------------------------------------
# Live stats mock test
# ---------------------------------------------------------------------------

class TestLiveStatsMock:
    def test_load_with_live_stats_calls_db(self):
        """Verify that _load_live_stats is called when db_url is set."""
        with patch.object(SignalCatalogService, "_load_registry"):
            with patch.object(SignalCatalogService, "_load_live_stats") as mock_stats:
                svc = SignalCatalogService(db_url="postgresql://test/db")
                svc._entries = {}
                svc._signal_index = {}
                svc.load(with_live_stats=True)
                mock_stats.assert_called_once()

    def test_load_without_db_skips_live_stats(self):
        """Verify live stats are skipped when no db_url."""
        with patch.object(SignalCatalogService, "_load_registry"):
            with patch.object(SignalCatalogService, "_load_live_stats") as mock_stats:
                svc = SignalCatalogService(db_url=None)
                svc._entries = {}
                svc._signal_index = {}
                svc.load(with_live_stats=True)
                mock_stats.assert_not_called()

    def test_load_stats_failure_doesnt_crash(self):
        """DB unavailability must not prevent catalog from loading."""
        with patch.object(SignalCatalogService, "_load_live_stats", side_effect=Exception("DB down")):
            svc = SignalCatalogService(db_url="postgresql://bad/url")
            svc.load(with_live_stats=True)  # should not raise
            assert svc._loaded is True
            assert svc._stats_source == "none"

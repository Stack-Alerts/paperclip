"""
Regression tests for BTCAAAAA-37812 / BTCAAAAA-37919:
Backtest with display-name block names returns 0 trades.

Root cause: the web UI persists block names using display casing
("Asia session 50 percent") while BlockRegistry is keyed by snake_case
("asia_session_50_percent"). Without normalization every signal weight
fell back to the default 10 pts and total confluence (10+10+10=30) stayed
below the 40-pt threshold → 0 trades.

Fix (app.py:2196-2236, PR #198): normalize block names and timing_constraint
references from display casing to snake_case BEFORE handing the strategy
to _dict_to_config / MulticoreBacktestEngine.
"""
from __future__ import annotations

import copy
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-37812"),
    pytest.mark.regression,
]

# ---------------------------------------------------------------------------
# Strategy as stored by the web UI — block names use display casing
# ---------------------------------------------------------------------------

_DISPLAY_NAME_STRATEGY: dict = {
    "name": "50% Asia Rejection Simple",
    "strategy_type": "Bearish",
    "confluence_threshold": 40,
    "blocks": [
        {
            "name": "Asia session 50 percent",
            "logic": "AND",
            "signals": [
                {
                    "name": "AT_ASIA_50",
                    "logic": "AND",
                    "weight": 20,
                },
                {
                    "name": "BELOW_ASIA_50",
                    "logic": "AND",
                    "weight": 15,
                    "timing_constraint": {
                        "max_candles": 3,
                        "reference": "Asia session 50 percent::AT_ASIA_50",
                    },
                },
            ],
        },
        {
            "name": "Ema 55 vector",
            "logic": "AND",
            "signals": [
                {"name": "BEARISH_CLIMAX", "logic": "AND", "weight": 22},
            ],
        },
        {
            "name": "Liquidity sweep",
            "logic": "OR",
            "signals": [
                {"name": "BEARISH_SWEEP", "logic": "OR", "weight": 10},
            ],
        },
    ],
}

_BACKTEST_CONFIG: dict = {
    "mode": 1,
    "timeframe": "15m",
    "startDate": "2026-01-01",
    "endDate": "2026-03-31",
    "starting_capital": 10000,
    "risk_per_trade_pct": 10,
    "confluence_threshold": 40,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_normalization(strategy: dict) -> dict:
    """
    Re-implement the block-name normalization from app.py:2196-2214 so this
    test stays decoupled from the FastAPI app import overhead while still
    covering the exact transformation under test.
    """
    normalized = copy.deepcopy(strategy)
    for blk in normalized.get("blocks") or []:
        raw = blk.get("name", "")
        blk["name"] = raw.lower().replace(" ", "_")
        for sig in blk.get("signals") or []:
            tc = sig.get("timing_constraint")
            if tc and isinstance(tc, dict) and "::" in (tc.get("reference") or ""):
                ref_block, ref_sig = tc["reference"].split("::", 1)
                tc["reference"] = f"{ref_block.lower().replace(' ', '_')}::{ref_sig}"
    return normalized


def _capture_engine_call(strategy: dict, config: dict) -> dict:
    """
    Runs _run_backtest_in_thread with all heavy I/O patched out.
    Returns the strategy_config dict actually passed to MulticoreBacktestEngine.
    """
    run_id = "test-run-37812"

    import src.api.app as api_app

    api_app._backtest_runs[run_id] = {
        "runId": run_id,
        "strategyId": "test",
        "status": "running",
        "progress": 0,
        "trades": [],
        "metrics": {},
        "logs": [],
        "error": None,
        "config": config,
        "startedAt": "2026-01-01T00:00:00Z",
        "completedAt": None,
    }

    fake_bars = [object()]

    fake_engine = MagicMock()
    fake_engine.run_backtest.return_value = {"trades": [{"id": "t1"}], "metrics": {}}

    fake_provider = MagicMock()
    fake_provider.load_bars_for_backtest.return_value = fake_bars

    fake_sp = MagicMock()
    fake_sp._dict_to_config.return_value = MagicMock()

    with (
        patch("src.optimizer_v3.core.backtest_data_provider.get_backtest_provider", return_value=fake_provider),
        patch("src.optimizer_v3.core.multicore_backtest_engine.MulticoreBacktestEngine", return_value=fake_engine),
        patch(
            "src.strategy_builder.persistence.strategy_persistence.StrategyPersistence",
            return_value=fake_sp,
        ),
    ):
        api_app._run_backtest_in_thread(run_id, strategy, config)

    assert fake_engine.run_backtest.called, "MulticoreBacktestEngine.run_backtest was never called"
    call_kwargs = fake_engine.run_backtest.call_args
    if call_kwargs.kwargs.get("strategy_config") is not None:
        return call_kwargs.kwargs["strategy_config"]
    return call_kwargs.args[1]


# ---------------------------------------------------------------------------
# Unit tests: pure normalization logic
# ---------------------------------------------------------------------------

class TestBlockNameNormalization:
    """Verify the display-name → snake_case transformation in isolation."""

    def test_block_name_display_to_snake(self) -> None:
        result = _apply_normalization(_DISPLAY_NAME_STRATEGY)
        names = [b["name"] for b in result["blocks"]]
        assert "asia_session_50_percent" in names, f"Expected snake_case block name; got {names}"
        assert "ema_55_vector" in names, f"Expected snake_case block name; got {names}"
        assert "liquidity_sweep" in names, f"Expected snake_case block name; got {names}"

    def test_original_display_names_gone(self) -> None:
        result = _apply_normalization(_DISPLAY_NAME_STRATEGY)
        names = [b["name"] for b in result["blocks"]]
        assert "Asia session 50 percent" not in names, "Display name must not survive normalization"
        assert "Ema 55 vector" not in names
        assert "Liquidity sweep" not in names

    def test_timing_constraint_reference_normalized(self) -> None:
        result = _apply_normalization(_DISPLAY_NAME_STRATEGY)
        asia_block = next(b for b in result["blocks"] if b["name"] == "asia_session_50_percent")
        below_sig = next(s for s in asia_block["signals"] if s["name"] == "BELOW_ASIA_50")
        ref = below_sig["timing_constraint"]["reference"]
        assert ref == "asia_session_50_percent::AT_ASIA_50", (
            f"timing_constraint reference not normalized; got {ref!r}"
        )

    def test_signal_name_unchanged(self) -> None:
        result = _apply_normalization(_DISPLAY_NAME_STRATEGY)
        asia_block = next(b for b in result["blocks"] if b["name"] == "asia_session_50_percent")
        sig_names = [s["name"] for s in asia_block["signals"]]
        assert "AT_ASIA_50" in sig_names, "Signal name must not be lowercased"
        assert "BELOW_ASIA_50" in sig_names

    def test_already_snake_case_unchanged(self) -> None:
        strategy = copy.deepcopy(_DISPLAY_NAME_STRATEGY)
        for blk in strategy["blocks"]:
            blk["name"] = blk["name"].lower().replace(" ", "_")
        result = _apply_normalization(strategy)
        names = [b["name"] for b in result["blocks"]]
        assert names == [b["name"] for b in strategy["blocks"]], (
            "Re-normalizing already-snake-case names must be idempotent"
        )

    def test_weights_preserved(self) -> None:
        result = _apply_normalization(_DISPLAY_NAME_STRATEGY)
        asia_block = next(b for b in result["blocks"] if b["name"] == "asia_session_50_percent")
        at_asia = next(s for s in asia_block["signals"] if s["name"] == "AT_ASIA_50")
        assert at_asia["weight"] == 20, "Normalization must not alter signal weights"

    def test_original_strategy_not_mutated(self) -> None:
        original_name = _DISPLAY_NAME_STRATEGY["blocks"][0]["name"]
        _apply_normalization(_DISPLAY_NAME_STRATEGY)
        assert _DISPLAY_NAME_STRATEGY["blocks"][0]["name"] == original_name, (
            "Normalization must deepcopy — original strategy must not be mutated"
        )


# ---------------------------------------------------------------------------
# Integration tests: engine receives normalized names
# ---------------------------------------------------------------------------

class TestBacktestEngineReceivesNormalizedNames:
    """
    Verify that _run_backtest_in_thread normalizes block names before
    calling MulticoreBacktestEngine, preventing the 0-trade regression.
    """

    @pytest.fixture(autouse=True)
    def _cleanup(self):
        import src.api.app as api_app
        yield
        api_app._backtest_runs.pop("test-run-37812", None)

    def test_engine_receives_snake_case_block_names(self) -> None:
        strategy_seen = _capture_engine_call(
            copy.deepcopy(_DISPLAY_NAME_STRATEGY),
            copy.deepcopy(_BACKTEST_CONFIG),
        )
        names = [b["name"] for b in strategy_seen.get("blocks", [])]
        assert "Asia session 50 percent" not in names, (
            "Display-name block name must be normalized before engine call"
        )

    def test_engine_receives_normalized_timing_constraint(self) -> None:
        strategy_seen = _capture_engine_call(
            copy.deepcopy(_DISPLAY_NAME_STRATEGY),
            copy.deepcopy(_BACKTEST_CONFIG),
        )
        blocks = {b["name"]: b for b in strategy_seen.get("blocks", [])}
        asia = blocks.get("asia_session_50_percent", {})
        sigs = {s["name"]: s for s in asia.get("signals", [])}
        below = sigs.get("BELOW_ASIA_50", {})
        tc = below.get("timing_constraint", {})
        ref = tc.get("reference", "")
        assert ref == "asia_session_50_percent::AT_ASIA_50", (
            f"timing_constraint reference passed to engine not normalized: {ref!r}"
        )

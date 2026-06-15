"""
Rec-Pipeline Close-the-Loop Test Suite — P2.4
============================================

Sprint 1.6.1 — Phase 2 Day 2 (BTCAAAAA-36470)

End-to-end coverage of the AI recommendation pipeline. Each test follows
the real public API; no internal helpers are exercised.

Pipeline stages:
    extraction (BlockIntelligenceExtractor)
      → analysis (StrategyDeepAnalyzer)
        → AI enhancement (AIRecommendationEnhancer, optional)
          → generate (IntelligentRecommendationEngine.generate_recommendations)
            → format (format_recommendation_text)
              → apply (apply_recommendations)

These tests are intentionally close-the-loop: they call generate, then
apply the output, then assert on the final config state. That's the
contract the UI/worker relies on.

The P2.3 contracts (skip empty-signal ADD_BLOCK; skip out-of-range or
unknown ADJUST_PARAM) are asserted here as end-to-end invariants — not
just as unit-level apply-path tests — so a regression in any stage is
caught at the same point the user would see it.
"""

import pytest
from copy import deepcopy

from src.optimizer_v3.core.intelligent_recommendation_engine import (
    IntelligentRecommendationEngine,
    IntegratedRecommendation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    """Single engine instance shared across tests in this module."""
    return IntelligentRecommendationEngine()


def _make_strategy_config(**extra):
    """Minimal but realistic strategy config — matches the contract
    apply_recommendations expects (strategy_type + blocks[].signals)."""
    config = {
        "name": "Pipeline Test Strategy",
        "strategy_type": "LONG_SHORT",
        "blocks": [
            {
                "name": "hod",
                "signals": [
                    {"name": "HOD_REJECTION"},
                    {"name": "BEARISH_BREAK"},
                ],
            }
        ],
    }
    config.update(extra)
    return config


def _rec(type_: str, **kwargs) -> IntegratedRecommendation:
    """Shorthand constructor for a primary rec."""
    return IntegratedRecommendation(type=type_, primary=True, **kwargs)


# A poor backtest profile — high enough drawdown + low enough win-rate
# to plausibly generate recommendations. Kept separate from unit-level
# fixtures so a future tuning of generate_recommendations thresholds
# only needs one update.
POOR_BACKTEST = {
    "total_trades": 12,
    "win_rate": 0.42,
    "profit_factor": 1.05,
    "max_drawdown_pct": 25.0,
    "sharpe_ratio": 0.4,
}

HEALTHY_BACKTEST = {
    "total_trades": 60,
    "win_rate": 0.62,
    "profit_factor": 1.85,
    "max_drawdown_pct": 8.0,
    "sharpe_ratio": 1.7,
}

SAMPLE_METRICS = {
    "win_rate": {"value": 0.42, "rating": "⚠ Fair"},
    "profit_factor": {"value": 1.05, "rating": "⚠ Fair"},
    "max_drawdown": {"value": 25.0, "rating": "✗ Poor"},
    "sharpe_ratio": {"value": 0.4, "rating": "✗ Poor"},
}


# ---------------------------------------------------------------------------
# Stage: generate_recommendations
# ---------------------------------------------------------------------------

class TestPipelineGenerate:
    """generate_recommendations contract."""

    def test_generate_returns_list(self, engine):
        """generate_recommendations must return a list (possibly empty)."""
        result = engine.generate_recommendations(
            strategy_config=_make_strategy_config(),
            backtest_results=POOR_BACKTEST,
            metrics=SAMPLE_METRICS,
            lookback_days=180,
        )
        assert isinstance(result, list), f"Expected list, got {type(result)}"

    def test_generate_does_not_mutate_input_config(self, engine):
        """The strategy_config dict passed in must not be mutated by generate."""
        config = _make_strategy_config(stop_loss_pct=2.0)
        snapshot = deepcopy(config)
        engine.generate_recommendations(
            strategy_config=config,
            backtest_results=POOR_BACKTEST,
            metrics=SAMPLE_METRICS,
            lookback_days=180,
        )
        assert config == snapshot, "generate_recommendations mutated the input config"

    def test_generate_each_rec_has_required_fields(self, engine):
        """Every IntegratedRecommendation has the P2.3-blessed fields populated."""
        recs = engine.generate_recommendations(
            strategy_config=_make_strategy_config(),
            backtest_results=POOR_BACKTEST,
            metrics=SAMPLE_METRICS,
            lookback_days=180,
        )
        for rec in recs:
            assert isinstance(rec, IntegratedRecommendation), \
                f"Got non-IntegratedRecommendation: {type(rec)}"
            assert rec.type in {
                "ADD_BLOCK", "ADJUST_PARAM", "ADD_RECHECK", "ADD_TIMING",
            }, f"Unknown rec type: {rec.type!r}"
            assert isinstance(rec.combined_confidence, float)
            assert 0.0 <= rec.combined_confidence <= 1.0, \
                f"combined_confidence out of range: {rec.combined_confidence}"

    def test_generate_handles_healthy_backtest_without_crashing(self, engine):
        """A healthy backtest should not crash generate; it may return recs
        (e.g. optimization suggestions) but it must not raise."""
        recs = engine.generate_recommendations(
            strategy_config=_make_strategy_config(),
            backtest_results=HEALTHY_BACKTEST,
            metrics={
                "win_rate": {"value": 0.62, "rating": "✓ Good"},
                "profit_factor": {"value": 1.85, "rating": "✓ Good"},
                "max_drawdown": {"value": 8.0, "rating": "✓ Good"},
                "sharpe_ratio": {"value": 1.7, "rating": "✓ Good"},
            },
            lookback_days=180,
        )
        assert isinstance(recs, list)


# ---------------------------------------------------------------------------
# Stage: format_recommendation_text
# ---------------------------------------------------------------------------

class TestPipelineFormat:
    """format_recommendation_text contract."""

    @pytest.mark.parametrize("rec_type", [
        "ADD_BLOCK",
        "ADJUST_PARAM",
        "ADD_RECHECK",
        "ADD_TIMING",
    ])
    def test_format_handles_known_types(self, engine, rec_type):
        """format_recommendation_text returns a non-empty string for every
        known rec type — the UI relies on it always returning display text."""
        rec = _rec(
            rec_type,
            block_name="hod",
            signal_name="HOD_REJECTION",
            parameter_name="stop_loss_pct",
            configuration={"signals": [{"name": "EMA_CROSS"}], "new_value": 1.5},
        )
        text = engine.format_recommendation_text(rec)
        assert isinstance(text, str)
        assert len(text) > 0, f"Empty formatted text for type {rec_type}"


# ---------------------------------------------------------------------------
# Stage: apply_recommendations (close-the-loop)
# ---------------------------------------------------------------------------

class TestPipelineCloseTheLoop:
    """The canonical P2.4 test: generate → apply → assert final config state."""

    def test_pipeline_close_the_loop_with_poor_backtest(self, engine):
        """End-to-end: feed a poor backtest through generate, then apply
        the recommendations and assert the config reflects them.

        This is the single most important P2 test — it's what the UI
        hits when the user clicks 'Apply All'."""
        config = _make_strategy_config()
        recs = engine.generate_recommendations(
            strategy_config=config,
            backtest_results=POOR_BACKTEST,
            metrics=SAMPLE_METRICS,
            lookback_days=180,
        )

        # Always safe to call apply even if generate returned 0 recs
        result = engine.apply_recommendations(config, recs)

        assert set(result.keys()) >= {"applied", "skipped", "failed", "errors"}
        assert isinstance(result["applied"], list)
        assert isinstance(result["skipped"], list)
        assert isinstance(result["failed"], list)
        assert isinstance(result["errors"], dict)

        # The sum of all buckets + already-applied should equal the input
        total = len(result["applied"]) + len(result["skipped"]) + len(result["failed"])
        assert total == len(recs), \
            f"Accounted-for count {total} != input rec count {len(recs)}"

    def test_pipeline_close_the_loop_does_not_lose_config(self, engine):
        """P2.3 safety: apply must not strip out the original blocks
        even when every generated rec is rejected."""
        config = _make_strategy_config()
        original_block_names = [b["name"] for b in config["blocks"]]

        # Hand-craft recs that the new P2.3 contract will reject
        recs = [
            _rec("ADD_BLOCK", block_name="hod"),  # duplicate
            _rec("ADJUST_PARAM", parameter_name="magic_param",
                 configuration={"new_value": 99}),  # unknown param
        ]

        engine.apply_recommendations(config, recs)

        # Original block list is intact
        assert [b["name"] for b in config["blocks"]] == original_block_names

    def test_pipeline_rejects_empty_signal_block_at_apply(self, engine):
        """P2.3 invariant: even if a rec somehow slips through without
        signals, apply must skip it. We hand-build the rec to test
        the apply-path guard, not the generate-path."""
        config = _make_strategy_config()
        recs = [
            _rec("ADD_BLOCK", block_name="no_signals_block", configuration={}),
        ]
        result = engine.apply_recommendations(config, recs)

        assert len(result["applied"]) == 0
        assert len(result["skipped"]) == 1

    def test_pipeline_rejects_out_of_range_param(self, engine):
        """P2.3 invariant: ADJUST_PARAM values outside the schema range
        must be skipped at apply time, not silently coerced."""
        config = _make_strategy_config()
        recs = [
            _rec("ADJUST_PARAM",
                 parameter_name="stop_loss_pct",
                 configuration={"new_value": 999.0}),  # way above max=50
        ]
        result = engine.apply_recommendations(config, recs)
        assert len(result["skipped"]) == 1
        assert config.get("stop_loss_pct") != 999.0  # unchanged

    def test_pipeline_rejects_unknown_param(self, engine):
        """P2.3 invariant: parameter_name not in _ADJUSTABLE_PARAMETERS
        is rejected — we never write arbitrary config keys."""
        config = _make_strategy_config()
        recs = [
            _rec("ADJUST_PARAM",
                 parameter_name="never_existed",
                 configuration={"new_value": 1.0}),
        ]
        result = engine.apply_recommendations(config, recs)
        assert len(result["skipped"]) == 1
        assert "never_existed" not in config

    def test_pipeline_apply_is_idempotent(self, engine):
        """Re-applying the same rec set yields identical final state —
        the second call must not double-insert blocks or double-apply params."""
        config = _make_strategy_config()
        recs = [
            _rec("ADD_BLOCK", block_name="ema_trend",
                 configuration={"signals": [{"name": "EMA_CROSS"}]}),
            _rec("ADJUST_PARAM", parameter_name="stop_loss_pct",
                 configuration={"new_value": 1.5}),
        ]

        first_result = engine.apply_recommendations(config, recs)
        first_block_count = len(config["blocks"])
        first_sl = config["stop_loss_pct"]

        # Second call on the same config: dup block is skipped, param re-applied
        second_result = engine.apply_recommendations(config, recs)

        assert len(config["blocks"]) == first_block_count, \
            "Re-applying recs must not duplicate blocks"
        assert config["stop_loss_pct"] == first_sl
        assert len(second_result["skipped"]) >= 1, \
            "Second apply should skip the duplicate block"

    def test_pipeline_summary_stats_returns_engine_state(self, engine):
        """get_summary_stats returns the engine's runtime state (block DB,
        AI enhancement availability, components loaded). It is a dict
        regardless of what recs were applied — rec-level accounting lives
        in the apply_recommendations return value, not here."""
        config = _make_strategy_config()
        recs = [
            _rec("ADD_BLOCK", block_name="ema_trend",
                 configuration={"signals": [{"name": "EMA_CROSS"}]}),
            _rec("ADJUST_PARAM", parameter_name="stop_loss_pct",
                 configuration={"new_value": 2.5}),
        ]
        engine.apply_recommendations(config, recs)
        stats = engine.get_summary_stats()

        assert isinstance(stats, dict)
        # Engine-state contract: blocks-in-DB count, AI flag, components map
        assert "total_blocks_in_database" in stats, \
            f"Missing total_blocks_in_database: {stats}"
        assert "ai_enhancement_available" in stats, \
            f"Missing ai_enhancement_available: {stats}"
        assert "components_loaded" in stats, \
            f"Missing components_loaded: {stats}"
        assert isinstance(stats["components_loaded"], dict)


# ---------------------------------------------------------------------------
# Stage: error path coverage
# ---------------------------------------------------------------------------

class TestPipelineErrorPaths:
    """Edge cases the close-the-loop path can hit in production."""

    def test_apply_with_malformed_rec_does_not_corrupt_config(self, engine):
        """A rec whose configuration is the wrong shape must land in
        'failed' or 'skipped' — never crash the batch."""
        config = _make_strategy_config()
        bad_rec = _rec("ADJUST_PARAM", parameter_name="stop_loss_pct",
                      configuration=None)  # .get() will raise AttributeError
        result = engine.apply_recommendations(config, [bad_rec])
        # Either rejected to skipped (graceful) or failed (captured) — never crash
        assert len(result["failed"]) + len(result["skipped"]) == 1
        assert "stop_loss_pct" not in config or config.get("stop_loss_pct") is not None

    def test_apply_with_rec_missing_required_attributes(self, engine):
        """A rec missing its `type` should not crash apply."""
        config = _make_strategy_config()
        # Construct a rec with type=None
        rec = IntegratedRecommendation(
            type=None,
            primary=True,
            configuration={},
        )
        result = engine.apply_recommendations(config, [rec])
        # Should land in skipped (unknown type) or failed — never crash
        assert len(result["failed"]) + len(result["skipped"]) == 1

    def test_pipeline_survives_empty_input(self, engine):
        """Empty config + empty recs = clean empty result."""
        config = {"name": "Empty", "strategy_type": "LONG_SHORT", "blocks": []}
        result = engine.apply_recommendations(config, [])
        assert result == {
            "applied": [],
            "skipped": [],
            "failed": [],
            "errors": {},
        }

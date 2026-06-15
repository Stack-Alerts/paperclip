"""
Unit Tests for IntelligentRecommendationEngine.apply_recommendations()
======================================================================

Sprint 1.9.3 — One-Click Apply Recommendations

Coverage:
- ADD_BLOCK: happy path, duplicate block skip, no block_name error
- ADJUST_PARAM: happy path, missing new_value skip, missing parameter_name skip
- ADD_RECHECK: happy path, signal not found skip
- ADD_TIMING: happy path, block not found skip
- Unknown type: graceful skip
- Exception in rec processing: captured in "failed", no crash
- Empty recommendations list: clean empty result
"""

import pytest
from types import SimpleNamespace

from src.optimizer_v3.core.intelligent_recommendation_engine import (
    IntelligentRecommendationEngine,
    IntegratedRecommendation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    """Create a single engine instance shared across tests in this module."""
    return IntelligentRecommendationEngine()


def _make_strategy_config(**extra):
    """Return a minimal strategy config dict with one existing block."""
    config = {
        "name": "Test Strategy",
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
    """Helper to build an IntegratedRecommendation quickly."""
    return IntegratedRecommendation(type=type_, primary=True, **kwargs)


# ---------------------------------------------------------------------------
# Tests: ADD_BLOCK
# ---------------------------------------------------------------------------

class TestApplyAddBlock:
    def test_add_block_happy_path(self, engine):
        """ADD_BLOCK appends a new block dict to config['blocks']."""
        config = _make_strategy_config()
        rec = _rec(
            "ADD_BLOCK",
            block_name="ema_trend",
            configuration={"signals": [{"name": "EMA_CROSS"}]},
        )
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 1
        assert len(result["skipped"]) == 0
        assert len(result["failed"]) == 0
        block_names = [b["name"] for b in config["blocks"]]
        assert "ema_trend" in block_names

    def test_add_block_skips_duplicate(self, engine):
        """ADD_BLOCK skips silently if block is already in config."""
        config = _make_strategy_config()
        rec = _rec("ADD_BLOCK", block_name="hod")  # "hod" already exists
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 0
        assert len(result["skipped"]) == 1
        # Should NOT add a second "hod" block
        hod_count = sum(1 for b in config["blocks"] if b["name"] == "hod")
        assert hod_count == 1

    def test_add_block_skips_when_no_block_name(self, engine):
        """ADD_BLOCK with no block_name goes to skipped, not failed."""
        config = _make_strategy_config()
        rec = _rec("ADD_BLOCK", block_name=None)
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 0
        assert len(result["skipped"]) == 1
        assert len(result["failed"]) == 0

    def test_add_block_skips_when_no_signals(self, engine):
        """P2.3 — ADD_BLOCK with empty/missing signals is skipped (silent no-op guard)."""
        config = _make_strategy_config()
        rec = _rec("ADD_BLOCK", block_name="empty_block", configuration={})
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 0
        assert len(result["skipped"]) == 1
        block_names = [b["name"] for b in config["blocks"]]
        assert "empty_block" not in block_names

    def test_add_block_carries_configuration(self, engine):
        """ADD_BLOCK should preserve configuration as parameters on the new block."""
        config = _make_strategy_config()
        cfg = {"signals": [{"name": "VOL_SPIKE"}], "parameters": {"threshold": 0.5}}
        rec = _rec("ADD_BLOCK", block_name="volume_filter", configuration=cfg)
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 1
        new_block = next(b for b in config["blocks"] if b["name"] == "volume_filter")
        assert new_block.get("parameters") == {"threshold": 0.5}
        assert new_block.get("signals") == [{"name": "VOL_SPIKE"}]

    def test_add_multiple_blocks_sequentially(self, engine):
        """Multiple ADD_BLOCK recs for distinct blocks are all applied."""
        config = _make_strategy_config()
        recs = [
            _rec("ADD_BLOCK", block_name="ema_trend",
                 configuration={"signals": [{"name": "EMA_CROSS"}]}),
            _rec("ADD_BLOCK", block_name="rsi_filter",
                 configuration={"signals": [{"name": "RSI_OB"}]}),
        ]
        result = engine.apply_recommendations(config, recs)

        assert len(result["applied"]) == 2
        block_names = [b["name"] for b in config["blocks"]]
        assert "ema_trend" in block_names
        assert "rsi_filter" in block_names


# ---------------------------------------------------------------------------
# Tests: ADJUST_PARAM
# ---------------------------------------------------------------------------

class TestApplyAdjustParam:
    def test_adjust_param_happy_path(self, engine):
        """ADJUST_PARAM sets the specified key on the config dict."""
        config = _make_strategy_config(stop_loss_pct=2.0)
        rec = _rec(
            "ADJUST_PARAM",
            parameter_name="stop_loss_pct",
            configuration={"new_value": 1.5},
        )
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 1
        assert config["stop_loss_pct"] == 1.5

    def test_adjust_param_skips_when_no_new_value(self, engine):
        """ADJUST_PARAM with missing new_value in configuration is skipped."""
        config = _make_strategy_config()
        rec = _rec(
            "ADJUST_PARAM",
            parameter_name="stop_loss_pct",
            configuration={},  # no new_value
        )
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 0
        assert len(result["skipped"]) == 1

    def test_adjust_param_skips_when_no_parameter_name(self, engine):
        """ADJUST_PARAM with no parameter_name is skipped."""
        config = _make_strategy_config()
        rec = _rec(
            "ADJUST_PARAM",
            parameter_name=None,
            configuration={"new_value": 0.5},
        )
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 0
        assert len(result["skipped"]) == 1

    def test_adjust_param_adds_new_key(self, engine):
        """ADJUST_PARAM can add a key that didn't exist in the config yet."""
        config = _make_strategy_config()
        assert "take_profit_pct" not in config
        rec = _rec(
            "ADJUST_PARAM",
            parameter_name="take_profit_pct",
            configuration={"new_value": 3.0},
        )
        engine.apply_recommendations(config, [rec])
        assert config["take_profit_pct"] == 3.0

    def test_adjust_param_none_configuration_is_skipped(self, engine):
        """ADJUST_PARAM where configuration is None is handled gracefully."""
        config = _make_strategy_config()
        rec = _rec(
            "ADJUST_PARAM",
            parameter_name="stop_loss_pct",
            configuration=None,
        )
        result = engine.apply_recommendations(config, [rec])
        assert len(result["skipped"]) == 1


# ---------------------------------------------------------------------------
# Tests: ADD_RECHECK
# ---------------------------------------------------------------------------

class TestApplyAddRecheck:
    def test_add_recheck_happy_path(self, engine):
        """ADD_RECHECK attaches a recheck sub-config to the target signal."""
        config = _make_strategy_config()
        recheck_cfg = {"bar_delay": 25, "validation_mode": "SIGNAL"}
        rec = _rec(
            "ADD_RECHECK",
            block_name="hod",
            signal_name="HOD_REJECTION",
            configuration=recheck_cfg,
        )
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 1
        # Verify the signal was updated
        block = next(b for b in config["blocks"] if b["name"] == "hod")
        signal = next(s for s in block["signals"] if s["name"] == "HOD_REJECTION")
        assert signal.get("recheck") == recheck_cfg

    def test_add_recheck_skips_when_signal_not_found(self, engine):
        """ADD_RECHECK skips silently when the target signal doesn't exist."""
        config = _make_strategy_config()
        rec = _rec(
            "ADD_RECHECK",
            block_name="hod",
            signal_name="NONEXISTENT_SIGNAL",
            configuration={"bar_delay": 10},
        )
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 0
        assert len(result["skipped"]) == 1

    def test_add_recheck_skips_when_block_not_found(self, engine):
        """ADD_RECHECK skips silently when the block doesn't exist."""
        config = _make_strategy_config()
        rec = _rec(
            "ADD_RECHECK",
            block_name="missing_block",
            signal_name="HOD_REJECTION",
            configuration={"bar_delay": 5},
        )
        result = engine.apply_recommendations(config, [rec])

        assert len(result["skipped"]) == 1

    def test_add_recheck_skips_when_no_block_name(self, engine):
        """ADD_RECHECK with no block_name goes to skipped."""
        config = _make_strategy_config()
        rec = _rec(
            "ADD_RECHECK",
            block_name=None,
            signal_name="HOD_REJECTION",
            configuration={"bar_delay": 5},
        )
        result = engine.apply_recommendations(config, [rec])
        assert len(result["skipped"]) == 1


# ---------------------------------------------------------------------------
# Tests: ADD_TIMING
# ---------------------------------------------------------------------------

class TestApplyAddTiming:
    def test_add_timing_happy_path(self, engine):
        """ADD_TIMING attaches a timing sub-config to the target block."""
        config = _make_strategy_config()
        timing_cfg = {"max_candles": 10}
        rec = _rec(
            "ADD_TIMING",
            block_name="hod",
            configuration=timing_cfg,
        )
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 1
        block = next(b for b in config["blocks"] if b["name"] == "hod")
        assert block.get("timing") == timing_cfg

    def test_add_timing_skips_when_block_not_found(self, engine):
        """ADD_TIMING skips silently when the target block doesn't exist."""
        config = _make_strategy_config()
        rec = _rec(
            "ADD_TIMING",
            block_name="missing_block",
            configuration={"max_candles": 5},
        )
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 0
        assert len(result["skipped"]) == 1

    def test_add_timing_skips_when_no_block_name(self, engine):
        """ADD_TIMING with no block_name goes to skipped."""
        config = _make_strategy_config()
        rec = _rec("ADD_TIMING", block_name=None, configuration={"max_candles": 5})
        result = engine.apply_recommendations(config, [rec])
        assert len(result["skipped"]) == 1


# ---------------------------------------------------------------------------
# Tests: Edge / error cases
# ---------------------------------------------------------------------------

class TestApplyEdgeCases:
    def test_empty_recommendations_list(self, engine):
        """Empty list returns a clean empty result without touching config."""
        config = _make_strategy_config()
        original_blocks = [b["name"] for b in config["blocks"]]
        result = engine.apply_recommendations(config, [])

        assert result["applied"] == []
        assert result["skipped"] == []
        assert result["failed"] == []
        assert result["errors"] == {}
        assert [b["name"] for b in config["blocks"]] == original_blocks

    def test_unknown_type_is_skipped(self, engine):
        """Recommendations with unknown type are silently skipped."""
        config = _make_strategy_config()
        rec = _rec("CONFIGURE_SIGNAL", block_name="hod")  # not a known type
        result = engine.apply_recommendations(config, [rec])

        assert len(result["applied"]) == 0
        assert len(result["skipped"]) == 1
        assert len(result["failed"]) == 0

    def test_exception_in_rec_goes_to_failed(self, engine):
        """If a rec raises during apply, it goes to failed with error captured."""
        config = _make_strategy_config()

        # Craft a bad rec that will cause AttributeError: configuration is not iterable
        bad_rec = IntegratedRecommendation(
            type="ADJUST_PARAM",
            primary=True,
            parameter_name="test_param",
            configuration={"new_value": object()},  # unpicklable but not an error here
        )
        # Force an error by making configuration a non-dict
        bad_rec.configuration = "not_a_dict"  # .get() will raise AttributeError

        result = engine.apply_recommendations(config, [bad_rec])

        assert len(result["failed"]) == 1
        assert len(result["errors"]) == 1
        # Config must be unchanged
        assert "test_param" not in config

    def test_result_summary_keys_always_present(self, engine):
        """Result dict always has applied / skipped / failed / errors keys."""
        config = _make_strategy_config()
        result = engine.apply_recommendations(config, [])
        assert "applied" in result
        assert "skipped" in result
        assert "failed" in result
        assert "errors" in result

    def test_mixed_success_and_skip(self, engine):
        """Mix of valid and skippable recs produces correct counts.

        Note: P2.3 contract requires ADD_BLOCK.configuration to carry a
        non-empty `signals` list, and ADJUST_PARAM.parameter_name to be in
        the _ADJUSTABLE_PARAMETERS schema — otherwise the rec is skipped
        (not applied) with a warning recorded in errors.
        """
        config = _make_strategy_config()
        recs = [
            _rec(
                "ADD_BLOCK",
                block_name="ema_trend",
                configuration={"signals": [{"name": "EMA_CROSS"}]},
            ),                                              # NEW — will be applied
            _rec("ADD_BLOCK", block_name="hod"),              # duplicate — will be skipped
            _rec(
                "ADJUST_PARAM",
                parameter_name="stop_loss_pct",
                configuration={"new_value": 2.0},
            ),                                              # applied
        ]
        result = engine.apply_recommendations(config, recs)

        assert len(result["applied"]) == 2
        assert len(result["skipped"]) == 1
        assert len(result["failed"]) == 0

    def test_config_not_mutated_on_all_skips(self, engine):
        """Config remains unchanged when all recs are skipped."""
        config = _make_strategy_config()
        original_blocks = [b["name"] for b in config["blocks"]]
        recs = [
            _rec("ADD_BLOCK", block_name=None),            # skipped: no block_name
            _rec("ADD_BLOCK", block_name="hod"),            # skipped: duplicate
        ]
        engine.apply_recommendations(config, recs)
        assert [b["name"] for b in config["blocks"]] == original_blocks

"""
Unit tests for the empirical impact model (BTCAAAAA-36473, R0 evidence layer).

All tests inject synthetic (config, result) observations — no live DB required.
"""

import pytest

from src.optimizer_v3.core.empirical_impact_model import (
    ChangeType,
    ConfigDiffer,
    ConfigResultObservation,
    EmpiricalImpactModel,
    REGIME_ALL,
)


def _block(name, logic="AND", **params):
    b = {"name": name, "logic": logic, "signals": []}
    b.update(params)
    return b


def _obs(strategy_id, vn, blocks, metrics, regime=REGIME_ALL):
    return ConfigResultObservation(strategy_id, vn, blocks, metrics, regime)


# ---------------------------------------------------------------------------
# Config diffing
# ---------------------------------------------------------------------------


class TestConfigDiffer:
    def test_detects_added_block(self):
        events = ConfigDiffer.diff([_block("a")], [_block("a"), _block("b")])
        assert any(e.change_type == ChangeType.ADD_BLOCK and e.block_name == "b" for e in events)

    def test_detects_removed_block(self):
        events = ConfigDiffer.diff([_block("a"), _block("b")], [_block("a")])
        assert any(e.change_type == ChangeType.REMOVE_BLOCK and e.block_name == "b" for e in events)

    def test_detects_logic_change(self):
        events = ConfigDiffer.diff([_block("a", logic="AND")], [_block("a", logic="OR")])
        assert any(e.change_type == ChangeType.LOGIC_CHANGE and e.block_name == "a" for e in events)

    def test_detects_param_adjustment(self):
        events = ConfigDiffer.diff([_block("a", period=14)], [_block("a", period=21)])
        assert any(e.change_type == ChangeType.ADJUST_PARAM and e.block_name == "a" for e in events)

    def test_identical_configs_no_events(self):
        assert ConfigDiffer.diff([_block("a", period=14)], [_block("a", period=14)]) == []

    def test_boolean_flip_is_not_param_adjust(self):
        # Booleans are logic flags, not tunable numeric params.
        events = ConfigDiffer.diff([_block("a", enabled=True)], [_block("a", enabled=False)])
        assert all(e.change_type != ChangeType.ADJUST_PARAM for e in events)


# ---------------------------------------------------------------------------
# Empirical estimation
# ---------------------------------------------------------------------------


class TestEmpiricalEstimation:
    def _add_block_corpus(self, n, base=0.50, after=0.60):
        """n strategies each adding block 'vwap' between v1 and v2, win_rate base->after."""
        obs = []
        for i in range(n):
            sid = f"s{i}"
            obs.append(_obs(sid, 1, [_block("rsi")], {"win_rate": base}))
            obs.append(_obs(sid, 2, [_block("rsi"), _block("vwap")], {"win_rate": after}))
        return obs

    def test_sufficient_data_returns_empirical_estimate(self):
        model = EmpiricalImpactModel(self._add_block_corpus(6), min_samples=5)
        est = model.estimate_impact(ChangeType.ADD_BLOCK, "win_rate", block_name="vwap")
        assert est.sufficient is True
        assert est.source == "empirical"
        assert est.n_samples == 6
        assert est.value == pytest.approx(0.20, rel=1e-6)  # (0.60-0.50)/0.50

    def test_confidence_band_present_when_sufficient(self):
        model = EmpiricalImpactModel(self._add_block_corpus(6), min_samples=5)
        est = model.estimate_impact(ChangeType.ADD_BLOCK, "win_rate", block_name="vwap")
        assert est.ci_low is not None and est.ci_high is not None
        assert est.ci_low <= est.value <= est.ci_high

    def test_insufficient_data_falls_back_to_labeled_heuristic(self):
        # Only 2 samples but threshold is 5 -> not sufficient.
        model = EmpiricalImpactModel(self._add_block_corpus(2), min_samples=5)
        est = model.estimate_impact(ChangeType.ADD_BLOCK, "win_rate", block_name="vwap")
        assert est.sufficient is False
        # Either a labeled heuristic or 'none' — never a silently-trusted empirical value.
        assert est.source in ("heuristic_fallback", "none")
        assert "insufficient empirical data" in est.detail

    def test_no_data_returns_insufficient(self):
        model = EmpiricalImpactModel([], min_samples=5)
        est = model.estimate_impact(ChangeType.REMOVE_BLOCK, "sharpe_ratio", block_name="x")
        assert est.sufficient is False
        assert est.n_samples == 0
        assert est.value is None or est.source == "heuristic_fallback"

    def test_drawdown_relative_effect_sign_preserved(self):
        # max_drawdown_pct dropping 20->15 is an improvement -> negative relative effect.
        obs = []
        for i in range(6):
            sid = f"s{i}"
            obs.append(_obs(sid, 1, [_block("a")], {"max_drawdown_pct": 20.0}))
            obs.append(_obs(sid, 2, [_block("a"), _block("atr")], {"max_drawdown_pct": 15.0}))
        model = EmpiricalImpactModel(obs, min_samples=5)
        est = model.estimate_impact(ChangeType.ADD_BLOCK, "max_drawdown_pct", block_name="atr")
        assert est.value == pytest.approx(-0.25, rel=1e-6)
        assert "improves" in est.detail

    def test_zero_baseline_observation_dropped(self):
        obs = [
            _obs("s0", 1, [_block("a")], {"win_rate": 0.0}),
            _obs("s0", 2, [_block("a"), _block("b")], {"win_rate": 0.5}),
        ]
        model = EmpiricalImpactModel(obs, min_samples=1)
        est = model.estimate_impact(ChangeType.ADD_BLOCK, "win_rate", block_name="b")
        # baseline 0 -> relative effect undefined -> dropped -> no empirical evidence.
        assert est.source in ("heuristic_fallback", "none")


class TestBroadeningAndRegime:
    def test_broadens_across_blocks_when_specific_block_thin(self):
        # 6 ADD_BLOCK events for win_rate but each on a distinct block (1 per block).
        obs = []
        for i in range(6):
            sid = f"s{i}"
            obs.append(_obs(sid, 1, [_block("base")], {"win_rate": 0.50}))
            obs.append(_obs(sid, 2, [_block("base"), _block(f"blk{i}")], {"win_rate": 0.55}))
        model = EmpiricalImpactModel(obs, min_samples=5)
        # Asking for a specific block has n=1; broadening across blocks reaches n=6.
        est = model.estimate_impact(ChangeType.ADD_BLOCK, "win_rate", block_name="blk0")
        assert est.sufficient is True
        assert est.source == "empirical_broadened"
        assert est.block_name is None
        assert est.n_samples == 6

    def test_regime_conditioning_filters_observations(self):
        obs = []
        for i in range(5):
            sid = f"bull{i}"
            obs.append(_obs(sid, 1, [_block("a")], {"win_rate": 0.50}, regime="BULL"))
            obs.append(_obs(sid, 2, [_block("a"), _block("b")], {"win_rate": 0.60}, regime="BULL"))
        for i in range(5):
            sid = f"bear{i}"
            obs.append(_obs(sid, 1, [_block("a")], {"win_rate": 0.50}, regime="BEAR"))
            obs.append(_obs(sid, 2, [_block("a"), _block("b")], {"win_rate": 0.45}, regime="BEAR"))
        model = EmpiricalImpactModel(obs, min_samples=5)
        bull = model.estimate_impact(ChangeType.ADD_BLOCK, "win_rate", block_name="b", regime="BULL")
        bear = model.estimate_impact(ChangeType.ADD_BLOCK, "win_rate", block_name="b", regime="BEAR")
        assert bull.value == pytest.approx(0.20, rel=1e-6)
        assert bear.value == pytest.approx(-0.10, rel=1e-6)


class TestRecommendationOutcomes:
    def test_applied_recommendation_pairs_are_folded_in(self):
        model = EmpiricalImpactModel([], min_samples=3)
        outcomes = [
            {
                "change_type": "ADJUST_PARAM",
                "block_name": "rsi",
                "metrics_before": {"profit_factor": 1.0},
                "metrics_after": {"profit_factor": 1.2},
            }
            for _ in range(3)
        ]
        model.add_recommendation_outcomes(outcomes)
        est = model.estimate_impact(ChangeType.ADJUST_PARAM, "profit_factor", block_name="rsi")
        assert est.sufficient is True
        assert est.value == pytest.approx(0.20, rel=1e-6)


class TestCoverage:
    def test_coverage_summary(self):
        model = EmpiricalImpactModel(
            [
                _obs("s0", 1, [_block("a")], {"win_rate": 0.5}),
                _obs("s0", 2, [_block("a"), _block("b")], {"win_rate": 0.6}),
            ],
            min_samples=5,
        )
        cov = model.coverage()
        assert cov["n_observations"] == 2
        assert cov["by_change_type"].get("ADD_BLOCK", 0) >= 1
        assert "win_rate" in cov["metrics_covered"]

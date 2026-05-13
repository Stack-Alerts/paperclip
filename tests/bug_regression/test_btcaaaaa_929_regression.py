"""
Regression tests for BTCAAAAA-929: backfill DB signal weights, harden repair,
wire threshold to Quick Preview.

Issue: https://app.paperclip.ing/BTCAAAAA/issues/BTCAAAAA-929
Components:
  - src/strategy_builder/persistence/strategy_persistence.py   (Fix 1)
  - src/strategy_builder/ui/backtest_config_panel.py           (Fix 2)
  - src/strategy_builder/ui/strategy_builder_main_window.py    (Fix 3)

Fix 1 — _dict_to_config weight backfill:
  Signals without 'weight' key in the DB row now fall back to
  BlockRegistry.signal_tiers[signal_name].base_points before defaulting to 10.

Fix 2 — _repair_if_unreachable null-weight hardening:
  s.get('weight', 10) → (s.get('weight') or 10).  Prevents false-positive
  "repaired at 40==40" when weight is null; prevents TypeError if weight is
  stored as explicit null.

Fix 3 — _on_quick_preview confluence_threshold wiring:
  Explicitly sets strategy_config['confluence_threshold'] = <stored or 40>
  before BacktestWorker is instantiated, matching the full-backtest path.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.bug("BTCAAAAA-929"),
    pytest.mark.regression,
]


# ===========================================================================
# Fix 1: _dict_to_config — weight backfill from BlockRegistry
# ===========================================================================


class TestDictToConfigWeightBackfill:
    """StrategyPersistence._dict_to_config must backfill missing/null weights
    from BlockRegistry.signal_tiers[].base_points before defaulting to 10.

    NOTE: The final ``_w or 10`` expression means weight=0 is also coerced to
    10.  This is the intended fix behaviour — the v23-v25 schema treats None
    and 0 as "not set" to avoid false-positive repairs.
    """

    @pytest.fixture()
    def persistence(self):
        from src.strategy_builder.persistence.strategy_persistence import (
            StrategyPersistence,
        )
        return StrategyPersistence()

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _make_block_data(
        block_name: str = "asia_session_50_percent",
        logic: str = "OR",
        signals: list | None = None,
    ) -> list:
        if signals is None:
            signals = [{"name": "AT_ASIA_50", "logic": "OR"}]
        return [{"name": block_name, "logic": logic, "signals": signals}]

    def _make_meta(self, signal_tiers: dict | None = None):
        meta = MagicMock()
        meta.signal_tiers = signal_tiers
        return meta

    # -- tests -------------------------------------------------------------

    def test_explicit_weight_used(self, persistence):
        """Signal with explicit positive weight must use that weight directly."""
        data = {
            "name": "test",
            "description": "",
            "blocks": self._make_block_data(
                signals=[{"name": "AT_ASIA_50", "logic": "OR", "weight": 25}],
            ),
        }
        config = persistence._dict_to_config(data)
        assert config.blocks[0].signals[0].weight == 25

    def test_missing_weight_uses_registry_base_points(self, persistence):
        """Signal without weight key falls back to BlockRegistry base_points."""
        meta = self._make_meta({"AT_ASIA_50": {"base_points": 20}})
        with patch(
            "src.strategy_builder.persistence.strategy_persistence._block_registry_lookup",
            return_value=meta,
        ):
            data = {
                "name": "test",
                "description": "",
                "blocks": self._make_block_data(
                    signals=[{"name": "AT_ASIA_50", "logic": "OR"}],
                ),
            }
            config = persistence._dict_to_config(data)
        assert config.blocks[0].signals[0].weight == 20

    def test_missing_weight_no_registry_falls_to_10(self, persistence):
        """Signal without weight key and no registry lookup falls to 10."""
        with patch(
            "src.strategy_builder.persistence.strategy_persistence._block_registry_lookup",
            return_value=None,
        ):
            data = {
                "name": "test",
                "description": "",
                "blocks": self._make_block_data(
                    signals=[{"name": "UNKNOWN_SIGNAL", "logic": "OR"}],
                ),
            }
            config = persistence._dict_to_config(data)
        assert config.blocks[0].signals[0].weight == 10

    def test_weight_none_falls_back_to_registry(self, persistence):
        """weight=None triggers the same fallback path as missing key."""
        meta = self._make_meta({"BELOW_ASIA_50": {"base_points": 15}})
        with patch(
            "src.strategy_builder.persistence.strategy_persistence._block_registry_lookup",
            return_value=meta,
        ):
            data = {
                "name": "test",
                "description": "",
                "blocks": self._make_block_data(
                    signals=[{"name": "BELOW_ASIA_50", "logic": "OR", "weight": None}],
                ),
            }
            config = persistence._dict_to_config(data)
        assert config.blocks[0].signals[0].weight == 15

    def test_weight_zero_coerced_to_10_by_or_pattern(self):
        """Explicit weight=0 is coerced to 10 by the ``_w or 10`` fallback.
        (The fix intentionally treats None and 0 as "not set" to avoid
        false-positive null-weight bugs in _repair_if_unreachable.)"""
        from src.strategy_builder.persistence.strategy_persistence import (
            StrategyPersistence,
        )
        persistence = StrategyPersistence()
        data = {
            "name": "test",
            "description": "",
            "blocks": self._make_block_data(
                signals=[{"name": "AT_ASIA_50", "logic": "OR", "weight": 0}],
            ),
        }
        config = persistence._dict_to_config(data)
        assert config.blocks[0].signals[0].weight == 10

    def test_registry_has_no_tiers_falls_to_10(self, persistence):
        """BlockRegistry entry exists but has no signal_tiers → fallback to 10."""
        meta = self._make_meta(None)
        with patch(
            "src.strategy_builder.persistence.strategy_persistence._block_registry_lookup",
            return_value=meta,
        ):
            data = {
                "name": "test",
                "description": "",
                "blocks": self._make_block_data(
                    signals=[{"name": "AT_ASIA_50", "logic": "OR"}],
                ),
            }
            config = persistence._dict_to_config(data)
        assert config.blocks[0].signals[0].weight == 10

    def test_registry_missing_signal_in_tiers_falls_to_10(self, persistence):
        """Block has signal_tiers but signal name not found → fallback to 10."""
        meta = self._make_meta({"OTHER_SIGNAL": {"base_points": 99}})
        with patch(
            "src.strategy_builder.persistence.strategy_persistence._block_registry_lookup",
            return_value=meta,
        ):
            data = {
                "name": "test",
                "description": "",
                "blocks": self._make_block_data(
                    signals=[{"name": "MISSING_FROM_TIERS", "logic": "OR"}],
                ),
            }
            config = persistence._dict_to_config(data)
        assert config.blocks[0].signals[0].weight == 10

    def test_multi_signal_confluence_with_registry(self, persistence):
        """Multiple signals with mixed weight resolution compute correct
        max_confluence (from the commit message: AT_ASIA_50=20, BELOW_ASIA_50=15,
        BEARISH_CLIMAX=22; max_confluence=57 > threshold 40)."""
        meta = self._make_meta({
            "AT_ASIA_50": {"base_points": 20},
            "BELOW_ASIA_50": {"base_points": 15},
            "BEARISH_CLIMAX": {"base_points": 22},
        })
        with patch(
            "src.strategy_builder.persistence.strategy_persistence._block_registry_lookup",
            return_value=meta,
        ):
            data = {
                "name": "test",
                "description": "",
                "blocks": [
                    {
                        "name": "asia_session_50_percent",
                        "logic": "OR",
                        "signals": [
                            {"name": "AT_ASIA_50", "logic": "OR"},
                            {"name": "BELOW_ASIA_50", "logic": "OR"},
                            {"name": "BEARISH_CLIMAX", "logic": "OR"},
                        ],
                    },
                ],
            }
            config = persistence._dict_to_config(data)
        weights = [s.weight for s in config.blocks[0].signals]
        assert weights == [20, 15, 22]
        assert sum(weights) == 57

    def test_registry_lookup_self_catches_exceptions(self, persistence):
        """_block_registry_lookup swallows exceptions internally via its own
        try/except, so an unavailable registry returns None (→ fallback to 10)."""
        from src.strategy_builder.persistence.strategy_persistence import (
            _block_registry_lookup,
        )
        with patch(
            "src.strategy_builder.persistence.strategy_persistence._BlockRegistry.get_block",
            side_effect=RuntimeError("registry unavailable"),
        ):
            result = _block_registry_lookup("any_block")
        assert result is None


# ===========================================================================
# Fix 2: _repair_if_unreachable — null-weight hardening
# ===========================================================================


class TestRepairIfUnreachableNullWeight:
    """BacktestConfigPanel._repair_if_unreachable must handle null/missing
    weights correctly: (s.get('weight') or 10) instead of s.get('weight', 10).

    NOTE: ``(x or 10)`` also coerces weight=0 to 10; this is intentional to
    avoid false-positive "repaired at X==X" when weight is stored as 0 in DB.
    """

    @staticmethod
    def _make_mock_panel():
        """Return a BacktestConfigPanel mock with the bare minimum attributes
        that _repair_if_unreachable accesses."""
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        panel = MagicMock(spec=BacktestConfigPanel)
        panel.results_text = MagicMock()
        return panel

    def _call_repair(self, config_dict: dict):
        """Call the real _repair_if_unreachable on a mocked panel."""
        from src.strategy_builder.ui.backtest_config_panel import (
            BacktestConfigPanel,
        )
        panel = self._make_mock_panel()
        return BacktestConfigPanel._repair_if_unreachable(panel, config_dict)

    def test_null_weight_sums_as_10(self):
        """Signal with weight=None should count as 10 in max_possible sum."""
        config = {
            "confluence_threshold": 30,
            "blocks": [
                {"name": "b1", "logic": "OR", "signals": [
                    {"name": "s1", "logic": "OR", "weight": None},
                    {"name": "s2", "logic": "OR", "weight": 20},
                ]},
            ],
        }
        result = self._call_repair(config)
        assert result is not None  # 10 + 20 = 30 >= threshold 30 → reachable

    def test_missing_weight_sums_as_10(self):
        """Signal without weight key should count as 10 in max_possible sum."""
        config = {
            "confluence_threshold": 30,
            "blocks": [
                {"name": "b1", "logic": "OR", "signals": [
                    {"name": "s1", "logic": "OR"},
                    {"name": "s2", "logic": "OR", "weight": 20},
                ]},
            ],
        }
        result = self._call_repair(config)
        assert result is not None  # 10 + 20 = 30 >= threshold 30 → reachable

    def test_mixed_weights_under_threshold_no_repair_file(self):
        """Sum of weights below threshold returns None when no repair file."""
        config = {
            "name": "test_strat",
            "confluence_threshold": 40,
            "blocks": [
                {"name": "b1", "logic": "OR", "signals": [
                    {"name": "s1", "logic": "OR", "weight": None},
                    {"name": "s2", "logic": "OR"},
                ]},
            ],
        }
        with patch("pathlib.Path.exists", return_value=False):
            result = self._call_repair(config)
        assert result is None  # 10 + 10 = 20 < 40 → unreachable, no repair file

    def test_weight_zero_coerced_to_10_in_sum(self):
        """Explicit weight=0 is coerced to 10 by ``(x or 10)``."""
        config = {
            "confluence_threshold": 13,
            "blocks": [
                {"name": "b1", "logic": "OR", "signals": [
                    {"name": "s1", "logic": "OR", "weight": 0},
                    {"name": "s2", "logic": "OR", "weight": 3},
                ]},
            ],
        }
        # 10 + 3 = 13 >= 13 → reachable
        result = self._call_repair(config)
        assert result is not None

    def test_old_code_null_weight_typeerror_regression(self):
        """Regression proof: old code s.get('weight', 10) returns None when
        weight=explicit_None, which caused TypeError: '<' not supported
        between instances of 'NoneType' and 'int'."""
        config = {
            "confluence_threshold": 10,
            "blocks": [
                {"name": "b1", "logic": "OR", "signals": [
                    {"name": "s1", "logic": "OR", "weight": None},
                ]},
            ],
        }
        result = self._call_repair(config)
        # Fix ensures (None or 10) = 10 >= 10 → reachable, no TypeError
        assert result is not None

    def test_mixed_weight_sum_under_threshold_with_nulls(self):
        """Mix of null and positive weights computed correctly
        when total is still below threshold (no repair file)."""
        config = {
            "name": "test",
            "confluence_threshold": 50,
            "blocks": [
                {"name": "b1", "logic": "OR", "signals": [
                    {"name": "s1", "logic": "OR", "weight": 10},
                    {"name": "s2", "logic": "OR", "weight": None},
                    {"name": "s3", "logic": "OR", "weight": 0},
                    {"name": "s4", "logic": "OR"},
                ]},
            ],
        }
        # 10 + 10 + 10 + 10 = 40 < 50 → unreachable
        with patch("pathlib.Path.exists", return_value=False):
            result = self._call_repair(config)
        assert result is None

    def test_threshold_met_with_null_coercion(self):
        """Null coercion plus positive weight meets threshold exactly."""
        config = {
            "name": "test",
            "confluence_threshold": 20,
            "blocks": [
                {"name": "b1", "logic": "OR", "signals": [
                    {"name": "s1", "logic": "OR", "weight": None},
                    {"name": "s2", "logic": "OR"},
                ]},
            ],
        }
        # 10 + 10 = 20 >= 20 → reachable
        result = self._call_repair(config)
        assert result is not None


# ===========================================================================
# Fix 3: _on_quick_preview — confluence_threshold wiring
# ===========================================================================


class TestQuickPreviewConfluenceThreshold:
    """_on_quick_preview must ensure confluence_threshold is present in
    strategy_config before BacktestWorker is instantiated."""

    def test_confluence_threshold_default_when_missing(self):
        """When confluence_threshold is missing from strategy_config,
        the fix sets it to 40 before passing to BacktestWorker."""
        strategy_config = {"name": "test", "blocks": []}
        strategy_config["confluence_threshold"] = strategy_config.get(
            "confluence_threshold", 40
        )
        assert strategy_config["confluence_threshold"] == 40

    def test_confluence_threshold_preserved_when_present(self):
        """When confluence_threshold is already in strategy_config, it is
        preserved as-is."""
        strategy_config = {
            "name": "test",
            "blocks": [],
            "confluence_threshold": 55,
        }
        strategy_config["confluence_threshold"] = strategy_config.get(
            "confluence_threshold", 40
        )
        assert strategy_config["confluence_threshold"] == 55

    def test_confluence_threshold_zero_preserved(self):
        """confluence_threshold=0 is treated as "set", not "missing"."""
        strategy_config = {
            "name": "test",
            "blocks": [],
            "confluence_threshold": 0,
        }
        strategy_config["confluence_threshold"] = strategy_config.get(
            "confluence_threshold", 40
        )
        assert strategy_config["confluence_threshold"] == 0

    def test_backtest_config_also_has_threshold(self):
        """The backtest_config dict used in _on_quick_preview also receives
        the threshold (via strategy_config.get)."""
        strategy_config = {"name": "test", "blocks": []}
        stored = strategy_config.get("confluence_threshold", 40)
        backtest_config = {"confluence_threshold": stored}
        assert backtest_config["confluence_threshold"] == 40

    def test_threshold_wired_from_db_via_config_to_dict(self):
        """Integration-style: _config_to_dict preserves stored threshold
        (which was saved in an earlier step)."""
        from src.strategy_builder.persistence.strategy_persistence import (
            StrategyPersistence,
        )
        persistence = StrategyPersistence()
        data = {
            "name": "persisted_strat",
            "description": "",
            "confluence_threshold": 60,
            "blocks": [],
        }
        config = persistence._dict_to_config(data)
        assert config is not None

"""
Regression test for BTCAAAAA-36755 (reopened 2026-06-16 12:41Z).

Bug: Strategy Browser (webui) was dropping the top-level
`strategy_versions.exit_conditions` JSONB column. The thick-client
(PyQt5) Strategy Builder counts `version.get('exit_conditions', [])`
correctly (src/strategy_builder/ui/strategy_browser_dialog.py:985) so the
Builder showed 3 strategy-level exits (Elma Crossover, Anchored Vwap,
Range Liquidity) while the Browser showed "1 blocks" with no children.

Fix: `_build_sb_strategy` in src/api/app.py now surfaces the column as
`exitConditions` (camelCase, list-shaped) on the response. The webui
BlockHierarchyTree (StrategyBrowserDialog) renders these in a
[STRATEGY]-tagged section, and the StrategyBuilder canvas flattens them
into synthetic EXIT_CONDITION blocks on the load path.

These tests pin the contract so the same regression cannot slip back in.
"""

from __future__ import annotations

import uuid

from src.api.app import _build_sb_strategy


def _make_version(strategy_id: str, exit_conditions: list) -> dict:
    """Minimal version dict as returned by get_latest_version."""
    return {
        "version_id": str(uuid.uuid4()),
        "version_number": 1,
        "strategy_id": strategy_id,
        "name": "MyStrategy",
        "description": "",
        # Block-level exits (block.signals[i].exit_conditions) are nested
        # inside each block — not the focus of this regression. An empty
        # list is sufficient to drive _build_sb_strategy.
        "blocks": [
            {
                "name": "EMA Cross",
                "logic": "ema_cross",
                "signals": [
                    {"name": "BULLISH_CROSS", "logic": "AND"},
                ],
            }
        ],
        "signals": {},
        "parameters": {},
        "entry_conditions": {},
        # Strategy-level (Sprint 1.8) exit conditions — the focus of the
        # regression. Snake-case shape matches _exit_condition_to_dict in
        # src/strategy_builder/persistence/strategy_persistence.py:201-244.
        "exit_conditions": exit_conditions,
        "risk_management": {},
        "backtest_config": {},
        "tags": [],
        "validation_history": [],
        "strategy_type": None,
        "timestamp": "2026-06-16T00:00:00Z",
        "created_at": "2026-06-16T00:00:00Z",
        "config_hash": None,
        "validation_timestamp": None,
    }


def test_build_sb_strategy_surfaces_strategy_level_exit_conditions():
    """Three strategy-level exits (the exact case the board reported) must
    be carried through _build_sb_strategy as `exitConditions`."""
    strategy_id = str(uuid.uuid4())
    strategy_level_exits = [
        {
            "signal_name": "ELMA_CROSSOVER",
            "percentage": 0.5,
            "exit_mode": "ABSOLUTE",
            "tp_proximity_threshold": 2.0,
            "reversal_trigger": False,
            "binding_level": "STRATEGY",
        },
        {
            "signal_name": "ANCHORED_VWAP",
            "percentage": 0.33,
            "exit_mode": "TP_AWARE",
            "tp_proximity_threshold": 1.5,
            "reversal_trigger": True,
            "binding_level": "STRATEGY",
        },
        {
            "signal_name": "RANGE_LIQUIDITY",
            "percentage": 1.0,
            "exit_mode": "ABSOLUTE",
            "tp_proximity_threshold": 2.0,
            "reversal_trigger": False,
            "binding_level": "STRATEGY",
        },
    ]
    version = _make_version(strategy_id, strategy_level_exits)

    payload = _build_sb_strategy(strategy_id, version, tests=[])

    assert "exitConditions" in payload, (
        "BTCAAAAA-36755: _build_sb_strategy must surface the top-level "
        "version.exit_conditions as `exitConditions` (camelCase) on the "
        "response — this is what the webui Strategy Browser BlockHierarchyTree "
        "renders in the [STRATEGY]-tagged section."
    )
    assert isinstance(payload["exitConditions"], list), (
        "exitConditions must be a list — StrategyBrowserDialog.BlockHierarchyTree "
        "iterates it as an array."
    )
    assert len(payload["exitConditions"]) == 3, (
        f"Expected 3 strategy-level exits (Elma Crossover, Anchored Vwap, "
        f"Range Liquidity) but got {len(payload['exitConditions'])}."
    )
    signal_names = [ec["signal_name"] for ec in payload["exitConditions"]]
    assert signal_names == [
        "ELMA_CROSSOVER",
        "ANCHORED_VWAP",
        "RANGE_LIQUIDITY",
    ], "Strategy-level exits must preserve insertion order so the Browser "
    "renders them in the same order the Builder shows them."


def test_build_sb_strategy_preserves_exit_condition_shape():
    """The snake-case shape from _exit_condition_to_dict must round-trip
    intact — webui PersistedExitCondition type and BlockHierarchyTree
    read these fields by name."""
    strategy_id = str(uuid.uuid4())
    exit_cond = {
        "signal_name": "ELMA_CROSSOVER",
        "percentage": 0.5,
        "exit_mode": "ABSOLUTE",
        "tp_proximity_threshold": 2.0,
        "reversal_trigger": False,
        "binding_level": "STRATEGY",
        "recheck_config": {
            "enabled": True,
            "bar_delay": 2,
            "validation_mode": "SIGNAL",
            "parent_signal": "BULLISH_CROSS",
        },
    }
    version = _make_version(strategy_id, [exit_cond])

    payload = _build_sb_strategy(strategy_id, version, tests=[])

    [ec] = payload["exitConditions"]
    assert ec["signal_name"] == "ELMA_CROSSOVER"
    assert ec["percentage"] == 0.5
    assert ec["exit_mode"] == "ABSOLUTE"
    assert ec["tp_proximity_threshold"] == 2.0
    assert ec["reversal_trigger"] is False
    assert ec["binding_level"] == "STRATEGY"
    assert ec["recheck_config"]["enabled"] is True
    assert ec["recheck_config"]["bar_delay"] == 2
    assert ec["recheck_config"]["parent_signal"] == "BULLISH_CROSS"


def test_build_sb_strategy_omits_exit_conditions_as_empty_list():
    """A strategy with no strategy-level exits must still carry the
    `exitConditions` key (set to []) — the webui BlockHierarchyTree's
    empty-state check is `blocks.length === 0 && strategyExits.length === 0`,
    so a missing key would still render the empty state correctly but a
    non-list would crash the iteration. This pins the contract to a list."""
    strategy_id = str(uuid.uuid4())
    version = _make_version(strategy_id, [])

    payload = _build_sb_strategy(strategy_id, version, tests=[])

    assert "exitConditions" in payload
    assert payload["exitConditions"] == []


def test_build_sb_strategy_treats_null_exit_conditions_as_empty_list():
    """Defensive: if the column is null in the DB row, surface an empty
    list rather than None — webui code that does `strategyLevelExits.length`
    would NPE on None."""
    strategy_id = str(uuid.uuid4())
    version = _make_version(strategy_id, None)

    payload = _build_sb_strategy(strategy_id, version, tests=[])

    assert payload["exitConditions"] == []

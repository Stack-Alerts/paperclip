#!/usr/bin/env python3
"""Seed a test strategy that deliberately trips validation rules.

The strategy is designed so the web UI's validation panel surfaces a
realistic mix of issue severities — including auto-fixable rules
(EXIT_009 conflicting modes, TIMING_004 RECHECK > window, STRUCTURAL_005
duplicate signal name) — so the board can exercise the fix logic.

Idempotent: if a strategy with the same name already exists, the script
appends a new version row to it rather than creating a duplicate.

Usage:
    python scripts/seed_validation_test_strategy.py
"""

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv
load_dotenv()

from src.optimizer_v3.database import get_database_manager


TEST_STRATEGY_NAME = "Validation Test - Has Failures"

# Block payload uses the same raw API shape Bart Test 2 uses.
# Deliberate issues:
#   STRUCTURAL_005: duplicate signal name within a block ("AT_ASIA_50" x2)
#   EXIT_009:       same exit signal_name "STOP_LOSS" with conflicting modes
#                   (ABSOLUTE on one signal, FLEXIBLE on another)
#   TIMING_004:     RECHECK bar_delay (10) > timing_constraint.max_candles (5)
TEST_STRATEGY_BLOCKS = [
    {
        "name": "asia_session_50_percent",
        "logic": "AND",
        "signals": [
            {
                "name": "AT_ASIA_50",
                "logic": "AND",
                "weight": 20,
                "exit_conditions": [
                    {
                        "signal_name": "STOP_LOSS",
                        "exit_mode": "ABSOLUTE",
                        "percentage": 1.0,
                        "binding_level": "SIGNAL",
                    }
                ],
            },
            {
                # Duplicate signal name within the same block — trips STRUCTURAL_005.
                "name": "AT_ASIA_50",
                "logic": "AND",
                "weight": 20,
                "exit_conditions": [
                    {
                        # Same exit signal name "STOP_LOSS" but FLEXIBLE this
                        # time — trips EXIT_009 (auto-fixable: consolidate).
                        "signal_name": "STOP_LOSS",
                        "exit_mode": "FLEXIBLE",
                        "percentage": 1.0,
                        "binding_level": "SIGNAL",
                    }
                ],
            },
        ],
        "indented": False,
        "metadata": None,
        "parameters": {},
    },
    {
        "name": "ema_55_vector",
        "logic": "AND",
        "signals": [
            {
                "name": "BEARISH_CLIMAX",
                "logic": "AND",
                "weight": 22,
                # RECHECK bar_delay 10 > timing_constraint.max_candles 5 →
                # signal can never trigger. Trips TIMING_004 (auto-fixable:
                # reduce recheck delay).
                "timing_constraint": {
                    "reference": "asia_session_50_percent::AT_ASIA_50",
                    "max_candles": 5,
                },
                "recheck_config": {
                    "enabled": True,
                    "bar_delay": 10,
                    "parent_signal": None,
                    "validation_mode": "SIGNAL",
                },
            }
        ],
        "indented": False,
        "metadata": None,
        "parameters": {},
    },
]


def main() -> int:
    print("=" * 72)
    print("  SEED: Validation Test - Has Failures")
    print("=" * 72)

    db = get_database_manager()

    with db.scoped_managers() as scoped:
        existing = scoped.strategy.get_all_strategies()
        match = next(
            (s for s in existing if s.get("name") == TEST_STRATEGY_NAME),
            None,
        )
        if match is not None:
            strategy_id = match["strategy_id"]
            print(f"  Reusing existing strategy {strategy_id}")
        else:
            strategy_id = scoped.strategy.create_strategy(TEST_STRATEGY_NAME)
            print(f"  Created strategy {strategy_id}")

        version_data = {
            "strategy_id": strategy_id,
            "name": TEST_STRATEGY_NAME,
            "description": (
                "Seeded validation test strategy. Intentionally trips "
                "STRUCTURAL_005 (duplicate signal name), EXIT_009 (conflicting "
                "exit modes for STOP_LOSS) and TIMING_004 (RECHECK delay 10 > "
                "timing window 5) so the web-UI validation panel and fix "
                "buttons can be exercised end-to-end."
            ),
            "strategy_type": "Bearish",
            "blocks": TEST_STRATEGY_BLOCKS,
            "signals": {},
            "parameters": {},
            "entry_conditions": {},
            "exit_conditions": {},
            "risk_management": {},
            "backtest_config": {},
            "tags": ["validation-test", "seed"],
        }
        version_id = scoped.strategy.create_strategy_version(version_data)
        print(f"  Created version {version_id}")

    print()
    print("Done. Open the web UI Strategy Browser and load")
    print(f"  \"{TEST_STRATEGY_NAME}\"")
    print("then click Validate to see the issues.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

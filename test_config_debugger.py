#!/usr/bin/env python
"""Test ConfigDebugger to verify it writes to log files"""

from src.debugger_logger.config_debugger import ConfigDebugger
from pathlib import Path

# Enable file logging
ConfigDebugger.LOGFILE_ENABLED = True

# Create debugger
debugger = ConfigDebugger(
    name="TEST_AI_Recommendations",
    log_file=Path("logs/test_ai_recommendations.log")
)

# Log test action 1
debugger.log_action(
    action="TEST_BACKTEST_COMPLETE",
    config_keys_used=[],
    parameters={
        'total_candles': 14040,
        'total_trades': 24,
        'tp_adjustments': {'TP1': 12}
    }
)

# Log test action 2
debugger.log_action(
    action="TEST_TRADES_RETRIEVED",
    config_keys_used=[],
    parameters={
        'trade_count': 24,
        'first_trade_id': '1',
        'has_trades': True
    }
)

print("✅ ConfigDebugger test completed!")
print(f"📁 Check log file: logs/test_ai_recommendations.log")

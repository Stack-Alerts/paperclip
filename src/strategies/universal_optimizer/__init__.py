"""
Universal Strategy Optimizer V2.0 - Modular Architecture

Institutional-grade strategy optimization framework with:
- 48x performance improvement (simultaneous config testing)
- Auto-configuration application
- Iteration tracking and block intelligence
- Multicore execution

Author: Cline AI
Date: 2026-01-09
Version: 2.0.0
"""

from .modules.optimizer_core import optimize_strategy_v2
from .modules.data_classes import OptimizationConfig, TradeResult, ConfigPerformance
from .modules.multi_config_simulator import MultiConfigSimulator

__all__ = [
    'optimize_strategy_v2',
    'OptimizationConfig',
    'TradeResult',
    'ConfigPerformance',
    'MultiConfigSimulator'
]

__version__ = '2.0.0'
"""
BTC Engine v3 - Data Manager Package
Institutional-Grade Data Management System

Modules:
- download: Data download and synchronization
- aggregation: Tick-to-bar aggregation
- validation: 3-level data validation
- nautilus: NautilusTrader integration
- monitoring: Data freshness and usage monitoring
- utils: Shared utilities
"""

__version__ = "1.0.0"
__author__ = "BTC Engine v3 Team"

from . import config
from . import utils

__all__ = ['config', 'utils']
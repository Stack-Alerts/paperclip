"""
Strategy Builder Package

Provides tools for building, testing, and managing trading strategies.

Author: BTC_Engine_v3
Date: 2026-01-09
Version: 1.0
"""

from src.utils.Strategy_Builder.models import (
    StrategyConfiguration,
    BlockSelection,
    SignalConfiguration,
    ValidationResult,
    BlockInfo,
    SignalInfo,
    StrategyMetadata,
    QuickTestResult,
    StrategyCategory,
    SignalRole,
    BlockType,
    TestType
)

from src.utils.Strategy_Builder.registry_bridge import RegistryBridge
from src.utils.Strategy_Builder.validator import StrategyValidator
from src.utils.Strategy_Builder.strategy_registry import StrategyRegistry
from src.utils.Strategy_Builder.generator import StrategyGenerator

__all__ = [
    # Models
    'StrategyConfiguration',
    'BlockSelection',
    'SignalConfiguration',
    'ValidationResult',
    'BlockInfo',
    'SignalInfo',
    'StrategyMetadata',
    'QuickTestResult',
    
    # Enums
    'StrategyCategory',
    'SignalRole',
    'BlockType',
    'TestType',
    
    # Core Components
    'RegistryBridge',
    'StrategyValidator',
    'StrategyRegistry',
    'StrategyGenerator',
]

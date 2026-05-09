"""
Strategy Validator - Institutional-Grade Validation

Validates strategy configurations to ensure they are:
- Logically correct
- Have valid block+signal combinations
- Meet weight requirements
- Have proper main signal configuration

Author: BTC_Engine_v3
Date: 2026-01-09
Status: Phase 1 - Foundation
"""

from typing import List, Set
import logging

from src.utils.Strategy_Builder.models import (
    StrategyConfiguration,
    ValidationResult,
    BlockSelection,
    SignalConfiguration,
    SignalRole
)
from src.utils.Strategy_Builder.registry_bridge import RegistryBridge

import logging
logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)


class StrategyValidator:
    """
    Validates strategy configurations for correctness
    
    Validation Layers:
    1. Block existence (are blocks registered?)
    2. Signal validity (do signals exist for blocks?)
    3. Weight constraints (within ranges? total reasonable?)
    4. Main signal logic (is main signal properly configured?)
    5. Role distribution (balanced filters/signals/boosters?)
    6. Conflict detection (incompatible blocks?)
    
    Usage:
        validator = StrategyValidator()
        result = validator.validate(strategy_config)
        
        if result.is_valid:
            logger.info("Strategy is valid!")
        else:
            for error in result.errors:
                logger.error(f"Error: {error}")
    """
    
    def __init__(self):
        """Initialize validator with registry bridge"""
        self.bridge = RegistryBridge()
        self.min_total_weight = 50
        self.max_total_weight = 200
        self.min_blocks = 1
        self.max_blocks = 10
        logger.info("StrategyValidator initialized")
    
    def validate(self, config: StrategyConfiguration) -> ValidationResult:
        """
        Perform complete validation of strategy configuration
        
        Args:
            config: Strategy configuration to validate
            
        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        result = ValidationResult()
        
        logger.info(f"Validating strategy: {config.strategy_name}")
        
        # Layer 1: Basic structure validation
        self._validate_basic_structure(config, result)
        
        # Layer 2: Block existence and validity
        self._validate_blocks_exist(config, result)
        
        # Layer 3: Signal validity
        self._validate_signals(config, result)
        
        # Layer 4: Weight constraints
        self._validate_weights(config, result)
        
        # Layer 5: Main signal configuration
        self._validate_main_signal(config, result)
        
        # Layer 6: Role distribution
        self._validate_role_distribution(config, result)
        
        # Layer 7: Conflict detection
        self._validate_conflicts(config, result)
        
        # Layer 8: Strategy-specific validation
        self._validate_strategy_specific(config, result)
        
        if result.is_valid:
            logger.info(f"Strategy {config.strategy_name} passed validation")
        else:
            logger.warning(
                f"Strategy {config.strategy_name} failed validation: "
                f"{len(result.errors)} error(s)"
            )
        
        return result
    
    def _validate_basic_structure(
        self, 
        config: StrategyConfiguration,
        result: ValidationResult
    ):
        """Validate basic structure requirements"""
        
        # Check block count
        block_count = len(config.blocks)
        
        if block_count < self.min_blocks:
            result.add_error(
                f"Strategy must have at least {self.min_blocks} block(s), "
                f"has {block_count}"
            )
        
        if block_count > self.max_blocks:
            result.add_error(
                f"Strategy has too many blocks ({block_count}), "
                f"maximum is {self.max_blocks}"
            )
            result.add_suggestion(
                "Consider splitting into multiple strategies or "
                "removing less important blocks"
            )
        
        # Check strategy name format
        if not config.strategy_name.startswith(f"strategy_{config.strategy_number:02d}_"):
            result.add_warning(
                f"Strategy name '{config.strategy_name}' doesn't follow convention. "
                f"Expected to start with 'strategy_{config.strategy_number:02d}_'"
            )
    
    def _validate_blocks_exist(
        self,
        config: StrategyConfiguration,
        result: ValidationResult
    ):
        """Validate all blocks exist in registry"""
        
        for block in config.blocks:
            # Check if block exists
            block_metadata = self.bridge.get_block_metadata(block.block_name)
            
            if not block_metadata:
                result.add_error(
                    f"Block '{block.block_name}' not found in registry"
                )
                result.add_suggestion(
                    f"Check available blocks with: "
                    f"RegistryBridge.get_blocks_by_category()"
                )
    
    def _validate_signals(
        self,
        config: StrategyConfiguration,
        result: ValidationResult
    ):
        """Validate all signals are valid for their blocks"""
        
        for block in config.blocks:
            # Skip if block doesn't exist (already reported)
            block_metadata = self.bridge.get_block_metadata(block.block_name)
            if not block_metadata:
                continue
            
            # Validate each signal configuration
            for signal_config in block.signals:
                validation = self.bridge.validate_block_signal(
                    block.block_name,
                    signal_config.signal_name
                )
                
                if not validation.is_valid:
                    result.add_error(
                        f"Invalid signal '{signal_config.signal_name}' "
                        f"for block '{block.block_name}'"
                    )
                    # Add suggestions from bridge
                    for suggestion in validation.suggestions:
                        result.add_suggestion(suggestion)
    
    def _validate_weights(
        self,
        config: StrategyConfiguration,
        result: ValidationResult
    ):
        """Validate weight constraints"""
        
        total_weight = 0
        
        for block in config.blocks:
            # Check individual weight in range
            min_w, max_w = block.weight_range
            
            if not (min_w <= block.weight <= max_w):
                result.add_error(
                    f"Block '{block.block_name}' weight {block.weight} "
                    f"not in range ({min_w}, {max_w})"
                )
            
            total_weight += block.weight
        
        # Check total weight
        if total_weight < self.min_total_weight:
            result.add_warning(
                f"Total weight ({total_weight}) is low. "
                f"Recommended minimum: {self.min_total_weight}"
            )
            result.add_suggestion(
                "Consider increasing block weights or adding more blocks"
            )
        
        if total_weight > self.max_total_weight:
            result.add_warning(
                f"Total weight ({total_weight}) is high. "
                f"Recommended maximum: {self.max_total_weight}"
            )
            result.add_suggestion(
                "Consider reducing block weights or removing less important blocks"
            )
    
    def _validate_main_signal(
        self,
        config: StrategyConfiguration,
        result: ValidationResult
    ):
        """Validate main signal block configuration"""
        
        # Check main signal block exists in blocks list
        main_block = None
        for block in config.blocks:
            if block.block_name == config.main_signal_block:
                main_block = block
                break
        
        if not main_block:
            result.add_error(
                f"Main signal block '{config.main_signal_block}' "
                f"not found in blocks list"
            )
            return
        
        # Check main signal block is marked
        if not main_block.is_main_signal:
            result.add_warning(
                f"Main signal block '{config.main_signal_block}' "
                f"not marked as main signal"
            )
        
        # Check main signal block has reasonable weight
        if main_block.weight < 20:
            result.add_warning(
                f"Main signal block '{config.main_signal_block}' "
                f"has low weight ({main_block.weight}). "
                f"Recommended minimum: 20"
            )
    
    def _validate_role_distribution(
        self,
        config: StrategyConfiguration,
        result: ValidationResult
    ):
        """Validate signal role distribution"""
        
        role_counts = {
            SignalRole.FILTER: 0,
            SignalRole.SIGNAL: 0,
            SignalRole.BOOSTER: 0,
            SignalRole.TEST_ALL: 0
        }
        
        for block in config.blocks:
            for signal_config in block.signals:
                role_counts[signal_config.role] += 1
        
        # Check for at least one signal
        if role_counts[SignalRole.SIGNAL] == 0:
            result.add_error(
                "Strategy must have at least one SIGNAL role"
            )
            result.add_suggestion(
                "Add a signal with role=SignalRole.SIGNAL"
            )
        
        # Warn about imbalance
        total_signals = sum(role_counts.values())
        if total_signals > 0:
            signal_pct = (role_counts[SignalRole.SIGNAL] / total_signals) * 100
            
            if signal_pct < 30:
                result.add_warning(
                    f"Only {signal_pct:.1f}% of signals are SIGNAL role. "
                    f"Strategy may have weak entry triggers."
                )
    
    def _validate_conflicts(
        self,
        config: StrategyConfiguration,
        result: ValidationResult
    ):
        """Detect conflicting block combinations"""
        
        block_categories = {}
        
        # Group blocks by category
        for block in config.blocks:
            block_metadata = self.bridge.get_block_metadata(block.block_name)
            if not block_metadata:
                continue
            
            category = block_metadata['category']
            if category not in block_categories:
                block_categories[category] = []
            block_categories[category].append(block.block_name)
        
        # Check for potentially conflicting patterns
        if 'PATTERNS' in block_categories:
            patterns = block_categories['PATTERNS']
            
            # Check for opposite patterns (bullish vs bearish)
            bullish_patterns = [p for p in patterns if 'bullish' in p.lower() or 'ascending' in p.lower()]
            bearish_patterns = [p for p in patterns if 'bearish' in p.lower() or 'descending' in p.lower()]
            
            if bullish_patterns and bearish_patterns:
                result.add_warning(
                    f"Strategy has both bullish ({bullish_patterns}) "
                    f"and bearish ({bearish_patterns}) patterns. "
                    f"This may create conflicting signals."
                )
                result.add_suggestion(
                    "Consider focusing on one direction or using filters "
                    "to separate conditions"
                )
    
    def _validate_strategy_specific(
        self,
        config: StrategyConfiguration,
        result: ValidationResult
    ):
        """Validate strategy-specific requirements based on category"""
        
        # Reversal strategies should have reversal indicators
        if config.strategy_category == 'REVERSAL':
            has_reversal_block = False
            
            for block in config.blocks:
                block_metadata = self.bridge.get_block_metadata(block.block_name)
                if not block_metadata:
                    continue
                
                # Check if block name suggests reversal
                if any(keyword in block.block_name.lower() 
                       for keyword in ['reversal', 'double', 'head', 'shoulders']):
                    has_reversal_block = True
                    break
            
            if not has_reversal_block:
                result.add_warning(
                    "REVERSAL strategy has no obvious reversal indicators"
                )
                result.add_suggestion(
                    "Consider adding reversal patterns like Double Top, "
                    "Head & Shoulders, etc."
                )
        
        # Continuation strategies should have trend filters
        elif config.strategy_category == 'CONTINUATION':
            has_trend_filter = False
            
            for block in config.blocks:
                if any(keyword in block.block_name.lower()
                       for keyword in ['ema', 'sma', 'trend', 'ma']):
                    has_trend_filter = True
                    break
            
            if not has_trend_filter:
                result.add_warning(
                    "CONTINUATION strategy has no trend filters"
                )
                result.add_suggestion(
                    "Consider adding EMA/SMA filters to confirm trend"
                )
    
    def quick_validate(self, config: StrategyConfiguration) -> bool:
        """
        Quick validation - returns True/False without detailed results
        
        Useful for fast checks before full validation
        
        Args:
            config: Strategy configuration
            
        Returns:
            True if valid, False otherwise
        """
        result = self.validate(config)
        return result.is_valid
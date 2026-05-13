"""
Registry Bridge - Clean Interface to BlockRegistry

Provides UI-friendly access to the BlockRegistry without exposing
internal implementation details.

Author: BTC_Engine_v3
Date: 2026-01-09
Status: Phase 1 - Foundation
"""

from typing import Dict, List, Optional, Tuple
from functools import lru_cache
import logging

from src.detectors.building_blocks.registry import BlockRegistry
from src.utils.Strategy_Builder.models import (
    BlockInfo,
    SignalInfo,
    ValidationResult,
    BlockType
)

import logging
logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)


class RegistryBridge:
    """
    Clean interface to BlockRegistry for Strategy Builder
    
    Purpose:
    - Query blocks by category
    - Get signal options for blocks
    - Validate block+signal combinations
    - Provide metadata for UI display
    - Cache results for performance
    
    Usage:
        bridge = RegistryBridge()
        blocks = bridge.get_blocks_by_category()
        signals = bridge.get_signal_options('double_top')
    """
    
    def __init__(self):
        """Initialize registry bridge"""
        self.registry = BlockRegistry
        self._cache_enabled = True
        logger.info("RegistryBridge initialized")
    
    @classmethod
    @lru_cache(maxsize=1)
    def get_blocks_by_category(cls) -> Dict[str, List[BlockInfo]]:
        """
        Get all blocks organized by category
        
        Returns:
            Dict mapping category names to lists of BlockInfo objects
            
        Example:
            {
                'PATTERNS': [
                    BlockInfo(name='double_top', display_name='Double Top', ...),
                    BlockInfo(name='head_shoulders', display_name='Head & Shoulders', ...),
                ],
                'PRICE_LEVELS': [...],
                ...
            }
        """
        logger.info("Fetching blocks by category from registry")
        
        result = {}
        registry = BlockRegistry
        
        # Get all registered blocks
        all_blocks = registry.get_all_blocks()
        
        if not all_blocks:
            logger.warning("No blocks found in registry!")
            return result
        
        # Organize by category
        for block_name, block_metadata in all_blocks.items():
            try:
                category = block_metadata.category.upper()
                
                # Get signal tiers
                signal_tiers = block_metadata.signal_tiers
                signal_names = list(signal_tiers.keys()) if signal_tiers else []
                
                # Get weight range from default weight (use +/- 10 range)
                default_weight = block_metadata.default_weight
                weight_range = (max(5, default_weight - 10), min(100, default_weight + 10))
                
                # Determine block type (default to EVENT if not specified)
                block_type = BlockType.EVENT
                
                # Create BlockInfo
                block_info = BlockInfo(
                    name=block_name,
                    display_name=block_name.replace('_', ' ').title(),
                    category=category,
                    block_type=block_type,
                    weight_range=weight_range,
                    default_weight=default_weight,
                    signals=signal_names,
                    description=block_metadata.description
                )
                
                # Add to category
                if category not in result:
                    result[category] = []
                result[category].append(block_info)
                
            except Exception as e:
                logger.error(f"Error processing block {block_name}: {e}")
                continue
        
        # Sort blocks within each category
        for category in result:
            result[category].sort(key=lambda x: x.display_name)
        
        logger.info(f"Found {len(all_blocks)} blocks across {len(result)} categories")
        return result
    
    @classmethod
    def get_signal_options(cls, block_name: str) -> List[SignalInfo]:
        """
        Get available signals for a specific block
        
        Args:
            block_name: Name of the block (e.g., 'double_top')
            
        Returns:
            List of SignalInfo objects with signal details
            
        Example:
            signals = bridge.get_signal_options('double_top')
            # Returns:
            # [
            #     SignalInfo(name='BEARISH_BREAKDOWN', display_name='Bearish Breakdown', ...),
            #     SignalInfo(name='PATTERN_FORMING', display_name='Pattern Forming', ...),
            # ]
        """
        logger.debug(f"Fetching signal options for block: {block_name}")
        
        registry = BlockRegistry
        block_metadata = registry.get_block(block_name)
        
        if not block_metadata:
            logger.warning(f"Block not found: {block_name}")
            return []
        
        signal_tiers = block_metadata.signal_tiers
        
        if not signal_tiers:
            logger.warning(f"No signals found for block: {block_name}")
            return []
        
        result = []
        for signal_name, tier_config in signal_tiers.items():
            try:
                # Extract tier details
                tier_type = tier_config.get('type', 'fixed')
                max_points = 0
                
                if tier_type == 'fixed':
                    max_points = tier_config.get('points', 0)
                elif tier_type == 'scaled':
                    max_points = tier_config.get('max', 0)
                elif tier_type == 'quality_thresholds':
                    thresholds = tier_config.get('thresholds', {})
                    if thresholds:
                        max_points = max(thresholds.values())
                
                signal_info = SignalInfo(
                    name=signal_name,
                    display_name=signal_name.replace('_', ' ').title(),
                    description=tier_config.get('description', ''),
                    tier_type=tier_type,
                    max_points=max_points
                )
                result.append(signal_info)
                
            except Exception as e:
                logger.error(f"Error processing signal {signal_name} for {block_name}: {e}")
                continue
        
        # Sort by name
        result.sort(key=lambda x: x.name)
        
        logger.debug(f"Found {len(result)} signals for {block_name}")
        return result
    
    @classmethod
    def validate_block_signal(cls, block_name: str, signal: str) -> ValidationResult:
        """
        Validate if a signal exists for a specific block
        
        Args:
            block_name: Name of the block
            signal: Name of the signal
            
        Returns:
            ValidationResult with errors if invalid
            
        Example:
            result = bridge.validate_block_signal('double_top', 'BEARISH_BREAKDOWN')
            if result.is_valid:
                logger.info("Valid combination!")
        """
        result = ValidationResult()
        
        # Check if block exists
        registry = BlockRegistry
        block_metadata = registry.get_block(block_name)
        
        if not block_metadata:
            result.add_error(f"Block '{block_name}' not found in registry")
            result.add_suggestion("Check available blocks with get_blocks_by_category()")
            return result
        
        # Use BlockRegistry's validate_signal method
        is_valid = registry.validate_signal(block_name, signal)
        
        if not is_valid:
            result.add_error(f"Signal '{signal}' not valid for block '{block_name}'")
            # Get available signals to suggest
            available = block_metadata.valid_signals
            result.add_suggestion(f"Available signals: {', '.join(available[:5])}")
            return result
        
        logger.debug(f"Validated: {block_name} + {signal} = OK")
        return result
    
    @classmethod
    def get_block_metadata(cls, block_name: str) -> Optional[Dict]:
        """
        Get metadata for a specific block
        
        Args:
            block_name: Name of the block
            
        Returns:
            Dictionary of metadata or None if block not found
        """
        registry = BlockRegistry
        block_metadata = registry.get_block(block_name)
        
        if not block_metadata:
            logger.warning(f"Block not found: {block_name}")
            return None
        
        # Convert BlockMetadata to dict
        return {
            'name': block_metadata.name,
            'category': block_metadata.category,
            'class_name': block_metadata.class_name,
            'module_path': block_metadata.module_path,
            'default_weight': block_metadata.default_weight,
            'valid_signals': block_metadata.valid_signals,
            'signal_tiers': block_metadata.signal_tiers,
            'description': block_metadata.description,
            'tags': block_metadata.tags
        }
    
    @classmethod
    def get_block_count(cls) -> int:
        """
        Get total number of registered blocks
        
        Returns:
            Count of blocks in registry
        """
        registry = BlockRegistry
        all_blocks = registry.get_all_blocks()
        return len(all_blocks) if all_blocks else 0
    
    @classmethod
    def get_category_count(cls) -> int:
        """
        Get number of categories
        
        Returns:
            Count of unique categories
        """
        blocks_by_category = cls.get_blocks_by_category()
        return len(blocks_by_category)
    
    @classmethod
    def search_blocks(cls, query: str) -> List[BlockInfo]:
        """
        Search for blocks by name or display name
        
        Args:
            query: Search string (case-insensitive)
            
        Returns:
            List of matching BlockInfo objects
            
        Example:
            results = bridge.search_blocks('double')
            # Returns blocks with 'double' in name
        """
        query_lower = query.lower()
        all_blocks = cls.get_blocks_by_category()
        
        results = []
        for category, blocks in all_blocks.items():
            for block in blocks:
                if (query_lower in block.name.lower() or 
                    query_lower in block.display_name.lower()):
                    results.append(block)
        
        return results
    
    @classmethod
    def clear_cache(cls):
        """Clear the LRU cache"""
        cls.get_blocks_by_category.cache_clear()
        logger.info("Registry bridge cache cleared")        

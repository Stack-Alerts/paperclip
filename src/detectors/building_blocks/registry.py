"""
Building Block Registry - Single Source of Truth
=================================================

This module implements the Building Block Registry Pattern, which solves
the systematic signal mismatch problem by providing a centralized registry
where all building blocks self-register with their metadata.

Key Benefits:
- No more signal name mismatches
- Add blocks in ONE place (the detector file)
- Automatic validation at import time
- ConfluenceCalculator auto-adapts
- Dual signal architecture (granular + simple)
- Scalable to 1000+ blocks

DUAL SIGNAL ARCHITECTURE (2026-01-15):
All building blocks must emit TWO signals:
- signal (granular): Detailed pattern/event specific signal
- signal_simple (simple): BULLISH/BEARISH/NEUTRAL directional signal

This enables both pattern-specific logic AND simple directional strategies.

Author: BTC_Engine_v3
Date: 2026-01-09
Version: 1.1 (Updated 2026-01-15 - Dual Signal Architecture)
"""

from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass
import importlib
import inspect
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

@dataclass
class BlockMetadata:
    """Metadata for a registered building block"""
    name: str
    category: str
    class_name: str
    module_path: str
    default_weight: int
    valid_signals: List[str]
    signal_tiers: Dict[str, Any]
    description: str = ""
    direction: str = "NEUTRAL"  # BULLISH, BEARISH, or NEUTRAL
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class BlockRegistry:
    """
    Central registry for all building blocks
    
    This registry auto-discovers blocks, validates their metadata,
    and provides a query interface for strategies, ConfluenceCalculator,
    and other tools.
    
    DUAL SIGNAL ARCHITECTURE EXAMPLE:
    =================================
    
    @register_block(
        name='double_top',
        category='PATTERNS',
        class_name='DoubleTopPattern',
        default_weight=30,
        valid_signals=[
            # Granular pattern signals
            'BEARISH_BREAKDOWN', 'PATTERN_FORMING', 'NO_PATTERN',
            # Simple directional signals
            'BULLISH', 'BEARISH', 'NEUTRAL',
            # Status signals
            'ERROR', 'INSUFFICIENT_DATA'
        ],
        signal_tiers={
            'BEARISH_BREAKDOWN': {'base_points': 30, 'formula': 'scaled'},
            'PATTERN_FORMING': {'base_points': 15, 'formula': 'scaled'},
            'NO_PATTERN': {'points': 0},
            'BULLISH': {'base_points': 30, 'formula': 'scaled'},
            'BEARISH': {'base_points': 30, 'formula': 'scaled'},
            'NEUTRAL': {'points': 0},
            'ERROR': {'points': 0},
            'INSUFFICIENT_DATA': {'points': 0}
        }
    )
    class DoubleTopPattern:
        def _determine_dual_signals(self, granular_signal: str) -> tuple:
            \"\"\"Map granular signals to simple directional signals\"\"\"
            if granular_signal == 'BEARISH_BREAKDOWN':
                return 'BEARISH_BREAKDOWN', 'BEARISH'
            elif granular_signal == 'PATTERN_FORMING':
                return 'PATTERN_FORMING', 'BEARISH'  # Bearish pattern
            else:
                return granular_signal, 'NEUTRAL'
        
        def analyze(self, df):
            # Detect pattern
            if self.detect_breakdown():
                granular, simple = self._determine_dual_signals('BEARISH_BREAKDOWN')
                return {
                    'signal': granular,           # e.g., 'BEARISH_BREAKDOWN'
                    'signal_simple': simple,      # e.g., 'BEARISH'
                    'confidence': 95,
                    'metadata': {
                        'signal_granular': granular,
                        'signal_simple': simple
                    }
                }
            else:
                granular, simple = self._determine_dual_signals('NO_PATTERN')
                return {
                    'signal': granular,
                    'signal_simple': simple,
                    'confidence': 0,
                    'metadata': {
                        'signal_granular': granular,
                        'signal_simple': simple
                    }
                }
    
    QUERY EXAMPLES:
    ===============
    
    # Get metadata
    metadata = BlockRegistry.get_block('double_top')
    
    # Instantiate block
    detector = BlockRegistry.instantiate('double_top', timeframe='15min')
    
    # Get valid signals
    signals = BlockRegistry.get_valid_signals('double_top')
    
    # Get signal tiers for confluence calculation
    tiers = BlockRegistry.get_block('double_top').signal_tiers
    """
    
    _blocks: Dict[str, BlockMetadata] = {}
    _initialized = False
    
    @classmethod
    def register(cls, metadata: Dict[str, Any]) -> callable:
        """
        Register a building block with metadata
        
        This is called by the @register_block decorator.
        Validates metadata and stores it in the registry.
        
        Args:
            metadata: Block metadata dictionary
            
        Returns:
            Decorator function that returns the class unchanged
            
        Raises:
            ValueError: If metadata is invalid or incomplete
        """
        # Validate required fields
        cls._validate_metadata(metadata)
        
        # Create metadata object
        name = metadata['name']
        block_meta = BlockMetadata(
            name=name,
            category=metadata['category'],
            class_name=metadata['class_name'],
            module_path=metadata.get('module_path', ''),
            default_weight=metadata.get('default_weight', 20),
            valid_signals=metadata['valid_signals'],
            signal_tiers=metadata.get('signal_tiers', {}),
            description=metadata.get('description', ''),
            direction=metadata.get('direction', 'NEUTRAL'),
            tags=metadata.get('tags', [])
        )
        
        # Store in registry
        cls._blocks[name] = block_meta
        
        # NOTE: ConfluenceCalculator now reads directly from registry
        # No need to update SIGNAL_TIERS (removed 2026-01-09)
        
        # Return decorator that doesn't modify the class
        def decorator(block_class):
            # Store class reference in metadata
            block_meta.module_path = f"{block_class.__module__}.{block_class.__name__}"
            return block_class
        
        return decorator
    
    @classmethod
    def _validate_metadata(cls, metadata: Dict[str, Any]):
        """
        Validate block metadata is complete and correct
        
        DUAL SIGNAL VALIDATION (2026-01-15):
        Now enforces that BULLISH, BEARISH, NEUTRAL must be in valid_signals
        for all blocks to support dual signal architecture.
        
        Raises:
            ValueError: If metadata is invalid
        """
        # Required fields
        required = ['name', 'category', 'class_name', 'valid_signals']
        for field in required:
            if field not in metadata:
                raise ValueError(f"Block registration missing required field: {field}")
        
        # DUAL SIGNAL ARCHITECTURE: Validate simple signals are present
        valid_signals = set(metadata['valid_signals'])
        simple_signals = {'BULLISH', 'BEARISH', 'NEUTRAL'}
        missing_simple = simple_signals - valid_signals
        
        if missing_simple:
            raise ValueError(
                f"Block '{metadata['name']}': "
                f"Missing required simple signals: {missing_simple}\n"
                f"All blocks must support dual signal architecture (BULLISH/BEARISH/NEUTRAL)"
            )
        
        # Validate signals are defined in tiers
        if 'signal_tiers' in metadata:
            signals = set(metadata['valid_signals'])
            tiers = set(metadata['signal_tiers'].keys())
            
            # Allow ERROR and INSUFFICIENT_DATA without tier definition
            undefined = signals - tiers - {'ERROR', 'INSUFFICIENT_DATA', 'NO_SIGNAL'}
            if undefined:
                raise ValueError(
                    f"Block '{metadata['name']}': "
                    f"Signals {undefined} declared in valid_signals but not defined in signal_tiers"
                )
    
    @classmethod
    def get_block(cls, name: str) -> Optional[BlockMetadata]:
        """Get metadata for a specific block"""
        return cls._blocks.get(name)
    
    @classmethod
    def get_all_blocks(cls) -> Dict[str, BlockMetadata]:
        """Get all registered blocks"""
        return cls._blocks.copy()
    
    @classmethod
    def get_blocks_by_category(cls, category: str) -> Dict[str, BlockMetadata]:
        """Get all blocks in a specific category"""
        return {
            name: meta
            for name, meta in cls._blocks.items()
            if meta.category == category
        }
    
    @classmethod
    def get_blocks_by_tag(cls, tag: str) -> Dict[str, BlockMetadata]:
        """Get all blocks with a specific tag"""
        return {
            name: meta
            for name, meta in cls._blocks.items()
            if tag in meta.tags
        }
    
    @classmethod
    def get_valid_signals(cls, name: str) -> List[str]:
        """Get list of valid signals for a block"""
        metadata = cls.get_block(name)
        return metadata.valid_signals if metadata else []
    
    @classmethod
    def get_default_weight(cls, name: str) -> int:
        """Get recommended default weight for a block"""
        metadata = cls.get_block(name)
        return metadata.default_weight if metadata else 20
    
    @classmethod
    def instantiate(cls, name: str, **kwargs) -> Any:
        """
        Dynamically instantiate a building block
        
        Args:
            name: Block name (as registered)
            **kwargs: Arguments to pass to block constructor
            
        Returns:
            Instance of the building block
            
        Raises:
            ValueError: If block not found or instantiation fails
        """
        metadata = cls.get_block(name)
        if not metadata:
            raise ValueError(f"Block '{name}' not found in registry")
        
        # Parse module path
        if '.' in metadata.module_path:
            module_name, class_name = metadata.module_path.rsplit('.', 1)
        else:
            # Fallback: try to construct module path
            category_to_module = {
                'PATTERNS': 'patterns',
                'OSCILLATORS': 'oscillators',
                'PRICE_LEVELS': 'price_levels',
                'SESSIONS': 'sessions',
                'MOVING_AVERAGES': 'moving_averages',
                'MARKET_STRUCTURE': 'market_structure',
                'VOLATILITY': 'volatility',
                'INSTITUTIONAL': 'institutional',
                'SMC_ICT': 'smc_ict',
                'ELLIOTT_WAVE': 'elliott_wave',
                'FIBONACCI': 'fibonacci',
                'PRICE_ACTION': 'price_action',
                'RISK_MANAGEMENT': 'risk_management',
                'SIGNALS': 'signals',
                'SUPPLY_DEMAND': 'supply_demand',
                'TREND': 'trend',
                'WYCKOFF': 'wyckoff'
            }
            category_path = category_to_module.get(metadata.category, metadata.category.lower())
            module_name = f'src.detectors.building_blocks.{category_path}.{name}'
            class_name = metadata.class_name
        
        try:
            # Import module
            module = importlib.import_module(module_name)
            
            # Get class
            block_class = getattr(module, class_name)
            
            # Instantiate
            return block_class(**kwargs)
            
        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Failed to instantiate block '{name}': {e}\n"
                f"Module: {module_name}\n"
                f"Class: {class_name}"
            )
    
    @classmethod
    def list_blocks(cls, category: Optional[str] = None) -> List[str]:
        """
        List all registered block names
        
        Args:
            category: Optional category filter
            
        Returns:
            List of block names
        """
        if category:
            return list(cls.get_blocks_by_category(category).keys())
        return list(cls._blocks.keys())
    
    @classmethod
    def validate_signal(cls, block_name: str, signal: str) -> bool:
        """
        Check if a signal is valid for a block
        
        Args:
            block_name: Name of the block
            signal: Signal to validate
            
        Returns:
            True if signal is valid, False otherwise
        """
        valid_signals = cls.get_valid_signals(block_name)
        return signal in valid_signals
    
    @classmethod
    def get_categories(cls) -> List[str]:
        """Get list of all categories"""
        return list(set(meta.category for meta in cls._blocks.values()))
    
    @classmethod
    def get_blocks_for_signal(cls, signal_name: str) -> List[str]:
        """
        Find all blocks that can provide a specific signal
        
        INSTITUTIONAL-GRADE AUTO-DISCOVERY (2026-02-16):
        For given signal, searches registry to find which blocks emit it.
        Used by signal evaluator to auto-load blocks for exit conditions.
        
        Args:
            signal_name: Signal to search for (e.g., 'BULLISH', 'BULLISH_CROSS')
        
        Returns:
            List of block names that can provide this signal, ordered by:
            1. Category priority (OSCILLATORS first for OVERSOLD/BULLISH)
            2. Default weight (higher = more reliable)
        
        Example:
            blocks = BlockRegistry.get_blocks_for_signal('BULLISH')
            # Returns: ['rsi', 'macd', 'stoch', ...] (all blocks that emit BULLISH)
            
            blocks = BlockRegistry.get_blocks_for_signal('BULLISH_CROSS')
            # Returns: ['macd_cross', 'ema_crossover', ...] (cross-specific blocks)
        """
        capable_blocks = []
        
        # Search all registered blocks
        for block_name, metadata in cls._blocks.items():
            if signal_name in metadata.valid_signals:
                capable_blocks.append({
                    'name': block_name,
                    'category': metadata.category,
                    'weight': metadata.default_weight
                })
        
        # Sort by priority:
        # 1. Category priority (oscillators/indicators first for signals like BULLISH, OVERSOLD)
        # 2. Weight (higher = more reliable)
        category_priority = {
            'OSCILLATORS': 1,  # RSI, MACD, Stoch - primary for OVERSOLD/BULLISH
            'TREND': 2,  # ADX, EMA - for BULLISH/BEARISH
            'INSTITUTIONAL': 3,  # VWAP, Order Flow
            'PRICE_ACTION': 4,  # Breakers, Order Blocks
            'SMC_ICT': 5,  # ICT concepts
            'PATTERNS': 6,  # Chart patterns
        }
        
        def sort_key(block):
            return (
                category_priority.get(block['category'], 99),  # Category first
                -block['weight']  # Then weight (negative for descending)
            )
        
        capable_blocks.sort(key=sort_key)
        
        # Return just the names
        return [b['name'] for b in capable_blocks]
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get registry statistics"""
        categories = {}
        for meta in cls._blocks.values():
            categories[meta.category] = categories.get(meta.category, 0) + 1
        
        return {
            'total_blocks': len(cls._blocks),
            'categories': categories,
            'blocks_by_category': {
                cat: len(cls.get_blocks_by_category(cat))
                for cat in cls.get_categories()
            }
        }
    
    @classmethod
    def print_summary(cls):
        """Print a summary of registered blocks"""
        stats = cls.get_stats()
        
        logger.info("="*80)
        logger.info("BUILDING BLOCK REGISTRY SUMMARY")
        logger.info("="*80)
        logger.info(f"\nTotal Registered Blocks: {stats['total_blocks']}")
        logger.info(f"\nBlocks by Category:")
        for category, count in sorted(stats['blocks_by_category'].items()):
            logger.info(f"  {category:20s}: {count:3d} blocks")
        logger.info("="*80)


def register_block(**metadata):
    """
    Decorator to register a building block with the registry
    
    DUAL SIGNAL ARCHITECTURE (2026-01-15):
    All blocks must include BULLISH, BEARISH, NEUTRAL in valid_signals.
    
    Usage Example:
    ==============
    
    @register_block(
        name='m_pattern',
        category='PATTERNS',
        class_name='MPatternDetector',
        default_weight=25,
        valid_signals=[
            # Granular pattern signals (specific events)
            'M_TOP_CONFIRMED', 'M_FORMING', 'NO_PATTERN',
            # Simple directional signals (REQUIRED)
            'BULLISH', 'BEARISH', 'NEUTRAL',
            # Status signals
            'ERROR', 'INSUFFICIENT_DATA'
        ],
        signal_tiers={
            # Granular signals
            'M_TOP_CONFIRMED': {'base_points': 25, 'formula': 'scaled'},
            'M_FORMING': {'base_points': 12, 'formula': 'scaled'},
            'NO_PATTERN': {'points': 0},
            # Simple signals (REQUIRED)
            'BULLISH': {'base_points': 25, 'formula': 'scaled'},
            'BEARISH': {'base_points': 25, 'formula': 'scaled'},
            'NEUTRAL': {'points': 0},
            # Status signals
            'ERROR': {'points': 0},
            'INSUFFICIENT_DATA': {'points': 0}
        },
        description='M pattern (double top) bearish reversal',
        tags=['reversal', 'bearish', 'pattern']
    )
    class MPatternDetector:
        def _determine_dual_signals(self, granular_signal: str) -> tuple:
            \"\"\"Map granular to simple signals\"\"\"
            if granular_signal == 'M_TOP_CONFIRMED':
                return 'M_TOP_CONFIRMED', 'BEARISH'
            elif granular_signal == 'M_FORMING':
                return 'M_FORMING', 'BEARISH'
            else:
                return granular_signal, 'NEUTRAL'
        
        def analyze(self, df):
            # Dual signal emission
            granular, simple = self._determine_dual_signals('M_TOP_CONFIRMED')
            return {
                'signal': granular,        # Granular: 'M_TOP_CONFIRMED'
                'signal_simple': simple,   # Simple: 'BEARISH'
                'confidence': 85,
                'metadata': {
                    'signal_granular': granular,
                    'signal_simple': simple
                }
            }
    
    Args:
        **metadata: Block metadata (see BlockMetadata for required fields)
        
    Returns:
        Decorated class (unchanged)
    """
    return BlockRegistry.register(metadata)


# Auto-discover and register blocks on import
def auto_discover_blocks(base_path: Optional[Path] = None):
    """
    Auto-discover and import all building block modules
    
    This ensures all blocks are registered when the registry is imported.
    Blocks with @register_block decorators will auto-register.
    
    Args:
        base_path: Optional base path to search (defaults to building_blocks dir)
    """
    if base_path is None:
        base_path = Path(__file__).parent
    
    # Categories to search (all subdirectories)
    categories = [
        'patterns', 'oscillators', 'price_levels', 'sessions',
        'moving_averages', 'market_structure', 'volatility',
        'institutional', 'smc_ict', 'elliott_wave', 'fibonacci',
        'price_action', 'risk_management', 'signals', 'supply_demand',
        'trend', 'wyckoff'
    ]
    
    for category in categories:
        category_path = base_path / category
        if not category_path.exists():
            continue
        
        # Import all Python files in category
        for py_file in category_path.glob('*.py'):
            if py_file.name.startswith('_'):
                continue
            
            module_name = f'src.detectors.building_blocks.{category}.{py_file.stem}'
            try:
                importlib.import_module(module_name)
            except Exception:
                # Silently skip modules that fail to import
                # (they may not have dependencies yet)
                pass


# Auto-discover blocks when module is imported
if not BlockRegistry._initialized:
    auto_discover_blocks()
    BlockRegistry._initialized = True

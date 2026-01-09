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
- Scalable to 1000+ blocks

Author: BTC_Engine_v3
Date: 2026-01-09
Version: 1.0
"""

from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass
import importlib
import inspect
from pathlib import Path


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
    
    Usage:
        # Register a block (done in detector file)
        @register_block(
            name='double_top',
            category='PATTERNS',
            class_name='DoubleTopPattern',
            default_weight=30,
            valid_signals=['BEARISH_BREAKDOWN', 'PATTERN_FORMING'],
            signal_tiers={...}
        )
        class DoubleTopPattern:
            pass
        
        # Query registry
        metadata = BlockRegistry.get_block('double_top')
        detector = BlockRegistry.instantiate('double_top', timeframe='15min')
        signals = BlockRegistry.get_valid_signals('double_top')
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
        
        Raises:
            ValueError: If metadata is invalid
        """
        # Required fields
        required = ['name', 'category', 'class_name', 'valid_signals']
        for field in required:
            if field not in metadata:
                raise ValueError(f"Block registration missing required field: {field}")
        
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
        
        print("="*80)
        print("BUILDING BLOCK REGISTRY SUMMARY")
        print("="*80)
        print(f"\nTotal Registered Blocks: {stats['total_blocks']}")
        print(f"\nBlocks by Category:")
        for category, count in sorted(stats['blocks_by_category'].items()):
            print(f"  {category:20s}: {count:3d} blocks")
        print("="*80)


def register_block(**metadata):
    """
    Decorator to register a building block with the registry
    
    Usage:
        @register_block(
            name='double_top',
            category='PATTERNS',
            class_name='DoubleTopPattern',
            default_weight=30,
            valid_signals=['BEARISH_BREAKDOWN', 'PATTERN_FORMING', 'NO_PATTERN'],
            signal_tiers={
                'BEARISH_BREAKDOWN': {'base_points': 30, 'formula': 'quality_thresholds'},
                'PATTERN_FORMING': {'max_points': 15, 'formula': 'scaled'},
                'NO_PATTERN': {'points': 0}
            },
            description='Double top bearish reversal pattern',
            tags=['reversal', 'bearish']
        )
        class DoubleTopPattern:
            def analyze(self, df):
                # Must return signal from valid_signals
                return {'signal': 'BEARISH_BREAKDOWN', 'confidence': 95}
    
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
    
    # Categories to search
    categories = [
        'patterns', 'oscillators', 'price_levels', 'sessions',
        'moving_averages', 'market_structure', 'volatility',
        'institutional', 'smc_ict'
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
                # (they may not be ready or have dependencies)
                pass

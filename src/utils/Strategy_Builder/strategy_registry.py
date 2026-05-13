"""
Strategy Registry - Strategy Storage & Management

Handles saving, loading, and managing strategy configurations.
Features:
- Auto-increment strategy numbers
- JSON persistence
- Search and list capabilities
- Metadata tracking

Author: BTC_Engine_v3
Date: 2026-01-09
Status: Phase 1 - Foundation
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.utils.Strategy_Builder.models import (
    StrategyConfiguration,
    StrategyMetadata,
    StrategyCategory
)
from src.utils.Strategy_Builder.validator import StrategyValidator

import logging
logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)


class StrategyRegistry:
    """
    Manages strategy configurations with persistence
    
    Features:
    - Auto-increment strategy numbers
    - Save/load to JSON
    - List and search strategies
    - Metadata tracking
    - Validation before save
    
    Usage:
        registry = StrategyRegistry()
        
        # Get next strategy number
        next_num = registry.get_next_strategy_number()
        
        # Save strategy
        registry.save_strategy(config)
        
        # Load strategy
        config = registry.load_strategy(1)
        
        # List all
        all_strategies = registry.list_strategies()
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize strategy registry
        
        Args:
            storage_dir: Directory to store strategies (optional)
                        Defaults to src/strategies/
        """
        if storage_dir is None:
            # Default to project strategies directory
            storage_dir = Path(__file__).parent.parent.parent / "strategies"
        
        self.storage_dir = Path(storage_dir)
        
        # Create organized folder structure
        self.drafts_dir = self.storage_dir / "drafts"
        self.unpublished_dir = self.storage_dir / "unpublished"
        self.published_dir = self.storage_dir / "published"
        
        # Ensure all directories exist
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        self.unpublished_dir.mkdir(parents=True, exist_ok=True)
        self.published_dir.mkdir(parents=True, exist_ok=True)
        
        self.validator = StrategyValidator()
        
        logger.info(f"StrategyRegistry initialized: {self.storage_dir}")
        logger.info(f"  Drafts: {self.drafts_dir}")
        logger.info(f"  Unpublished: {self.unpublished_dir}")
        logger.info(f"  Published: {self.published_dir}")
    
    def get_next_strategy_number(self) -> int:
        """
        Get next available strategy number
        
        Scans existing strategies and returns next sequential number.
        
        Returns:
            Next available strategy number (1-150)
            
        Raises:
            ValueError: If all 150 strategy slots are filled
        """
        existing_numbers = set()
        
        # Scan for existing strategy files
        for file in self.storage_dir.glob("strategy_*.json"):
            try:
                # Extract number from filename: strategy_001_name.json
                parts = file.stem.split('_', 2)
                if len(parts) >= 2:
                    num = int(parts[1])
                    existing_numbers.add(num)
            except (ValueError, IndexError):
                continue
        
        # Find first available number (1-150)
        for num in range(1, 151):
            if num not in existing_numbers:
                return num
        
        raise ValueError("All 150 strategy slots are filled. Delete strategies to make room.")
    
    def _get_strategy_filename(self, config: StrategyConfiguration, is_draft: bool = False, is_published: bool = False) -> Path:
        """
        Generate filename for strategy based on its state
        
        Format: strategy_NNN_name.json
        Example: strategy_001_reversal_m.json
        
        Args:
            config: Strategy configuration
            is_draft: Whether this is a draft
            is_published: Whether this is published
            
        Returns:
            Path to strategy file in appropriate folder
        """
        # Remove 'strategy_NN_' prefix if present to get base name
        base_name = config.strategy_name
        if base_name.startswith(f"strategy_{config.strategy_number:02d}_"):
            base_name = base_name[len(f"strategy_{config.strategy_number:02d}_"):]
        
        filename = f"strategy_{config.strategy_number:03d}_{base_name}.json"
        
        # Determine folder based on state
        if is_draft:
            return self.drafts_dir / filename
        elif is_published:
            return self.published_dir / filename
        else:
            return self.unpublished_dir / filename
    
    def save_strategy(
        self,
        config: StrategyConfiguration,
        validate: bool = True,
        overwrite: bool = False,
        is_published: bool = False
    ) -> Path:
        """
        Save strategy configuration to JSON in appropriate folder
        
        Folder Structure:
        - drafts/       : Work-in-progress strategies
        - unpublished/  : Complete but not yet published
        - published/    : Ready for Intelligent Trade Manager
        
        Args:
            config: Strategy configuration to save
            validate: Whether to validate before saving (default: True)
            overwrite: Whether to overwrite existing file (default: False)
            is_published: Whether to save as published (default: False)
            
        Returns:
            Strategy number (int) of saved strategy
            
        Raises:
            ValueError: If validation fails or file exists without overwrite
        """
        # Validate if requested
        if validate:
            result = self.validator.validate(config)
            if not result.is_valid:
                error_msg = "\n".join(result.errors)
                raise ValueError(f"Strategy validation failed:\n{error_msg}")
        
        # Determine if this is a draft
        is_draft = config.description and "[DRAFT]" in config.description
        
        # Get filename in appropriate folder
        filepath = self._get_strategy_filename(config, is_draft, is_published)
        
        # If overwriting, check if name changed and rename associated files
        if overwrite:
            old_config = self.load_strategy(config.strategy_number)
            if old_config and old_config.strategy_name != config.strategy_name:
                # Name changed - rename all associated files
                self._rename_associated_files(config.strategy_number, old_config.strategy_name, config.strategy_name)
            
            # Delete from all folders
            self._delete_from_all_folders(config.strategy_number)
        
        # Check if file exists
        if filepath.exists() and not overwrite:
            raise ValueError(
                f"Strategy file already exists: {filepath.name}\n"
                f"Use overwrite=True to replace it."
            )
        
        # Convert to dict for JSON serialization
        strategy_dict = config.model_dump()
        
        # Add metadata
        strategy_dict['_metadata'] = {
            'saved_at': datetime.now().isoformat(),
            'version': '1.0',
            'status': 'published' if is_published else ('draft' if is_draft else 'unpublished')
        }
        
        # Save to JSON
        with open(filepath, 'w') as f:
            json.dump(strategy_dict, f, indent=2)
        
        folder_name = filepath.parent.name
        logger.info(f"Strategy saved to {folder_name}/: {filepath.name}")
        return filepath
    
    def _rename_associated_files(self, strategy_number: int, old_name: str, new_name: str):
        """
        Rename all generated files when strategy name changes
        
        Renames:
        - Strategy file: src/strategies/strategy_NNN_oldname.py → strategy_NNN_newname.py
        - Test file: tests/strategies/test_NNN_oldname.py → test_NNN_newname.py  
        - Config file: config/optimizer_NNN_oldname.yaml → optimizer_NNN_newname.yaml
        
        Args:
            strategy_number: Strategy number
            old_name: Old strategy name
            new_name: New strategy name
        """
        # Build old and new filenames (removing any strategy_NN_ prefix)
        old_base = old_name
        if old_base.startswith(f"strategy_{strategy_number:02d}_"):
            old_base = old_base[len(f"strategy_{strategy_number:02d}_"):]
        
        new_base = new_name
        if new_base.startswith(f"strategy_{strategy_number:02d}_"):
            new_base = new_base[len(f"strategy_{strategy_number:02d}_"):]
        
        # Define file mappings: old pattern → new name
        file_renames = [
            # Strategy file
            (
                self.storage_dir / f"strategy_{strategy_number:03d}_{old_base}.py",
                self.storage_dir / f"strategy_{strategy_number:03d}_{new_base}.py"
            ),
            # Test file
            (
                Path(__file__).parent.parent.parent / "tests" / "strategies" / f"test_{strategy_number:03d}_{old_base}.py",
                Path(__file__).parent.parent.parent / "tests" / "strategies" / f"test_{strategy_number:03d}_{new_base}.py"
            ),
            # Optimizer config
            (
                Path(__file__).parent.parent.parent / "config" / f"optimizer_{strategy_number:03d}_{old_base}.yaml",
                Path(__file__).parent.parent.parent / "config" / f"optimizer_{strategy_number:03d}_{new_base}.yaml"
            ),
        ]
        
        # Rename each file if it exists
        for old_path, new_path in file_renames:
            if old_path.exists():
                try:
                    old_path.rename(new_path)
                    logger.info(f"Renamed: {old_path.name} → {new_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to rename {old_path.name}: {e}")
            else:
                logger.debug(f"File not found (skip): {old_path.name}")
    
    def _delete_from_all_folders(self, strategy_number: int):
        """Delete strategy from all folders (when moving between states)"""
        pattern = f"strategy_{strategy_number:03d}_*.json"
        
        for folder in [self.drafts_dir, self.unpublished_dir, self.published_dir]:
            for filepath in folder.glob(pattern):
                filepath.unlink()
                logger.info(f"Deleted old version: {filepath}")
    
    def load_strategy(self, strategy_number: int) -> Optional[StrategyConfiguration]:
        """
        Load strategy by number from any folder
        
        Args:
            strategy_number: Strategy number to load
            
        Returns:
            StrategyConfiguration or None if not found
        """
        # Search all folders
        pattern = f"strategy_{strategy_number:03d}_*.json"
        matching_files = []
        
        for folder in [self.drafts_dir, self.unpublished_dir, self.published_dir]:
            matching_files.extend(folder.glob(pattern))
        
        if not matching_files:
            logger.warning(f"Strategy {strategy_number} not found in any folder")
            return None
        
        if len(matching_files) > 1:
            logger.warning(
                f"Multiple files found for strategy {strategy_number}, "
                f"using first: {matching_files[0].name}"
            )
        
        filepath = matching_files[0]
        return self.load_strategy_from_file(filepath)
    
    def load_strategy_from_file(self, filepath: Path) -> Optional[StrategyConfiguration]:
        """
        Load strategy from specific file
        
        Args:
            filepath: Path to strategy JSON file
            
        Returns:
            StrategyConfiguration or None if load fails
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Remove metadata if present
            data.pop('_metadata', None)
            
            # Recreate StrategyConfiguration
            config = StrategyConfiguration(**data)
            
            logger.info(f"Strategy loaded: {filepath.name}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load strategy from {filepath}: {e}")
            return None
    
    def list_strategies(
        self,
        category: Optional[StrategyCategory] = None
    ) -> List[StrategyMetadata]:
        """
        List all strategies with metadata from all folders
        
        Args:
            category: Optional category filter
            
        Returns:
            List of StrategyMetadata objects
        """
        strategies = []
        
        # Scan all folders
        for folder in [self.drafts_dir, self.unpublished_dir, self.published_dir]:
            for filepath in sorted(folder.glob("strategy_*.json")):
                try:
                    config = self.load_strategy_from_file(filepath)
                    if config is None:
                        continue
                    
                    # Filter by category if specified
                    if category and config.strategy_category != category:
                        continue
                    
                    # Create metadata
                    metadata = StrategyMetadata(
                        number=config.strategy_number,
                        name=config.strategy_name,
                        category=config.strategy_category,
                        created_date=config.created_date if hasattr(config, 'created_date') else datetime.now().isoformat(),
                        modified_date=config.modified_date if hasattr(config, 'modified_date') else datetime.now().isoformat(),
                        file_path=str(filepath),
                        config_path=str(filepath),  # Same as file_path for now
                        version=config.version if hasattr(config, 'version') else 1,
                        description=config.description if hasattr(config, 'description') else ""
                    )
                    strategies.append(metadata)
                    
                except Exception as e:
                    logger.error(f"Error processing {filepath.name}: {e}")
                    continue
        
        return strategies
    
    def search_strategies(self, query: str) -> List[StrategyMetadata]:
        """
        Search strategies by name
        
        Case-insensitive search in strategy names.
        
        Args:
            query: Search string
            
        Returns:
            List of matching StrategyMetadata objects
        """
        query_lower = query.lower()
        all_strategies = self.list_strategies()
        
        matching = [
            s for s in all_strategies
            if query_lower in s.name.lower()
        ]
        
        return matching
    
    def delete_strategy(self, strategy_number: int) -> bool:
        """
        Delete strategy by number from any folder
        
        Args:
            strategy_number: Strategy number to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Search all folders
        pattern = f"strategy_{strategy_number:03d}_*.json"
        matching_files = []
        
        for folder in [self.drafts_dir, self.unpublished_dir, self.published_dir]:
            matching_files.extend(folder.glob(pattern))
        
        if not matching_files:
            logger.warning(f"Strategy {strategy_number} not found in any folder")
            return False
        
        # Delete all matching files
        for filepath in matching_files:
            filepath.unlink()
            logger.info(f"Strategy deleted: {filepath.name}")
        
        return True
    
    def get_strategy_count(self) -> int:
        """
        Get total number of saved strategies across all folders
        
        Returns:
            Count of strategy files
        """
        count = 0
        for folder in [self.drafts_dir, self.unpublished_dir, self.published_dir]:
            count += len(list(folder.glob("strategy_*.json")))
        return count
    
    def get_next_strategy_number(self) -> int:
        """
        Get next available strategy number (searches all folders)
        
        Scans existing strategies and returns next sequential number.
        
        Returns:
            Next available strategy number (1-150)
            
        Raises:
            ValueError: If all 150 strategy slots are filled
        """
        existing_numbers = set()
        
        # Scan all folders for existing strategy files
        for folder in [self.drafts_dir, self.unpublished_dir, self.published_dir]:
            for file in folder.glob("strategy_*.json"):
                try:
                    # Extract number from filename: strategy_001_name.json
                    parts = file.stem.split('_', 2)
                    if len(parts) >= 2:
                        num = int(parts[1])
                        existing_numbers.add(num)
                except (ValueError, IndexError):
                    continue
        
        # Find first available number (1-150)
        for num in range(1, 151):
            if num not in existing_numbers:
                return num
        
        raise ValueError("All 150 strategy slots are filled. Delete strategies to make room.")
    
    def get_category_counts(self) -> Dict[str, int]:
        """
        Get strategy count by category
        
        Returns:
            Dictionary mapping category names to counts
        """
        counts = {}
        strategies = self.list_strategies()
        
        for strategy in strategies:
            category = strategy.category
            counts[category] = counts.get(category, 0) + 1
        
        return counts
    
    def validate_all_strategies(self) -> Dict[int, Any]:
        """
        Validate all saved strategies
        
        Useful for checking if strategies are still valid after
        registry changes or building block updates.
        
        Returns:
            Dictionary mapping strategy numbers to validation results
        """
        results = {}
        strategies = self.list_strategies()
        
        for metadata in strategies:
            config = self.load_strategy(metadata.number)
            if config:
                validation = self.validator.validate(config)
                results[metadata.number] = {
                    'is_valid': validation.is_valid,
                    'errors': validation.errors,
                    'warnings': validation.warnings
                }
        
        return results
    
    def export_strategy(self, strategy_number: int, output_path: Path) -> bool:
        """
        Export strategy to specific location
        
        Args:
            strategy_number: Strategy to export
            output_path: Where to export
            
        Returns:
            True if exported successfully
        """
        config = self.load_strategy(strategy_number)
        if not config:
            return False
        
        try:
            strategy_dict = config.model_dump()
            with open(output_path, 'w') as f:
                json.dump(strategy_dict, f, indent=2)
            
            logger.info(f"Strategy exported to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def import_strategy(
        self,
        filepath: Path,
        strategy_number: Optional[int] = None,
        validate: bool = True
    ) -> Optional[StrategyConfiguration]:
        """
        Import strategy from external file
        
        Args:
            filepath: Path to strategy JSON
            strategy_number: Optional number to assign (auto if None)
            validate: Whether to validate before import
            
        Returns:
            Loaded StrategyConfiguration or None if failed
        """
        try:
            # Load from file
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            data.pop('_metadata', None)
            
            # Assign strategy number if needed
            if strategy_number is None:
                strategy_number = self.get_next_strategy_number()
            
            data['strategy_number'] = strategy_number
            
            # Update strategy name to match number
            base_name = data.get('strategy_name', 'imported')
            if base_name.startswith('strategy_'):
                # Remove old number prefix
                parts = base_name.split('_', 2)
                if len(parts) >= 3:
                    base_name = parts[2]
            
            data['strategy_name'] = f"strategy_{strategy_number:02d}_{base_name}"
            
            # Create config
            config = StrategyConfiguration(**data)
            
            # Save to registry
            self.save_strategy(config, validate=validate, overwrite=False)
            
            logger.info(f"Strategy imported as #{strategy_number}")
            return config
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return None
    
    def generate_strategy_files(
        self,
        strategy_number: int,
        strategy_dir: Optional[Path] = None,
        test_dir: Optional[Path] = None,
        config_dir: Optional[Path] = None
    ) -> Optional[Dict[str, Path]]:
        """
        Convenience method: Load strategy and generate all files
        
        Args:
            strategy_number: Strategy number to generate files for
            strategy_dir: Output directory for strategy files
            test_dir: Output directory for test files
            config_dir: Output directory for optimizer configs
            
        Returns:
            Dictionary with paths to generated files, or None if failed
            
        Example:
            registry = StrategyRegistry()
            files = registry.generate_strategy_files(1)
            logger.info(f"Strategy: {files['strategy']}")
            logger.info(f"Test: {files['test']}")
            logger.info(f"Optimizer: {files['optimizer']}")
        """
        # Lazy import to avoid circular dependency
        from src.utils.Strategy_Builder.generator import StrategyGenerator
        
        # Load strategy
        config = self.load_strategy(strategy_number)
        if not config:
            logger.error(f"Strategy {strategy_number} not found")
            return None
        
        # Generate files
        try:
            generator = StrategyGenerator()
            files = generator.generate_all(
                config,
                strategy_dir=strategy_dir,
                test_dir=test_dir,
                config_dir=config_dir
            )
            
            logger.info(f"Generated files for strategy {strategy_number}")
            return files
            
        except Exception as e:
            logger.error(f"File generation failed: {e}")
            return None

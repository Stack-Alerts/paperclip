"""
Strategy Generator - Code Generation Module

Generates NautilusTrader strategy files, tests, and optimizer configs
from validated StrategyConfiguration objects using Jinja2 templates.

import logging
logger = logging.getLogger(__name__)


Author: Strategy Builder v1.0
Date: 2026-01-09
"""

import ast
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

from jinja2 import Environment, FileSystemLoader, Template
import yaml

from src.utils.Strategy_Builder.models import StrategyConfiguration, BlockSelection
class StrategyGenerator:
    """
    Generates strategy files from validated configurations
    
    Uses Jinja2 templates to create:
    - NautilusTrader strategy Python files
    - pytest test files
    - Optimizer configuration YAML files
    """
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize generator with template directory
        
        Args:
            template_dir: Directory containing Jinja2 templates.
                         Defaults to src/utils/Strategy_Builder/templates
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / 'templates'
        
        self.template_dir = Path(template_dir)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Load templates
        self.strategy_template = self.env.get_template('strategy_template.py.j2')
        self.test_template = self.env.get_template('test_template.py.j2')
        self.optimizer_template = self.env.get_template('optimizer_config.yaml.j2')
        
    def generate_strategy_file(
        self,
        config: StrategyConfiguration,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Generate NautilusTrader strategy Python file
        
        Args:
            config: Validated strategy configuration
            output_dir: Output directory (defaults to src/strategies/)
            
        Returns:
            Path to generated strategy file
        """
        if output_dir is None:
            output_dir = Path('src/strategies')
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare template context
        context = self._prepare_context(config)
        
        # Render template
        code = self.strategy_template.render(**context)
        
        # Generate filename (use cleaned name to avoid double-prefix)
        clean_name = self._clean_strategy_name(config.strategy_name)
        filename = f"strategy_{config.strategy_number:03d}_{clean_name.lower().replace(' ', '_')}.py"
        filepath = output_dir / filename
        
        # Save file
        with open(filepath, 'w') as f:
            f.write(code)
        
        # Validate syntax
        if not self.validate_python_syntax(filepath):
            raise SyntaxError(f"Generated strategy file has syntax errors: {filepath}")
        
        return filepath
    
    def generate_test_file(
        self,
        config: StrategyConfiguration,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Generate pytest test file
        
        Args:
            config: Validated strategy configuration
            output_dir: Output directory (defaults to tests/strategies/)
            
        Returns:
            Path to generated test file
        """
        if output_dir is None:
            output_dir = Path('tests/strategies')
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare template context
        context = self._prepare_context(config)
        
        # Render template
        code = self.test_template.render(**context)
        
        # Generate filename (use cleaned name to avoid double-prefix)
        clean_name = self._clean_strategy_name(config.strategy_name)
        filename = f"test_{config.strategy_number:03d}_{clean_name.lower().replace(' ', '_')}.py"
        filepath = output_dir / filename
        
        # Save file
        with open(filepath, 'w') as f:
            f.write(code)
        
        # Validate syntax
        if not self.validate_python_syntax(filepath):
            raise SyntaxError(f"Generated test file has syntax errors: {filepath}")
        
        return filepath
    
    def generate_optimizer_config(
        self,
        config: StrategyConfiguration,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Generate optimizer configuration YAML file
        
        Args:
            config: Validated strategy configuration
            output_dir: Output directory (defaults to config/)
            
        Returns:
            Path to generated config file
        """
        if output_dir is None:
            output_dir = Path('config')
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare template context
        context = self._prepare_context(config)
        
        # Render template
        yaml_content = self.optimizer_template.render(**context)
        
        # Generate filename (use cleaned name to avoid double-prefix)
        clean_name = self._clean_strategy_name(config.strategy_name)
        filename = f"optimizer_{config.strategy_number:03d}_{clean_name.lower().replace(' ', '_')}.yaml"
        filepath = output_dir / filename
        
        # Save file
        with open(filepath, 'w') as f:
            f.write(yaml_content)
        
        # Validate YAML syntax
        if not self.validate_yaml_syntax(filepath):
            raise ValueError(f"Generated config file has YAML syntax errors: {filepath}")
        
        return filepath
    
    def generate_all(
        self,
        config: StrategyConfiguration,
        strategy_dir: Optional[Path] = None,
        test_dir: Optional[Path] = None,
        config_dir: Optional[Path] = None
    ) -> Dict[str, Path]:
        """
        Generate all files at once
        
        Args:
            config: Validated strategy configuration
            strategy_dir: Strategy output directory
            test_dir: Test output directory
            config_dir: Config output directory
            
        Returns:
            Dictionary with paths to all generated files
        """
        return {
            'strategy': self.generate_strategy_file(config, strategy_dir),
            'test': self.generate_test_file(config, test_dir),
            'optimizer': self.generate_optimizer_config(config, config_dir)
        }
    
    def _prepare_context(self, config: StrategyConfiguration) -> Dict[str, Any]:
        """
        Prepare template context data
        
        Args:
            config: Strategy configuration
            
        Returns:
            Dictionary of context variables for templates
        """
        # Clean strategy name (remove any existing strategy_XX_ prefix)
        clean_name = self._clean_strategy_name(config.strategy_name)
        
        # Generate class name (PascalCase)
        class_name = self._generate_class_name(clean_name)
        
        # Generate filename (snake_case)
        filename = f"strategy_{config.strategy_number:03d}_{clean_name.lower().replace(' ', '_')}"
        
        # Generate imports
        imports = self._generate_imports(config.blocks)
        
        # Generate block class name mapping from registry
        block_class_map = self._generate_block_class_map(config.blocks)
        
        # Prepare context
        context = {
            'config': config,
            'class_name': class_name,
            'filename': filename,
            'imports': imports,
            'block_class_map': block_class_map,
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        return context
    
    def _clean_strategy_name(self, strategy_name: str) -> str:
        """
        Remove any existing strategy_XX_ prefix from name
        
        Args:
            strategy_name: Original strategy name
            
        Returns:
            Cleaned name without prefix
            
        Examples:
            "strategy_01_test_strategy" -> "test_strategy"
            "test_strategy" -> "test_strategy"
        """
        # Pattern: strategy_\d+_
        pattern = r'^strategy_\d+_'
        cleaned = re.sub(pattern, '', strategy_name)
        return cleaned if cleaned else strategy_name
    
    def _generate_class_name(self, strategy_name: str) -> str:
        """
        Generate PascalCase class name from strategy name
        
        Ensures valid Python class names by:
        - Prepending "Strategy" prefix
        - Filtering out numeric-only parts
        - Using PascalCase convention
        
        Args:
            strategy_name: Strategy name (may have spaces, underscores)
            
        Returns:
            PascalCase class name (guaranteed valid Python identifier)
            
        Examples:
            "01_HOD_Rejection" -> "StrategyHodRejection"
            "reversal m pattern" -> "StrategyReversalMPattern"
            "ema_trend_following" -> "StrategyEmaTrendFollowing"
        """
        # Split on spaces and underscores
        words = re.split(r'[\s_]+', strategy_name)
        
        # Filter out numeric-only words and capitalize
        # This handles cases like "01" from "01_HOD_Rejection"
        valid_words = [
            word.capitalize() 
            for word in words 
            if word and not word.isdigit()
        ]
        
        # Join words
        name_part = ''.join(valid_words)
        
        # Always prepend "Strategy" to ensure valid Python identifier
        # and avoid conflicts with built-in names
        class_name = f"Strategy{name_part}"
        
        return class_name
    
    def _generate_block_class_map(self, blocks: List[BlockSelection]) -> Dict[str, str]:
        """
        Generate mapping of block_name to class_name from registry
        
        Args:
            blocks: List of selected building blocks
            
        Returns:
            Dictionary mapping block_name to actual class_name
            
        Example:
            {'hod': 'HOD', 'stochastic_rsi': 'StochasticRSI'}
        """
        from src.detectors.building_blocks.registry import BlockRegistry
        
        registry = BlockRegistry()
        class_map = {}
        
        for block in blocks:
            block_name = block.block_name
            block_metadata = registry.get_block(block_name)
            
            if block_metadata:
                class_map[block_name] = block_metadata.class_name
            else:
                logger.info(f"Warning: Block '{block_name}' not in registry")
                # Fallback to generated name
                class_map[block_name] = self._generate_class_name(block_name)
        
        return class_map
    
    def _generate_imports(self, blocks: List[BlockSelection]) -> List[str]:
        """
        Generate import statements for building blocks using BlockRegistry
        
        Uses the BlockRegistry as the single source of truth for:
        - Module paths
        - Class names
        - Import statements
        
        Args:
            blocks: List of selected building blocks
            
        Returns:
            List of import statement strings
        """
        from src.detectors.building_blocks.registry import BlockRegistry
        imports = []
        seen = set()  # Track unique imports
        registry = BlockRegistry()
        
        for block in blocks:
            block_name = block.block_name
            
            # Get block metadata from registry (single source of truth)
            block_metadata = registry.get_block(block_name)
            
            if not block_metadata:
                # Fallback if block not in registry (shouldn't happen in production)
                logger.warning(f"Warning: Block '{block_name}' not found in registry, skipping import")
                continue
            
            # Get import info from registry metadata
            module_path = block_metadata.module_path
            class_name = block_metadata.class_name
            
            # WORKAROUND: Remove class name from end of module_path if present
            # Registry incorrectly includes class name in module_path
            if module_path.endswith(f".{class_name}"):
                module_path = module_path[:-len(f".{class_name}")]
            
            # Create import statement
            import_stmt = f"from {module_path} import {class_name}"
            
            # Add if not duplicate
            if import_stmt not in seen:
                imports.append(import_stmt)
                seen.add(import_stmt)
        
        return sorted(imports)  # Sort for consistency
    
    def validate_python_syntax(self, filepath: Path) -> bool:
        """
        Validate Python file syntax
        
        Args:
            filepath: Path to Python file
            
        Returns:
            True if syntax is valid, False otherwise
        """
        try:
            with open(filepath, 'r') as f:
                code = f.read()
            
            # Try to parse as AST
            ast.parse(code)
            return True
            
        except SyntaxError as e:
            logger.error(f"Syntax error in {filepath}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating {filepath}: {e}")
            return False
    
    def validate_yaml_syntax(self, filepath: Path) -> bool:
        """
        Validate YAML file syntax
        
        Args:
            filepath: Path to YAML file
            
        Returns:
            True if syntax is valid, False otherwise
        """
        try:
            with open(filepath, 'r') as f:
                yaml.safe_load(f)
            return True
            
        except yaml.YAMLError as e:
            logger.error(f"YAML error in {filepath}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error validating {filepath}: {e}")
            return False
    
    def dry_run(
        self,
        config: StrategyConfiguration
    ) -> Dict[str, str]:
        """
        Perform dry run (render templates without saving)
        
        Args:
            config: Strategy configuration
            
        Returns:
            Dictionary with rendered code for each file type
        """
        context = self._prepare_context(config)
        
        return {
            'strategy': self.strategy_template.render(**context),
            'test': self.test_template.render(**context),
            'optimizer': self.optimizer_template.render(**context)
        }


# Convenience function
def generate_strategy(
    config: StrategyConfiguration,
    validate: bool = True
) -> Dict[str, Path]:
    """
    Convenience function to generate all files from config
    
    Args:
        config: Strategy configuration
        validate: Whether to validate syntax
        
    Returns:
        Dictionary with paths to generated files
    """
    generator = StrategyGenerator()
    return generator.generate_all(config)

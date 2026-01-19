"""
Strategy Persistence
Save/load strategies to/from JSON and YAML files
Maintains version compatibility and data integrity
Reference: docs/v3/UI-UX/23_STRATEGY_PERSISTENCE.md
"""

import json
import yaml
from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum

from src.strategy_builder.core.strategy_config_engine import (
    StrategyConfig,
    BlockConfig,
    SignalConfig,
    TimingConstraint,
    RecheckConfig
)


class PersistenceFormat(Enum):
    """File format for persistence"""
    JSON = "json"
    YAML = "yaml"


@dataclass
class PersistenceResult:
    """Result of save/load operation"""
    success: bool
    config: Optional[StrategyConfig] = None
    errors: List[str] = field(default_factory=list)


class StrategyPersistence:
    """
    Strategy persistence manager
    Handles saving and loading strategies to/from files
    """
    
    VERSION = "1.0.0"
    
    def __init__(self):
        """Initialize persistence manager"""
        pass
        
    def save(
        self,
        config: StrategyConfig,
        filepath: Path,
        format: Optional[PersistenceFormat] = None
    ) -> PersistenceResult:
        """
        Save strategy to file
        
        Args:
            config: Strategy configuration to save
            filepath: Path to save file
            format: Format to use (auto-detected if not specified)
            
        Returns:
            PersistenceResult indicating success/failure
        """
        try:
            # Auto-detect format if not specified
            if format is None:
                format = self._detect_format(filepath)
                
            # Convert config to dict
            data = self._config_to_dict(config)
            
            # Add version info
            data['version'] = self.VERSION
            
            # Save based on format
            if format == PersistenceFormat.JSON:
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
            elif format == PersistenceFormat.YAML:
                with open(filepath, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False)
            else:
                return PersistenceResult(
                    success=False,
                    errors=[f"Unsupported format: {format}"]
                )
                
            return PersistenceResult(success=True)
            
        except Exception as e:
            return PersistenceResult(
                success=False,
                errors=[f"Save error: {str(e)}"]
            )
            
    def load(self, filepath: Path) -> PersistenceResult:
        """
        Load strategy from file
        
        Args:
            filepath: Path to load from
            
        Returns:
            PersistenceResult with loaded config
        """
        try:
            # Check file exists
            if not filepath.exists():
                return PersistenceResult(
                    success=False,
                    errors=[f"File not found: {filepath}"]
                )
                
            # Detect format
            format = self._detect_format(filepath)
            
            # Load based on format
            if format == PersistenceFormat.JSON:
                with open(filepath, 'r') as f:
                    data = json.load(f)
            elif format == PersistenceFormat.YAML:
                with open(filepath, 'r') as f:
                    data = yaml.safe_load(f)
            else:
                return PersistenceResult(
                    success=False,
                    errors=[f"Unsupported format: {format}"]
                )
                
            # Check version compatibility
            if 'version' not in data:
                return PersistenceResult(
                    success=False,
                    errors=["Missing version information"]
                )
                
            # Convert dict to config
            config = self._dict_to_config(data)
            
            return PersistenceResult(
                success=True,
                config=config
            )
            
        except json.JSONDecodeError as e:
            return PersistenceResult(
                success=False,
                errors=[f"Invalid JSON: {str(e)}"]
            )
        except yaml.YAMLError as e:
            return PersistenceResult(
                success=False,
                errors=[f"Invalid YAML: {str(e)}"]
            )
        except Exception as e:
            return PersistenceResult(
                success=False,
                errors=[f"Load error: {str(e)}"]
            )
            
    def _detect_format(self, filepath: Path) -> PersistenceFormat:
        """
        Detect format from file extension
        
        Args:
            filepath: File path
            
        Returns:
            Detected format
        """
        suffix = filepath.suffix.lower()
        
        if suffix == '.json':
            return PersistenceFormat.JSON
        elif suffix in ['.yaml', '.yml']:
            return PersistenceFormat.YAML
        else:
            # Default to JSON
            return PersistenceFormat.JSON
            
    def _config_to_dict(self, config: StrategyConfig) -> dict:
        """
        Convert StrategyConfig to dictionary
        
        Args:
            config: Strategy configuration
            
        Returns:
            Dictionary representation
        """
        data = {
            'name': config.name,
            'description': config.description,
            'blocks': []
        }
        
        for block in config.blocks:
            block_data = {
                'name': block.name,
                'logic': block.logic,
                'signals': []
            }
            
            for signal in block.signals:
                signal_data = {
                    'name': signal.name,
                    'logic': signal.logic
                }
                
                # Add timing constraint if present
                if signal.timing_constraint:
                    signal_data['timing_constraint'] = {
                        'max_candles': signal.timing_constraint.max_candles,
                        'reference': signal.timing_constraint.reference
                    }
                
                # Add recheck config if present
                if signal.recheck_config:
                    signal_data['recheck_config'] = {
                        'enabled': signal.recheck_config.enabled,
                        'bar_delay': signal.recheck_config.bar_delay
                    }
                    
                block_data['signals'].append(signal_data)
                
            data['blocks'].append(block_data)
            
        return data
        
    def _dict_to_config(self, data: dict) -> StrategyConfig:
        """
        Convert dictionary to StrategyConfig
        
        Args:
            data: Dictionary data
            
        Returns:
            Strategy configuration
        """
        config = StrategyConfig()
        config.name = data.get('name', '')
        config.description = data.get('description', '')
        
        for block_data in data.get('blocks', []):
            block = BlockConfig(
                name=block_data['name'],
                logic=block_data['logic'],
                signals=[]
            )
            
            for signal_data in block_data.get('signals', []):
                # Create timing constraint if present
                timing_constraint = None
                if 'timing_constraint' in signal_data:
                    tc_data = signal_data['timing_constraint']
                    timing_constraint = TimingConstraint(
                        max_candles=tc_data['max_candles'],
                        reference=tc_data['reference']
                    )
                
                # Create recheck config if present
                recheck_config = None
                if 'recheck_config' in signal_data:
                    rc_data = signal_data['recheck_config']
                    recheck_config = RecheckConfig(
                        enabled=rc_data.get('enabled', False),
                        bar_delay=rc_data.get('bar_delay', 0)
                    )
                    
                signal = SignalConfig(
                    name=signal_data['name'],
                    logic=signal_data['logic'],
                    timing_constraint=timing_constraint,
                    recheck_config=recheck_config
                )
                
                block.signals.append(signal)
                
            config.blocks.append(block)
            
        return config

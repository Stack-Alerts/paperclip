"""
Strategy Validator
Advanced validation with NautilusTrader compatibility checks
Ensures strategies meet institutional-grade quality standards
Reference: docs/v3/UI-UX/22_STRATEGY_VALIDATOR.md
"""

from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.strategy_builder.core.strategy_config_engine import StrategyConfig
from src.strategy_builder.core.signal_dependency_resolver import SignalDependencyResolver


class ValidationLevel(Enum):
    """Validation strictness levels"""
    BASIC = "basic"          # Basic structural validation
    STANDARD = "standard"    # Standard validation (default)
    STRICT = "strict"        # Strict validation for production


@dataclass
class ValidationRule:
    """Definition of a validation rule"""
    name: str
    description: str
    level: ValidationLevel
    check_function: Optional[callable] = None


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)


class ExitConditionValidator:
    """
    Exit Condition Validator
    Sprint 1.8 Task 1.8.34
    
    Validates exit conditions at all binding levels (STRATEGY, BLOCK, SIGNAL)
    """
    
    VALID_EXIT_MODES = ["ABSOLUTE", "FLEXIBLE"]
    VALID_BINDING_LEVELS = ["STRATEGY", "BLOCK", "SIGNAL"]
    
    @staticmethod
    def validate_exit_conditions(config: StrategyConfig) -> List[str]:
        """
        Validate all exit conditions across strategy
        
        Validation rules:
        1. Total percentage per binding level cannot exceed 100%
        2. Each percentage must be 0 < pct <= 1.0
        3. Exit mode must be ABSOLUTE or FLEXIBLE
        4. Binding level must be STRATEGY, BLOCK, or SIGNAL
        5. No circular exit dependencies (exits can reference entries, not other exits)
        
        Args:
            config: Strategy configuration to validate
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Validate strategy-level exit conditions
        if hasattr(config, 'exit_conditions') and config.exit_conditions:
            errors.extend(
                ExitConditionValidator._validate_exit_level(
                    config.exit_conditions,
                    "Strategy"
                )
            )
            
            # Check total percentage for strategy level
            total_pct = sum(ec.percentage for ec in config.exit_conditions)
            if total_pct > 1.0:
                errors.append(
                    f"Strategy-level exit conditions total {total_pct*100:.0f}% (max 100%)"
                )
        
        # Validate block-level exit conditions
        for block in config.blocks:
            if hasattr(block, 'exit_conditions') and block.exit_conditions:
                errors.extend(
                    ExitConditionValidator._validate_exit_level(
                        block.exit_conditions,
                        f"Block '{block.name}'"
                    )
                )
                
                # Check total percentage for this block
                total_pct = sum(ec.percentage for ec in block.exit_conditions)
                if total_pct > 1.0:
                    errors.append(
                        f"Block '{block.name}' exit conditions total {total_pct*100:.0f}% (max 100%)"
                    )
            
            # Validate signal-level exit conditions
            for signal in block.signals:
                if hasattr(signal, 'exit_conditions') and signal.exit_conditions:
                    errors.extend(
                        ExitConditionValidator._validate_exit_level(
                            signal.exit_conditions,
                            f"Signal '{block.name}::{signal.name}'"
                        )
                    )
                    
                    # Check total percentage for this signal
                    total_pct = sum(ec.percentage for ec in signal.exit_conditions)
                    if total_pct > 1.0:
                        errors.append(
                            f"Signal '{block.name}::{signal.name}' exit conditions total {total_pct*100:.0f}% (max 100%)"
                        )
        
        return errors
    
    @staticmethod
    def _validate_exit_level(exit_conditions: List, level_name: str) -> List[str]:
        """Validate exit conditions at a specific level"""
        errors = []
        
        for ec in exit_conditions:
            # Validate percentage range
            if ec.percentage <= 0 or ec.percentage > 1.0:
                errors.append(
                    f"{level_name}: Exit condition '{ec.signal_name}' has invalid percentage {ec.percentage*100:.1f}% (must be 0-100%)"
                )
            
            # Validate exit mode
            if ec.exit_mode not in ExitConditionValidator.VALID_EXIT_MODES:
                errors.append(
                    f"{level_name}: Exit condition '{ec.signal_name}' has invalid exit_mode '{ec.exit_mode}' (must be ABSOLUTE or FLEXIBLE)"
                )
            
            # Validate binding level
            if hasattr(ec, 'binding_level') and ec.binding_level not in ExitConditionValidator.VALID_BINDING_LEVELS:
                errors.append(
                    f"{level_name}: Exit condition '{ec.signal_name}' has invalid binding_level '{ec.binding_level}'"
                )
            
            # Validate FLEXIBLE mode parameters
            if ec.exit_mode == "FLEXIBLE":
                if ec.tp_proximity_threshold <= 0:
                    errors.append(
                        f"{level_name}: Exit condition '{ec.signal_name}' has invalid tp_proximity_threshold {ec.tp_proximity_threshold} (must be > 0)"
                    )
                if ec.reversal_trigger <= 0:
                    errors.append(
                        f"{level_name}: Exit condition '{ec.signal_name}' has invalid reversal_trigger {ec.reversal_trigger} (must be > 0)"
                    )
        
        return errors


class StrategyValidator:
    """
    Advanced strategy validator with NautilusTrader compatibility
    Provides multiple validation levels and comprehensive checks
    """
    
    VALID_LOGICS = ["AND", "OR"]
    MAX_RECOMMENDED_BLOCKS = 15
    MAX_RECOMMENDED_SIGNALS_PER_BLOCK = 10
    
    def __init__(self):
        """Initialize validator with rules"""
        self.rules = self._initialize_rules()
        self.dependency_resolver = SignalDependencyResolver()
        self.exit_validator = ExitConditionValidator()
        
    def _initialize_rules(self) -> List[ValidationRule]:
        """Initialize validation rules"""
        return [
            ValidationRule(
                name="strategy_has_name",
                description="Strategy must have a name",
                level=ValidationLevel.BASIC
            ),
            ValidationRule(
                name="strategy_has_blocks",
                description="Strategy must have at least one block",
                level=ValidationLevel.BASIC
            ),
            ValidationRule(
                name="blocks_have_signals",
                description="Each block must have at least one signal",
                level=ValidationLevel.BASIC
            ),
            ValidationRule(
                name="valid_logic",
                description="Block and signal logic must be valid (AND/OR)",
                level=ValidationLevel.STANDARD
            ),
            ValidationRule(
                name="timing_constraints_valid",
                description="Timing constraints must be properly configured",
                level=ValidationLevel.STANDARD
            ),
            ValidationRule(
                name="no_duplicates",
                description="No duplicate block or signal names",
                level=ValidationLevel.STANDARD
            ),
            ValidationRule(
                name="no_circular_dependencies",
                description="No circular timing dependencies",
                level=ValidationLevel.STRICT
            ),
        ]
        
    def validate(
        self,
        config: StrategyConfig,
        level: ValidationLevel = ValidationLevel.STANDARD
    ) -> ValidationResult:
        """
        Validate strategy configuration
        
        Args:
            config: Strategy configuration to validate
            level: Validation strictness level
            
        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        
        # Always run BASIC checks
        errors.extend(self._validate_basic(config))
        
        # Run STANDARD checks if level >= STANDARD
        if level.value in [ValidationLevel.STANDARD.value, ValidationLevel.STRICT.value]:
            errors.extend(self._validate_standard(config))
            warnings.extend(self._check_warnings(config))
            
        # Run STRICT checks if level == STRICT
        if level == ValidationLevel.STRICT:
            errors.extend(self._validate_strict(config))
            
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
        
    def _validate_basic(self, config: StrategyConfig) -> List[str]:
        """Basic structural validation"""
        errors = []
        
        # Check strategy has name
        if not config.name or config.name.strip() == "":
            errors.append("Strategy must have a name")
            
        # Check strategy has blocks
        if not config.blocks or len(config.blocks) == 0:
            errors.append("Strategy must have at least one block")
            return errors  # Can't continue without blocks
            
        # Check each block has signals
        for block in config.blocks:
            if not block.signals or len(block.signals) == 0:
                errors.append(f"Block '{block.name}' must have at least one signal")
                
        return errors
        
    def _validate_standard(self, config: StrategyConfig) -> List[str]:
        """Standard validation checks"""
        errors = []
        
        # Validate block and signal logic
        for block in config.blocks:
            if block.logic not in self.VALID_LOGICS:
                errors.append(f"Block '{block.name}' has invalid logic '{block.logic}'. Must be AND or OR")
                
            for signal in block.signals:
                if signal.logic not in self.VALID_LOGICS:
                    errors.append(
                        f"Signal '{signal.name}' in block '{block.name}' has invalid logic '{signal.logic}'. Must be AND or OR"
                    )
                    
        # Validate timing constraints
        errors.extend(self._validate_timing_constraints(config))
        
        # Check for duplicates
        errors.extend(self._check_duplicates(config))
        
        # Validate exit conditions (Sprint 1.8 Task 1.8.35)
        errors.extend(self.exit_validator.validate_exit_conditions(config))
        
        return errors
        
    def _validate_strict(self, config: StrategyConfig) -> List[str]:
        """Strict validation for production"""
        errors = []
        
        # Check for circular dependencies
        try:
            graph = self.dependency_resolver.build_graph(config)
            if graph.has_circular_dependency():
                errors.append("Strategy has circular timing dependencies")
        except Exception as e:
            errors.append(f"Error checking dependencies: {str(e)}")
            
        return errors
        
    def _validate_timing_constraints(self, config: StrategyConfig) -> List[str]:
        """Validate timing constraints"""
        errors = []
        
        for block in config.blocks:
            for signal in block.signals:
                constraint = signal.timing_constraint
                
                if constraint:
                    # Check reference is not empty
                    if not constraint.reference or constraint.reference.strip() == "":
                        errors.append(
                            f"Signal '{signal.name}' in block '{block.name}' has timing constraint with empty reference"
                        )
                        
                    # Check max_candles is positive
                    if constraint.max_candles <= 0:
                        errors.append(
                            f"Signal '{signal.name}' in block '{block.name}' has invalid max_candles ({constraint.max_candles}). Must be > 0"
                        )
                        
                    # Check reference signal exists in same block
                    signal_names = [s.name for s in block.signals]
                    if constraint.reference and constraint.reference not in signal_names:
                        errors.append(
                            f"Signal '{signal.name}' in block '{block.name}' references non-existent signal '{constraint.reference}'"
                        )
                        
        return errors
        
    def _check_duplicates(self, config: StrategyConfig) -> List[str]:
        """Check for duplicate block and signal names"""
        errors = []
        
        # Check duplicate block names
        block_names = [block.name for block in config.blocks]
        if len(block_names) != len(set(block_names)):
            duplicates = [name for name in block_names if block_names.count(name) > 1]
            errors.append(f"Duplicate block names found: {set(duplicates)}")
            
        # Check duplicate signal names within each block
        for block in config.blocks:
            signal_names = [signal.name for signal in block.signals]
            if len(signal_names) != len(set(signal_names)):
                duplicates = [name for name in signal_names if signal_names.count(name) > 1]
                errors.append(
                    f"Block '{block.name}' has duplicate signal names: {set(duplicates)}"
                )
                
        return errors
        
    def _check_warnings(self, config: StrategyConfig) -> List[str]:
        """Check for potential issues (warnings)"""
        warnings = []
        
        # Check number of blocks
        if len(config.blocks) > self.MAX_RECOMMENDED_BLOCKS:
            warnings.append(
                f"Strategy has {len(config.blocks)} blocks. Consider simplifying (recommended max: {self.MAX_RECOMMENDED_BLOCKS})"
            )
            
        # Check signals per block
        for block in config.blocks:
            if len(block.signals) > self.MAX_RECOMMENDED_SIGNALS_PER_BLOCK:
                warnings.append(
                    f"Block '{block.name}' has {len(block.signals)} signals. Consider simplifying (recommended max: {self.MAX_RECOMMENDED_SIGNALS_PER_BLOCK})"
                )
                
        return warnings
        
    def validate_nautilus_compatibility(self, config: StrategyConfig) -> ValidationResult:
        """
        Validate NautilusTrader compatibility
        
        Args:
            config: Strategy configuration
            
        Returns:
            ValidationResult for Nautilus compatibility
        """
        errors = []
        warnings = []
        
        # Check strategy name is valid Python identifier
        if not config.name.replace('_', '').isalnum():
            errors.append(
                f"Strategy name '{config.name}' must be valid Python identifier (alphanumeric + underscores)"
            )
            
        # Check block names are valid
        for block in config.blocks:
            if not block.name.replace('_', '').isalnum():
                errors.append(
                    f"Block name '{block.name}' must be valid Python identifier"
                )
                
        # Check signal names are valid
        for block in config.blocks:
            for signal in block.signals:
                if not signal.name.replace('_', '').isalnum():
                    errors.append(
                        f"Signal name '{signal.name}' must be valid Python identifier"
                    )
                    
        # Nautilus-specific warnings
        if len(config.blocks) > 10:
            warnings.append(
                "Large number of blocks may impact NautilusTrader performance"
            )
            
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )

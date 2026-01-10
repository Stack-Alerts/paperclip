"""
Strategy Builder Data Models

Type-safe models for strategy configuration.
Uses Pydantic for automatic validation and clear errors.

Author: BTC_Engine_v3
Date: 2026-01-09
Status: Phase 1 - Foundation
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import ConfigDict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime


class SignalRole(str, Enum):
    """Signal role in strategy logic"""
    FILTER = "FILTER"      # Must be true for entry
    SIGNAL = "SIGNAL"      # Primary entry trigger
    BOOSTER = "BOOSTER"    # Increases confluence
    TEST_ALL = "TEST_ALL"  # Test all permutations in optimizer


class BlockType(str, Enum):
    """Block type from registry"""
    EVENT = "EVENT"
    SIGNAL = "SIGNAL"
    CONTEXT = "CONTEXT"
    HYBRID = "HYBRID"


class StrategyCategory(str, Enum):
    """Strategy category"""
    REVERSAL = "REVERSAL"
    CONTINUATION = "CONTINUATION"
    SCALPING = "SCALPING"
    RANGE_TRADING = "RANGE_TRADING"
    BREAKOUT = "BREAKOUT"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"


class TestType(str, Enum):
    """Quick validation test types"""
    SINGLE = "SINGLE"  # Test current weights only (fastest)
    LIGHT = "LIGHT"    # Test 4-8 configs (quick optimization)
    FULL = "FULL"      # Test all 48 configs (full optimization)


class SignalConfiguration(BaseModel):
    """Configuration for a single signal"""
    signal_name: str
    signal_display_name: str
    role: SignalRole
    required: bool = True
    min_confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    
    class Config:
        use_enum_values = True


class BlockSelection(BaseModel):
    """A selected building block with its configuration"""
    model_config = ConfigDict(use_enum_values=True)
    
    block_name: str
    block_display_name: str
    block_category: str
    block_type: BlockType
    weight: int = Field(ge=0, le=100)
    weight_range: Tuple[int, int]
    enabled: bool = True
    signals: List[SignalConfiguration] = Field(default_factory=list)
    is_main_signal: bool = False
    
    @field_validator('weight_range')
    @classmethod
    def valid_weight_range(cls, v):
        """Ensure weight range is valid"""
        if len(v) != 2:
            raise ValueError(f"Weight range must be tuple of 2 values, got {len(v)}")
        if v[0] > v[1]:
            raise ValueError(f"Weight range min ({v[0]}) > max ({v[1]})")
        return v
    
    @model_validator(mode='after')
    def weight_in_range(self):
        """Ensure weight is within range"""
        min_w, max_w = self.weight_range
        if not (min_w <= self.weight <= max_w):
            raise ValueError(
                f"Weight {self.weight} not in range ({min_w}, {max_w})"
            )
        return self


class StrategyConfiguration(BaseModel):
    """Complete strategy configuration"""
    model_config = ConfigDict(use_enum_values=True)
    
    strategy_name: str  
    strategy_number: int = Field(ge=1)
    strategy_category: StrategyCategory
    side: str = "LONG"  # Trade direction: SHORT or LONG
    description: str = ""
    
    # Blocks
    main_signal_block: str
    blocks: List[BlockSelection] = Field(default_factory=list)
    
    # Parameters
    min_confluence: int = Field(default=70, ge=0, le=200)
    risk_reward_ratio: str = "1:3"
    max_bars_held: int = Field(default=1000, ge=100)
    
    # Risk Management
    risk_per_trade_pct: float = Field(default=1.0, ge=0.1, le=5.0)
    max_leverage: float = Field(default=2.0, ge=1.0, le=10.0)
    
    # Optimization
    optimization_enabled: bool = True
    test_days: int = Field(default=180, ge=30)
    optimization_configs: int = Field(default=48, ge=4)
    
    # Test permutations (for TEST_ALL signals)
    test_permutations: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    created_date: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat())
    modified_date: Optional[str] = Field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1
    
    @field_validator('risk_reward_ratio')
    @classmethod
    def valid_risk_reward(cls, v):
        """Ensure risk:reward ratio is valid format"""
        if ':' not in v:
            raise ValueError(f"Risk:reward must be in format '1:3', got '{v}'")
        try:
            risk, reward = v.split(':')
            risk_val = float(risk)
            reward_val = float(reward)
            if risk_val <= 0 or reward_val <= 0:
                raise ValueError(f"Both risk and reward must be positive")
        except ValueError as e:
            raise ValueError(f"Invalid risk:reward format '{v}': {e}")
        return v
    
    @model_validator(mode='after')
    def validate_strategy(self):
        """Validate strategy name convention and main signal block"""
        # Don't auto-fix strategy name - users control their own names
        # The filename will handle the numbering format
        
        # Validate main signal block
        if not any(b.block_name == self.main_signal_block for b in self.blocks):
            raise ValueError(
                f"Main signal block '{self.main_signal_block}' not in blocks list"
            )
        
        # Ensure main signal block is marked
        for block in self.blocks:
            if block.block_name == self.main_signal_block and not block.is_main_signal:
                block.is_main_signal = True
        
        return self


class ValidationResult(BaseModel):
    """Result of validation"""
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    
    def add_error(self, message: str):
        """Add an error"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning"""
        self.warnings.append(message)
    
    def add_suggestion(self, message: str):
        """Add a suggestion"""
        self.suggestions.append(message)
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        if self.is_valid:
            summary = "✅ Validation passed"
            if self.warnings:
                summary += f" with {len(self.warnings)} warning(s)"
            return summary
        else:
            return f"❌ Validation failed with {len(self.errors)} error(s)"


class BlockInfo(BaseModel):
    """Information about a block from registry"""
    name: str
    display_name: str
    category: str
    block_type: BlockType
    weight_range: Tuple[int, int]
    default_weight: int
    signals: List[str]
    description: str = ""
    
    class Config:
        use_enum_values = True


class SignalInfo(BaseModel):
    """Information about a signal"""
    name: str
    display_name: str
    description: str = ""
    tier_type: str = ""  # 'fixed', 'scaled', 'quality_thresholds'
    max_points: int = 0


class StrategyMetadata(BaseModel):
    """Metadata for a registered strategy"""
    number: int
    name: str
    category: StrategyCategory
    created_date: str
    modified_date: str
    file_path: str
    config_path: str
    version: int = 1
    status: str = "DRAFT"  # DRAFT, VALIDATED, OPTIMIZED, LIVE
    description: str = ""
    
    class Config:
        use_enum_values = True


class QuickTestResult(BaseModel):
    """Results from quick validation test"""
    test_passed: bool
    test_type: TestType
    test_days: int
    
    # Basic Metrics
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    net_pnl: float = 0.0
    net_pnl_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    
    # Trade Analysis
    avg_trade_duration: str = ""
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Recommendation
    recommendation: str = "NEEDS_WORK"  # 'PROMISING', 'NEEDS_WORK', 'FAILED'
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    
    # Full Results (optional)
    detailed_results: Optional[Dict] = None
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        if self.recommendation == 'PROMISING':
            return f"✅ Strategy shows promise! {self.total_trades} trades, {self.win_rate:.1f}% win rate"
        elif self.recommendation == 'NEEDS_WORK':
            return f"⚠️ Needs improvement. {', '.join(self.issues) if self.issues else 'Review metrics'}"
        else:
            return f"❌ Strategy failed. {', '.join(self.issues) if self.issues else 'Poor performance'}"
    
    @field_validator('recommendation')
    @classmethod
    def valid_recommendation(cls, v):
        """Ensure recommendation is valid"""
        valid = ['PROMISING', 'NEEDS_WORK', 'FAILED']
        if v not in valid:
            raise ValueError(f"Recommendation must be one of {valid}, got '{v}'")
        return v
    
    model_config = ConfigDict(use_enum_values=True)

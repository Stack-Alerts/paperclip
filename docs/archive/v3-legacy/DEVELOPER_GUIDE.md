# BTC Scalp Bot V10 - Developer Guide

**Version**: 10.0  
**Last Updated**: December 16, 2025  
**Audience**: Developers extending the framework  

---

## Table of Contents

1. [Introduction](#introduction)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Core Concepts](#core-concepts)
5. [Creating Custom Layers](#creating-custom-layers)
6. [Creating Custom Strategies](#creating-custom-strategies)
7. [Extending the Indicator Engine](#extending-the-indicator-engine)
8. [Adding CLI Commands](#adding-cli-commands)
9. [Testing Guidelines](#testing-guidelines)
10. [Best Practices](#best-practices)
11. [Common Patterns](#common-patterns)
12. [Debugging Tips](#debugging-tips)

---

## Introduction

### Purpose of This Guide

This guide teaches developers how to extend the BTC Scalp Bot V10 framework by adding:
- New analysis layers
- Custom trading strategies
- Additional indicators
- CLI commands
- Custom features

### Prerequisites

**Required Knowledge**:
- Python 3.12+ programming
- Object-oriented programming (OOP)
- Pandas/NumPy for data manipulation
- Basic trading concepts
- Git version control

**Recommended Knowledge**:
- Machine learning basics
- Technical analysis
- Testing with pytest
- Docker (for deployment)

### Framework Philosophy

The framework is built on these principles:
1. **Plugin Architecture**: Easy to add new components
2. **Interface-Based**: Components communicate via well-defined interfaces
3. **Factory Pattern**: Dynamic component creation
4. **Separation of Concerns**: Each module has a specific purpose
5. **Testability**: All components can be unit tested

---

## Development Environment Setup

### 1. Clone and Install

```bash
# Clone repository
git clone <repository-url>
cd BTC_Engine_LLM

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### 2. Install Development Tools

```bash
# Testing
pip install pytest pytest-cov pytest-asyncio

# Code quality
pip install black mypy pylint flake8

# Documentation
pip install sphinx sphinx-rtd-theme
```

### 3. IDE Setup (VS Code Recommended)

**Recommended Extensions**:
- Python (Microsoft)
- Pylance
- Python Test Explorer
- GitLens
- autoDocstring

**VS Code Settings** (`.vscode/settings.json`):
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true
}
```

### 4. Pre-commit Hooks (Optional)

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install
```

**`.pre-commit-config.yaml`**:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

---

## Project Structure

### Directory Layout

```
BTC_Engine_LLM/
├── config/                    # Configuration files
│   ├── base_config.py        # Base configuration
│   ├── strategies/           # Strategy configurations
│   └── *.yaml                # YAML configs
├── data/                      # Data storage
│   ├── raw/                  # Raw market data
│   ├── processed/            # Processed data
│   ├── models/               # Trained models
│   └── reports/              # Generated reports
├── docs/                      # Documentation
├── scripts/                   # Entry point scripts
│   └── bot.py                # Main CLI script
├── src/                       # Source code
│   ├── backtesting/          # Backtesting engine
│   ├── cli/                  # CLI commands
│   ├── core/                 # Core components
│   │   ├── framework/        # Plugin architecture
│   │   ├── data_pipeline.py
│   │   ├── indicator_engine.py
│   │   └── ...
│   ├── layers/               # Analysis layers
│   │   ├── layer1_traditional.py
│   │   ├── layer2_volume_delta.py
│   │   └── ...
│   ├── trading/              # Trading components
│   ├── reporting/            # Reporting tools
│   └── utils/                # Utilities
├── tests/                     # Test files
│   ├── unit/
│   ├── integration/
│   └── performance/
├── requirements.txt           # Dependencies
└── README.md                 # Main documentation
```

### Key Modules

| Module | Purpose | Extensibility |
|--------|---------|---------------|
| `src/core/framework/` | Plugin architecture | High |
| `src/layers/` | Analysis layers | High |
| `config/strategies/` | Trading strategies | High |
| `src/cli/` | CLI commands | Medium |
| `src/core/indicator_engine.py` | Indicators | Medium |
| `src/backtesting/` | Backtesting | Low |
| `src/trading/` | Trade execution | Low |

---

## Core Concepts

### 1. Base Layer

All analysis layers inherit from `BaseLayer`:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd

class BaseLayer(ABC):
    """Base class for all analysis layers"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize layer with configuration
        
        Args:
            config: Layer configuration dictionary
        """
        self.config = config
        self.name = self.__class__.__name__
        self.logger = get_logger(self.name)
    
    @abstractmethod
    def generate_signal(
        self, 
        data: pd.DataFrame, 
        indicators: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate trading signal from data and indicators
        
        Args:
            data: OHLCV price data
            indicators: Calculated technical indicators
            
        Returns:
            Signal dictionary with keys:
                - direction: 'buy', 'sell', or 'neutral'
                - confidence: float 0-1
                - strength: float 0-1
                - metadata: dict with additional info
        """
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Validate input data has required columns and length
        
        Args:
            data: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        return all(col in data.columns for col in required_cols)
```

### 2. Signal Structure

Signals are dictionaries with standard format:

```python
{
    'direction': 'buy',      # 'buy', 'sell', or 'neutral'
    'confidence': 0.75,      # 0.0 to 1.0
    'strength': 0.82,        # 0.0 to 1.0
    'timestamp': datetime,   # Signal generation time
    'metadata': {            # Layer-specific info
        'indicators_used': ['RSI', 'MACD'],
        'score': 0.65,
        'reason': 'EMA crossover with strong momentum'
    }
}
```

### 3. Base Strategy

Trading strategies inherit from `BaseStrategy`:

```python
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """Base class for trading strategies"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.compositor = LayerCompositor(config)
    
    @abstractmethod
    def should_enter(
        self, 
        signal: Dict[str, Any], 
        data: pd.DataFrame
    ) -> bool:
        """Decide if should enter trade"""
        pass
    
    @abstractmethod
    def should_exit(
        self, 
        position: Dict[str, Any], 
        signal: Dict[str, Any]
    ) -> bool:
        """Decide if should exit trade"""
        pass
    
    def calculate_position_size(
        self, 
        capital: float, 
        risk_per_trade: float
    ) -> float:
        """Calculate position size"""
        return capital * risk_per_trade
```

### 4. Factory Pattern

Components are registered and created via factories:

```python
class LayerFactory:
    """Factory for creating analysis layers"""
    
    _registry = {}
    
    @classmethod
    def register(cls, name: str, layer_class: type):
        """Register a layer class"""
        cls._registry[name] = layer_class
    
    @classmethod
    def create(cls, name: str, config: Dict) -> BaseLayer:
        """Create layer instance"""
        if name not in cls._registry:
            raise ValueError(f"Layer {name} not registered")
        return cls._registry[name](../../v3/archived/legacy/config)
    
    @classmethod
    def list_layers(cls) -> list:
        """List registered layers"""
        return list(cls._registry.keys())

# Register layers
LayerFactory.register('layer1', Layer1Traditional)
LayerFactory.register('layer2', Layer2VolumeDelta)
# ...
```

---

## Creating Custom Layers

### Step 1: Create Layer File

Create file `src/layers/layer6_custom.py`:

```python
"""
Layer 6: Custom Analysis Layer
Your description here
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from src.core.framework.base_layer import BaseLayer
from src.utils.logger import get_logger

class Layer6Custom(BaseLayer):
    """Custom analysis layer"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize custom layer
        
        Args:
            config: Configuration dictionary with:
                - parameter1: Description
                - parameter2: Description
        """
        super().__init__(config)
        
        # Extract parameters
        self.parameter1 = config.get('parameter1', default_value)
        self.parameter2 = config.get('parameter2', default_value)
        
        self.logger.info(
            f"Layer6Custom initialized",
            extra={
                'parameter1': self.parameter1,
                'parameter2': self.parameter2
            }
        )
    
    def generate_signal(
        self, 
        data: pd.DataFrame, 
        indicators: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Generate trading signal using custom logic
        
        Args:
            data: OHLCV price data
            indicators: Technical indicators
            
        Returns:
            Signal dictionary
        """
        # Validate inputs
        if not self.validate_data(data):
            raise ValueError("Invalid data format")
        
        if len(data) < self.parameter1:
            raise ValueError(f"Insufficient data: need {self.parameter1} bars")
        
        try:
            # Your custom analysis logic
            signal_value = self._calculate_signal(data, indicators)
            
            # Determine direction
            if signal_value > 0.3:
                direction = 'buy'
            elif signal_value < -0.3:
                direction = 'sell'
            else:
                direction = 'neutral'
            
            # Calculate confidence
            confidence = abs(signal_value)
            
            # Build signal
            signal = {
                'direction': direction,
                'confidence': min(confidence, 1.0),
                'strength': abs(signal_value),
                'timestamp': data.index[-1],
                'metadata': {
                    'signal_value': signal_value,
                    'parameter1': self.parameter1,
                    'indicators_used': ['custom1', 'custom2']
                }
            }
            
            self.logger.debug(
                f"Signal generated: {direction}",
                extra={'confidence': confidence}
            )
            
            return signal
            
        except Exception as e:
            self.logger.error(f"Signal generation failed: {e}")
            # Return neutral signal on error
            return self._neutral_signal()
    
    def _calculate_signal(
        self, 
        data: pd.DataFrame, 
        indicators: pd.DataFrame
    ) -> float:
        """
        Custom signal calculation logic
        
        Returns:
            Signal value between -1 and 1
        """
        # Example: Combine multiple indicators
        signal = 0.0
        
        # Component 1: Price momentum
        returns = data['close'].pct_change(self.parameter1)
        momentum = returns.iloc[-1]
        signal += momentum * 0.4
        
        # Component 2: Custom indicator
        if 'custom_indicator' in indicators:
            custom = indicators['custom_indicator'].iloc[-1]
            signal += custom * 0.6
        
        return np.clip(signal, -1, 1)
    
    def _neutral_signal(self) -> Dict[str, Any]:
        """Return neutral signal"""
        return {
            'direction': 'neutral',
            'confidence': 0.0,
            'strength': 0.0,
            'timestamp': pd.Timestamp.now(),
            'metadata': {}
        }
```

### Step 2: Register Layer

In `src/layers/__init__.py`, add:

```python
from src.layers.layer6_custom import Layer6Custom
from src.core.framework.layer_factory import LayerFactory

# Register custom layer
LayerFactory.register('layer6', Layer6Custom)
```

### Step 3: Configure Layer

Create configuration in `config/layer_presets/layer6_config.yaml`:

```yaml
layer6:
  enabled: true
  parameter1: 20
  parameter2: 0.5
  weight: 0.10  # Weight in compositor
```

### Step 4: Test Layer

Create test file `tests/test_layer6_custom.py`:

```python
import pytest
import pandas as pd
import numpy as np
from src.layers.layer6_custom import Layer6Custom

@pytest.fixture
def sample_data():
    """Create sample OHLCV data"""
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')
    data = pd.DataFrame({
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.rand(100) * 1000
    }, index=dates)
    return data

@pytest.fixture
def sample_indicators():
    """Create sample indicators"""
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')
    indicators = pd.DataFrame({
        'custom_indicator': np.random.randn(100) * 0.5
    }, index=dates)
    return indicators

def test_layer6_initialization():
    """Test layer initialization"""
    config = {'parameter1': 20, 'parameter2': 0.5}
    layer = Layer6Custom(config)
    assert layer.parameter1 == 20
    assert layer.parameter2 == 0.5

def test_layer6_signal_generation(sample_data, sample_indicators):
    """Test signal generation"""
    config = {'parameter1': 20, 'parameter2': 0.5}
    layer = Layer6Custom(config)
    
    signal = layer.generate_signal(sample_data, sample_indicators)
    
    # Validate signal structure
    assert 'direction' in signal
    assert 'confidence' in signal
    assert 'strength' in signal
    assert signal['direction'] in ['buy', 'sell', 'neutral']
    assert 0 <= signal['confidence'] <= 1

def test_layer6_insufficient_data():
    """Test error handling with insufficient data"""
    config = {'parameter1': 200, 'parameter2': 0.5}
    layer = Layer6Custom(config)
    
    # Create small dataset
    small_data = pd.DataFrame({
        'open': [100, 101],
        'high': [102, 103],
        'low': [99, 100],
        'close': [101, 102],
        'volume': [1000, 1100]
    })
    
    with pytest.raises(ValueError):
        layer.generate_signal(small_data, pd.DataFrame())
```

Run tests:
```bash
pytest tests/test_layer6_custom.py -v
```

### Step 5: Integrate with Compositor

Update compositor configuration to include new layer:

```python
# In your strategy config
layer_weights = {
    'layer1': 0.20,
    'layer2': 0.15,
    'layer3': 0.10,
    'layer4': 0.20,
    'layer5': 0.25,
    'layer6': 0.10  # Your new layer
}
```

---

## Creating Custom Strategies

### Step 1: Create Strategy File

Create `config/strategies/my_custom_strategy.py`:

```python
"""
Custom Trading Strategy
Description of your strategy logic
"""

from typing import Dict, Any
import pandas as pd
from src.core.framework.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    """Custom trading strategy implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize strategy
        
        Args:
            config: Strategy configuration
        """
        super().__init__(config)
        
        # Strategy parameters
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        self.min_layers = config.get('min_layers', 3)
        self.risk_per_trade = config.get('risk_per_trade', 0.02)
        
        # Layer weights
        self.layer_weights = config.get('layer_weights', {
            'layer1': 0.25,
            'layer2': 0.15,
            'layer3': 0.10,
            'layer4': 0.25,
            'layer5': 0.25
        })
    
    def should_enter(
        self, 
        signal: Dict[str, Any], 
        data: pd.DataFrame
    ) -> bool:
        """
        Determine if should enter trade
        
        Args:
            signal: Composite signal from compositor
            data: Current market data
            
        Returns:
            True if should enter, False otherwise
        """
        # Check confidence threshold
        if signal['confidence'] < self.confidence_threshold:
            return False
        
        # Check direction
        if signal['direction'] == 'neutral':
            return False
        
        # Check minimum layer agreement
        if signal.get('agreement', 0) < self.min_layers / 5:
            return False
        
        # Custom condition: Check trend alignment
        if not self._check_trend_alignment(data):
            return False
        
        # Custom condition: Check volatility
        if not self._check_volatility(data):
            return False
        
        return True
    
    def should_exit(
        self, 
        position: Dict[str, Any], 
        signal: Dict[str, Any]
    ) -> bool:
        """
        Determine if should exit trade
        
        Args:
            position: Current position info
            signal: Current signal
            
        Returns:
            True if should exit, False otherwise
        """
        # Exit on opposite signal
        if signal['direction'] != position['direction']:
            if signal['confidence'] > 0.6:
                return True
        
        # Exit if stop-loss hit
        if self._check_stop_loss(position):
            return True
        
        # Exit if take-profit hit
        if self._check_take_profit(position):
            return True
        
        # Exit if holding too long
        if self._check_max_hold_time(position):
            return True
        
        return False
    
    def _check_trend_alignment(self, data: pd.DataFrame) -> bool:
        """Check if price aligns with trend"""
        # Example: Simple moving average trend
        if len(data) < 50:
            return True
        
        sma_50 = data['close'].rolling(50).mean().iloc[-1]
        current_price = data['close'].iloc[-1]
        
        return current_price > sma_50
    
    def _check_volatility(self, data: pd.DataFrame) -> bool:
        """Check if volatility is within acceptable range"""
        if len(data) < 20:
            return True
        
        returns = data['close'].pct_change()
        volatility = returns.rolling(20).std().iloc[-1]
        
        # Only trade if volatility is moderate
        return 0.01 < volatility < 0.05
    
    def _check_stop_loss(self, position: Dict[str, Any]) -> bool:
        """Check if stop-loss is hit"""
        current_price = position.get('current_price')
        entry_price = position.get('entry_price')
        stop_loss = position.get('stop_loss')
        
        if position['direction'] == 'buy':
            return current_price <= stop_loss
        else:
            return current_price >= stop_loss
    
    def _check_take_profit(self, position: Dict[str, Any]) -> bool:
        """Check if take-profit is hit"""
        current_price = position.get('current_price')
        take_profit = position.get('take_profit')
        
        if position['direction'] == 'buy':
            return current_price >= take_profit
        else:
            return current_price <= take_profit
    
    def _check_max_hold_time(self, position: Dict[str, Any]) -> bool:
        """Check if exceeded maximum hold time"""
        max_hold_bars = 24  # 24 hours for 1h timeframe
        bars_held = position.get('bars_held', 0)
        return bars_held >= max_hold_bars

# Strategy configuration
STRATEGY_CONFIG = {
    'name': 'my_custom',
    'confidence_threshold': 0.7,
    'min_layers': 3,
    'risk_per_trade': 0.02,
    'layer_weights': {
        'layer1': 0.25,
        'layer2': 0.15,
        'layer3': 0.10,
        'layer4': 0.25,
        'layer5': 0.25
    }
}
```

### Step 2: Register Strategy

In `config/strategies/__init__.py`:

```python
from config.strategies.my_custom_strategy import MyCustomStrategy, STRATEGY_CONFIG

# Register strategy
from src.core.framework.strategy_factory import StrategyFactory
StrategyFactory.register('my_custom', MyCustomStrategy)
```

### Step 3: Test Strategy

```bash
# Backtest your strategy
python3 scripts/bot.py backtest --config my_custom --days 90 --capital 10000
```

---

## Extending the Indicator Engine

### Adding Custom Indicator

In `src/core/indicator_engine.py`, add your indicator:

```python
def add_custom_indicator(self, data: pd.DataFrame) -> pd.DataFrame:
    """
    Add custom indicator to dataframe
    
    Args:
        data: OHLCV dataframe
        
    Returns:
        DataFrame with custom_indicator column added
    """
    # Example: Custom momentum indicator
    # Combines price change with volume
    
    price_change = data['close'].pct_change(20)
    volume_ratio = data['volume'] / data['volume'].rolling(20).mean()
    
    data['custom_indicator'] = price_change * volume_ratio
    
    # Normalize to -1 to 1 range
    data['custom_indicator'] = (
        2 * (data['custom_indicator'] - data['custom_indicator'].min()) / 
        (data['custom_indicator'].max() - data['custom_indicator'].min()) - 1
    )
    
    return data
```

Register in indicator groups:

```python
def add_indicators(self, data: pd.DataFrame, groups: list = None) -> pd.DataFrame:
    # ... existing code ...
    
    if groups is None or 'custom' in groups:
        data = self.add_custom_indicator(data)
    
    return data
```

---

## Adding CLI Commands

### Step 1: Create Command Module

Create `src/cli/my_command.py`:

```python
"""
Custom CLI command implementation
"""

import click
from src.utils.logger import get_logger

logger = get_logger(__name__)

@click.command()
@click.option('--param1', type=str, required=True, help='Parameter 1')
@click.option('--param2', type=int, default=10, help='Parameter 2')
@click.option('--verbose', is_flag=True, help='Verbose output')
def my_command(param1, param2, verbose):
    """
    Custom command description
    
    Example usage:
        python scripts/bot.py my-command --param1 value --param2 20
    """
    try:
        logger.info(f"Running my_command with {param1}, {param2}")
        
        # Your command logic here
        result = perform_custom_operation(param1, param2)
        
        # Display results
        if verbose:
            display_detailed_results(result)
        else:
            display_summary(result)
        
        logger.info("Command completed successfully")
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        raise click.ClickException(str(e))

def perform_custom_operation(param1, param2):
    """Your custom operation logic"""
    # Implementation
    return result

def display_detailed_results(result):
    """Display detailed output"""
    click.echo("Detailed Results:")
    # Format and display
    
def display_summary(result):
    """Display summary output"""
    click.echo(f"Summary: {result}")
```

### Step 2: Register Command

In `src/cli/commands.py`:

```python
from src.cli.my_command import my_command

# In the main CLI group
@click.group()
def cli():
    """BTC Scalp Bot CLI"""
    pass

# Register commands
cli.add_command(backtest)
cli.add_command(paper)
# ... existing commands ...
cli.add_command(my_command)  # Add your command
```

---

## Testing Guidelines

### Unit Test Template

```python
import pytest
import pandas as pd
import numpy as np
from your_module import YourClass

class TestYourClass:
    """Test suite for YourClass"""
    
    @pytest.fixture
    def instance(self):
        """Create instance for testing"""
        config = {'param1': 'value1'}
        return YourClass(config)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data"""
        return pd.DataFrame({
            'close': np.random.randn(100) + 100
        })
    
    def test_initialization(self, instance):
        """Test initialization"""
        assert instance.param1 == 'value1'
    
    def test_method(self, instance, sample_data):
        """Test specific method"""
        result = instance.method(sample_data)
        assert result is not None
    
    def test_error_handling(self, instance):
        """Test error conditions"""
        with pytest.raises(ValueError):
            instance.method(invalid_input)
```

### Integration Test Template

```python
def test_end_to_end_flow():
    """Test complete workflow"""
    # 1. Setup
    data_pipeline = DataPipeline()
    indicator_engine = IndicatorEngine()
    layer = CustomLayer(config)
    
    # 2. Execute
    data = data_pipeline.fetch_data('BTC/USDT', '1h', days=30)
    indicators = indicator_engine.add_indicators(data)
    signal = layer.generate_signal(data, indicators)
    
    # 3. Verify
    assert signal['direction'] in ['buy', 'sell', 'neutral']
    assert 0 <= signal['confidence'] <= 1
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_layer6_custom.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_layer6_custom.py::test_layer6_initialization
```

---

## Best Practices

### 1. Code Style

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for all functions/classes
- Keep functions small and focused
- Use meaningful variable names

```python
def calculate_signal_strength(
    price_data: pd.DataFrame,
    window: int = 20
) -> float:
    """
    Calculate signal strength based on price momentum
    
    Args:
        price_data: DataFrame with OHLCV data
        window: Lookback period for calculation
        
    Returns:
        Signal strength between 0 and 1
        
    Raises:
        ValueError: If insufficient data
    """
    if len(price_data) < window:
        raise ValueError(f"Need at least {window} bars")
    
    momentum = price_data['close'].pct_change(window).iloc[-1]
    return abs(momentum)
```

### 2. Error Handling

```python
def safe_operation(data):
    """Always handle errors gracefully"""
    try:
        result = risky_operation(data)
        return result
    except InsufficientDataError as e:
        logger.warning(f"Insufficient data: {e}")
        return default_value
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return fallback_value
```

### 3. Logging

```python
# Use structured logging
logger.info(
    "Signal generated",
    extra={
        'direction': signal['direction'],
        'confidence': signal['confidence'],
        'layer': 'layer6'
    }
)

# Different log levels
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
```

### 4. Configuration

```python
# Use configuration files
class MyLayer(BaseLayer):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Extract with defaults
        self.param1 = config.get('param1', default_value)
        self.param2 = config.get('param2', default_value)
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration parameters"""
        if self.param1 < 0:
            raise ValueError("param1 must be positive")
```

### 5. Documentation

```python
class WellDocumentedLayer(BaseLayer):
    """
    Brief description of what this layer does
    
    This layer analyzes [specific aspect] to generate trading signals
    based on [methodology].
    
    Attributes:
        param1 (int): Description of param1
        param2 (float): Description of param2
        
    Example:
        >>> config = {'param1': 20, 'param2': 0.5}
        >>> layer = WellDocumentedLayer(config)
        >>> signal = layer.generate_signal(data, indicators)
    """
    pass
```

---

## Common Patterns

### 1. Lazy Initialization

```python
class LazyComponent:
    def __init__(self, config):
        self.config = config
        self._expensive_resource = None
    
    @property
    def expensive_resource(self):
        """Initialize only when needed"""
        if self._expensive_resource is None:
            self._expensive_resource = load_expensive_resource()
        return self._expensive_resource
```

### 2. Caching Results

```python
from functools import lru_cache

class CachedCalculations:
    @lru_cache(maxsize=128)
    def expensive_calculation(self, param):
        """Cache results of expensive calculations"""
        return complex_computation(param)
```

### 3. Context Managers

```python
class ResourceManager:
    def __enter__(self):
        self.resource = acquire_resource()
        return self.resource
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        release_resource(self.resource)

# Usage
with ResourceManager() as resource:
    use_resource(resource)
```

---

## Debugging Tips

### 1. Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Use IPython for Interactive Debugging

```python
# Add breakpoint in code
import IPython; IPython.embed()

# Or use pdb
import pdb; pdb.set_trace()
```

### 3. Profile Performance

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumtime')
stats.print_stats(20)  # Top 20 functions
```

### 4. Memory Profiling

```python
from memory_profiler import profile

@profile
def memory_intensive_function():
    # Your code
    pass
```

### 5. Validate Data at Each Step

```python
def process_data(data):
    # Check input
    assert not data.empty, "Empty dataframe"
    assert 'close' in data.columns, "Missing close column"
    
    # Process
    result = transform(data)
    
    # Check output
    assert not result.isnull().any().any(), "NaN values in result"
    
    return result
```

---

## Conclusion

This guide covered:
- ✅ Setting up development environment
- ✅ Understanding project structure
- ✅ Creating custom layers
- ✅ Creating custom strategies
- ✅ Extending indicator engine
- ✅ Adding CLI commands
- ✅ Testing guidelines
- ✅ Best practices
- ✅ Common patterns
- ✅ Debugging tips

**Next Steps**:
1. Read the [Architecture Documentation](ARCHITECTURE.md)
2. Study existing layer implementations
3. Create your first custom layer
4. Write tests for your code
5. Contribute back to the project!

**Resources**:
- [Python Style Guide (PEP 8)](https://pep8.org/)
- [Pandas Documentation](https://pandas.pydata.org/)
- [Pytest Documentation](https://docs.pytest.org/)

---

*Last Updated: December 16, 2025*  
*Version: 10.0*  
*For Developers*

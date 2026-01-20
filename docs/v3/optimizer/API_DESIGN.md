# Optimizer V3 - API Design Specification
**Complete API architecture for Strategy Analyzer and related components**

**Version**: 1.0.0  
**Date**: 2026-01-20  
**Status**: ✅ Complete

## 📋 Table of Contents
1. [OptimizerV3 API](#optimizerv3-api)
2. [StrategyAnalyzer API](#strategyanalyzer-api)
3. [ParallelExecutor API](#parallelexecutor-api)
4. [ResultsRanker API](#resultsranker-api)
5. [API Versioning Strategy](#api-versioning-strategy)
6. [Integration Patterns](#integration-patterns)

---

## 1. OptimizerV3 API

### 1.1 Core Class

```python
class OptimizerV3:
    """
    Main optimizer orchestration class.
    
    Coordinates strategy analysis, parameter extraction, optimization space
    generation, parallel execution, and results ranking.
    """
    
    def __init__(
        self,
        strategy_path: str | Path,
        data_path: str | Path,
        logger: Optional[OptimizerLogger] = None,
        max_workers: int = -1,
        max_combinations: int = 10000
    ):
        """
        Initialize Optimizer V3.
        
        Args:
            strategy_path: Path to strategy JSON file
            data_path: Path to market data
            logger: Optional logger instance
            max_workers: Maximum parallel workers (-1 = all CPU cores)
            max_combinations: Maximum optimization combinations
        """
        pass
    
    def analyze_strategy(self) -> Dict[str, Any]:
        """
        Analyze strategy and extract parameters.
        
        Returns:
            Dictionary with strategy analysis results including:
            - strategy_name: str
            - timing_parameters: List[Dict]
            - recheck_parameters: List[Dict]
            - risk_parameters: List[Dict]
            - dependency_graph: Dict
            - total_parameters: int
        """
        pass
    
    def generate_optimization_space(
        self,
        strategy: str = 'grid',
        custom_ranges: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate optimization parameter space.
        
        Args:
            strategy: Sampling strategy ('grid', 'random', 'adaptive')
            custom_ranges: Optional custom parameter ranges
            
        Returns:
            List of parameter configuration dictionaries
        """
        pass
    
    def optimize(
        self,
        start_date: str,
        end_date: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Execute full optimization workflow.
        
        Args:
            start_date: Start date for backtest (YYYY-MM-DD)
            end_date: End date for backtest (YYYY-MM-DD)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with optimization results:
            - best_config: Dict
            - all_results: List[Dict]
            - statistics: Dict
            - execution_time: float
        """
        pass
    
    def get_best_config(self, metric: str = 'sharpe_ratio') -> Dict[str, Any]:
        """
        Get best configuration by metric.
        
        Args:
            metric: Optimization metric (sharpe_ratio, total_return, win_rate, etc.)
            
        Returns:
            Best configuration dictionary
        """
        pass
```

### 1.2 Usage Example

```python
from src.optimizer_v3 import OptimizerV3

# Initialize optimizer
optimizer = OptimizerV3(
    strategy_path='user_strategies/hod_rejection.json',
    data_path='data/btc_1h.parquet',
    max_workers=8,
    max_combinations=5000
)

# Analyze strategy
analysis = optimizer.analyze_strategy()
print(f"Found {analysis['total_parameters']} optimizable parameters")

# Generate optimization space
configs = optimizer.generate_optimization_space(strategy='adaptive')
print(f"Generated {len(configs)} configurations")

# Run optimization
results = optimizer.optimize(
    start_date='2024-01-01',
    end_date='2024-12-31',
    progress_callback=lambda p: print(f"Progress: {p}%")
)

# Get best configuration
best = optimizer.get_best_config(metric='sharpe_ratio')
print(f"Best Sharpe: {best['metrics']['sharpe_ratio']:.2f}")
```

---

## 2. StrategyAnalyzer API

### 2.1 Core Class

```python
class StrategyAnalyzer:
    """
    Extract and analyze optimizable parameters from strategies.
    """
    
    def __init__(
        self,
        logger: Optional[OptimizerLogger] = None,
        validator: Optional[DataValidator] = None
    ):
        """
        Initialize strategy analyzer.
        
        Args:
            logger: Optional logger instance
            validator: Optional validator instance
        """
        pass
    
    def analyze_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete strategy analysis.
        
        Args:
            strategy: Strategy configuration dictionary
            
        Returns:
            Analysis results with all extracted parameters
        """
        pass
    
    def extract_timing_parameters(
        self,
        strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract timing constraint parameters.
        
        Args:
            strategy: Strategy configuration
            
        Returns:
            List of timing parameter dictionaries
        """
        pass
    
    def extract_recheck_parameters(
        self,
        strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract recheck configuration parameters.
        
        Args:
            strategy: Strategy configuration
            
        Returns:
            List of recheck parameter dictionaries
        """
        pass
    
    def extract_risk_parameters(
        self,
        strategy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract risk management parameters.
        
        Args:
            strategy: Strategy configuration
            
        Returns:
            List of risk parameter dictionaries
        """
        pass
    
    def extract_all_parameters(
        self,
        strategy: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract all optimizable parameters.
        
        Args:
            strategy: Strategy configuration
            
        Returns:
            Dictionary categorizing all parameters by type
        """
        pass
    
    def set_default_ranges(self, ranges: Dict[str, Any]) -> None:
        """
        Update default optimization ranges.
        
        Args:
            ranges: Dictionary of default ranges
        """
        pass
    
    def get_parameter_summary(
        self,
        parameters: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Get parameter statistics.
        
        Args:
            parameters: Categorized parameters
            
        Returns:
            Summary statistics dictionary
        """
        pass
```

### 2.2 Parameter Dictionary Structure

```python
# Timing Parameter
{
    'block': str,              # Block name
    'parameter': str,          # Parameter name (e.g., 'max_candles')
    'type': 'timing',         # Parameter type
    'base_value': int,        # Original value
    'current_value': int,     # Current value
    'min': int,               # Minimum value for optimization
    'max': int,               # Maximum value for optimization
    'step': int,              # Step size
    'optimizable': bool       # Whether parameter can be optimized
}

# Recheck Parameter
{
    'block': str,
    'parameter': str,
    'type': 'recheck',
    'base_value': Union[int, bool],
    'current_value': Union[int, bool],
    'min': Optional[int],
    'max': Optional[int],
    'step': Optional[int],
    'options': Optional[List],  # For boolean parameters
    'optimizable': bool
}

# Risk Parameter
{
    'block': 'global',
    'parameter': str,
    'type': 'risk',
    'base_value': Decimal,
    'current_value': Decimal,
    'min': Decimal,
    'max': Decimal,
    'step': Decimal,
    'optimizable': bool
}
```

---

## 3. ParallelExecutor API

### 3.1 Core Class

```python
class ParallelExecutor:
    """
    Execute backtests in parallel with checkpoint support.
    """
    
    def __init__(
        self,
        max_workers: int = -1,
        checkpoint_dir: Optional[str | Path] = None,
        logger: Optional[OptimizerLogger] = None
    ):
        """
        Initialize parallel executor.
        
        Args:
            max_workers: Maximum parallel workers (-1 = all cores)
            checkpoint_dir: Directory for checkpoints
            logger: Optional logger instance
        """
        pass
    
    def execute(
        self,
        strategy: Dict[str, Any],
        configurations: List[Dict[str, Any]],
        data_path: str | Path,
        start_date: str,
        end_date: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute parallel backtests.
        
        Args:
            strategy: Base strategy configuration
            configurations: List of parameter configurations to test
            data_path: Path to market data
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            progress_callback: Progress callback (current, total)
            
        Returns:
            List of backtest results
        """
        pass
    
    def save_checkpoint(self, results: List[Dict], config_index: int) -> None:
        """Save execution checkpoint"""
        pass
    
    def load_checkpoint(self) -> Tuple[List[Dict], int]:
        """Load execution checkpoint"""
        pass
    
    def clear_checkpoints(self) -> None:
        """Clear all checkpoints"""
        pass
```

### 3.2 Result Dictionary Structure

```python
# Backtest Result
{
    'configuration': Dict[str, Any],  # Parameter configuration used
    'metrics': {
        'total_return': Decimal,
        'sharpe_ratio': Decimal,
        'max_drawdown': Decimal,
        'win_rate': Decimal,
        'profit_factor': Decimal,
        'total_trades': int,
        'avg_trade_duration': float,
        'avg_win': Decimal,
        'avg_loss': Decimal
    },
    'trades': List[Dict],            # All trades executed
    'equity_curve': List[Dict],      # Equity curve data
    'execution_time': float,         # Execution time in seconds
    'errors': List[str]              # Any errors encountered
}
```

---

## 4. ResultsRanker API

### 4.1 Core Class

```python
class ResultsRanker:
    """
    Rank and filter optimization results.
    """
    
    def __init__(self, logger: Optional[OptimizerLogger] = None):
        """
        Initialize results ranker.
        
        Args:
            logger: Optional logger instance
        """
        pass
    
    def rank_results(
        self,
        results: List[Dict[str, Any]],
        metric: str = 'sharpe_ratio',
        ascending: bool = False,
        min_trades: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Rank results by metric.
        
        Args:
            results: List of backtest results
            metric: Metric to rank by
            ascending: Sort direction
            min_trades: Minimum trades for valid result
            
        Returns:
            Sorted list of results
        """
        pass
    
    def filter_results(
        self,
        results: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter results by criteria.
        
        Args:
            results: List of backtest results
            filters: Filter criteria dict
            
        Returns:
            Filtered results
        
        Example filters:
            {
                'min_sharpe': 1.5,
                'max_drawdown': -0.20,
                'min_trades': 50,
                'min_win_rate': 0.55
            }
        """
        pass
    
    def get_top_n(
        self,
        results: List[Dict[str, Any]],
        n: int = 10,
        metric: str = 'sharpe_ratio'
    ) -> List[Dict[str, Any]]:
        """
        Get top N results.
        
        Args:
            results: List of backtest results
            n: Number of top results
            metric: Metric for ranking
            
        Returns:
            Top N results
        """
        pass
    
    def generate_performance_report(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate performance statistics.
        
        Args:
            results: List of backtest results
            
        Returns:
            Performance report dictionary
        """
        pass
```

---

## 5. API Versioning Strategy

### 5.1 Versioning Scheme

**Semantic Versioning**: MAJOR.MINOR.PATCH (e.g., 1.0.0)

- **MAJOR**: Breaking API changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### 5.2 Version Headers

All API responses include version:

```python
{
    'api_version': '1.0.0',
    'component': 'OptimizerV3',
    'timestamp': '2026-01-20T12:00:00Z',
    'data': { ... }
}
```

### 5.3 Deprecation Policy

1. **Warning Period**: 2 minor versions
2. **Documentation**: Mark deprecated methods with `@deprecated` decorator
3. **Migration Guide**: Provide upgrade path documentation
4. **Backward Compatibility**: Maintain for at least 6 months

### 5.4 Version Compatibility Matrix

| Optimizer Version | NautilusTrader | Python | PyQt6 |
|------------------|----------------|--------|-------|
| 1.0.0            | ^1.0.0        | ^3.10  | ^6.4  |
| 1.1.0            | ^1.0.0        | ^3.10  | ^6.4  |
| 2.0.0            | ^1.2.0        | ^3.11  | ^6.5  |

---

## 6. Integration Patterns

### 6.1 Full Workflow Integration

```python
from src.optimizer_v3 import OptimizerV3
from src.optimizer_v3.core import StrategyAnalyzer, ParallelExecutor, ResultsRanker

# Step 1: Load and analyze strategy
analyzer = StrategyAnalyzer()
with open('strategy.json') as f:
    strategy = json.load(f)

analysis = analyzer.analyze_strategy(strategy)

# Step 2: Generate optimization space
from src.optimizer_v3.core import OptimizationSpace
opt_space = OptimizationSpace(max_combinations=1000)
configs = opt_space.generate_optimization_space(
    analyzer.extract_all_parameters(strategy),
    'adaptive'
)

# Step 3: Execute parallel backtests
executor = ParallelExecutor(max_workers=8, checkpoint_dir='checkpoints')
results = executor.execute(
    strategy=strategy,
    configurations=configs,
    data_path='data/btc_1h.parquet',
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# Step 4: Rank and filter results
ranker = ResultsRanker()
top_results = ranker.get_top_n(results, n=10, metric='sharpe_ratio')

# Step 5: Generate performance report
report = ranker.generate_performance_report(top_results)
print(f"Best Sharpe: {report['best_sharpe']:.2f}")
```

### 6.2 Error Handling Pattern

```python
from src.optimizer_v3.core.validator import ValidationError

try:
    # Validate strategy
    validator.validate_strategy(strategy)
    
    # Extract parameters
    params = analyzer.extract_all_parameters(strategy)
    
    # Generate space
    configs = opt_space.generate_optimization_space(params)
    
    # Validate space
    is_valid, errors = opt_space.validate_optimization_space(configs)
    if not is_valid:
        raise ValidationError(f"Invalid optimization space: {errors}")
    
    # Execute
    results = executor.execute(...)
    
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### 6.3 Progress Monitoring Pattern

```python
def progress_callback(current: int, total: int):
    """Progress callback for UI updates"""
    percent = (current / total) * 100
    print(f"Progress: {percent:.1f}% ({current}/{total})")
    # Update progress bar in UI
    progress_bar.setValue(percent)

# Use with executor
results = executor.execute(
    strategy=strategy,
    configurations=configs,
    data_path=data_path,
    start_date=start_date,
    end_date=end_date,
    progress_callback=progress_callback
)
```

---

## 7. API Documentation Standards

### 7.1 Docstring Format

All API methods use Google-style docstrings:

```python
def method_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    Brief description of method.
    
    Longer description if needed, explaining behavior,
    constraints, and usage patterns.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ExceptionType: When this exception is raised
    
    Example:
        >>> method_name(value1, value2)
        result
    """
```

### 7.2 Type Hints

All public API methods must have complete type hints:

```python
from typing import Optional, Dict, List, Any, Callable, Union
from decimal import Decimal
from pathlib import Path
from nautilus_trader.model.objects import Price, Quantity, Money

def analyze_strategy(
    self,
    strategy: Dict[str, Any],
    custom_ranges: Optional[Dict[str, Any]] = None
) -> Dict[str, Union[str, int, List[Dict[str, Any]]]]:
    """Method implementation"""
```

---

## 8. Change Log

### Version 1.0.0 (2026-01-20)
- ✅ Initial API design
- ✅ OptimizerV3 API specification
- ✅ StrategyAnalyzer API specification
- ✅ ParallelExecutor API specification
- ✅ ResultsRanker API specification
- ✅ Versioning strategy defined
- ✅ Integration patterns documented

### Future Versions
- 1.1.0: Add ML-based parameter suggestion API
- 1.2.0: Add real-time optimization API
- 2.0.0: Multi-strategy optimization support

---

**Document Status**: ✅ Complete  
**Last Updated**: 2026-01-20  
**Approved By**: Development Team

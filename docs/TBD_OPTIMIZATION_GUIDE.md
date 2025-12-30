# TBD Layer Optimization Guide

Complete guide for systematic parameter optimization of the TBD (Trade By Design) layer.

## Overview

The TBD optimization system provides automated, systematic parameter search to find optimal configurations for the TBD trading layer. It uses:

- **Multi-core parallel execution** for fast testing
- **Configuration tracking** to avoid duplicate tests
- **Adaptive search** to progressively refine parameters
- **Comprehensive analysis** of results and parameter impacts

## Quick Start

### 1. Basic Optimization Run

```bash
# Adaptive search (recommended for first run)
python3 scripts/optimization/run_tbd_optimization.py --method adaptive --rounds 3
```

This will:
- Test ~300-500 configurations
- Use adaptive refinement to find best parameters
- Complete in 2-4 hours (depending on CPU cores)
- Save results to `data/reports/tbd_optimization/`

### 2. View Results

Results are automatically saved to:
- `optimization_results.json` - All results sorted by performance
- `optimization_report.txt` - Human-readable summary
- `analysis_report.txt` - Statistical analysis
- Charts: `parameter_impact.png`, `return_vs_winrate.png`, etc.

### 3. Apply Best Configuration

The best configuration is shown in the report. Update `config/strategies/layer_tbd_only.py` with the optimal parameters.

## Optimization Methods

### Adaptive Search (Recommended)

Progressive refinement strategy:
1. **Round 1**: Test 200 random configurations
2. **Round 2**: Focus on top 3, test variations
3. **Round 3**: Further refine around best

```bash
python3 scripts/optimization/run_tbd_optimization.py \
  --method adaptive \
  --rounds 3 \
  --max-iterations 1000
```

**Best for**: Finding optimal configuration efficiently

### Grid Search

Tests all parameter combinations:

```bash
python3 scripts/optimization/run_tbd_optimization.py \
  --method grid \
  --max-iterations 500
```

**Best for**: Exhaustive search of small parameter spaces
**Warning**: Can be very slow with many parameters

### Random Search

Tests random parameter combinations:

```bash
python3 scripts/optimization/run_tbd_optimization.py \
  --method random \
  --n-random 1000
```

**Best for**: Quick exploration of parameter space

## Command-Line Options

### Search Configuration

```bash
--method {grid,random,adaptive}  # Optimization method (default: adaptive)
--n-random N                     # Random configs for random search (default: 1000)
--rounds N                       # Refinement rounds for adaptive (default: 3)
```

### Testing Parameters

```bash
--preset {quick,standard,extended,production}  # Walk-forward preset (default: standard)
--initial-capital AMOUNT         # Starting capital in USDT (default: 10000)
--max-compound-risk PCT          # Max risk per period (default: 0.25)
```

### Execution Control

```bash
--max-workers N                  # Parallel workers (default: CPU cores - 1)
--max-iterations N               # Max configs to test (default: 5000)
--early-stopping PCT             # Stop if win rate >= threshold (default: 0.8)
```

### Output Options

```bash
--output-dir PATH                # Output directory (default: data/reports/tbd_optimization)
--no-analysis                    # Skip analysis report
--no-charts                      # Skip chart generation
```

## Parameter Space

The optimizer tests combinations of these parameters:

### Pattern Detection

- `enable_m_pattern`: Enable M-pattern (double top) detection
- `enable_w_pattern`: Enable W-pattern (double bottom) detection
- `enable_three_hits_rule`: Enable three hits reversal rule
- `enable_trapping_volume`: Enable trapping volume detection
- `enable_board_meeting`: Enable board meeting consolidation
- `enable_one_formation`: Enable one formation breakout
- `enable_weekend_trap`: Enable weekend trap pattern

### Confirmation Requirements

- `minimum_confirmations`: Required confirmations (2-4)
- `require_volume_confirmation`: Require volume confirmation
- `require_trend_alignment`: Require trend alignment

### Pattern Parameters

**M/W Patterns:**
- `mw_peak_tolerance`: Peak symmetry tolerance (0.15-0.35)
- `mw_pattern_length_min`: Minimum pattern length (6-10 bars)
- `mw_pattern_length_max`: Maximum pattern length (50-80 bars)

**Three Hits:**
- `three_hits_touch_tolerance`: Touch precision (0.003-0.010)
- `three_hits_min_wick_ratio`: Minimum rejection wick (0.55-0.65)
- `three_hits_require_confirmation`: Wait for confirmation bar

**Trapping Volume:**
- `trap_wick_threshold`: Minimum wick ratio (0.50-0.65)
- `trap_volume_multiplier_min`: Minimum volume spike (1.3-2.0x)
- `trap_body_max_ratio`: Maximum body size (0.30-0.40)
- `trap_require_confirmation`: Wait for confirmation

### Risk Management

- `atr_stop_multiplier`: ATR multiplier for stops (1.0-2.5)

### Timing Filters

- `avoid_weekend_trading`: Skip weekend trading
- `avoid_first_30min_london`: Skip first 30min of London
- `enable_session_filter`: Enable session filtering

## Example Workflows

### Workflow 1: Initial Optimization

```bash
# Step 1: Run adaptive search
python3 scripts/optimization/run_tbd_optimization.py \
  --method adaptive \
  --rounds 3 \
  --preset standard

# Step 2: Review results
cat data/reports/tbd_optimization/optimization_report.txt
cat data/reports/tbd_optimization/analysis_report.txt

# Step 3: Apply best config to layer_tbd_only.py
```

### Workflow 2: Focused Refinement

```bash
# After initial optimization, refine specific parameters

# Edit scripts/optimization/run_tbd_optimization.py
# Narrow parameter_ranges to focus on specific params

# Run focused search
python3 scripts/optimization/run_tbd_optimization.py \
  --method grid \
  --max-iterations 200
```

### Workflow 3: Extended Testing

```bash
# Test on longer timeframe with more capital
python3 scripts/optimization/run_tbd_optimization.py \
  --method adaptive \
  --preset extended \
  --initial-capital 25000 \
  --max-compound-risk 0.30 \
  --rounds 4
```

### Workflow 4: Resume Previous Run

```bash
# The optimizer automatically skips previously tested configs

# Same command continues from where it left off
python3 scripts/optimization/run_tbd_optimization.py \
  --method adaptive \
  --output-dir data/reports/tbd_optimization
```

## Understanding Results

### Optimization Report

```
TOP 20 CONFIGURATIONS
Rank   Return     WR      PF      Trades   Config Hash
1      +45.23%    68.5%   2.15    145      a1b2c3d4e5
2      +42.18%    65.2%   2.08    138      f6g7h8i9j0
...
```

**Key Metrics:**
- **Return**: Total compounded return
- **WR**: Win rate (% winning trades)
- **PF**: Profit factor (gross profit / gross loss)
- **Trades**: Total number of trades

### Analysis Report

```
PARAMETER IMPACT ANALYSIS
Parameter                    Return Corr    WR Corr    Best Value
enable_m_pattern             +0.234         +0.189     True
trap_wick_threshold          -0.156         -0.128     0.60
minimum_confirmations        -0.098         +0.045     3
```

**Interpretation:**
- **Positive correlation**: Higher value → better performance
- **Negative correlation**: Lower value → better performance
- **Best Value**: Value used in top performing config

### Common Patterns

```
Common Features (80%+ agreement):
  enable_m_pattern: True (95%)
  trap_wick_threshold: 0.60 (85%)
  minimum_confirmations: 3 (90%)
```

Shows parameters where top configs strongly agree.

## Performance Considerations

### Execution Time

Approximate times for `--preset standard` (90 days, 6 periods):

| Configs | Workers | Time (est) |
|---------|---------|------------|
| 100     | 4       | ~2 hours   |
| 500     | 8       | ~5 hours   |
| 1000    | 16      | ~6 hours   |

### Memory Usage

- Each worker: ~500 MB RAM
- Full optimization: 4-8 GB total

### CPU Usage

- Uses all available cores except 1
- Override with `--max-workers N`

## Troubleshooting

### Issue: Tests timing out

**Solution**: Increase timeout in `tbd_optimizer.py`:
```python
timeout=900  # 15 minutes instead of 10
```

### Issue: Out of memory

**Solution**: Reduce workers:
```bash
--max-workers 4
```

### Issue: No valid results

**Possible causes:**
1. Data not available for date range
2. Walk-forward script errors
3. Configuration incompatibilities

**Solution**: Check individual test output:
```bash
python3 scripts/layer_testing/walk_forward_tbd.py --preset standard
```

### Issue: Slow progress

**Solution**: Use faster preset:
```bash
--preset quick  # 30 days, 3 periods
```

## Advanced Usage

### Custom Parameter Ranges

Edit `scripts/optimization/run_tbd_optimization.py`:

```python
parameter_ranges = {
    # Focus on specific parameters
    'trap_wick_threshold': [0.58, 0.60, 0.62, 0.64],
    'trap_volume_multiplier_min': [1.4, 1.5, 1.6, 1.7, 1.8],
    # ... other parameters
}
```

### Analyze Existing Results

```bash
python3 -m src.optimization.result_analyzer \
  --results data/reports/tbd_optimization/optimization_results.json \
  --output analysis_report.txt \
  --top-n 30
```

### Export Best Config

Python script to extract and format best configuration:

```python
import json

with open('data/reports/tbd_optimization/optimization_results.json', 'r') as f:
    results = json.load(f)

best = results[0]  # Sorted by performance
best_params = best['config']['layer_tbd_params']

print("Best Configuration:")
for key, value in sorted(best_params.items()):
    print(f"  {key}: {value}")
```

## Integration with Trading System

### Apply Optimal Configuration

1. Review optimization results
2. Copy best parameters from report
3. Update `config/strategies/layer_tbd_only.py`:

```python
'layer_tbd_params': {
    # Update with optimal values
    'enable_m_pattern': True,
    'trap_wick_threshold': 0.60,
    'minimum_confirmations': 3,
    # ... etc
}
```

4. Test configuration:

```bash
python3 scripts/layer_testing/walk_forward_tbd.py --preset standard
```

5. If validated, deploy to paper trading

## Best Practices

1. **Start with adaptive search**: Most efficient for initial optimization
2. **Use standard preset**: Good balance of accuracy and speed
3. **Review analysis report**: Understand parameter impacts
4. **Validate best config**: Re-run walk-forward on best configuration
5. **Monitor live performance**: Parameters may need adjustment over time
6. **Re-optimize periodically**: Market conditions change

## File Structure

```
data/reports/tbd_optimization/
├── tested_configurations.json    # All tested configs (hash → result)
├── optimization_results.json     # Results sorted by performance
├── optimization_report.txt       # Human-readable summary
├── analysis_report.txt           # Statistical analysis
├── parameter_impact.png          # Parameter correlation chart
├── return_vs_winrate.png        # Performance scatter plot
└── top_configs_comparison.png   # Top N configs comparison
```

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review log files in output directory
3. Test individual components (walk-forward, analyzer)
4. Consult project documentation

---

**Version**: 1.0.0  
**Last Updated**: 2025-12-29  
**Maintainer**: BTC Engine Team

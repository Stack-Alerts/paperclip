# CLI Command Reference

Complete reference for all BTC Scalp Bot V10 command-line interface commands.

## Table of Contents

- [Overview](#overview)
- [Global Options](#global-options)
- [Commands](#commands)
  - [backtest](#backtest) - Run backtesting
  - [optimize](#optimize) - Auto-tune strategy parameters (NEW)
  - [paper](#paper) - Paper trading
  - [live](#live) - Live trading
  - [train](#train) - Train ML models
  - [test](#test) - Run tests
  - [validate](#validate) - Validate configuration
  - [status](#status) - Check system health
  - [profile](#profile) - Performance profiling
  - [list-strategies](#list-strategies) - List strategies
- [Examples](#examples)

## Overview

All commands follow this pattern:

```bash
python3 scripts/bot.py COMMAND [OPTIONS]
```

Get help for any command:

```bash
python3 scripts/bot.py --help
python3 scripts/bot.py COMMAND --help
```

## Global Options

```bash
--version              Show version and exit
--help                 Show help message
```

---

## Commands

### backtest

Run historical backtesting to validate strategy performance.

**Syntax:**
```bash
python3 scripts/bot.py backtest [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | choice | **required** | Strategy: `scalp_conservative`, `scalp_aggressive`, `scalp_ml_heavy` |
| `--days` | `-d` | int | 90 | Number of days to backtest |
| `--capital` | | float | 10000 | Initial capital in USDT |
| `--start-date` | | string | | Start date (YYYY-MM-DD), overrides --days |
| `--end-date` | | string | today | End date (YYYY-MM-DD) |
| `--processes` | `-p` | int | 16 | Number of parallel processes |
| `--output` | `-o` | path | data/reports | Output directory for reports |
| `--optimize` | | flag | false | Run parameter optimization |
| `--verbose` | `-v` | flag | false | Verbose output with detailed logging |

**Examples:**

```bash
# Basic 90-day backtest
python3 scripts/bot.py backtest --config scalp_conservative --days 90 --capital 10000

# 6-month backtest with optimization
python3 scripts/bot.py backtest -c scalp_aggressive -d 180 --optimize --processes 16

# Specific date range
python3 scripts/bot.py backtest -c scalp_ml_heavy \
  --start-date 2024-01-01 \
  --end-date 2024-06-01 \
  --capital 50000

# Verbose output to custom directory
python3 scripts/bot.py backtest -c scalp_conservative \
  --days 90 \
  --output ./my_reports \
  --verbose
```

**Output:**

- Console: Performance summary with key metrics
- File: Detailed JSON report in output directory
- Logs: Saved to `logs/` directory

---

### optimize

Auto-tune strategy parameters for optimal performance (does NOT train ML models).

**What it optimizes:**
- Layer weights and thresholds
- Risk management parameters
- Entry/exit signal parameters
- Compositor settings
- 70+ configurable parameters

**What it does NOT do:**
- Does NOT train XGBoost or CNN-LSTM models
- Does NOT modify ML model architectures
- Use `train` command for ML model training

**Syntax:**
```bash
python3 scripts/bot.py optimize [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--days` | `-d` | int | 90 | Historical data period |
| `--capital` | | float | 10000 | Initial capital for testing |
| `--timeframe` | | choice | 15m | Primary timeframe |
| `--objective` | | choice | sharpe | Objective: `sharpe`, `return`, `sortino` |
| `--algorithm` | | choice | bayesian | Algorithm: `bayesian`, `genetic` |
| `--max-iterations` | | int | 100 | Maximum optimization iterations |
| `--n-jobs` | `-j` | int | -1 | Parallel jobs (-1 = all cores) |
| `--output` | `-o` | path | data/optimization | Output directory |

**Examples:**

```bash
# Basic optimization (Bayesian, Sharpe ratio)
python3 scripts/bot.py optimize --days 90 --capital 10000

# Genetic algorithm optimization
python3 scripts/bot.py optimize -d 180 \
  --algorithm genetic \
  --max-iterations 200 \
  --objective return

# Fast optimization (fewer iterations)
python3 scripts/bot.py optimize -d 60 \
  --max-iterations 50 \
  --n-jobs 16

# Optimize for Sortino ratio
python3 scripts/bot.py optimize -d 120 \
  --objective sortino \
  --algorithm bayesian
```

**Output:**

- Optimized configuration saved to `data/optimization/`
- Performance comparison (before vs after)
- Parameter evolution visualization
- Walk-forward validation results

**Optimization Time:**

- **Bayesian (100 iter)**: 2-4 hours
- **Genetic (200 iter)**: 4-8 hours
- Depends on: CPU cores, data period, iterations

**Key Difference:**

```
train    → Trains ML models (XGBoost, CNN-LSTM)
optimize → Tunes strategy parameters (weights, thresholds, risk)
```

Both commands are independent:
- Run `train` to update ML models with new data
- Run `optimize` to find best parameter combinations
- They don't affect each other

---

### paper

Run paper trading with simulated orders (no real money).

**Syntax:**
```bash
python3 scripts/bot.py paper [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | choice | **required** | Strategy configuration |
| `--capital` | | float | 10000 | Paper trading capital in USDT |
| `--duration` | | int | 0 | Duration in hours (0 = indefinite) |
| `--dashboard` | | flag | false | Enable live dashboard (Streamlit) |
| `--report-interval` | | int | 60 | Report interval in minutes |

**Examples:**

```bash
# Run indefinitely with dashboard
python3 scripts/bot.py paper --config scalp_conservative \
  --capital 10000 \
  --dashboard

# 24-hour paper trading test
python3 scripts/bot.py paper -c scalp_aggressive \
  --capital 5000 \
  --duration 24

# Report every 30 minutes
python3 scripts/bot.py paper -c scalp_ml_heavy \
  --capital 20000 \
  --report-interval 30
```

**Dashboard:**

If `--dashboard` is enabled, access at `http://localhost:8501`

**Stop Paper Trading:**

Press `Ctrl+C` to gracefully stop

---

### live

Run live trading with real money ⚠️ **CAUTION**

**Syntax:**
```bash
python3 scripts/bot.py live [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--config` | `-c` | choice | **required** | Strategy configuration |
| `--confirm` | | flag | **required** | Confirm live trading (required) |
| `--max-trades` | | int | | Maximum number of trades |
| `--duration` | | int | | Duration in hours |
| `--dry-run` | | flag | false | Test without executing orders |

**⚠️ IMPORTANT WARNINGS:**

- Live trading uses REAL MONEY
- ALWAYS test in paper trading first
- Start with small capital
- Monitor closely
- Use `--dry-run` first to test

**Examples:**

```bash
# Dry run first (recommended)
python3 scripts/bot.py live --config scalp_conservative --dry-run

# Live trading (with confirmation)
python3 scripts/bot.py live --config scalp_conservative --confirm

# Limited live trading
python3 scripts/bot.py live -c scalp_conservative \
  --confirm \
  --max-trades 5 \
  --duration 8

# NEVER DO THIS without extensive testing!
```

**Safety Checklist:**

- [ ] Backtested for 90+ days
- [ ] Paper traded for 1+ week
- [ ] Tested dry-run mode
- [ ] Configured stop-losses
- [ ] Using small capital
- [ ] Monitoring actively

---

### train

Train machine learning models (Layer 4 & Layer 5).

**Syntax:**
```bash
python3 scripts/bot.py train [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--model` | `-m` | choice | all | Model: `xgboost`, `cnn_lstm`, `all` |
| `--data-days` | | int | 180 | Days of historical data to use |
| `--optimize` | | flag | false | Run hyperparameter optimization |
| `--processes` | `-p` | int | 16 | Number of parallel processes |
| `--save-path` | | path | data/models | Custom save path |

**Examples:**

```bash
# Train all models (recommended)
python3 scripts/bot.py train --model all --data-days 180

# Train XGBoost only
python3 scripts/bot.py train -m xgboost --data-days 365

# Train with hyperparameter optimization
python3 scripts/bot.py train -m all --optimize --processes 16

# Train CNN-LSTM with more data
python3 scripts/bot.py train -m cnn_lstm --data-days 365
```

**Training Time:**

- **XGBoost**: 10-30 minutes
- **CNN-LSTM**: 30-120 minutes (depends on GPU)
- **Optimization**: 2-8 hours

**Output:**

Models saved to `data/models/`:
- `xgboost/xgboost_model.pkl`
- `cnn_lstm/cnn_lstm_model.keras`

---

### test

Run system tests with coverage reporting.

**Syntax:**
```bash
python3 scripts/bot.py test [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--type` | `-t` | choice | all | Test type: `unit`, `integration`, `all` |
| `--verbose` | `-v` | flag | false | Verbose test output |
| `--coverage` | | flag | true | Generate coverage report |
| `--list` | | flag | false | List available tests |
| `--specific` | `-s` | string | | Run specific test file/function |

**Examples:**

```bash
# Run all tests
python3 scripts/bot.py test

# Run integration tests only
python3 scripts/bot.py test --type integration --verbose

# List available tests
python3 scripts/bot.py test --list

# Run specific test
python3 scripts/bot.py test --specific tests/test_layer1.py

# Run without coverage
python3 scripts/bot.py test --type unit --no-coverage
```

**Output:**

- Console: Test results with pass/fail
- HTML: Coverage report at `htmlcov/index.html`

---

### validate

Validate system configuration and dependencies.

**Syntax:**
```bash
python3 scripts/bot.py validate [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--detailed` | `-d` | flag | false | Show detailed validation info |
| `--tree` | | flag | false | Show configuration file tree |

**Examples:**

```bash
# Quick validation
python3 scripts/bot.py validate

# Detailed validation
python3 scripts/bot.py validate --detailed

# Show config tree
python3 scripts/bot.py validate --tree
```

**Checks:**

- ✅ Configuration files
- ✅ Model availability
- ✅ Data directories
- ✅ Python environment
- ✅ Package dependencies

---

### status

Check system health and component status.

**Syntax:**
```bash
python3 scripts/bot.py status [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--detailed` | `-d` | flag | false | Show detailed component status |

**Examples:**

```bash
# Quick status check
python3 scripts/bot.py status

# Detailed status
python3 scripts/bot.py status --detailed
```

**Components Checked:**

- Data Pipeline
- Indicator Engine
- Analysis Layers (1-5)
- ML Models
- Services

---

### profile

Profile system performance and identify bottlenecks.

**Syntax:**
```bash
python3 scripts/bot.py profile [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--bars` | | int | 1000 | Number of bars for testing |
| `--output` | `-o` | path | | Save results to JSON file |

**Examples:**

```bash
# Quick profile
python3 scripts/bot.py profile

# Extended profile
python3 scripts/bot.py profile --bars 5000

# Save results
python3 scripts/bot.py profile --bars 2000 --output profile.json
```

**Benchmarks:**

- Indicator Engine speed
- Layer performance
- Compositor speed
- Performance recommendations

---

### list-strategies

List all available strategy configurations.

**Syntax:**
```bash
python3 scripts/bot.py list-strategies
```

**No options required.**

**Output:**

```
Available Strategies:
  • scalp_conservative
  • scalp_aggressive
  • scalp_ml_heavy
  • custom_strategy_1

Total: 4 strategies
```

---

## Examples

### Complete Workflow

```bash
# 1. Validate installation
python3 scripts/bot.py validate

# 2. Check system status
python3 scripts/bot.py status

# 3. Train models
python3 scripts/bot.py train --model all --data-days 180

# 4. Run backtest
python3 scripts/bot.py backtest --config scalp_conservative \
  --days 90 --capital 10000

# 5. Paper trade
python3 scripts/bot.py paper --config scalp_conservative \
  --capital 10000 --dashboard

# 6. Profile performance
python3 scripts/bot.py profile --bars 1000

# 7. Run tests
python3 scripts/bot.py test --type integration
```

### Development Workflow

```bash
# Validate after code changes
python3 scripts/bot.py validate --detailed

# Run tests
python3 scripts/bot.py test --verbose

# Check status
python3 scripts/bot.py status

# Profile performance
python3 scripts/bot.py profile
```

### Production Deployment

```bash
# Pre-deployment checks
python3 scripts/bot.py validate --detailed
python3 scripts/bot.py test --type all --coverage
python3 scripts/bot.py status --detailed
python3 scripts/bot.py profile --bars 5000

# Start live trading
python3 scripts/bot.py live --config scalp_conservative --confirm
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error/Failure |

---

## Environment Variables

```bash
# Optional environment variables
export TRADING_ENV=production  # production, development, test
export LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
export NUM_PROCESSES=16        # Override default processes
```

---

## Tips & Best Practices

### Performance

- Use `--processes 16` for faster backtesting
- Profile regularly to identify bottlenecks
- Enable multiprocessing in config for indicator calculation

### Testing

- Always run `validate` after installation
- Test strategies in this order: backtest → paper → live
- Use `--optimize` sparingly (computationally expensive)

### Safety

- Never skip paper trading
- Start live trading with minimum capital
- Monitor live trading actively
- Use `--dry-run` to test live mode

### Development

- Run `test` before committing code
- Use `--verbose` for debugging
- Check `status` regularly during development

---

## Troubleshooting

### Command Not Found

```bash
# Ensure you're in project root
cd /path/to/BTC_Engine_LLM

# Use full path
python3 scripts/bot.py --help
```

### Permission Denied

```bash
# Make script executable
chmod +x scripts/bot.py
```

### Import Errors

```bash
# Check installation
python3 scripts/bot.py validate

# Reinstall dependencies
pip install -r requirements.txt
```

---

**Next**: [User Guide](USER_GUIDE.md) | [Troubleshooting](TROUBLESHOOTING.md) | [Back to README](../README.md)

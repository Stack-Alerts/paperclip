# Getting Started with BTC Scalp Bot V10

Welcome! This guide will help you install, configure, and run your first backtest with the BTC Scalp Bot V10.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Validation](#quick-validation)
- [First Backtest](#first-backtest)
- [Understanding Results](#understanding-results)
- [Next Steps](#next-steps)

## Prerequisites

Before you begin, ensure you have:

### System Requirements

**Minimum:**
- **OS**: Linux, macOS, or Windows 10+
- **Python**: 3.10 or higher
- **RAM**: 8GB
- **Storage**: 10GB free space
- **Internet**: Stable connection

**Recommended:**
- **Python**: 3.12+
- **RAM**: 16GB+
- **Storage**: 50GB SSD
- **CPU**: 16+ cores for multiprocessing
- **GPU**: CUDA-capable (optional, for ML training)

### Software Dependencies

- **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
- **TA-Lib C library** - Required for technical indicators
- **Git** - For cloning the repository

## Installation

### Step 1: Install TA-Lib

TA-Lib is required for technical indicator calculations.

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install ta-lib
```

#### macOS

```bash
brew install ta-lib
```

#### Windows

1. Download the appropriate `.whl` file from [TA-Lib Unofficial Binaries](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)
2. Install with pip:
   ```bash
   pip install TA_Lib‑0.4.XX‑cpXXX‑cpXXX‑win_amd64.whl
   ```

### Step 2: Clone Repository

```bash
# Clone the repository
git clone <repository-url>
cd BTC_Engine_LLM

# Or if you have SSH set up
git clone git@github.com:username/BTC_Engine_LLM.git
cd BTC_Engine_LLM
```

### Step 3: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 4: Install Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# This will install:
# - pandas, numpy (data processing)
# - ccxt (exchange integration)
# - tensorflow, xgboost (machine learning)
# - click, rich (CLI interface)
# - And many more...
```

Installation may take 5-10 minutes depending on your internet connection.

### Step 5: Verify Installation

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Verify TA-Lib installation
python3 -c "import talib; print('TA-Lib OK')"

# Check TensorFlow
python3 -c "import tensorflow; print('TensorFlow OK')"
```

## Quick Validation

Validate your installation with the built-in validation tool:

```bash
python3 scripts/bot.py validate
```

**Expected Output:**
```
Configuration Validation
━━━━━━━━━━━━━━━━━━━━━━━━━

Checking Configuration Files...
  ✅ base_config.py - Found
  ✅ bot_config.yaml - Valid
  ✅ exchange_config.yaml - Valid
  ✅ model_config.yaml - Valid

Checking Models...
  ✅ xgboost - Ready
  ✅ cnn_lstm - Ready

Checking Data Directories...
  ✅ data/raw - 20 files
  ✅ data/processed - 1 files
  ✅ data/models - 4 files

Checking Python Environment...
  ✅ Python 3.12.3 - Compatible
  ✅ All packages installed

━━━━━━━━━━━━━━━━━━━━━━━━━
✅ All checks passed!
```

### Troubleshooting Validation Issues

**If you see errors:**

1. **Missing TA-Lib**: Reinstall TA-Lib C library
2. **Missing packages**: Run `pip install -r requirements.txt` again
3. **Permission errors**: Use `sudo` on Linux/macOS or run as administrator on Windows
4. **Model files missing**: These will be created when you train models (optional for backtesting)

## First Backtest

Let's run your first backtest using the conservative strategy!

### Step 1: Run Basic Backtest

```bash
python3 scripts/bot.py backtest \
  --config scalp_conservative \
  --days 90 \
  --capital 10000
```

**What this does:**
- Uses the `scalp_conservative` strategy (lower risk)
- Tests the last 90 days of data
- Starts with $10,000 capital
- Uses multiprocessing for faster execution

### Step 2: Wait for Completion

The backtest will:
1. Load historical BTC/USDT data
2. Calculate 54 technical indicators
3. Generate signals from all 5 layers
4. Execute simulated trades
5. Calculate performance metrics

**Expected runtime**: 2-5 minutes (depending on your CPU)

### Step 3: Review Output

You'll see output like this:

```
═══════════════════════════════════════════════
BTC SCALP BOT V10 - BACKTEST MODE
═══════════════════════════════════════════════

Configuration: scalp_conservative
Initial Capital: $10,000.00
Date Range: 2024-09-01 to 2024-12-01 (90 days)
Multiprocessing: 16 cores

────────────────────────────────────────────────

Loading data...
Calculating indicators...
Running backtest...

Performance Summary:
────────────────────────────────────────────────
Initial Capital:     $10,000.00
Final Equity:        $12,450.00
Total Return:        +24.50%
Max Drawdown:        -5.20%
Sharpe Ratio:        2.45
Win Rate:            62.5%
Total Trades:        48
Profitable Trades:   30
Losing Trades:       18

✅ Backtest completed successfully!
Report saved to: data/reports/backtest_20241201_123456.json
```

## Understanding Results

### Key Metrics Explained

**Total Return**: Overall profit/loss percentage
- **Good**: > 10% for 90 days
- **Excellent**: > 20% for 90 days

**Max Drawdown**: Largest peak-to-trough decline
- **Good**: < 10%
- **Excellent**: < 5%

**Sharpe Ratio**: Risk-adjusted returns
- **Good**: > 1.0
- **Excellent**: > 2.0

**Win Rate**: Percentage of profitable trades
- **Good**: > 55%
- **Excellent**: > 60%

### View Detailed Report

```bash
# Find your report
ls data/reports/

# View with Python
python3 -c "import json; print(json.dumps(json.load(open('data/reports/backtest_XXXXX.json')), indent=2))"
```

## Next Steps

### 1. Try Different Strategies

```bash
# Aggressive strategy (higher risk/reward)
python3 scripts/bot.py backtest --config scalp_aggressive --days 90 --capital 10000

# ML-heavy strategy (relies more on AI models)
python3 scripts/bot.py backtest --config scalp_ml_heavy --days 90 --capital 10000
```

### 2. Optimize Parameters

```bash
# Run with parameter optimization
python3 scripts/bot.py backtest \
  --config scalp_conservative \
  --days 180 \
  --optimize \
  --processes 16
```

### 3. Train ML Models

```bash
# Train all models with 6 months of data
python3 scripts/bot.py train --model all --data-days 180

# This improves Layer 4 (XGBoost) and Layer 5 (CNN-LSTM)
```

### 4. Paper Trading

Once you're satisfied with backtest results:

```bash
# Run paper trading (simulated, no real money)
python3 scripts/bot.py paper \
  --config scalp_conservative \
  --capital 10000 \
  --dashboard  # Opens web dashboard
```

### 5. Check System Status

```bash
# Validate configuration
python3 scripts/bot.py validate --detailed

# Check component health
python3 scripts/bot.py status

# Profile performance
python3 scripts/bot.py profile --bars 1000
```

## Common Commands Reference

```bash
# Backtesting
python3 scripts/bot.py backtest --config STRATEGY --days DAYS --capital AMOUNT

# Paper Trading
python3 scripts/bot.py paper --config STRATEGY --capital AMOUNT [--dashboard]

# Training
python3 scripts/bot.py train --model MODEL --data-days DAYS [--optimize]

# System Management
python3 scripts/bot.py validate [--detailed]
python3 scripts/bot.py status [--detailed]
python3 scripts/bot.py profile [--bars N]
python3 scripts/bot.py test [--type TYPE]

# List available strategies
python3 scripts/bot.py list-strategies
```

## Getting Help

### Documentation

- **[CLI Reference](CLI_REFERENCE.md)** - All commands and options
- **[User Guide](USER_GUIDE.md)** - Detailed usage instructions
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
- **[Architecture](ARCHITECTURE.md)** - System design details

### Command Help

```bash
# Get help for any command
python3 scripts/bot.py --help
python3 scripts/bot.py backtest --help
python3 scripts/bot.py paper --help
```

### Support

- 📖 **Documentation**: [docs/](../../v3/archived/docs)
- 🐛 **Issues**: [GitHub Issues](../../v3/archived/issues)
- 💬 **Discord**: [Join Server](#)

## Safety Tips

Before proceeding to live trading:

1. ✅ **Run extensive backtests** (multiple strategies, time periods)
2. ✅ **Paper trade for at least 1 week** to validate real-time performance
3. ✅ **Start with small capital** in live trading
4. ✅ **Monitor closely** for the first few days
5. ✅ **Have stop-loss** limits configured
6. ⚠️  **Never risk more than you can afford to lose**

## Congratulations! 🎉

You've successfully:
- ✅ Installed BTC Scalp Bot V10
- ✅ Validated your setup
- ✅ Run your first backtest
- ✅ Understood the results

You're now ready to explore more advanced features!

---

**Next**: [CLI Reference](CLI_REFERENCE.md) | [User Guide](USER_GUIDE.md) | [Back to README](../test-notes/README.md)

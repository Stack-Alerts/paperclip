# Troubleshooting Guide

Common issues and solutions for BTC Scalp Bot V10.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Runtime Errors](#runtime-errors)
- [Performance Issues](#performance-issues)
- [Trading Issues](#trading-issues)
- [Model Training Problems](#model-training-problems)
- [Data Issues](#data-issues)
- [General Tips](#general-tips)

## Installation Issues

### TA-Lib Installation Failed

**Problem**: `pip install TA-Lib` fails

**Solution**:

1. **Install C library first** (TA-Lib Python requires the C library):

   ```bash
   # Ubuntu/Debian
   sudo apt-get install ta-lib
   
   # macOS
   brew install ta-lib
   
   # Windows
   # Download .whl from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
   pip install TA_Lib-0.4.XX-cpXXX-cpXXX-win_amd64.whl
   ```

2. **Verify installation**:
   ```bash
   python3 -c "import talib; print('TA-Lib OK')"
   ```

### TensorFlow Installation Issues

**Problem**: TensorFlow won't install or import fails

**Solutions**:

```bash
# Check Python version (needs 3.10-3.12)
python3 --version

# Install specific TensorFlow version
pip install tensorflow==2.15.0

# For Apple Silicon Macs
pip install tensorflow-macos tensorflow-metal

# For CUDA GPU support
pip install tensorflow-gpu==2.15.0
```

### Package Dependency Conflicts

**Problem**: Conflicting package versions

**Solution**:

```bash
# Create fresh virtual environment
python3 -m venv venv_new
source venv_new/bin/activate  # Linux/Mac
# or venv_new\Scripts\activate  # Windows

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Import Errors After Installation

**Problem**: `ModuleNotFoundError` when running bot

**Solution**:

```bash
# Ensure you're in project root
cd /path/to/BTC_Engine_LLM

# Check if virtual environment is activated
which python3  # Should show venv path

# Reinstall in editable mode
pip install -e .

# Or add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/BTC_Engine_LLM"
```

## Configuration Problems

### Configuration File Not Found

**Problem**: `Config file not found` error

**Solution**:

```bash
# Check if config files exist
ls config/

# Copy example files if missing
cp config/exchange_config.yaml.example config/exchange_config.yaml
cp config/bot_config.yaml.example config/bot_config.yaml

# Validate configuration
python3 scripts/bot.py validate
```

### Invalid YAML Syntax

**Problem**: `yaml.YAMLError: while parsing`

**Solution**:

1. **Check YAML syntax** - use proper indentation (spaces, not tabs)
2. **Validate online**: https://www.yamllint.com/
3. **Common issues**:
   ```yaml
   # WRONG: using tabs
   config:
   	value: 123
   
   # RIGHT: using spaces
   config:
     value: 123
   
   # WRONG: unquoted special chars
   password: my:password
   
   # RIGHT: quoted
   password: "my:password"
   ```

### Strategy Not Found

**Problem**: `Strategy 'xyz' not found`

**Solution**:

```bash
# List available strategies
python3 scripts/bot.py list-strategies

# Check strategy files exist
ls config/strategies/

# Use exact strategy name (case-sensitive)
python3 scripts/bot.py backtest --config scalp_conservative
```

## Runtime Errors

### Memory Error During Backtest

**Problem**: `MemoryError` or system freezes

**Solutions**:

1. **Reduce data size**:
   ```bash
   # Use fewer days
   python3 scripts/bot.py backtest --config scalp_conservative --days 30
   ```

2. **Disable multiprocessing**:
   ```bash
   # Edit config/bot_config.yaml
   indicator_engine:
     multiprocessing: false
   ```

3. **Increase system swap** (Linux):
   ```bash
   sudo swapon --show
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### Exchange API Errors

**Problem**: `ccxt.AuthenticationError` or `ccxt.NetworkError`

**Solutions**:

1. **Check API credentials**:
   ```yaml
   # config/exchange_config.yaml
   api_key: "your-actual-key"
   api_secret: "your-actual-secret"
   ```

2. **Verify API permissions** (needs: read, trade)

3. **Check network connection**:
   ```bash
   ping api.binance.com
   ```

4. **Test API connection**:
   ```python
   import ccxt
   exchange = ccxt.binance({
       'apiKey': 'your-key',
       'secret': 'your-secret'
   })
   print(exchange.fetch_balance())
   ```

### Model Loading Errors

**Problem**: `Model file not found` or `Failed to load model`

**Solutions**:

```bash
# Check if models exist
ls data/models/xgboost/
ls data/models/cnn_lstm/

# Train models if missing
python3 scripts/bot.py train --model all --data-days 180

# Verify model files
python3 scripts/bot.py validate --detailed
```

### Indicator Calculation Errors

**Problem**: Indicators fail to calculate or return NaN

**Solutions**:

1. **Ensure sufficient data** (need at least 200 bars for some indicators)

2. **Check for missing values**:
   ```python
   import pandas as pd
   df = pd.read_csv('data/raw/BTC_USDT_PERP_1h.csv')
   print(df.isnull().sum())  # Should be 0 for all columns
   ```

3. **Verify OHLCV data**:
   ```bash
   # Check data format
   python3 -c "
   import pandas as pd
   df = pd.read_csv('data/raw/BTC_USDT_PERP_1h.csv')
   print(df.head())
   print(df.dtypes)
   "
   ```

## Performance Issues

### Slow Backtest Execution

**Problem**: Backtest takes too long

**Solutions**:

1. **Enable multiprocessing**:
   ```bash
   python3 scripts/bot.py backtest \
     --config scalp_conservative \
     --processes 16
   ```

2. **Enable indicator caching** (in `config/bot_config.yaml`):
   ```yaml
   indicator_engine:
     caching: true
     multiprocessing: true
     processes: 16
   ```

3. **Profile performance**:
   ```bash
   python3 scripts/bot.py profile --bars 1000
   ```

4. **Reduce data size** (use fewer days or larger timeframe)

### High Memory Usage

**Problem**: Bot uses too much RAM

**Solutions**:

1. **Monitor memory**:
   ```bash
   # Linux
   htop
   
   # Check bot specifically
   ps aux | grep bot.py
   ```

2. **Reduce batch size** for indicators

3. **Clear cache periodically** (in long-running processes)

4. **Use smaller data chunks**

### Slow Layer 5 (CNN-LSTM)

**Problem**: CNN-LSTM layer is slow

**Solutions**:

1. **Enable GPU** (if available):
   ```python
   # Check GPU availability
   import tensorflow as tf
   print(tf.config.list_physical_devices('GPU'))
   ```

2. **Install CUDA/cuDNN** for GPU support

3. **Reduce sequence length** (in `config/model_config.yaml`):
   ```yaml
   cnn_lstm:
     sequence_length: 30  # Default: 60
   ```

4. **Consider disabling Layer 5** for faster execution:
   ```python
   # In strategy config
   layer_weights = {
       'layer4': 0.35,  # Increase XGBoost weight
       'layer5': 0.0    # Disable CNN-LSTM
   }
   ```

## Trading Issues

### No Trades Executed in Backtest

**Problem**: Backtest completes but shows 0 trades

**Reasons & Solutions**:

1. **Confidence threshold too high**:
   ```python
   # Lower threshold in strategy config
   confidence_threshold = 0.5  # Try 0.4 or 0.3
   ```

2. **Check signal generation**:
   ```bash
   python3 scripts/bot.py backtest --config scalp_conservative --verbose
   # Look for "Signal generated" messages
   ```

3. **Insufficient signal agreement**:
   ```python
   # Reduce min_layers required
   min_layers = 2  # Try 1 or 2 instead of 3
   ```

4. **Data quality issues** - verify data has sufficient volatility

### Excessive Losses in Backtest

**Problem**: Strategy loses money consistently

**Solutions**:

1. **Review strategy parameters**:
   ```bash
   # Try conservative strategy first
   python3 scripts/bot.py backtest --config scalp_conservative
   ```

2. **Check fees configuration** (might be too high)

3. **Verify slippage settings**

4. **Analyze layer performance**:
   ```bash
   # Check which layers are performing poorly
   python3 scripts/bot.py backtest --config scalp_conservative --verbose
   ```

5. **Train models with more data**:
   ```bash
   python3 scripts/bot.py train --model all --data-days 365
   ```

### Paper Trading Not Connecting

**Problem**: Paper trading can't connect to exchange

**Solutions**:

```bash
# Check network connectivity
ping api.binance.com

# Test exchange connection
python3 -c "
import ccxt
exchange = ccxt.binance()
print(exchange.fetch_ticker('BTC/USDT'))
"

# Check if testnet is configured (if using testnet)
# Edit config/exchange_config.yaml
testnet: true  # or false for mainnet
```

## Model Training Problems

### Training Takes Too Long

**Problem**: Model training is very slow

**Solutions**:

1. **Use fewer processes** (counterintuitively, too many can slow things down):
   ```bash
   python3 scripts/bot.py train --model xgboost --processes 8
   ```

2. **Reduce data size**:
   ```bash
   python3 scripts/bot.py train --model all --data-days 90
   ```

3. **Skip optimization**:
   ```bash
   # Optimization can take hours
   python3 scripts/bot.py train --model all  # Without --optimize
   ```

4. **For CNN-LSTM, use GPU** if available

### Model Training Fails

**Problem**: Training crashes or fails to save models

**Solutions**:

1. **Check disk space**:
   ```bash
   df -h
   ```

2. **Verify write permissions**:
   ```bash
   ls -la data/models/
   chmod -R 755 data/models/
   ```

3. **Check data quality**:
   ```bash
   python3 scripts/bot.py validate --detailed
   ```

4. **Reduce model complexity** (in `config/model_config.yaml`):
   ```yaml
   xgboost:
     n_estimators: 100  # Reduce from 200
     max_depth: 4       # Reduce from 6
   ```

### Poor Model Performance

**Problem**: Trained models don't improve results

**Solutions**:

1. **Train with more data**:
   ```bash
   python3 scripts/bot.py train --model all --data-days 365
   ```

2. **Enable hyperparameter optimization**:
   ```bash
   python3 scripts/bot.py train --model all --optimize --processes 16
   ```

3. **Check feature engineering** - might need more/different features

4. **Verify training/test split** - check for data leakage

5. **Consider retraining regularly** (market conditions change)

## Data Issues

### Missing Historical Data

**Problem**: Required data files not found

**Solutions**:

```bash
# Check what data exists
ls data/raw/

# Download historical data
python3 -c "
from src.core.data_pipeline import DataPipeline
pipeline = DataPipeline()
pipeline.download_historical_data(days=180)
"

# Or use dedicated download script if available
python3 scripts/download_data.py --days 180
```

### Data Quality Issues

**Problem**: Corrupt or invalid data

**Solutions**:

1. **Validate data**:
   ```python
   import pandas as pd
   df = pd.read_csv('data/raw/BTC_USDT_PERP_1h.csv')
   
   # Check for NaN
   print(df.isnull().sum())
   
   # Check data types
   print(df.dtypes)
   
   # Check for duplicates
   print(df.duplicated().sum())
   
   # Check price ranges (should be reasonable)
   print(df[['open', 'high', 'low', 'close']].describe())
   ```

2. **Re-download data** if corrupt:
   ```bash
   rm data/raw/BTC_USDT_PERP_*.csv
   # Re-download
   ```

3. **Check timestamp ordering**:
   ```python
   df['timestamp'] = pd.to_datetime(df['timestamp'])
   assert df['timestamp'].is_monotonic_increasing
   ```

## General Tips

### Enable Debug Logging

```bash
# Set log level in config or environment
export LOG_LEVEL=DEBUG

# Or run with verbose flag
python3 scripts/bot.py backtest --config scalp_conservative --verbose
```

### Check System Status Regularly

```bash
# Quick health check
python3 scripts/bot.py status

# Detailed status
python3 scripts/bot.py status --detailed

# Validate configuration
python3 scripts/bot.py validate --detailed
```

### Run Tests After Changes

```bash
# Run all tests
python3 scripts/bot.py test

# Run integration tests
python3 scripts/bot.py test --type integration --verbose
```

### Profile for Performance Issues

```bash
# Quick profile
python3 scripts/bot.py profile

# Extended profile
python3 scripts/bot.py profile --bars 5000 --output profile.json
```

### Clean Start

If all else fails, try a clean installation:

```bash
# Backup data
cp -r data/ data_backup/

# Remove virtual environment
rm -rf venv/

# Create fresh environment
python3 -m venv venv
source venv/bin/activate

# Reinstall
pip install --upgrade pip
pip install -r requirements.txt

# Validate
python3 scripts/bot.py validate --detailed
```

## Getting Help

### Where to Get Help

1. **Documentation**:
   - [Getting Started](GETTING_STARTED.md)
   - [CLI Reference](CLI_REFERENCE.md)
   - [User Guide](USER_GUIDE.md)

2. **Built-in Help**:
   ```bash
   python3 scripts/bot.py --help
   python3 scripts/bot.py COMMAND --help
   ```

3. **Community**:
   - 💬 Discord: [Join Server](#)
   - 🐛 GitHub Issues: [Report Bug](../issues)
   - 📧 Email: support@example.com

### Reporting Bugs

When reporting issues, include:

1. **System information**:
   ```bash
   python3 --version
   pip list | grep -E '(tensorflow|xgboost|ccxt|pandas)'
   uname -a  # Linux/Mac
   ```

2. **Error message** (full traceback)

3. **Steps to reproduce**

4. **Expected vs actual behavior**

5. **Configuration** (remove sensitive info like API keys!)

---

**Need More Help?** Check the [User Guide](USER_GUIDE.md) or join our [Discord](#)

**Back to**: [README](../README.md) | [Getting Started](GETTING_STARTED.md) | [CLI Reference](CLI_REFERENCE.md)

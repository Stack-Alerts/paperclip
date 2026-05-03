# Optimizer V3 - User Guide
**Institutional-Grade Strategy Optimization System**

Version: 3.0.0  
Last Updated: 2026-01-20

---

## 📋 Table of Contents

1. [Getting Started](#getting-started)
2. [Quick Start Guide](#quick-start-guide)
3. [Understanding the Interface](#understanding-the-interface)
4. [Running an Optimization](#running-an-optimization)
5. [Understanding Results](#understanding-results)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Features](#advanced-features)
9. [Performance Tips](#performance-tips)
10. [FAQ](#faq)

---

## Getting Started

### Prerequisites

Before using Optimizer V3, ensure you have:

1. **System Requirements:**
   - Python 3.10 or higher
   - PostgreSQL 12 or higher
   - 8GB RAM minimum (16GB recommended)
   - 4 CPU cores minimum (8 cores recommended)
   - 10GB free disk space

2. **Software Installed:**
   - NautilusTrader (`pip install nautilus-trader`)
   - PyQt6 (`pip install PyQt6`)
   - All dependencies from `pyproject.toml`

3. **Database Setup:**
   - PostgreSQL running and accessible
   - Database `optimizer_v3` created
   - Credentials configured in `.env`

### Installation

```bash
# Clone repository
git clone https://github.com/Stack-Alerts/BTC_Engine_v3.git
cd BTC_Engine_v3

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -m src.optimizer_v3.database.init_db

# Launch application
python scripts/launch_strategy_builder.py
```

---

## Quick Start Guide

### 5-Minute Quick Start

1. **Open Strategy Builder**
   ```bash
   python scripts/launch_strategy_builder.py
   ```

2. **Load or Create a Strategy** (Window 1)
   - Click "Load Strategy" to use existing
   - Or build new strategy using blocks

3. **Configure Backtest** (Window 2, Tab 1)
   - Set date range
   - Configure risk parameters
   - Select timeframe

4. **Select Parameters to Optimize**
   - Check boxes next to parameters
   - Review estimated config count
   - Adjust ranges if needed

5. **Click "Optimize"**
   - Monitor progress in Tab 2 (Live Output)
   - View trades in Tab 3
   - Check metrics in Tab 4

6. **Review Results**
   - Compare configurations in Tab 5
   - Apply best config with "Apply Optimal"

---

## Understanding the Interface

### Window 1: Strategy Builder
Build and edit strategies using building blocks.

### Window 2: Backtest Configuration & Optimizer

#### Tab 1: Configuration
- **Backtest Settings:** Date range, timeframe, capital
- **Risk Parameters:** Stop loss, take profit, position size
- **Optimization Controls:**
  - Parameter checkboxes (select what to optimize)
  - Config count estimator
  - "Optimize" button

#### Tab 2: Live Output
- **Progress Bar:** Overall optimization progress
- **Current Config:** Details of currently running config
- **Resource Monitor:** CPU, Memory, Disk usage
- **Error Log:** Any errors encountered
- **Time Estimates:** ETA, elapsed time

#### Tab 3: Trades
- **Trade List:** All trades from all configurations
- **Trade Details:** Entry, exit, PnL, duration
- **Real-time Updates:** As trades execute
- **Export:** Save to Excel/CSV

#### Tab 4: Metrics
- **Performance Table:** All metrics for all configs
- **Sorted View:** Best to worst performance
- **Detailed Metrics:**
  - Sharpe Ratio
  - Win Rate
  - Profit Factor
  - Max Drawdown
  - Total PnL
  - Number of Trades
  - Risk/Reward Ratio

#### Tab 5: Compare
- **Side-by-Side:** Compare last 3 configurations
- **Difference Highlighting:** Green (better), Red (worse)
- **Parameter Comparison:** Original vs optimized
- **Statistical Significance:** Confidence levels

---

## Running an Optimization

### Step-by-Step Process

#### 1. Define Your Strategy
```
Example: HOD Rejection Strategy
- Entry: HOD rejection + RSI divergence
- Exit: Take profit or stop loss
- Risk: 1% per trade
```

#### 2. Configure Backtest Parameters

**Date Range:**
- Start: 2024-01-01
- End: 2024-12-31
- Timeframe: 15m

**Capital:**
- Starting: $10,000
- Position Size: 1% risk per trade

**Risk Management:**
- Stop Loss: 2% (or optimize)
- Take Profit: 4% (or optimize)
- Max Position Size: 0.1 BTC

#### 3. Select Parameters to Optimize

Check boxes for parameters you want to optimize:
- ☑ Stop Loss (range: 1% - 3%)
- ☑ Take Profit (range: 3% - 6%)
- ☐ Position Size (keep fixed at 1%)

**Config Count Estimate:** 20 configurations
**Estimated Time:** 15 minutes

#### 4. Monitor Progress

**Tab 2 shows:**
- Progress: 7/20 configs complete (35%)
- Current Config: SL=2.5%, TP=4.5%
- CPU: 85%, Memory: 1.2GB
- ETA: 10 minutes remaining

#### 5. Review Results

**Tab 4 - Top 3 Configs:**

| Rank | SL% | TP% | Sharpe | Win Rate | PnL |
|------|-----|-----|--------|----------|-----|
| 1 | 2.0 | 5.0 | 2.45 | 68% | $5,420 |
| 2 | 2.5 | 5.5 | 2.31 | 65% | $4,980 |
| 3 | 1.5 | 4.5 | 2.18 | 70% | $4,750 |

#### 6. Apply Best Configuration

Click "Apply Optimal Config" to use Rank 1 settings:
- Stop Loss: 2.0%
- Take Profit: 5.0%

---

## Understanding Results

### Key Metrics Explained

#### Sharpe Ratio
**What it is:** Risk-adjusted return measure  
**Range:** -3 to +5 (typically)  
**Good Value:** > 2.0  
**Interpretation:**
- < 1.0: Poor risk-adjusted returns
- 1.0 - 2.0: Good
- 2.0 - 3.0: Very good
- \> 3.0: Excellent

#### Win Rate
**What it is:** Percentage of winning trades  
**Range:** 0% - 100%  
**Good Value:** > 55%  
**Notes:** Higher isn't always better if wins are small

#### Profit Factor
**What it is:** Gross profit / Gross loss  
**Range:** 0 - ∞  
**Good Value:** > 1.5  
**Interpretation:**
- < 1.0: Losing strategy
- 1.0 - 1.5: Marginal
- 1.5 - 2.0: Good
- \> 2.0: Excellent

#### Max Drawdown
**What it is:** Largest peak-to-trough decline  
**Range:** 0% - 100%  
**Good Value:** < 20%  
**Critical:** Must be within your risk tolerance

#### Total PnL
**What it is:** Net profit/loss after all costs  
**Type:** Money (USD)  
**Good Value:** Positive and significant  
**Note:** Consider # of trades and time period

### Statistical Significance

**Confidence Levels:**
- ★★★ (99%): Very high confidence in results
- ★★☆ (95%): High confidence
- ★☆☆ (90%): Moderate confidence
- ☆☆☆ (<90%): Low confidence - needs more data

**Minimum Trade Count:** 30 trades for statistical validity

---

## Best Practices

### 1. Start Simple

**First Optimization:**
- Test 1-2 parameters only
- Use narrow ranges
- Limit to 10-20 configs

**Example:**
```
First run: Just test Stop Loss (1%-3%)
Second run: Add Take Profit (3%-6%)
Third run: Add position sizing
```

### 2. Use Appropriate Ranges

**Too Narrow:**
```
❌ Stop Loss: 1.9% - 2.1% (only 3 values)
   Not enough exploration
```

**Too Wide:**
```
❌ Stop Loss: 0.5% - 10% (100+ values)
   Too many configs, overfitting risk
```

**Just Right:**
```
✅ Stop Loss: 1.0% - 3.0% (10-20 values)
   Good balance of exploration
```

### 3. Validate Results

**Walk-Forward Testing:**
1. Optimize on Period A (e.g., Jan-Jun 2024)
2. Test on Period B (Jul-Dec 2024)
3. If still profitable, strategy robust

**Out-of-Sample Validation:**
- Reserve 20% of data for validation
- Never optimize on validation period
- Check if performance holds

### 4. Monitor Resource Usage

**Tab 2 Resource Monitor:**
- CPU: Should be 70-90% (efficient usage)
- Memory: Should stay < 2GB
- If critical levels reached, reduce workers

### 5. Save Your Work

**After Each Optimization:**
1. Export results to Excel (Tab 4)
2. Save strategy with new config (Window 1)
3. Document what you changed and why

---

## Troubleshooting

### Common Issues

#### Issue: "Database connection failed"

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify credentials in .env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=optimizer_v3
POSTGRES_USER=optimizer_admin
POSTGRES_PASSWORD=your_password_here

# Test connection
psql -h localhost -U optimizer_admin -d optimizer_v3
```

#### Issue: "Optimization running very slow"

**Causes & Solutions:**

1. **Too many workers:**
   ```
   Set MAX_WORKERS = CPU_CORES - 2
   ```

2. **Large date range:**
   ```
   Reduce from 1 year to 6 months
   Or use higher timeframe (15m → 1h)
   ```

3. **Too many parameters:**
   ```
   Optimize 2-3 parameters at a time
   Not 5-6 simultaneously
   ```

#### Issue: "Out of memory error"

**Solutions:**
```bash
# Reduce parallel workers
# In .env:
MAX_WORKERS=2  # Instead of 8

# Reduce history length
PERF_HISTORY_LENGTH=100  # Instead of 300

# Clear cache
rm -rf profiles/*
```

#### Issue: "No trades generated"

**Check:**
1. Strategy has valid signals
2. Date range has market data
3. Entry conditions not too strict
4. Position size not too small

### Error Messages

#### "NautilusTrader type error"
**Meaning:** Using wrong type (float instead of Money/Quantity)  
**Solution:** All financial values must use NautilusTrader types:
```python
# ❌ Wrong
stop_loss = 100.50  # float

# ✅ Correct
from nautilus_trader.model.objects import Money, Currency
usd = Currency.from_str("USD")
stop_loss = Money(100.50, usd)
```

#### "Config count too large"
**Meaning:** Too many parameter combinations  
**Solution:** Reduce ranges or parameters:
```
Before: 5 parameters × 20 values each = 3.2M configs
After: 3 parameters × 10 values each = 1,000 configs
```

---

## Advanced Features

### Early Stopping

Automatically stops optimization if no improvement:

```python
# In .env:
EARLY_STOP_PATIENCE=10  # Stop after 10 configs with no improvement
EARLY_STOP_MIN_DELTA=0.001  # Minimum improvement threshold
```

**When to use:**
- Large parameter spaces
- Time-constrained optimization
- Quick exploration

### Checkpoint Recovery

Auto-saves progress every N configs:

```python
# In .env:
ENABLE_CHECKPOINTS=true
CHECKPOINT_INTERVAL=5  # Save every 5 configs
```

**Benefits:**
- Resume if crash occurs
- Can stop/start optimization
- Protected against data loss

### Parameter Dependencies

Some parameters depend on others:

```python
# Example: Take Profit must be > Stop Loss
# Optimizer automatically enforces this

def validate_config(config):
    if config['take_profit'] <= config['stop_loss']:
        return False  # Invalid config
    return True
```

---

## Performance Tips

### 1. Optimal Worker Count

```python
# Formula:
optimal_workers = CPU_CORES - 2

# Example (8-core system):
MAX_WORKERS=6  # Leave 2 for OS
```

### 2. Use Caching

```python
# In .env:
TEST_CACHE_ENABLED=true  # Cache backtest data
TEST_CACHE_TTL=3600  # 1 hour cache lifetime
```

### 3. Database Optimization

```sql
-- Add indexes for faster queries
CREATE INDEX idx_config_sharpe ON results(sharpe_ratio);
CREATE INDEX idx_config_timestamp ON results(timestamp);
```

### 4. Reduce Logging

```python
# In .env:
LOG_LEVEL=WARNING  # Instead of DEBUG
TEST_LOG_LEVEL=ERROR  # Reduce test logging
```

---

## FAQ

### Q: How many configs should I test?
**A:** Start with 10-20 for quick exploration. For final optimization, 50-100 is good. Over 500 risks overfitting.

### Q: What's a good Sharpe ratio?
**A:** 
- \> 1.5: Acceptable
- \> 2.0: Good
- \> 3.0: Excellent
- \> 4.0: Exceptional (verify not overfit)

### Q: Should I optimize all parameters?
**A:** No. Start with 2-3 most impactful (usually stop loss, take profit). Add more only if needed.

### Q: How do I avoid overfitting?
**A:**
1. Use walk-forward testing
2. Validate on out-of-sample data
3. Limit parameter count
4. Require minimum 30 trades
5. Check statistical significance

### Q: Can I run multiple optimizations simultaneously?
**A:** Not recommended. Use all available workers for one optimization for faster results.

### Q: What if all configurations lose money?
**A:** 
1. Check strategy logic
2. Verify signal conditions
3. Test on different time period
4. Reduce parameter ranges
5. Add more building blocks

### Q: How long does optimization take?
**A:**
- 10 configs × 6 months data: ~5-10 minutes
- 50 configs × 1 year data: ~30-60 minutes
- 100 configs × 2 years data: ~2-4 hours

### Q: Do I need NautilusTrader knowledge?
**A:** No for basic use. The interface handles type conversions. For advanced features, NautilusTrader documentation helps.

### Q: Can I export results?
**A:** Yes. Click "Export" in Tab 4 to save as Excel. Click "Export Comparison" in Tab 5 for side-by-side analysis.

---

## Getting Help

### Documentation
- **Architecture:** `docs/v3/OPTIMIZER_V3_REQUIREMENTS.md`
- **NautilusTrader:** https://nautilustrader.io/docs/
- **Configuration:** `docs/v3/OPTIMIZER_V3_CONFIGURATION_SYSTEM.md`
- **Flow Diagrams:** `docs/v3/UI-UX/optimizer_v3_sprints/OPTIMIZER_V3_FLOW_DIAGRAM.md`

### Support
- **GitHub Issues:** https://github.com/Stack-Alerts/BTC_Engine_v3/issues
- **Email:** support@stackalerts.com

### Contributing
- See `CONTRIBUTING.md` for guidelines
- All contributions must pass tests
- Follow NautilusTrader type safety rules

---

## Appendix

### A. NautilusTrader Types Quick Reference

```python
from nautilus_trader.model.objects import Money, Quantity, Price, Currency
from nautilus_trader.model.enums import OrderSide, OrderType

# Money (always with currency)
usd = Currency.from_str("USD")
amount = Money(1000.50, usd)

# Quantity (position size)
qty = Quantity.from_str("0.1")

# Price
price = Price.from_str("50000.00")

# Order Side (use enum, not string)
side = OrderSide.BUY  # ✅ Correct
side = "BUY"  # ❌ Wrong
```

### B. Keyboard Shortcuts

- `Ctrl+O`: Open strategy
- `Ctrl+S`: Save strategy
- `Ctrl+B`: Run backtest
- `Ctrl+Shift+O`: Start optimization
- `Ctrl+E`: Export results
- `F5`: Refresh current view
- `Esc`: Cancel operation

### C. Configuration File Locations

```
~/.optimizer_v3/
├── config.json          # User preferences
├── cache/               # Cached backtest data
├── exports/             # Exported results
├── logs/                # Application logs
└── checkpoints/         # Optimization checkpoints
```

---

**Last Updated:** 2026-01-20  
**Version:** 3.0.0  
**Authors:** Stack Alerts Development Team

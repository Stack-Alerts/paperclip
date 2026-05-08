# BTC Trade Engine — User Guide

**Version:** 1.0  
**Platform:** BTC Trade Engine (Powered by NautilusTrader)  
**Audience:** Trade Engineers — systematic traders who build and automate strategies  
**Last Updated:** 2026-05-08

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard Overview](#2-dashboard-overview)
3. [Strategy Builder](#3-strategy-builder)
4. [Running Walk-Forward Tests](#4-running-walk-forward-tests)
5. [Autopilot / Live Trading](#5-autopilot--live-trading)
6. [Settings & Configuration](#6-settings--configuration)
7. [Monitoring & Logs](#7-monitoring--logs)
8. [Troubleshooting](#8-troubleshooting)
9. [Screenshot Requirements](#9-screenshot-requirements)

---

## 1. Getting Started

### 1.1 Prerequisites

Before launching the platform, confirm your system meets the following requirements:

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10 | 3.11+ |
| RAM | 8 GB | 16 GB |
| CPU Cores | 4 | 8+ |
| Disk Space | 10 GB free | 50 GB free |
| OS | Linux / macOS | Linux (Ubuntu 22.04+) |

You will also need:
- **PostgreSQL 12+** running locally or accessible over the network
- An active internet connection for live data feeds (Binance API)

### 1.2 Installation

```bash
# 1. Navigate to the project directory
cd /home/sirrus/projects/BTC-Trade-Engine-PaperClip

# 2. Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install all dependencies
pip install -r requirements.txt

# 4. Verify NautilusTrader is installed correctly
python -c "import nautilus_trader as nt; print(f'NautilusTrader v{nt.__version__} — OK')"
```

### 1.3 Environment Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Open `.env` in a text editor. The key settings are:

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_DB` | Database name | `optimizer_v3` |
| `POSTGRES_USER` | Database user | `optimizer_admin` |
| `POSTGRES_PASSWORD` | Database password | `your_password` |
| `BINANCE_API_KEY` | Binance API key (for live trading) | `your_api_key` |
| `BINANCE_SECRET` | Binance API secret | `your_secret` |
| `MAX_WORKERS` | Parallel backtest workers | `6` (CPU cores − 2) |

> **Security note:** Never share your `.env` file or commit it to version control. The API key and secret grant access to your exchange account.

### 1.4 Database Initialisation

```bash
# Initialise the database schema
python -m src.optimizer_v3.database.init_db
```

If PostgreSQL is not yet running:

```bash
# Start PostgreSQL (Linux)
sudo systemctl start postgresql
sudo systemctl enable postgresql   # auto-start on boot
```

### 1.5 Launching the Application

```bash
python scripts/launch_strategy_builder.py
```

The Strategy Builder main window will open. The platform is now ready to use.

> **Screenshot needed (1):** The application main window immediately after launch, showing the default empty state.

---

## 2. Dashboard Overview

The platform is built around a two-window layout:

| Window | Purpose |
|--------|---------|
| **Window 1 — Strategy Builder** | Create, load, and edit trading strategies |
| **Window 2 — Backtest & Optimizer** | Configure backtests, run optimizations, review results |

### 2.1 Window 1 — Strategy Builder

> **Screenshot needed (2):** Strategy Builder window with a sample strategy loaded, annotated with section labels.

The Strategy Builder window is divided into four main areas:

**Block Search & Filter (left panel)**  
Browse all available building blocks — patterns, oscillators, price levels, sessions, trend indicators, and more. Use the search bar to filter by name. Click a block to view its signals and description before adding it.

**Strategy Configuration (centre panel)**  
The working area where you assemble your strategy. Blocks appear here after you add them. Each block shows its logic type (AND / OR), weight, and configured signals. Drag blocks up or down to reorder them, or use the ▲ / ▼ arrows.

**Strategy Info Panel (top)**  
Shows the strategy name, auto-generated description, bullish/bearish type indicator, and the count of required signals (AND blocks).

**Real-time Preview (right panel)**  
A live mini-backtest that runs on the last 30 days of data whenever you change the strategy. Shows a candlestick chart with signal markers and quick metrics (signals triggered, estimated win rate, estimated P&L). Updates automatically within 500 ms of each change.

### 2.2 Window 2 — Backtest & Optimizer

> **Screenshot needed (3):** Backtest & Optimizer window showing all five tabs with Tab 1 (Configuration) active.

Window 2 has five tabs:

| Tab | Name | Purpose |
|-----|------|---------|
| 1 | Configuration | Set date range, risk parameters, optimization settings |
| 2 | Live Output | Monitor progress in real time during a run |
| 3 | Trades | Browse all trade records from the current run |
| 4 | Metrics | Compare performance statistics across configurations |
| 5 | Compare | Side-by-side view of the last three configurations |

---

## 3. Strategy Builder

A *strategy* is a set of building blocks — each representing a market signal or condition — combined with logic rules that together define when to enter and exit a trade.

### 3.1 Core Concepts

**Building Blocks**  
Self-contained market indicators or pattern detectors. Each block belongs to a category (e.g., PATTERNS, OSCILLATORS, PRICE_LEVELS) and emits one or more named signals (e.g., `BEARISH_BREAKDOWN`, `OVERBOUGHT`).

**AND vs. OR Logic**  
When you add a block you choose its logic type:
- **AND (Required):** The block's signal *must* fire for a trade entry to be considered.
- **OR (Optional / Booster):** The block adds to the confluence score but is not required on its own.

**Confluence Score**  
Each block has a *weight* (a number, typically 10–40). The confluence score is the sum of weights of all blocks whose signals are currently active. A trade entry is only triggered when the score reaches the configured minimum (default: 70 out of 100).

**Signal Roles**  
Within a block, each signal is assigned a role:
- **SIGNAL** — The primary entry trigger.
- **FILTER** — Must be true; eliminates low-quality setups.
- **BOOSTER** — Increases confluence score when active.

**Strategy Categories**  
Reversal, Continuation, Scalping, Range Trading, Breakout, Momentum, Mean Reversion. Choose the category that best describes your trade thesis.

### 3.2 Creating a New Strategy

1. In Window 1, click **New Strategy**.
2. Enter a descriptive name (e.g., `m_pattern_rsi_london`). Names must be unique.
3. The strategy info panel appears at the top. The centre panel is now empty and ready for blocks.

### 3.3 Adding Building Blocks

1. In the search bar (left panel), type a block name (e.g., `double top`) or browse by category.
2. Click the block to expand its detail card — review the available signals, typical occurrence rate, and weight range.
3. Click **Add as AND** (required) or **Add as OR** (optional/booster).
4. The block appears in the centre panel. A default signal is pre-selected.

> **Tip:** Start with one primary pattern block set to AND, then add one or two confirming blocks (oscillators, price levels) also as AND. Add further supporting blocks as OR boosters.

### 3.4 Configuring Signals Within a Block

1. Click on a block in the centre panel to expand its signal configuration.
2. The default signal is shown. Click **Add Signal** to add another signal from the same block.
3. For each signal, choose its role (SIGNAL / FILTER / BOOSTER).
4. Optionally enable **Within X Candles**: tick the checkbox, enter a candle count (e.g., `20`), and choose a reference signal. This means signal B must have fired within 20 candles of signal A.

### 3.5 Configuring Stop Loss and Take Profit

Expand the **Adaptive SL/TP Configuration** panel below the block list:

| Setting | Options | Description |
|---------|---------|-------------|
| Stop Loss Mode | Fibonacci, Aggressive, Conservative | How the stop loss distance is calculated |
| SL Fibonacci Level | 0.236, 0.382, 0.5, 0.618 | Retracement level used as SL anchor |
| Take Profit Mode | Fibonacci, Hybrid, Static | How profit targets are set |
| TP1 / TP2 / TP3 | Percentage values | Partial exit levels (e.g., 1.5%, 3.0%, 5.0%) |

> **Screenshot needed (4):** The Adaptive SL/TP panel in expanded state with example values filled in.

### 3.6 Validating a Strategy

The platform validates your strategy continuously. Errors appear as a red badge on the affected block, with a tooltip explaining the issue. Common validation errors:

| Error | Meaning | Fix |
|-------|---------|-----|
| Main signal block not found | The main signal block name does not match any added block | Ensure the first AND block is the primary pattern |
| Block not found in registry | A block name is misspelled or not yet available | Use the search panel to find the correct name |
| Weight out of range | A block's weight is outside its allowed range | Adjust the weight slider to the valid range |
| No SIGNAL role found | No signal has the SIGNAL role assigned | Assign SIGNAL role to at least one signal |
| Conflicting patterns | Both bullish and bearish signals exist | Use only bullish OR bearish signals, not both |

When all errors are cleared, the strategy is valid and ready to save.

### 3.7 Saving and Loading Strategies

**Save:** Click **Save Strategy**. The configuration is saved as a JSON file in `user_strategies/`. The strategy is auto-numbered (e.g., strategy 001).

**Load:** Click **Load Strategy**. A list of saved strategies appears, showing name, type (Bullish/Bearish), and last modified date. Click a strategy to load it back into the builder.

**Export / Import:** Use File → Export to save a strategy to a custom location. Use File → Import to bring in a strategy from another location (useful for sharing).

---

## 4. Running Walk-Forward Tests

Walk-forward testing is the primary way to validate a strategy on historical data before risking real capital.

### 4.1 What Is Walk-Forward Testing?

Walk-forward testing simulates trading your strategy on a historical data window, candle by candle. Unlike a simple backtest, the expanding-window approach avoids peeking at future data — giving a realistic picture of how the strategy would have performed in real conditions.

### 4.2 Configuring a Test (Tab 1)

In Window 2, Tab 1:

**Date Range**

| Field | Description | Example |
|-------|-------------|---------|
| Start Date | Beginning of test period | `2024-01-01` |
| End Date | End of test period | `2024-12-31` |
| Timeframe | Candle size | `15m` (default) |

**Capital & Risk**

| Field | Description | Example |
|-------|-------------|---------|
| Starting Capital | Account size in USD | `$10,000` |
| Risk Per Trade | Percentage of capital at risk | `1%` |
| Max Position Size | Maximum BTC per trade | `0.1 BTC` |

**Stop Loss & Take Profit**  
Set values here if you want to test fixed parameters. Leave unchecked to use the Adaptive SL/TP configuration from the Strategy Builder.

### 4.3 Test Modes

**Mode 1 — Historical Walk-Forward**  
Tests your strategy from a point in the past to the present. Each candle is processed in sequence. Results are shown when the last candle is reached. Use this mode for strategy development and validation.

**Mode 2 — Live Continuation**  
Starts with a historical walk-forward phase, then continues processing new live candles as they arrive in real time. Use this mode to monitor a strategy that has been historically validated and to observe it on current market conditions.

### 4.4 Running a Test

1. Ensure your strategy is loaded in Window 1 (it will be highlighted in the strategy list).
2. In Window 2, Tab 1, fill in the date range, capital, and risk parameters.
3. Click **Run Test**.
4. Watch progress in **Tab 2 (Live Output)**.

> **Screenshot needed (5):** Tab 2 (Live Output) mid-run, showing progress bar, current config details, and resource monitor.

### 4.5 Reading the Results

**Tab 3 — Trades**  
Each row is one completed trade. Columns include:

| Column | Description |
|--------|-------------|
| Entry Time | When the position was opened |
| Exit Time | When the position was closed |
| Side | Long or Short |
| Entry Price | Price at entry |
| Exit Price | Price at exit |
| PnL | Profit or loss in USD |
| Duration | How long the trade was held |

**Tab 4 — Metrics**  
Performance statistics for the run (or, during optimisation, for every parameter combination tested):

| Metric | What It Means | Good Value |
|--------|--------------|------------|
| Sharpe Ratio | Risk-adjusted return | > 2.0 |
| Win Rate | % of trades that were profitable | > 55% |
| Profit Factor | Gross profit ÷ gross loss | > 1.5 |
| Max Drawdown | Largest peak-to-trough decline | < 20% |
| Total PnL | Net profit/loss in USD | Positive |
| Trade Count | Number of completed trades | > 30 for statistical validity |

> **Screenshot needed (6):** Tab 4 (Metrics) showing a results table with at least five configurations ranked by Sharpe Ratio.

**Tab 5 — Compare**  
Shows the last three parameter configurations side-by-side. Cells highlighted in green are improvements; cells in red are regressions. Use this to quickly see which parameter change made the difference.

---

## 5. Autopilot / Live Trading

> **Warning:** Live trading involves real financial risk. Only activate Autopilot after thorough walk-forward validation on multiple time periods and after careful review of your risk settings.

### 5.1 What Autopilot Does

Autopilot connects the platform to Binance Futures (BTC/USDT Perpetual) and places real orders automatically whenever your strategy's confluence conditions are met. The platform runs continuously, processing each new 15-minute candle.

### 5.2 Prerequisites Before Going Live

Before activating Autopilot:

- [ ] Binance API key and secret are entered in `.env`
- [ ] The API key has **Futures trading enabled** on Binance (but *not* withdrawals)
- [ ] The strategy has been walk-forward validated on at least 6 months of data
- [ ] Sharpe Ratio > 1.5 on the validation period
- [ ] Max Drawdown < 20% on the validation period
- [ ] Risk per trade is set to a comfortable level (start with 0.5%–1%)

### 5.3 Activating Autopilot

1. In Window 1, load the strategy you wish to run live.
2. In Window 2, Tab 1, confirm risk parameters.
3. Switch to **Mode 2 (Live Continuation)** and click **Run Test** — this will run the historical phase first.
4. Once the historical phase completes and you see "Historical complete. Waiting for live candles…", the strategy is now live.
5. New candles are processed automatically every 15 minutes.

> **Screenshot needed (7):** The Live Continuation status panel showing "LIVE" status, historical period complete, and real-time P&L updating.

### 5.4 Monitoring a Live Strategy

During live operation, Tab 2 shows:

| Field | Description |
|-------|-------------|
| Test Status | 🟢 LIVE |
| Historical Period | Days of historical data (complete) |
| Live Period | Days/hours since live mode started |
| New Candles Processed | Count of live candles seen |
| Live P&L | Current running P&L since going live |

### 5.5 Stopping Autopilot

Click **Stop Test** at any time. The platform will:
1. Close any open positions (if configured to do so — check your risk settings)
2. Generate a final performance report covering the full test period (historical + live)
3. Return the window to idle state

### 5.6 Risk Management Safeguards

The platform has built-in safeguards:

| Safeguard | Description |
|-----------|-------------|
| Per-trade risk limit | Each trade risks at most `RISK_PER_TRADE_PCT` of capital |
| Max leverage cap | Leverage is capped at the value set in the strategy config (default: 2×) |
| Stop loss enforcement | All entries place a stop loss order simultaneously |
| Max bars held | Positions are force-closed after `MAX_BARS_HELD` candles (default: 1000) |

---

## 6. Settings & Configuration

### 6.1 Environment Variables (`.env`)

All runtime settings are controlled via the `.env` file. After editing, restart the application for changes to take effect.

**Database**

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | Database name | `optimizer_v3` |
| `POSTGRES_USER` | Database username | — |
| `POSTGRES_PASSWORD` | Database password | — |

**Exchange API**

| Variable | Description |
|----------|-------------|
| `BINANCE_API_KEY` | Binance Futures API key |
| `BINANCE_SECRET` | Binance Futures API secret |
| `BINANCE_TESTNET` | Set to `true` to use Binance testnet (paper trading) |

**Performance**

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_WORKERS` | Parallel backtest workers | CPU cores − 2 |
| `TEST_CACHE_ENABLED` | Cache backtest data to disk | `true` |
| `TEST_CACHE_TTL` | Cache lifetime in seconds | `3600` |
| `PERF_HISTORY_LENGTH` | Candles kept in memory for metrics | `100` |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |

**Optimiser**

| Variable | Description | Default |
|----------|-------------|---------|
| `EARLY_STOP_PATIENCE` | Stop after N configs with no improvement | `10` |
| `EARLY_STOP_MIN_DELTA` | Minimum improvement threshold | `0.001` |
| `ENABLE_CHECKPOINTS` | Save progress during optimisation | `true` |
| `CHECKPOINT_INTERVAL` | Save every N configs | `5` |

### 6.2 Strategy-Level Risk Settings

Each strategy stores its own risk settings in its JSON configuration file (`user_strategies/`):

| Setting | Description | Default |
|---------|-------------|---------|
| `min_confluence` | Minimum score required to trigger a trade | `70` |
| `risk_per_trade_pct` | % of capital risked per trade | `1.0` |
| `max_leverage` | Maximum leverage multiplier | `2.0` |
| `max_bars_held` | Force-close after this many candles | `1000` |
| `risk_reward_ratio` | Minimum R:R target | `1:3` |

### 6.3 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + O` | Open / load strategy |
| `Ctrl + S` | Save strategy |
| `Ctrl + B` | Run backtest |
| `Ctrl + Shift + O` | Start optimisation |
| `Ctrl + E` | Export results |
| `F5` | Refresh current view |
| `Esc` | Cancel running operation |

---

## 7. Monitoring & Logs

### 7.1 Log Files

The application writes logs to the `logs/` directory. Log files are named by date (e.g., `strategy_builder_2026-05-08.log`).

| Log Level | What Is Recorded |
|-----------|-----------------|
| DEBUG | Detailed internal state (verbose; enable only when debugging) |
| INFO | Normal operation events — trades opened/closed, candles processed |
| WARNING | Non-fatal issues — missed candles, slow response from exchange |
| ERROR | Failures that need attention — database errors, API failures |

To view logs in real time:

```bash
tail -f logs/strategy_builder_$(date +%Y-%m-%d).log
```

### 7.2 System Status Indicators

Within the application, status indicators appear in the Live Output tab:

| Indicator | Meaning |
|-----------|---------|
| 🟢 LIVE | Strategy running, receiving live candles |
| 🟡 RUNNING | Backtest or optimisation in progress |
| 🔴 ERROR | An error occurred; check the error log panel |
| ⚪ IDLE | Application ready, no active run |

### 7.3 Resource Monitor

Tab 2 shows live resource usage:

| Metric | Good Range | Action If Exceeded |
|--------|-----------|-------------------|
| CPU | 70%–90% | Reduce `MAX_WORKERS` in `.env` |
| Memory | < 2 GB | Reduce `PERF_HISTORY_LENGTH` or clear cache |
| Disk | < 80% | Delete old optimiser output files or archive them |

---

## 8. Troubleshooting

### 8.1 Application Will Not Start

**Symptom:** Error on launch — `ImportError` or `ModuleNotFoundError`

**Fix:**
```bash
# Ensure the virtual environment is active
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify NautilusTrader
python -c "import nautilus_trader; print('OK')"
```

### 8.2 Database Connection Failed

**Symptom:** `Database connection failed` error on launch or when running a test.

**Fix:**
```bash
# Confirm PostgreSQL is running
sudo systemctl status postgresql

# Test the connection manually
psql -h localhost -U optimizer_admin -d optimizer_v3

# Check .env credentials match PostgreSQL user and database
```

### 8.3 No Trades Generated

**Symptom:** Backtest completes but the trade count is 0.

**Possible causes and fixes:**

| Cause | Fix |
|-------|-----|
| Confluence threshold too high | Lower `min_confluence` in strategy settings (try 60) |
| No blocks with SIGNAL role | Ensure at least one signal has the SIGNAL role |
| Date range has no market data | Check that your data covers the selected date range (`data/` folder) |
| AND blocks too restrictive | Try changing some AND blocks to OR temporarily to verify signals fire |

### 8.4 Optimisation Running Very Slowly

**Symptom:** Estimated time is hours for a small number of configurations.

**Fix:**
- Reduce `MAX_WORKERS` to CPU cores − 2 (avoid over-parallelism)
- Shorten the test date range
- Reduce the number of parameters being optimised (2–3 at a time is ideal)
- Enable `TEST_CACHE_ENABLED=true` in `.env` so historical data is not reloaded each run

### 8.5 Out-of-Memory Error

**Symptom:** Application crashes with a memory error during a large optimisation.

**Fix:**
```
# In .env:
MAX_WORKERS=2
PERF_HISTORY_LENGTH=100

# Delete cached data
rm -rf profiles/*
```

### 8.6 Live Trading — Orders Not Placing

**Symptom:** Live mode is running but no orders appear on Binance.

**Checklist:**
- [ ] `BINANCE_API_KEY` and `BINANCE_SECRET` are correctly set in `.env`
- [ ] API key has Futures trading enabled (not just spot)
- [ ] `BINANCE_TESTNET` is set to `false` (or removed from `.env`)
- [ ] Account has sufficient margin for the configured position size
- [ ] Strategy is in LIVE status (🟢), not just historical phase

### 8.7 Signal Not Firing as Expected

**Symptom:** You expect a pattern to trigger but no signal appears.

**Fix:**
- Use the Real-time Preview panel to verify signals on recent candles
- Check the signal role is set to SIGNAL (not FILTER or BOOSTER)
- Check timing constraints — a `Within X Candles` constraint may be filtering out valid setups
- Review block weight — if the confluence threshold is 70 and the block weight is only 20, additional blocks must also fire

---

## 9. Screenshot Requirements

The following screenshots are needed to complete this user guide. Please capture each on a real or representative system state:

| # | Section | Screen / Window | What to Show |
|---|---------|----------------|-------------|
| 1 | 1.5 Launching | Main window after launch | Empty/default state of both windows |
| 2 | 2.1 Strategy Builder | Window 1 with strategy loaded | Annotated: block search, centre panel, info panel, preview |
| 3 | 2.2 Backtest Window | Window 2, Tab 1 active | All five tabs visible, Configuration tab fields |
| 4 | 3.5 SL/TP Config | Adaptive SL/TP panel expanded | Example values: Fibonacci SL at 0.618, TP1=1.5%, TP2=3.0% |
| 5 | 4.4 Running Test | Tab 2 during active run | Progress bar, current config info, resource monitor |
| 6 | 4.5 Results | Tab 4 Metrics | Results table, at least 5 rows, sorted by Sharpe Ratio |
| 7 | 5.3 Live Mode | Live Continuation status | "LIVE" status badge, historical complete, live P&L counter |

---

*For architecture and developer documentation, see `docs/architecture/`. For strategy reference, see `docs/strategies/`. For building block signal details, see `docs/building-blocks/`.*

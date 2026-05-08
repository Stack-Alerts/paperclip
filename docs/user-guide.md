# BTC Trade Engine — User Guide

**Version:** 1.0  
**Platform:** BTC Trade Engine (Powered by NautilusTrader)  
**Audience:** Trade Engineers — systematic traders who build and automate strategies  
**Last Updated:** 2026-05-08

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Application Overview](#2-application-overview)
3. [Strategy Builder — Main Window](#3-strategy-builder--main-window)
4. [The Four-Step Workflow](#4-the-four-step-workflow)
5. [Strategy Browser](#5-strategy-browser)
6. [Backtest Configuration Window](#6-backtest-configuration-window)
7. [Settings](#7-settings)
8. [Data Management](#8-data-management)
9. [Debug Logger](#9-debug-logger)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Getting Started

### 1.1 Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10 | 3.11+ |
| RAM | 8 GB | 16 GB |
| CPU Cores | 4 | 8+ |
| Disk Space | 10 GB free | 50 GB free |
| OS | Linux / macOS | Linux (Ubuntu 22.04+) |

You also need:
- **PostgreSQL 12+** running locally or accessible over the network (all strategies are stored in the database)
- An active internet connection for live data updates from Binance

### 1.2 Installation

```bash
# 1. Navigate to the project directory
cd /path/to/BTC-Trade-Engine-PaperClip

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

Edit `.env` with your settings. Key variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_HOST` | Database host | `localhost` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_DB` | Database name | `optimizer_v3` |
| `POSTGRES_USER` | Database user | `optimizer_admin` |
| `POSTGRES_PASSWORD` | Database password | `your_password` |

> **Security note:** Never share your `.env` file or commit it to version control. API keys are stored securely in the OS keyring — do not put them in `.env`. Use **Tools → Settings** to configure API keys once the application is running.

### 1.4 Database Initialisation

```bash
# Start PostgreSQL if it is not already running (Linux)
sudo systemctl start postgresql

# Initialise the database schema
python -m src.optimizer_v3.database.init_db
```

### 1.5 Launching the Application

```bash
python scripts/launch_strategy_builder.py
```

This starts the **BTC Trade Engine — Strategy Builder** main window. On first launch, a data update modal appears automatically to fetch the latest BTC/USDT candle data from Binance before the auto-update system starts.

---

## 2. Application Overview

The BTC Trade Engine is a single-window desktop application (PyQt5) centred on one primary window: the **Strategy Builder**. All other windows — the Strategy Browser, Backtest Configuration, Validation Report, Settings, and Log Viewer — open as independent floating windows from the menu bar or toolbar.

### 2.1 Window Title

The window title always shows the currently loaded strategy name and an asterisk (`*`) when there are unsaved changes:

```
BTC Trade Engine - Strategy Builder — MyStrategy *
```

### 2.2 Layout

The main window is split into two resizable panes separated by a draggable splitter handle:

| Pane | Contents |
|------|----------|
| **Left (40%)** | Strategy Information Panel (top) + Strategy Blocks Panel (bottom) |
| **Right (60%)** | Block Search Panel |

Both panes are non-collapsible — they cannot be dragged to zero width.

---

## 3. Strategy Builder — Main Window

### 3.1 Menu Bar

The menu bar has four menus:

#### File Menu
| Action | Shortcut | Description |
|--------|----------|-------------|
| New Strategy | Ctrl+N | Reset to a blank strategy (prompts to save if unsaved changes exist) |
| Open Strategy… | Ctrl+O | Open the **Strategy Browser** to load a saved strategy from the database |
| Save Strategy | Ctrl+S | Save the current strategy to the database as a new version |
| Save Strategy As… | Ctrl+Shift+S | Save a copy under a new name (creates a new strategy record) |
| Exit | Ctrl+Q | Close the application |

#### Edit Menu
| Action | Description |
|--------|-------------|
| Clear All Blocks | Remove all building blocks from the current strategy (cannot be undone) |

#### Tools Menu
| Action | Description |
|--------|-------------|
| Update Data… | Manually open the data update modal to fetch the latest candles from Binance |
| Verify Data… | Run a read-only integrity scan across all timeframes and report gaps |
| Settings… | Open the Settings dialog (API keys, preferences, admin options) |
| Debug Logger | Submenu to toggle console/logfile debug output and view the current log |

#### Help Menu
| Action | Description |
|--------|-------------|
| About Strategy Builder | Show version and capability information |

### 3.2 Toolbar

The toolbar sits below the menu bar and contains:

- **New** — create a new strategy
- **Open** — open the Strategy Browser
- **Save** — save the current strategy
- **Stepper Ribbon** (centred) — the four-step workflow progress indicator

### 3.3 Stepper Ribbon

The stepper ribbon displays the four workflow steps as clickable buttons:

```
📝 Design  →  ✓ Validate  →  🧪 Test / Optimize  →  🚀 Publish
```

Each step button changes colour to reflect its state:

| Colour | State |
|--------|-------|
| Grey | Pending (not yet reached) |
| Blue | Currently active |
| Green (✓) | Completed successfully |
| Red (✗) | Failed (e.g. validation errors) |

Clicking a step button advances to that step **if its prerequisites are met**:

- **Design (Step 0):** Always available.
- **Validate (Step 1):** Requires a strategy name and at least one block.
- **Test / Optimize (Step 2):** Requires validation to have passed (green).
- **Publish (Step 3):** Requires a test to have been initiated.

> Any modification to the strategy (adding/removing blocks, changing the name or type, reconfiguring signals) resets the Validate step back to its default state and requires re-validation.

### 3.4 Strategy Information Panel (Left — Top)

The **Strategy Information Panel** is the upper section of the left pane, labelled **"Strategy Information"**. It contains:

- **Strategy Name** — editable text field; required before saving.
- **Description** — auto-generated read-only text area that updates when blocks are added or removed.
- **Strategy Type** — radio buttons: **Bullish** (long) or **Bearish** (short).
- **Metadata summary row** — shows counts of required signals, optional signals, rechecked signals, exit conditions, and time constraints as the strategy is assembled.

### 3.5 Strategy Blocks Panel (Left — Bottom)

The **Strategy Blocks Panel** occupies the lower section of the left pane. It is a scrollable list showing every building block that has been added to the strategy, in the order they will be evaluated.

Each block entry shows:
- The block name (formatted display name)
- Its signals, with AND/OR logic badges
- Timing constraints (if configured)
- Recheck settings (if configured)
- Exit conditions attached to each signal or block
- Controls: **▲ Up**, **▼ Down** (reorder), **✕ Remove**
- A gear button on each signal to configure recheck settings
- Exit condition buttons to add, edit, or remove exit conditions

### 3.6 Block Search Panel (Right)

The **Block Search Panel** on the right side lets you browse and add building blocks to your strategy.

Features:
- **Search bar** — filter blocks by name in real time
- **Category filter** — dropdown to filter by block category
- **Block list** — expandable items; click to expand a block and see its available signals
- **Signal checkboxes** — select which signals within a block to add
- **Add as AND / Add as OR** — add selected signals with the chosen logic type
- **Added indicator** — once a block is added, its button updates to show it has been added (green checkmark)

> Signals marked as exit signals can also be added directly as exit conditions from this panel using the exit button alongside each signal.

---

## 4. The Four-Step Workflow

### Step 0 — Design

This is where you build your strategy:

1. Enter a **Strategy Name** in the Strategy Information Panel.
2. Select **Bullish** or **Bearish** as the strategy type.
3. In the Block Search Panel (right), find building blocks and expand them to view their signals.
4. Select the signals you want, then click **Add as AND** or **Add as OR**.
5. In the Strategy Blocks Panel (left), reorder blocks with the ▲/▼ arrows.
6. Optionally configure **timing constraints** on signals (gear icon → timing constraint dialog) to require signals to fire within a set number of candles of each other.
7. Optionally configure **recheck settings** to require a signal to be confirmed again after a bar delay.
8. Optionally add **exit conditions** to define when to close positions.

### Step 1 — Validate

Click the **Validate** step button in the Stepper Ribbon. The application runs an institutional-grade validation check on the strategy configuration and opens the **Validation Report Window**.

The Validation Report shows:
- Blocking issues (must be fixed before proceeding)
- Warnings (recommended but not mandatory)
- Auto-fix suggestions for common issues (click "Apply Fix" where available)

If validation passes, the Validate button turns green (✓) and the status is persisted to the database automatically.

If validation fails, the button turns red (✗) and you must address the blocking issues and re-run validation.

### Step 2 — Test / Optimize

Click the **Test / Optimize** step button. This opens the **Backtest Configuration Window** — see [Section 6](#6-backtest-configuration-window) for full details.

Signal calibration runs automatically when you click **Run Test** inside that window.

### Step 3 — Publish

Click the **Publish** step button to manage the publish status of the strategy. *(Publish status management is a forthcoming feature.)*

---

## 5. Strategy Browser

The **Strategy Browser** is a standalone window that opens via **File → Open Strategy…** (Ctrl+O) or the **Open** toolbar button.

### 5.1 Purpose

The Strategy Browser is the primary way to **load, manage, and organise strategies stored in the database**. There are no JSON files — all strategy data is persisted in PostgreSQL.

### 5.2 Window Layout

The Strategy Browser window (`StrategyBrowserDialog`) is split into two vertical sections by a draggable splitter:

- **Upper section** — strategy table
- **Lower section** — strategy details panel (shown when a strategy is selected)

### 5.3 Header and Filters

At the top of the window:
- **Search box** — type to filter strategies by name, description, type, or date in real time
- **Strategy Type filter** — dropdown: All / Bullish / Bearish
- **Strategy count** — shows how many strategies match the current filter

### 5.4 Strategy Table

The table has six columns:

| Column | Description |
|--------|-------------|
| Strategy Name | Name and a colour-coded summary of the first three blocks and their signals |
| Type | Bullish (green dot) or Bearish (red dot) |
| Version | Dropdown to select which version to load (each save creates a new version) |
| Last Modified | Date and time the version was created |
| Validation | `Un-Validated` (grey), `Pass` (green), or `Fail` (red) |
| Published | Draft / Published status |

Clicking a row selects it and populates the details panel. **Double-clicking a row opens the strategy immediately.**

Columns are sortable by clicking the header.

### 5.5 Strategy Details Panel

When a strategy is selected, the lower panel shows three columns:

- **Strategy Information** — name, type badge, description, version number, creation date, and tags
- **Configuration** — a hierarchical display of all signals with their AND/OR logic, timing constraints, recheck settings, and exit conditions at signal, block, and strategy level
- **Performance** — test count, best Sharpe ratio, win rate, total trades, and a brief summary from the best backtest result

### 5.6 Action Buttons

| Button | Availability | Description |
|--------|-------------|-------------|
| Delete | When a row is selected | Permanently delete the selected strategy (or specific versions) from the database |
| Duplicate | When a row is selected | Create a copy of the selected strategy as a new database entry |
| Export to JSON | When a row is selected | Export the strategy configuration to a JSON file for backup or transfer |
| Import from JSON | Always | Import a previously exported JSON file back into the database |
| Cancel | Always | Close the browser without loading anything |
| Open | When a row is selected | Load the selected strategy (at the chosen version) into the Strategy Builder |

### 5.7 Strategy Versioning

Every **Save** (Ctrl+S) creates a **new version** of the strategy in the database — it does not overwrite the previous version. The Version column in the Strategy Browser shows a dropdown listing all available versions (v1, v2, v3, …). You can select an older version to load a historical snapshot.

**Save As** creates an entirely new strategy record with a new name and its own independent version history.

---

## 6. Backtest Configuration Window

The Backtest Configuration Window (`BacktestConfigDialog`) opens when you click the **Test / Optimize** step in the Stepper Ribbon or click **Open** in the relevant context. It is a non-modal floating window with six tabs.

### 6.1 Tab 1 — Config

Configure and launch a backtest run. Key settings include:

- **Lookback Days** — how many days of historical data to use
- **Training Window** — the walk-forward training window size
- **Mode 1 / Mode 2** — historical backtest or live replay mode
- **TP/SL Configuration** — take-profit and stop-loss parameters
- **Starting Capital** — initial account balance in USDT

Click **▶ Run Test** to start. Signal calibration runs automatically before the backtest executes.

### 6.2 Tab 2 — Live Output

A real-time scrolling log of all output from the running backtest, including data loading progress, NautilusTrader engine messages, and any errors.

### 6.3 Tab 3 — Trades

A live table of all trades executed during the backtest, updated in real time as the run progresses.

### 6.4 Tab 4 — Metrics

Performance analysis for the completed (or running) backtest, including:
- Sharpe ratio, Sortino ratio, Calmar ratio
- Win rate, profit factor, maximum drawdown
- Total trades, average trade duration
- Equity curve summary

### 6.5 Tab 5 — AI Recommendations

An AI-powered recommendations panel that previews and sends analysis requests to the configured AI model (via OpenRouter). Provides intelligent suggestions for improving strategy parameters based on backtest results.

### 6.6 Tab 6 — Compare

Side-by-side comparison of two different backtest configurations, allowing you to evaluate the impact of parameter changes.

### 6.7 Pause, Resume, and Stop

During a running backtest, controls are available to **Pause**, **Resume**, and **Stop** execution.

---

## 7. Settings

Open via **Tools → Settings…**. The Settings dialog has three tabs:

### 7.1 Tab — API Keys

Secret fields for credentials. Each field shows a masked display (last 4 characters only). Controls:
- **Show 10s** — reveals the full value in plain text for 10 seconds, then auto-masks
- **Edit** — enter edit mode to change the value (leave blank to keep the existing value)

API key fields:
| Field | Description |
|-------|-------------|
| OpenRouter AI Key | API key for AI recommendations (via OpenRouter) |
| LakeAPI Key | API key for LakeAPI market data |
| LakeAPI Secret | API secret for LakeAPI |

> All secret values are stored in the **OS keyring** (GNOME Keyring on Linux, Keychain on macOS), never in `.env` or any plain-text file.

### 7.2 Tab — Preferences

Non-secret user settings organised in groups:

- **AI Configuration** — AI model identifier (e.g. `anthropic/claude-4.5-sonnet`)
- **Performance & Resources** — CPU workers, memory limits, update intervals
- **Data & API** — LakeAPI region, monthly transfer limit
- **Alerts & Logging** — enable alerts, log level, alert email address
- **UI Preferences** — dark theme, UI theme

### 7.3 Tab — Admin (PIN-Protected)

The Admin tab is hidden until you authenticate with an admin PIN (click **"Admin Access"** below the tabs and enter your PIN).

Admin settings cover database connection details, connection pool configuration, DB SSL, backup settings, risk management thresholds, optimization ranges, and performance metric weights.

> **First-time use:** If no admin PIN is set, you will be prompted to create one. The PIN is stored as a bcrypt hash in the OS keyring — it is never stored in plain text.

---

## 8. Data Management

### 8.1 Automatic Data Updates

When the application starts, it displays a **Data Update Modal** that checks for missing BTC/USDT candle data and fetches any gaps from Binance. This modal closes automatically once the update completes.

After startup, the application runs a **background auto-update cycle** every 15 minutes that:
1. Detects any gaps in the 15-minute and 1-hour bar datasets
2. Downloads missing bars from Binance
3. Updates the status bar with a countdown to the next update

### 8.2 Manual Data Update

Use **Tools → Update Data…** to open the Data Update Modal at any time and manually trigger a gap-fill from Binance.

### 8.3 Data Verification

Use **Tools → Verify Data…** to run a **read-only** integrity scan across all timeframes. This reports any detected gaps without modifying any stored data.

---

## 9. Debug Logger

The **Tools → Debug Logger** submenu provides controls for diagnostic logging:

| Option | Description |
|--------|-------------|
| Enable Debugger in Console | Toggle debug output to the terminal console |
| Enable Debugger in Log File | Toggle debug output to files in the `logs/` directory |
| Clear Old Logs | Delete old log files from `logs/` to free disk space |
| View Current Log File | Open the current session log in the built-in **Log Viewer** window |

Both console and log file logging are **enabled by default** on startup.

---

## 10. Troubleshooting

### Application does not start

- Confirm PostgreSQL is running: `sudo systemctl status postgresql`
- Confirm your `.env` has the correct `POSTGRES_*` settings
- Run `python scripts/launch_strategy_builder.py` from a terminal to see full error output

### Strategy Browser shows no strategies

- The database may be empty — create and save a strategy first
- Check PostgreSQL connectivity: the status bar will show an error if the database is unreachable

### Data update fails at startup

- Check your internet connection — Binance is required for live data
- If the update times out (60-second hard limit), the application will continue and retry at the next 15-minute boundary
- Use **Tools → Verify Data…** to see which timeframes have gaps

### Validation fails with unexpected errors

- Use the Validation Report window to read the exact blocking issue messages
- Apply auto-fix suggestions where available (click "Apply Fix" in the report)
- If fixes are applied, save the strategy and re-run validation

### Backtest produces no trades

- Ensure the strategy has passed validation (green ✓ on the Validate step)
- Check the **Live Output** tab for error messages during the run
- Ensure the lookback period covers a date range that has data (use **Verify Data** to confirm)

### Settings dialog — Admin tab not visible

- Click **"Admin Access"** below the Settings tabs and enter your admin PIN
- If you have not set a PIN, you will be prompted to create one on first access

---

*Screenshot placeholders — exact window names from source code:*

| Section | Window / Dialog Name |
|---------|---------------------|
| Main window | `StrategyBuilderMainWindow` |
| Strategy Browser | `StrategyBrowserDialog` |
| New Strategy dialog | `NewStrategyDialog` |
| Backtest Configuration | `BacktestConfigDialog` |
| Validation Report | `ValidationReportWindow` |
| Exit Condition dialog | `ExitConditionDialog` |
| Timing Constraint dialog | `TimingConstraintDialog` |
| Settings | `SettingsDialog` |
| Data Update Modal | `DataUpdateModal` |
| Data Verify dialog | `DataVerifyDialog` |
| Log Viewer | `LogViewerWindow` |

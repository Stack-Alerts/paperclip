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

The window title always shows the currently loaded strategy name. When there are unsaved changes an asterisk (`*`) is appended:

```
BTC Trade Engine - Strategy Builder — MyStrategy *
```

### 2.2 Layout

The main window (`StrategyBuilderMainWindow`) opens at 1400 × 900 pixels by default. The central area is split into two resizable panes by a draggable 8-pixel splitter handle (dark `#3C4149` background with a `⋮⋮⋮` drag icon):

| Pane | Default width | Contents |
|------|--------------|----------|
| **Left (40%)** | 560 px | Strategy Information Panel (top) + Strategy Blocks Panel (bottom) |
| **Right (60%)** | 840 px | Block Search Panel |

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
| Debug Logger | Submenu — see [Section 9](#9-debug-logger) |

#### Help Menu

| Action | Description |
|--------|-------------|
| About Strategy Builder | Show version and capability information |

### 3.2 Toolbar

The toolbar sits below the menu bar. It is non-movable and shows icons with text labels (`ToolButtonTextBesideIcon`, 32 × 32 icons):

- **New** — create a new strategy
- **Open** — open the Strategy Browser
- **Save** — save the current strategy
- **Stepper Ribbon** (centred in the window) — the four-step workflow progress indicator

### 3.3 Stepper Ribbon

The Stepper Ribbon displays four workflow steps as clickable buttons separated by `→` arrows:

```
📝 Design  →  ✓ Validate  →  🧪 Test / Optimize  →  🚀 Publish
```

Each button reflects its current state with a colour:

| Colour | State | Button text prefix |
|--------|-------|--------------------|
| Grey (`#374151`) | Pending — not yet reached | Original icon |
| Blue (`#204486`) | Currently active | Original icon |
| Green (`#10B981`) | Completed successfully | `✓` replaces icon |
| Red (`#C35252`) | Failed (e.g. validation errors) | `✗` replaces icon |

The ribbon is dynamically centred in the window on resize.

> Any modification to the strategy (adding/removing blocks, changing the name or type, reconfiguring signals) resets the Validate step to its default state and requires re-validation before proceeding.

### 3.4 Strategy Information Panel (Left — Top)

**Source:** `StrategyInfoPanel` (`src/strategy_builder/ui/strategy_info_panel.py`)

The Strategy Information Panel is the upper section of the left pane, enclosed in a group box labelled **"💡 Strategy Information"** (bold 12pt title). It contains:

**Strategy Name**
An editable `QLineEdit` (placeholder: `"e.g., Example_MA_Crossover"`, max 100 characters, min-height 36 px). This field is required before saving. When a saved strategy is loaded its version number is shown in the display name (e.g. `My Strategy (v3)`), but the version suffix is stripped before saving.

**Description**
A read-only `QTextEdit` (min-height 130 px, max-height 190 px, word-wrap on). The description is auto-generated from the current block and signal configuration — it cannot be edited directly. The label above it updates to show a block and signal count summary once blocks are added:

```
Description: 2 block(s) (1 required, 1 optional), 4 signal(s) (2 required, 2 optional).
```

**Metadata summary row** — all on one horizontal line, separated by `|`:

| Item | Colour | Notes |
|------|--------|-------|
| `Strategy Type:` + **Bullish** radio | Green | Long strategies |
| `Strategy Type:` + **Bearish** radio | Red | Short strategies |
| `Required:` + count | Green (bold) | Signals from all REQUIRED (AND) blocks |
| `Optional:` + count | Blue (bold) | Signals from all OPTIONAL (OR) blocks |
| `Rechecked:` + count | Orange (bold) | Signals with a recheck validation configured |
| `Exit Conditions:` + count | Red (bold) | Total exit conditions at all binding levels |
| `Time Constraint:` + `Yes`/`No` | Green bold / grey | Whether any signal has a timing constraint |

[SCREENSHOT: StrategyInfoPanel — showing a loaded strategy with 2 blocks, metadata row populated]

### 3.5 Strategy Blocks Panel (Left — Bottom)

**Source:** `StrategyBlocksPanel` / `BlockConfigItem` (`src/strategy_builder/ui/strategy_blocks_panel.py`, `BlockConfigItem._init_ui()` lines 76–599)

The Strategy Blocks Panel occupies the lower section of the left pane. It is a scrollable list of all building blocks added to the strategy, shown in evaluation order.

Each block is rendered as a `BlockConfigItem` widget with a blue border (`button_primary` color, 2 px, rounded corners) and a medium-dark background. The widget is divided into three areas: the **header row**, the **signals section**, and (when applicable) the **block-level exits section**.

#### Header Row

The header row is a horizontal layout containing, left to right:

1. **Position label** — `#1`, `#2`, etc. — rendered in the primary blue colour, bold 12pt, minimum width 40 px.
2. **Block name** — `📊 <FormattedBlockName>` — bold 10pt, default text colour.
3. **Logic badge** — a fixed-size label showing:
   - `REQUIRED` (green background) — for AND-logic blocks
   - `OPTIONAL` (blue background) — for OR-logic blocks
4. **Signal count** — `Signals: N` — muted text colour, 9pt.
5. **Controls** (right side, stacked vertically):
   - **Move row** (horizontal, right-aligned): `▴` (up) and `▾` (down) buttons — sharp small triangles, each max-width 40 px, font-size 18px bold. The up button is disabled at position #1; the down button is disabled at the last position.
   - **`⚙️ Config` button** (min-width 100 px, primary/blue style) — **only rendered for blocks at position #2 or higher**. Opens the timing constraint dialog for block-level timing.
   - **`✕ Remove` button** (min-width 100 px, red/danger style) — always present. Removes the block from the strategy.

[SCREENSHOT: BlockConfigItem — header row showing position #2, REQUIRED badge, ▴▾ buttons, ⚙️ Config, and ✕ Remove]

#### Signals Section

Rendered as a dark `QFrame` with a light background (`bg_light`) and border, below the header row. It appears whenever the block has at least one signal.

**Section header:** `Signals:` label in bold blue (info colour).

**Per-signal row** (one row per signal, numbered from 1):

- **Signal label** — `{N}. {SignalName} [{LOGIC}]` — green (`#4ADE80`) for AND signals, blue (`#60A5FA`) for OR signals, 9pt.
  - If a timing constraint is configured: the label extends inline with an orange segment: `⏱️ Within {X} candles of {ref_signal}`.
- **`Recheck On Delayed Candles` button** (min-width 180 px, min-height 28 px) — shown **only when no recheck is yet configured** for this signal. Clicking opens a dialog to set the bar delay and RECHECK mode (WITHIN or AT).
- **`⚙️ Config` button** (min-width 90 px, min-height 28 px, primary/blue style) — shown **only for signals at index 2 or higher** (i.e. the second signal onwards in the block). Opens the timing constraint dialog for this signal.

**RECHECK row** (indented 4 spaces, shown when a recheck is configured):

```
    └── RECHECK (WITHIN 5 bars)
```

Green/success colour, bold, 9pt. Three control buttons on the right:
- `⚙` gear — configure the recheck (bar delay and mode).
- `⎘` duplicate — add a nested RECHECK.
- `✕` remove — delete this recheck.

**Nested RECHECK row** (indented 8 spaces):

```
        └── RECHECK of Signal (WITHIN 3 bars)
```

Blue/info colour, 9pt. Same `⚙`, `⎘`, `✕` buttons.

**Signal exit condition row** (indented 4 spaces, shown when exits are bound to this signal):

```
    └── 🔴 EXIT: exit_signal_name (50%)
```

Exit-tree-item style, 9pt. Three buttons: `⚙` configure, `⎘` duplicate, `✕` remove.

**Exit recheck row** (indented 8 spaces, shown when the exit itself has a recheck):

```
        └── RECHECK (WITHIN 3 bars)
```

Green/success colour, bold, 9pt. Two buttons: `⚙` configure, `✕` remove.

[SCREENSHOT: BlockConfigItem — signals section showing a signal with timing constraint, a RECHECK, and an EXIT condition]

#### Block-Level Exits Section

Shown below the signals section when exit conditions are bound at the block level (not to a specific signal). Rendered as a separate dark `QFrame`.

**Section header:** `Block-Level Exit Conditions:` — red/error colour, bold.

**Per exit row:**

```
🔴  exit_signal_name (50%) - ABSOLUTE mode
```

Exit-tree-item style, 9pt. Three buttons: `⚙` configure, `⎘` duplicate, `✕` remove.

[SCREENSHOT: BlockConfigItem — block-level exits section]

### 3.6 Block Search Panel (Right)

**Source:** `BlockSearchPanel` / `BlockListItem` (`src/strategy_builder/ui/block_search_panel.py`)

The Block Search Panel on the right side of the window is enclosed in a group box labelled **"🔧 Available Building Blocks"** (bold 12pt title).

#### Search and Filter Controls

- **`🔍 Search:` label** + text input (min-height 36 px) — placeholder: `"Search by block name, description, or signal..."`. Filters the block list in real time by block name, description text, or signal name.
- **`Category:` label** + dropdown — starts with `"All Categories"`, then populated with categories from the block registry.
- **`Type:` label** + dropdown — starts with `"All Types"`, then populated with block types from the registry.

#### Block List

A scrollable area containing one `BlockListItem` per block from the registry. Each item shows:

1. **`📊 {FormattedBlockName}`** — bold 12pt.
2. **Metadata line** — `Category: {cat} | Type: {type}` (muted, 9pt). A weight value (`| Weight: N points`) is appended if the block has a `default_weight`.
3. **Expand button** (min/max height 72 px, full width, dark background) — shows the signal count:
   - Collapsed: `▶ Show Signals ({N})`
   - Expanded: `▼ Hide Signals ({N})`
   - When some signals have been added: `▶ Show Signals ({remaining} available, {added} added)`
   - When all signals have been added: `✓ All Signals Added ({N})` — button is disabled.

#### Expanded Signal List

When the expand button is clicked, the panel shows:

- **`"Select signals to add:"` header** — primary colour, 10pt bold.
- **Per-signal checkbox** — signal name with optional occurrence count `({N} found, {X.Y}%)` appended if statistics are loaded. An italic description in muted text appears below each checkbox (indented 40 px), if available.
  - Added signals have their checkboxes disabled and shown with a strikethrough (grey text, grey indicator).
- **Button row:**
  - `➕ Add as AND (Required)` — adds selected signals as a REQUIRED (AND) block. When the strategy has no blocks yet, this button's label changes to `➕ Add Required Signal`.
  - `➕ Add as OR (Optional)` — adds selected signals as an OPTIONAL (OR) block. **Disabled when the strategy has no blocks yet.**
  - `➕ Add as Exit` — opens the Exit Condition Dialog for one selected signal. **Disabled when the strategy has no blocks yet.**
- **`"Note: Signal counts based on last 180 days of BTC data"`** — muted, 9pt, italic.

[SCREENSHOT: BlockSearchPanel — showing an expanded block with signal checkboxes, AND/OR/Exit buttons]

---

## 4. The Four-Step Workflow

### Step 0 — Design

This is where you build your strategy:

1. Enter a **Strategy Name** in the Strategy Information Panel.
2. Select **Bullish** or **Bearish** as the strategy type.
3. In the Block Search Panel (right), find a building block and click its expand button (`▶ Show Signals`) to view its signals.
4. Select one or more signal checkboxes, then click **`➕ Add as AND (Required)`** or **`➕ Add as OR (Optional)`** to add them.
5. In the Strategy Blocks Panel (left), reorder blocks with the `▴` (up) and `▾` (down) buttons.
6. Optionally configure **timing constraints** on signals: click `⚙️ Config` on a signal (available from the second signal onwards) to specify that this signal must fire within N candles of a reference signal.
7. Optionally configure **recheck validation** on signals: click `Recheck On Delayed Candles` on a signal to require the signal to reoccur within a bar window before counting as confirmed.
8. Optionally add **exit conditions** to define when to close positions (signal-level, block-level, or strategy-level).

### Step 1 — Validate

Click the **Validate** step button in the Stepper Ribbon. The application runs an institutional-grade validation check and opens the **Validation Report Window** (`ValidationReportWindow`).

The report shows results in four sections:
- **✅ Basic Validation** (green border) — structural checks
- **✅ Standard Validation** (blue border) — logic and constraint checks
- **✅ Strict Validation** (purple border) — circular dependency checks
- **🔴 Exit Condition Validation** (red border) — shown only when exit conditions are present
- **⚠️ Warnings** (orange border) — shown only when warnings exist

A **NautilusTrader Compatibility** indicator is also shown (`✅ Compatible` when valid).

If validation **passes**, the Validate button turns green (`✓ Validate`) and the validation status is persisted to the database automatically.

If validation **fails**, the button turns red (`✗ Validate`) and you must address the blocking issues and re-run validation.

### Step 2 — Test / Optimize

Click the **Test / Optimize** step button. This opens the **Backtest Configuration Window** (`BacktestConfigDialog`) — see [Section 6](#6-backtest-configuration-window) for full details.

Signal calibration runs automatically before the backtest executes when you click **▶ Run Test** inside that window.

### Step 3 — Publish

Click the **Publish** step button to manage the publish status of the strategy.

---

## 5. Strategy Browser

**Source:** `StrategyBrowserDialog` (`src/strategy_builder/ui/strategy_browser_dialog.py`)

The Strategy Browser opens via **File → Open Strategy…** (Ctrl+O) or the **Open** toolbar button. It is a standalone `QMainWindow` (default size 1200 × 800 px) titled `"Strategy Browser"`.

### 5.1 Purpose

The Strategy Browser is the primary way to **load, manage, and organise strategies stored in the database**. There are no JSON files — all strategy data is persisted in PostgreSQL.

### 5.2 Window Layout

The Strategy Browser window is split into two vertical sections by a draggable splitter:

- **Upper section** — strategy table
- **Lower section** — strategy details panel (shown when a strategy is selected)

### 5.3 Header and Filters

At the top of the window:
- **Search box** — type to filter strategies by name, description, type, or date in real time
- **Strategy Type filter** — dropdown: All / Bullish / Bearish
- **Strategy count** — shows how many strategies match the current filter

### 5.4 Strategy Table

The table displays strategies with columns for name, type, version, last modified date, validation status, and published status. Clicking a row selects it and populates the details panel. **Double-clicking a row opens the strategy immediately.**

### 5.5 Strategy Details Panel

When a strategy is selected, the lower panel shows:

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

Every **Save** (Ctrl+S) creates a **new version** of the strategy in the database — it does not overwrite the previous version. **Save As** creates an entirely new strategy record with a new name and its own independent version history.

---

## 6. Backtest Configuration Window

**Source:** `BacktestConfigDialog` (`src/strategy_builder/ui/backtest_config_dialog.py`)

The Backtest Configuration Window opens when you click the **Test / Optimize** step in the Stepper Ribbon. It is a non-modal floating window with six tabs.

### 6.1 Tab 1 — 💠 Config

Configure and launch a backtest run. Key settings include:

- **Lookback Days** — how many days of historical data to use
- **Training Window** — the walk-forward training window size
- **Mode 1 / Mode 2** — historical backtest or live replay mode
- **TP/SL Configuration** — take-profit and stop-loss parameters
- **Starting Capital** — initial account balance in USDT

Click **▶ Run Test** to start. Signal calibration runs automatically before the backtest executes (the dedicated Calibrate tab was removed — calibration is now automatic).

### 6.2 Tab 2 — ● Live Output

A real-time scrolling log of all output from the running backtest, including data loading progress, NautilusTrader engine messages, and any errors.

### 6.3 Tab 3 — 💰 Trades

A live table of all trades executed during the backtest, updated in real time as the run progresses.

### 6.4 Tab 4 — 💹 Metrics

Performance analysis for the completed (or running) backtest, including Sharpe ratio, Sortino ratio, Calmar ratio, win rate, profit factor, maximum drawdown, total trades, average trade duration, and an equity curve summary.

### 6.5 Tab 5 — 🤖 AI Recommendations

An AI-powered recommendations panel that previews and sends analysis requests to the configured AI model (via OpenRouter). Provides intelligent suggestions for improving strategy parameters based on backtest results.

### 6.6 Tab 6 — 🔁 Compare

Side-by-side comparison of two different backtest configurations, allowing you to evaluate the impact of parameter changes.

### 6.7 Pause, Resume, and Stop

During a running backtest, controls are available to **Pause**, **Resume**, and **Stop** execution.

---

## 7. Settings

**Source:** `SettingsDialog` (`src/strategy_builder/ui/settings_dialog.py`)

Open via **Tools → Settings…**. The Settings dialog has three tabs:

### 7.1 Tab — API Keys

Secret fields for credentials. Each field is rendered by `SecretFieldWidget` and shows:

```
[ ••••••••••••last4 ]   [Show 10s]   [Edit]
```

- **Show 10s** — reveals the full value in plain text for 10 seconds, then auto-masks.
- **Edit** — switches to an inline password-echo `QLineEdit`. Leaving the field blank keeps the existing value. Click **Cancel** to exit edit mode without changes.

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

The Admin tab is hidden until you authenticate with an admin PIN. Click **"Admin Access"** below the tabs and enter your PIN in the `AdminPinDialog`.

The PIN dialog supports two modes:
- **Setup mode** — if no PIN is set, you are prompted to create one (enter and confirm).
- **Authentication mode** — enter your existing PIN. After 3 consecutive failures the dialog locks for 30 seconds and shows a countdown.

Admin settings cover database connection details, connection pool configuration, DB SSL, backup settings, risk management thresholds, optimisation ranges, and performance metric weights.

> The admin PIN is stored as a bcrypt hash in the OS keyring — it is never stored in plain text.

---

## 8. Data Management

### 8.1 Automatic Data Updates

When the application starts, it displays a **Data Update Modal** (`DataUpdateModal`) that checks for missing BTC/USDT candle data and fetches any gaps from Binance. This modal runs synchronously (blocking) and the auto-update system starts only after the modal closes — this prevents race conditions between the modal write and the background update thread.

After startup, the application runs a **background auto-update cycle** that:
1. Detects any gaps in the 15-minute and 1-hour bar datasets, anchoring the scan to the last bar on disk for each timeframe.
2. Downloads missing bars from Binance (60-second hard timeout per cycle).
3. Updates the status bar with a countdown to the next update.

### 8.2 Manual Data Update

Use **Tools → Update Data…** to open the Data Update Modal at any time and manually trigger a gap-fill from Binance.

### 8.3 Data Verification

Use **Tools → Verify Data…** (`DataVerifyDialog`) to run a **read-only** integrity scan across all timeframes. This reports any detected gaps without modifying any stored data.

---

## 9. Debug Logger

The **Tools → Debug Logger** submenu provides controls for diagnostic logging:

| Option | Default | Description |
|--------|---------|-------------|
| Enable Debugger in Console | On (checked) | Toggle debug output to the terminal console |
| Enable Debugger in Log File | On (checked) | Toggle debug output to files in the `logs/` directory |
| Clear Old Logs | — | Delete old log files from `logs/` to free disk space |
| View Current Log File | — | Open the current session log in the built-in **Log Viewer** window (`LogViewerWindow`) |

Both console and log file logging are enabled by default on startup.

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
- If the update times out (60-second hard limit per cycle), the application will continue and retry at the next update boundary
- Use **Tools → Verify Data…** to see which timeframes have gaps

### Validation fails with unexpected errors

- Read the exact blocking issue messages in the Validation Report window (`ValidationReportWindow`)
- Apply auto-fix suggestions where available
- If fixes are applied, save the strategy and re-run validation

### Backtest produces no trades

- Ensure the strategy has passed validation (green `✓` on the Validate step)
- Check the **● Live Output** tab for error messages during the run
- Ensure the lookback period covers a date range with data — use **Verify Data** to confirm

### Settings dialog — Admin tab not visible

- Click **"Admin Access"** below the Settings tabs and enter your admin PIN
- If no PIN has been set, you will be prompted to create one on first access

---

*Source class reference — window/dialog names from source code:*

| Window / Dialog | Class name |
|-----------------|-----------|
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

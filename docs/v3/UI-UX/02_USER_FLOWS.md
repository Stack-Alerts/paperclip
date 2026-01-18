# User Flows - Strategy Builder Redesign
**Document**: 02_USER_FLOWS.md  
**Status**: 🟢 Complete  
**Priority**: P0 - Critical  
**Last Updated**: 2026-01-16

---

## Complete Strategy Building User Journey

This document details all user interaction flows for the Strategy Builder redesign, from initial strategy creation through testing and deployment.

---

## Flow 1: Create New Strategy

**Goal**: User creates a new trading strategy from scratch

**Steps**:
1. User clicks "New Strategy" button
2. System displays Strategy Information Panel
3. User enters:
   - Strategy Name (required)
   - Strategy Type: Bullish/Bearish (auto-detected later)
4. System creates empty strategy configuration
5. System displays Block Search & Selection panel
6. User proceeds to add building blocks

**Success State**: Empty strategy created, ready for block addition  
**Error States**: Name already exists → prompt for unique name

---

## Flow 2: Add Building Block

**Goal**: Add a building block to the strategy

**Steps**:
1. User types in Block Search field or browses categories
2. System shows filtered results with:
   - Block name (e.g., "Elliott Wave Oscillator")
   - Category (e.g., "ELLIOTT_WAVE")
   - Type (e.g., "EVENT")
   - Default Weight (e.g., "22 points")
   - Description
   - Signal statistics (occurrence counts and percentages)
3. User clicks on desired block
4. System validates block hasn't been added yet
5. System displays "Add as AND" or "Add as OR" buttons
6. User clicks AND (mandatory) or OR (optional/booster)
7. System:
   - Adds block to Strategy Configuration panel
   - Removes block from available search results
   - Auto-calculates required signals if AND block
   - Shows block with default signal selected
8. Real-time preview updates

**Success State**: Block added to strategy, removed from search  
**Error States**: Block already added → show error message

---

## Flow 3: Configure Block Signals

**Goal**: Add and configure signals within a building block

**Steps**:
1. User clicks on added block in Strategy Configuration
2. System expands block showing:
   - Currently selected signal (default)
   - "Add Signal" button
   - AND/OR logic controls
   - Timing constraint controls
3. User clicks "Add Signal" button
4. System shows dropdown of available signals with statistics
5. User selects signal (e.g., "BEARISH_DIVERGENCE")
6. System displays configuration options:
   - AND/OR toggle (default: AND)
   - "Within X Candles" checkbox
   - Dependency selector (optional)
7. User configures:
   - Sets to AND (required) or OR (booster)
   - Optionally checks "Within X Candles"
   - If checked, enters candle count (e.g., 20)
   - Selects reference signal (e.g., "from Signal 1")
8. System:
   - Validates configuration
   - Updates required signal count
   - Resolves dependencies
   - Updates real-time preview

**Success State**: Signal added with configuration applied  
**Error States**: Invalid timing → show validation error

---

## Flow 4: Reorder Building Blocks

**Goal**: Change order of blocks using drag-and-drop or up/down buttons

**Steps**:
1. User clicks "Move Up" (▲) or "Move Down" (▼) button on block
   OR User drags block to new position
2. System:
   - Updates block order
   - Re-validates dependencies
   - Re-calculates signal requirements
   - Updates real-time preview
3. System shows updated configuration

**Success State**: Blocks reordered, dependencies maintained  
**Error States**: Invalid order due to dependencies → prevent move + show error

---

## Flow 5: Indent Block (Create Dependency)

**Goal**: Indent a block to show it depends on previous block

**Steps**:
1. User clicks "Indent" button (→) on block
2. System:
   - Visually indents the block
   - Marks block as dependent on previous block
   - Shows dependency indicator
   - Updates logic flow visualization
3. User can "Unindent" (←) to remove dependency

**Success State**: Dependency created and visualized  
**Error States**: Can't indent first block → show error

---

## Flow 6: Configure Timing Constraints

**Goal**: Set "Within X candles" constraint for a signal

**Steps**:
1. User clicks "Within X Candles" button next to signal
2. System shows modal/dropdown with:
   - Candle count input (number)
   - Reference signal dropdown
3. User enters:
   - Number of candles (e.g., 20)
   - Reference: "from Signal 1" or "from any previous signal"
4. User clicks "Apply"
5. System:
   - Validates constraint
   - Shows constraint visually (e.g., "⏱ 20 candles from Signal 1")
   - Updates dependency resolver
   - Updates real-time preview

**Success State**: Timing constraint applied and visible  
**Error States**: Invalid candle count → show validation error

---

## Flow 7: Configure Adaptive SL/TP

**Goal**: Configure stop loss and take profit settings

**Steps**:
1. User expands "Adaptive SL/TP Configuration" panel
2. System shows existing Adaptive SL v2.0 interface
3. User configures:
   - Stop Loss Mode: Fibonacci/Aggressive/Conservative
   - SL Fibonacci Level: 0.236, 0.382, 0.5, 0.618
   - Take Profit Mode: Fibonacci/Hybrid/Static
   - TP Levels: TP1, TP2, TP3 percentages
4. User saves configuration
5. System validates and stores SL/TP config

**Success State**: SL/TP configured for strategy  
**Error States**: Invalid percentages → show validation error

---

## Flow 8: Run Historical Walkforward Test (Mode 1)

**Goal**: Test strategy on historical data with expanding window

**Steps**:
1. User expands "Testing Controls" panel
2. User selects "Mode 1: Historical Walkforward"
3. User configures:
   - Testing Window: 180 days
   - Training Window: 30 days (optional)
   - Timeframe: 15min
4. User clicks "Run Test" button
5. System:
   - Validates strategy configuration
   - Generates NautilusTrader code
   - Loads historical data (210 days if 30 training + 180 testing)
   - Initializes BacktestEngine
   - Starts walkforward from day -210
6. Progress bar shows:
   - Current candle being processed
   - Signals triggered so far
   - Trades executed
   - Current P&L
7. Test completes at current candle
8. System displays comprehensive results:
   - Total signals triggered
   - Trades executed
   - Win rate, profit factor, Sharpe ratio
   - Max drawdown
   - TP1/TP2/TP3 adjustment counts per position
   - SL adjustment counts per position
9. User can view:
   - Detailed trade log
   - Chart with signal markers
   - Performance metrics
   - Code generated

**Success State**: Test completes, results displayed  
**Error States**: Configuration invalid → show errors before running

---

## Flow 9: Run Live Continuation Test (Mode 2)

**Goal**: Test strategy historically then continue with live data

**Steps**:
1. User selects "Mode 2: Live Continuation"
2. User configures same as Mode 1
3. User clicks "Run Test"
4. System:
   - Executes historical phase (same as Mode 1)
   - Reaches current candle
   - Shows "Historical phase complete. Waiting for live candles..."
   - Switches to live data stream mode
5. As new candles arrive:
   - System processes each candle
   - Updates metrics in real-time
   - Shows live signal detection
   - Updates position tracking
6. User sees continuous updates:
   - New candles received: X
   - Total test duration: 180 + X days
   - Live P&L updates
7. User clicks "Stop Test" when desired
8. System:
   - Stops live stream
   - Generates final report
   - Shows complete results (historical + live period)

**Success State**: Live test running, updates shown in real-time  
**Euser can stop anytime**  
**Error States**: Live feed disconnected → show error, offer retry

---

## Flow 10: View Real-Time Preview

**Goal**: See live backtest preview as strategy is built

**Steps**:
1. Preview panel automatically active when building strategy
2. As user adds blocks/signals:
   - System runs quick backtest (last 30 days)
   - Shows preliminary results
   - Updates chart with signal markers
3. User sees:
   - Signal trigger visualization on chart
   - Quick metrics (signals, potential trades)
   - Performance estimate
4. Preview updates on every configuration change
5. User can pause/resume preview
6. User can expand preview to full window

**Success State**: Preview shows live feedback  
**Error States**: Insufficient data → show message

---

## Flow 11: Save Strategy

**Goal**: Save strategy configuration for later use

**Steps**:
1. User clicks "Save Strategy" button
2. System validates strategy is complete
3. System saves:
   - Strategy configuration (JSON)
   - Block selections
   - Signal configurations
   - AND/OR logic
   - Timing constraints
   - SL/TP settings
4. System generates auto-description based on blocks/signals
5. Strategy added to "My Strategies" list
6. User sees confirmation

**Success State**: Strategy saved successfully  
**Error States**: Validation failed → show specific errors

---

## Flow 12: Load Existing Strategy

**Goal**: Load and edit a previously saved strategy

**Steps**:
1. User clicks "Load Strategy" button
2. System shows "My Strategies" list with:
   - Strategy name
   - Bullish/Bearish indicator (highlighted)
   - Last modified date
   - Quick stats
3. User selects strategy
4. System:
   - Loads configuration
   - Populates all panels
   - Recreates block structure
   - Restores signal configurations
   - Shows real-time preview
5. User can edit or run tests

**Success State**: Strategy loaded successfully  
**Error States**: Strategy file corrupted → show error

---

## Flow 13: Search and Filter Blocks

**Goal**: Find specific blocks using advanced search

**Steps**:
1. User types in search field
2. System filters by:
   - Block name
   - Signal names
   - Block description
   - Signal descriptions
3. User clicks "Advanced Filters" button
4. System shows filter options:
   - Category (dropdown)
   - Type (EVENT/SIGNAL/CONTEXT/HYBRID)
   - Tags (multi-select)
   - Signal occurrence range (e.g., >10%)
5. User applies filters
6. System shows filtered results
7. User can save filter preset

**Success State**: Relevant blocks displayed  
**Error States**: No matches → suggest broader search

---

## Flow 14: Remove Building Block

**Goal**: Remove a block from strategy

**Steps**:
1. User clicks "Remove" (×) button on block
2. System checks for dependencies
3. If dependencies exist:
   - Show warning: "Block X depends on this block"
   - Offer to remove dependents too
4. User confirms removal
5. System:
   - Removes block and dependents
   - Returns blocks to available search
   - Recalculates required signals
   - Updates real-time preview

**Success State**: Block removed, search updated  
**Error States**: Dependencies prevent removal → user must remove dependents first

---

## Flow 15: Handle Validation Errors

**Goal**: Guide user to fix configuration errors

**Steps**:
1. System continuously validates configuration
2. When error detected:
   - Shows error indicator (red badge)
   - Highlights problematic element
   - Shows tooltip with error message
3. Common errors:
   - "Signal X requires Signal Y to fire first"
   - "Timing constraint exceeds available candles"
   - "AND blocks require at least 1 signal"
   - "Circular dependency detected"
4. User hovers over error indicator
5. System shows:
   - Error description
   - Suggested fix
   - "Fix Automatically" button (if possible)
6. User fixes error manually or clicks auto-fix
7. System validates and clears error

**Success State**: Error resolved, validation passes  
**Error States**: Multiple errors → show prioritized list

---

## Related Documents

- [01_ARCHITECTURE_OVERVIEW.md](01_ARCHITECTURE_OVERVIEW.md) - System architecture
- [03_COMPONENT_SPECS.md](03_COMPONENT_SPECS.md) - Component specifications
- [04_BLOCK_MANAGEMENT.md](04_BLOCK_MANAGEMENT.md) - Block management details
- [05_SIGNAL_CONFIGURATION.md](05_SIGNAL_CONFIGURATION.md) - Signal config details

---

**Document Status**: 🟢 Complete  
**Review Status**: 🔴 Pending Review  
**Version**: 1.0.0

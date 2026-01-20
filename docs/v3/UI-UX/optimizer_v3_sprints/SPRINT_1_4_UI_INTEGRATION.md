# SPRINT 1.4: UI INTEGRATION (WINDOW 2 EXTENSIONS)
**Optimize Button, Progress Tracking, Results Display - ZERO Hardcoded Styles**

**Duration**: 3 days  
**Tasks**: 9  
**Dependencies**: Sprint 1.3 complete  
**Status**: ☐ Not Started

## 📋 SPRINT OVERVIEW

**Purpose**: Integrate Optimizer v3 into existing Window 2 (Backtest Configuration):
- Config (Tab 1): Configuration and optimization settings
- Live Output (Tab 2): Real-time progress tracking
- Trades (Tab 3): Trade execution and management
- Metrics (Tab 4): Performance metrics and analysis
- Compare (Tab 5): Configuration comparison view

**Critical Success Factors**:
- 100% NautilusTrader type coverage
- ZERO hardcoded styles anywhere
- ALL styles from `src/strategy_builder/ui/styles.py`
- Match Window 1 & 2 visual style exactly
- Dark theme consistent
- Validation: `grep` check must pass (0 violations)

## 📚 INTEGRATION DOCUMENTS

This sprint integrates with the following detailed specifications:

1. **[OPTIMIZER_V3_UI_STYLING_GUIDE.md](../OPTIMIZER_V3_UI_STYLING_GUIDE.md)**
   - Central stylesheet enforcement
   - Zero hardcoded styles
   - Style constants and helpers
   - Dark theme support
   - Style validation
   - Pre-commit hooks

2. **[OPTIMIZER_V3_CONFIGURATION_SYSTEM.md](../OPTIMIZER_V3_CONFIGURATION_SYSTEM.md)**
   - Configuration hierarchy
   - Runtime behavior
   - Parameter validation
   - Storage management
   - UI integration patterns

3. **[OPTIMIZER_V3_FLOW_DIAGRAM.md](./OPTIMIZER_V3_FLOW_DIAGRAM.md)**
   - System architecture
   - UI component flow
   - Data flow patterns
   - Configuration flow
   - Integration points

2. **[NAUTILUS_BACKTEST_CONFIG_WINDOW_INTEGRATION.md](../NAUTILUS_BACKTEST_CONFIG_WINDOW_INTEGRATION.md)**
   - Window Tab 1 configuration
   - Settings validation
   - Type conversion
   - Parameter tracking

3. **[NAUTILUS_LIVE_OUTPUT_INTEGRATION.md](../NAUTILUS_LIVE_OUTPUT_INTEGRATION.md)**
   - Real-time progress updates
   - Error reporting
   - System status monitoring
   - Resource usage tracking

4. **[NAUTILUS_TRADES_PANEL_INTEGRATION.md](../NAUTILUS_TRADES_PANEL_INTEGRATION.md)**
   - Institutional-grade trade tracking
   - Excel-like interface
   - Comprehensive reporting
   - Export capabilities

## ✅ TASK CHECKLIST

### Window 2 Tab 1 Integration
- [x] 1.4.1 Add "Optimize" button (Tab 1)
- [x] 1.4.2 Parameter selection checkboxes
- [x] 1.4.3 Config count estimator

### Window 2 Tab Integration
- [x] 1.4.4 Live Output (Tab 2)
- [x] 1.4.5 Trades Panel (Tab 3)
- [x] 1.4.6 Metrics Display (Tab 4)
- [x] 1.4.7 Compare View (Tab 5)
- [ ] 1.4.8 Apply Optimal Config Button

### Testing & Validation
- [ ] 1.4.9 Integration tests + styling validation
- [ ] 1.4.10 Sprint sign-off

## 📝 TASK DETAILS

### **Environment Configuration**
**Duration**: 1 hour  
**Dependencies**: Sprint 1.3 complete

**Implementation**:
```bash
# Add to .env file

# UI Theme Configuration
UI_THEME=dark  # dark or light
UI_FONT_FAMILY=Segoe UI
UI_FONT_SIZE_BASE=14
UI_FONT_SIZE_SMALL=12
UI_FONT_SIZE_LARGE=16
UI_FONT_WEIGHT_NORMAL=400
UI_FONT_WEIGHT_BOLD=600

# Window Configuration
WINDOW_MIN_WIDTH=1280
WINDOW_MIN_HEIGHT=800
WINDOW_OPACITY=1.0
WINDOW_TITLE_HEIGHT=32
WINDOW_BORDER_RADIUS=4

# Tab Configuration
TAB_HEIGHT=32
TAB_MIN_WIDTH=120
TAB_MAX_WIDTH=200
TAB_SPACING=2
TAB_BORDER_RADIUS=4

# Panel Configuration
PANEL_MARGIN=8
PANEL_PADDING=16
PANEL_BORDER_RADIUS=4
PANEL_SHADOW_BLUR=10
PANEL_SHADOW_COLOR=#00000020

# Control Configuration
BUTTON_HEIGHT=32
BUTTON_MIN_WIDTH=100
BUTTON_PADDING=16
BUTTON_BORDER_RADIUS=4
BUTTON_FONT_SIZE=14

# Table Configuration
TABLE_ROW_HEIGHT=32
TABLE_HEADER_HEIGHT=40
TABLE_CELL_PADDING=8
TABLE_ALTERNATING_COLORS=true
TABLE_GRID_COLOR=#E0E0E0
TABLE_SELECTION_COLOR=#007ACC40

# Chart Configuration
CHART_MIN_HEIGHT=300
CHART_PADDING=16
CHART_AXIS_FONT_SIZE=12
CHART_LEGEND_FONT_SIZE=12
CHART_LINE_WIDTH=2
CHART_POINT_SIZE=6

# Progress Bar Configuration
PROGRESS_HEIGHT=24
PROGRESS_BORDER_RADIUS=12
PROGRESS_ANIMATION_MS=750
PROGRESS_UPDATE_INTERVAL=100

# Animation Configuration
ANIMATION_DURATION=200  # milliseconds
ANIMATION_EASING=easeInOutCubic
HOVER_ANIMATION=true
TRANSITION_ANIMATION=true

# Color Scheme
COLOR_PRIMARY=#007ACC
COLOR_SECONDARY=#6C757D
COLOR_SUCCESS=#28A745
COLOR_WARNING=#FFC107
COLOR_ERROR=#DC3545
COLOR_INFO=#17A2B8
COLOR_BACKGROUND=#FFFFFF
COLOR_SURFACE=#F8F9FA
COLOR_TEXT=#212529
COLOR_BORDER=#DEE2E6

# Dark Theme Colors
COLOR_DARK_PRIMARY=#0098FF
COLOR_DARK_SECONDARY=#A1A9B0
COLOR_DARK_SUCCESS=#34D058
COLOR_DARK_WARNING=#FFD700
COLOR_DARK_ERROR=#FF4D4D
COLOR_DARK_INFO=#58C7DB
COLOR_DARK_BACKGROUND=#1E1E1E
COLOR_DARK_SURFACE=#252526
COLOR_DARK_TEXT=#CCCCCC
COLOR_DARK_BORDER=#404040

# Responsive Breakpoints
BREAKPOINT_SMALL=640
BREAKPOINT_MEDIUM=768
BREAKPOINT_LARGE=1024
BREAKPOINT_XL=1280
BREAKPOINT_XXL=1536

# Update Intervals
UI_UPDATE_INTERVAL=100  # milliseconds
CHART_UPDATE_INTERVAL=1000  # milliseconds
TABLE_UPDATE_INTERVAL=500  # milliseconds
ANIMATION_UPDATE_INTERVAL=16  # milliseconds (60 FPS)

# Performance Settings
MAX_CHART_POINTS=1000
TABLE_VIRTUALIZATION=true
LAZY_LOADING=true
DEBOUNCE_DELAY=150  # milliseconds
THROTTLE_DELAY=100  # milliseconds
```

**Configuration Loading**:
```python
from dotenv import load_dotenv
import os
from typing import Dict, Any

def get_ui_config() -> Dict[str, Any]:
    """Load UI configuration from environment"""
    load_dotenv()
    
    return {
        'theme': {
            'mode': os.getenv('UI_THEME'),
            'font': {
                'family': os.getenv('UI_FONT_FAMILY'),
                'size_base': int(os.getenv('UI_FONT_SIZE_BASE')),
                'size_small': int(os.getenv('UI_FONT_SIZE_SMALL')),
                'size_large': int(os.getenv('UI_FONT_SIZE_LARGE')),
                'weight_normal': int(os.getenv('UI_FONT_WEIGHT_NORMAL')),
                'weight_bold': int(os.getenv('UI_FONT_WEIGHT_BOLD'))
            }
        },
        'window': {
            'min_width': int(os.getenv('WINDOW_MIN_WIDTH')),
            'min_height': int(os.getenv('WINDOW_MIN_HEIGHT')),
            'opacity': float(os.getenv('WINDOW_OPACITY')),
            'title_height': int(os.getenv('WINDOW_TITLE_HEIGHT')),
            'border_radius': int(os.getenv('WINDOW_BORDER_RADIUS'))
        },
        'tab': {
            'height': int(os.getenv('TAB_HEIGHT')),
            'min_width': int(os.getenv('TAB_MIN_WIDTH')),
            'max_width': int(os.getenv('TAB_MAX_WIDTH')),
            'spacing': int(os.getenv('TAB_SPACING')),
            'border_radius': int(os.getenv('TAB_BORDER_RADIUS'))
        },
        'panel': {
            'margin': int(os.getenv('PANEL_MARGIN')),
            'padding': int(os.getenv('PANEL_PADDING')),
            'border_radius': int(os.getenv('PANEL_BORDER_RADIUS')),
            'shadow_blur': int(os.getenv('PANEL_SHADOW_BLUR')),
            'shadow_color': os.getenv('PANEL_SHADOW_COLOR')
        },
        'control': {
            'button_height': int(os.getenv('BUTTON_HEIGHT')),
            'button_min_width': int(os.getenv('BUTTON_MIN_WIDTH')),
            'button_padding': int(os.getenv('BUTTON_PADDING')),
            'button_border_radius': int(os.getenv('BUTTON_BORDER_RADIUS')),
            'button_font_size': int(os.getenv('BUTTON_FONT_SIZE'))
        },
        'table': {
            'row_height': int(os.getenv('TABLE_ROW_HEIGHT')),
            'header_height': int(os.getenv('TABLE_HEADER_HEIGHT')),
            'cell_padding': int(os.getenv('TABLE_CELL_PADDING')),
            'alternating_colors': os.getenv('TABLE_ALTERNATING_COLORS').lower() == 'true',
            'grid_color': os.getenv('TABLE_GRID_COLOR'),
            'selection_color': os.getenv('TABLE_SELECTION_COLOR')
        },
        'chart': {
            'min_height': int(os.getenv('CHART_MIN_HEIGHT')),
            'padding': int(os.getenv('CHART_PADDING')),
            'axis_font_size': int(os.getenv('CHART_AXIS_FONT_SIZE')),
            'legend_font_size': int(os.getenv('CHART_LEGEND_FONT_SIZE')),
            'line_width': int(os.getenv('CHART_LINE_WIDTH')),
            'point_size': int(os.getenv('CHART_POINT_SIZE'))
        },
        'progress': {
            'height': int(os.getenv('PROGRESS_HEIGHT')),
            'border_radius': int(os.getenv('PROGRESS_BORDER_RADIUS')),
            'animation_ms': int(os.getenv('PROGRESS_ANIMATION_MS')),
            'update_interval': int(os.getenv('PROGRESS_UPDATE_INTERVAL'))
        },
        'animation': {
            'duration': int(os.getenv('ANIMATION_DURATION')),
            'easing': os.getenv('ANIMATION_EASING'),
            'hover': os.getenv('HOVER_ANIMATION').lower() == 'true',
            'transition': os.getenv('TRANSITION_ANIMATION').lower() == 'true'
        },
        'colors': {
            'light': {
                'primary': os.getenv('COLOR_PRIMARY'),
                'secondary': os.getenv('COLOR_SECONDARY'),
                'success': os.getenv('COLOR_SUCCESS'),
                'warning': os.getenv('COLOR_WARNING'),
                'error': os.getenv('COLOR_ERROR'),
                'info': os.getenv('COLOR_INFO'),
                'background': os.getenv('COLOR_BACKGROUND'),
                'surface': os.getenv('COLOR_SURFACE'),
                'text': os.getenv('COLOR_TEXT'),
                'border': os.getenv('COLOR_BORDER')
            },
            'dark': {
                'primary': os.getenv('COLOR_DARK_PRIMARY'),
                'secondary': os.getenv('COLOR_DARK_SECONDARY'),
                'success': os.getenv('COLOR_DARK_SUCCESS'),
                'warning': os.getenv('COLOR_DARK_WARNING'),
                'error': os.getenv('COLOR_DARK_ERROR'),
                'info': os.getenv('COLOR_DARK_INFO'),
                'background': os.getenv('COLOR_DARK_BACKGROUND'),
                'surface': os.getenv('COLOR_DARK_SURFACE'),
                'text': os.getenv('COLOR_DARK_TEXT'),
                'border': os.getenv('COLOR_DARK_BORDER')
            }
        },
        'breakpoints': {
            'small': int(os.getenv('BREAKPOINT_SMALL')),
            'medium': int(os.getenv('BREAKPOINT_MEDIUM')),
            'large': int(os.getenv('BREAKPOINT_LARGE')),
            'xl': int(os.getenv('BREAKPOINT_XL')),
            'xxl': int(os.getenv('BREAKPOINT_XXL'))
        },
        'intervals': {
            'ui': int(os.getenv('UI_UPDATE_INTERVAL')),
            'chart': int(os.getenv('CHART_UPDATE_INTERVAL')),
            'table': int(os.getenv('TABLE_UPDATE_INTERVAL')),
            'animation': int(os.getenv('ANIMATION_UPDATE_INTERVAL'))
        },
        'performance': {
            'max_chart_points': int(os.getenv('MAX_CHART_POINTS')),
            'table_virtualization': os.getenv('TABLE_VIRTUALIZATION').lower() == 'true',
            'lazy_loading': os.getenv('LAZY_LOADING').lower() == 'true',
            'debounce_delay': int(os.getenv('DEBOUNCE_DELAY')),
            'throttle_delay': int(os.getenv('THROTTLE_DELAY'))
        }
    }
```

### **Task 1.4.1: Add "Optimize" Button to Tab 1**
**Duration**: 3 hours  
**Dependencies**: Sprint 1.3 complete

**Implementation**: See [NAUTILUS_BACKTEST_CONFIG_WINDOW_INTEGRATION.md](../NAUTILUS_BACKTEST_CONFIG_WINDOW_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Button added to Tab 1
- [ ] Uses BUTTON_STYLE from styles.py
- [ ] No hardcoded colors/fonts
- [ ] Visual match with existing buttons

**Styling Validation**:
```bash
# Must return 0 (no violations)
grep -r "setStyleSheet\|QFont\|#[0-9A-Fa-f]\{6\}" \
    src/optimizer_v3/ui/optimizer_controls.py | wc -l
```

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

### **Task 1.4.2: Parameter Selection Checkboxes**
**Duration**: 3 hours  
**Dependencies**: 1.4.1

**Implementation**: See [NAUTILUS_BACKTEST_CONFIG_WINDOW_INTEGRATION.md](../NAUTILUS_BACKTEST_CONFIG_WINDOW_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Checkboxes use CHECKBOX_STYLE from styles.py
- [ ] GroupBox uses GROUPBOX_STYLE from styles.py
- [ ] No hardcoded styles
- [ ] Visual consistency with Window 1

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

### **Task 1.4.3: Config Count Estimator**
**Duration**: 2 hours  
**Dependencies**: 1.4.2

**Implementation**: See [NAUTILUS_BACKTEST_CONFIG_WINDOW_INTEGRATION.md](../NAUTILUS_BACKTEST_CONFIG_WINDOW_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Uses PRIMARY_COLOR from styles.py
- [ ] No hardcoded hex colors
- [ ] Proper type safety

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.4.4: Live Output (Tab 2)**
**Duration**: 4 hours  
**Dependencies**: 1.4.3

**Implementation**: See [NAUTILUS_LIVE_OUTPUT_INTEGRATION.md](../NAUTILUS_LIVE_OUTPUT_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Uses PROGRESSBAR_STYLE from styles.py
- [ ] Matches Window 2 Tab 2 existing progress bars
- [ ] No hardcoded styles
- [ ] Real-time updates
- [ ] Resource monitoring

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

### **Task 1.4.5: Trades Panel (Tab 3)**
**Duration**: 6 hours  
**Dependencies**: 1.4.4

**Implementation**: See [NAUTILUS_TRADES_PANEL_INTEGRATION.md](../NAUTILUS_TRADES_PANEL_INTEGRATION.md) for complete implementation.

**Trade Panel Requirements**:
1. Trade List:
   - Real-time trade updates
   - Trade status indicators
   - Entry/exit details
   - PnL tracking
   - Risk metrics

2. Trade Details:
   - Complete trade information
   - Entry/exit prices
   - Position size
   - Stop loss/take profit
   - Trade duration
   - Commission & slippage

3. Performance Metrics:
   - Running PnL
   - Win rate
   - Average trade PnL
   - Risk/reward ratios
   - Drawdown tracking

4. Interactive Features:
   - Sort by any column
   - Filter trades
   - Export functionality
   - Double-click for details
   - Right-click menu

**Acceptance Criteria**:
- [ ] Uses TABLE_STYLE and TABLE_HEADER_STYLE
- [ ] Real-time updates working
- [ ] All trade metrics displayed
- [ ] Interactive features functional
- [ ] Export capability working
- [ ] Dark theme compatible
- [ ] No hardcoded styles
- [ ] NautilusTrader type safety

**Testing**:
```python
def test_trades_panel():
    """Test trades panel functionality"""
    panel = TradesPanel()
    
    # Test trade addition
    trade = create_test_trade()
    panel.add_trade(trade)
    assert len(panel.get_trades()) == 1
    
    # Test metrics update
    metrics = panel.get_metrics()
    assert isinstance(metrics['total_pnl'], Money)
    assert isinstance(metrics['win_rate'], Decimal)
    
    # Test interaction
    panel.sort_by('pnl', ascending=False)
    panel.filter_by({'outcome': 'WIN'})
    
    # Test export
    panel.export_trades('test.xlsx')
    assert os.path.exists('test.xlsx')
```

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer ☐ NautilusTrader Expert

### **Task 1.4.6: Metrics Display (Tab 4)**
**Duration**: 8 hours  
**Dependencies**: 1.4.4

**Implementation**: See [NAUTILUS_TRADES_PANEL_INTEGRATION.md](../NAUTILUS_TRADES_PANEL_INTEGRATION.md) for complete implementation.

**Metrics Display Requirements**:
1. Performance Metrics Table:
   - Sharpe Ratio (Decimal, 4 decimals)
   - Win Rate (Percentage, 2 decimals)
   - Profit Factor (Decimal, 3 decimals)
   - Max Drawdown (Money type)
   - Total PnL (Money type)
   - Average Trade PnL (Money type)
   - Number of Trades (Integer)
   - Average Trade Duration (Time)
   - Risk/Reward Ratio (Decimal, 2 decimals)
   - Capital Efficiency (Percentage, 2 decimals)

2. Parameter Comparison:
   - Side-by-side view of user vs optimized settings
   - Highlight changes in optimized parameters
   - Show percentage improvement for each metric
   - Statistical significance indicators
   - Confidence levels for improvements

3. Trade Analysis:
   - Trade distribution chart
   - Hourly performance breakdown
   - Drawdown chart
   - Equity curve
   - Rolling Sharpe ratio
   - Rolling win rate

4. Risk Metrics:
   - Value at Risk (VaR)
   - Expected Shortfall
   - Maximum consecutive losses
   - Recovery factor
   - Sortino ratio
   - Calmar ratio

**Acceptance Criteria**:
- [ ] Uses TABLE_STYLE and TABLE_HEADER_STYLE
- [ ] Matches Window 2 Tab 4 existing tables
- [ ] No hardcoded styles
- [ ] Properly formats Money type values
- [ ] Properly formats Quantity type values
- [ ] Properly formats Decimal values
- [ ] Color coding for positive/negative values
- [ ] Center alignment for all cells
- [ ] Bold highlighting for best config
- [ ] Summary panel with proper type formatting
- [ ] All styling from styles.py
- [ ] 100% test coverage for type handling
- [ ] All metrics properly formatted with correct precision
- [ ] Side-by-side comparison view working
- [ ] Statistical significance testing implemented
- [ ] Charts render correctly
- [ ] Dark theme compatible
- [ ] Export functionality for all metrics
- [ ] Proper NautilusTrader type handling throughout

**Testing**:
```python
def test_metrics_display():
    """Test metrics display formatting"""
    display = MetricsDisplay()
    
    # Test Money type formatting
    money_value = Money('1234.5678', 'USD')
    assert display.format_money(money_value) == '$1,234.57'
    
    # Test Decimal formatting
    sharpe = Decimal('2.45678')
    assert display.format_sharpe(sharpe) == '2.4568'
    
    # Test percentage formatting
    win_rate = Decimal('0.6789')
    assert display.format_percentage(win_rate) == '67.89%'
    
    # Test statistical significance
    p_value = Decimal('0.0234')
    assert display.is_significant(p_value) == True
    
    # Test chart data preparation
    equity_data = [(datetime.now(), Money('1000', 'USD'))]
    chart_data = display.prepare_equity_chart(equity_data)
    assert len(chart_data) > 0

def test_comparison_view():
    """Test parameter comparison display"""
    comparison = ParameterComparison()
    
    original = {
        'stop_loss': Money('100', 'USD'),
        'take_profit': Money('200', 'USD')
    }
    
    optimized = {
        'stop_loss': Money('120', 'USD'),
        'take_profit': Money('240', 'USD')
    }
    
    diff = comparison.compare(original, optimized)
    assert diff['stop_loss']['change'] == '+20%'
    assert diff['take_profit']['change'] == '+20%'
```

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer ☐ NautilusTrader Expert

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer ☐ NautilusTrader Expert

### **Task 1.4.6: Compare View (Tab 5)**
**Duration**: 6 hours  
**Dependencies**: 1.4.5

**Implementation**: See [NAUTILUS_COMPARISON_VIEW_INTEGRATION.md](../NAUTILUS_COMPARISON_VIEW_INTEGRATION.md) for complete implementation.

**Compare Tab Requirements**:
1. Layout:
   - Three vertical panels for last 3 configurations
   - Equal width distribution (33.33% each)
   - Synchronized vertical scrolling
   - Dark theme compatible
   - Proper spacing and alignment
   - Consistent font sizes
   - Column headers with timestamps

2. Configuration Display (Per Panel):
   - Strategy name and version
   - Timestamp of run
   - Total runtime
   - Hardware utilization
   - Parameter settings
     * Stop loss
     * Take profit
     * Position sizing
     * Entry conditions
     * Exit conditions
     * Risk parameters
   - Performance metrics
     * Sharpe ratio
     * Win rate
     * Profit factor
     * Max drawdown
     * Total PnL
     * Number of trades

3. Visual Comparison:
   - Color-coded differences:
     * Better values in green
     * Worse values in red
     * Neutral changes in gray
   - Parameter changes highlighted
   - Percentage differences shown
   - Statistical significance indicators
   - Confidence level markers
   - Trend indicators (↑↓→)

4. Charts & Visualizations:
   - Equity curves overlay
   - Drawdown comparison
   - Trade distribution comparison
   - Performance by hour overlay
   - Win rate by setup comparison
   - Risk metrics comparison

5. Interactive Features:
   - Click to expand sections
   - Hover for detailed metrics
   - Double-click for full details
   - Export comparison to Excel
   - Save comparison state
   - Load previous comparisons

**Acceptance Criteria**:
- [ ] Three vertical panels implemented
- [ ] Uses PANEL_STYLE from styles.py
- [ ] No hardcoded styles
- [ ] Synchronized scrolling works
- [ ] Difference highlighting works
- [ ] All NautilusTrader types formatted
- [ ] Statistical indicators shown
- [ ] Performance charts rendered
- [ ] Interactive features working
- [ ] Export functionality works
- [ ] Dark theme compatible
- [ ] Proper spacing throughout
- [ ] Memory efficient
- [ ] Performance optimized

**Testing**:
```python
def test_compare_view():
    """Test comparison view functionality"""
    compare = CompareView()
    
    # Test layout
    assert len(compare.panels) == 3
    assert all(p.width() == compare.width() / 3 for p in compare.panels)
    
    # Test data loading
    configs = [
        load_config('latest'),
        load_config('previous'),
        load_config('oldest')
    ]
    compare.load_configs(configs)
    
    # Test highlighting
    diffs = compare.get_differences()
    assert len(diffs) > 0
    assert all('significance' in d for d in diffs)
    
    # Test synchronization
    compare.panels[0].scroll_to(100)
    assert all(p.scroll_position() == 100 for p in compare.panels)
    
    # Test interaction
    section = compare.panels[0].get_section('Performance')
    section.expand()
    assert all(p.get_section('Performance').is_expanded() for p in compare.panels)
    
    # Test export
    path = 'test_comparison.xlsx'
    compare.export_comparison(path)
    assert os.path.exists(path)
```

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer ☐ NautilusTrader Expert

### **Task 1.4.7: Apply Optimal Config Button**
**Duration**: 2 hours  
**Dependencies**: 1.4.5

**Implementation**: See [NAUTILUS_TRADES_PANEL_INTEGRATION.md](../NAUTILUS_TRADES_PANEL_INTEGRATION.md) for complete implementation.

**Acceptance Criteria**:
- [ ] Uses PRIMARY_BUTTON_STYLE from styles.py
- [ ] No hardcoded styles
- [ ] Proper type handling

**Sign-off**: ☐ Developer ☐ Lead

### **Task 1.4.9: Integration Tests + Styling Validation**
**Duration**: 4 hours  
**Dependencies**: 1.4.6

**Testing**:
```python
def test_style_imports():
    """Verify all UI files import from styles.py"""
    import glob
    import os
    
    ui_files = glob.glob('src/optimizer_v3/ui/**/*.py', recursive=True)
    ui_files = [f for f in ui_files if not f.endswith('styles.py')]
    
    for file in ui_files:
        with open(file) as f:
            content = f.read()
            assert 'from src.strategy_builder.ui.styles import' in content, \
                f"{file} missing styles.py import!"

def test_ui_integration():
    """Test full UI integration"""
    # Functional tests
    controls = OptimizerControls()
    assert controls.optimize_btn is not None
    
def test_no_hardcoded_styles():
    """CRITICAL: Verify zero hardcoded styles"""
    import subprocess
    result = subprocess.run([
        'grep', '-r',
        'setStyleSheet.*"|QFont\\(|#[0-9A-Fa-f]',
        'src/optimizer_v3/ui/',
        '--include=*.py'
    ], capture_output=True)
    
    violations = [l for l in result.stdout.decode().split('\n') 
                  if l and 'from src.strategy_builder.ui.styles' not in l]
    
    assert len(violations) == 0, f"Found {len(violations)} hardcoded styles!"

def test_visual_consistency():
    """Manual: Screenshot comparison with Window 1 & 2"""
    # Manual test - reviewer checks screenshots
    pass
```

**Validation Checklist**:
- [ ] Zero hardcoded colors (grep passes)
- [ ] Zero inline fonts (grep passes)
- [ ] All imports from styles.py present
- [ ] Visual match with Window 1 & 2
- [ ] Dark theme consistent
- [ ] All NautilusTrader types validated

**Sign-off**: ☐ Developer ☐ Lead ☐ UI Designer

### **Task 1.4.10: Sprint Sign-off**
**Duration**: 1 hour  
**Dependencies**: 1.4.7

**Final Checklist**:
- [ ] All 8 tasks complete
- [ ] Styling validation passed (0 violations)
- [ ] Visual consistency verified
- [ ] Integration tests passing
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] All NautilusTrader types validated

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect ☐ UI Designer

## 🎯 SPRINT SIGN-OFF

**Complete When**:
- [ ] All UI components in Window 2
- [ ] ZERO hardcoded styles (grep check passes)
- [ ] Visual consistency with existing UI
- [ ] All tests passing
- [ ] All NautilusTrader types validated
- [ ] All integration documents referenced
- [ ] Real-time updates working
- [ ] Export functionality tested

**Critical Validation Command**:
```bash
# MUST return 0
grep -r "setStyleSheet\|QFont\|#[0-9A-Fa-f]\{6\}" \
    src/optimizer_v3/ui/ --include="*.py" --exclude="styles.py" | wc -l
```

**Sign-off**: ☐ Developer ☐ Lead ☐ Architect ☐ UI Designer

**Next Sprint**: `SPRINT_1_5_TESTING_POLISH.md`

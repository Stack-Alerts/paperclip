# NAUTILUS COMPARISON VIEW INTEGRATION
**Three-Panel Configuration Comparison with Statistical Analysis**

## 📋 OVERVIEW

This document specifies the integration requirements for the Comparison View (Window 2 Tab 5) in Optimizer v3, ensuring institutional-grade configuration comparison with statistical validation.

## 🔒 CRITICAL REQUIREMENTS

1. **NautilusTrader Type Safety**
   - All values use proper NautilusTrader types
   - Money for monetary values
   - Quantity for position sizes
   - Decimal for ratios/percentages

2. **Zero Hardcoded Styles**
   - All styles from styles.py
   - Dark theme compatible
   - Consistent visual language
   - Proper spacing and alignment

3. **Performance Requirements**
   - Memory efficient panel rendering
   - Smooth synchronized scrolling
   - Responsive UI updates
   - Efficient data loading

## 🎨 LAYOUT SPECIFICATION

### 1. Panel Structure
```python
class ComparisonPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(PANEL_STYLE)
        self.setFixedWidth(self.parent().width() / 3)
```

### 2. Panel Components
```python
class ConfigurationSection(QGroupBox):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(SECTION_STYLE)
        self.setFont(create_font(FONT_SIZE_BASE))
```

### 3. Visual Hierarchy
```python
SECTION_MARGINS = {
    'top': SPACING_UNIT * 2,
    'right': SPACING_UNIT * 2,
    'bottom': SPACING_UNIT * 2,
    'left': SPACING_UNIT * 2
}

HEADER_STYLE = f"""
    QLabel {{
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_LARGE}px;
        font-weight: {FONT_WEIGHT_BOLD};
        color: {PRIMARY_COLOR};
    }}
"""
```

## 🔧 IMPLEMENTATION

### 1. Panel Synchronization
```python
class CompareView(QWidget):
    def __init__(self):
        self.panels = [ComparisonPanel() for _ in range(3)]
        self.sync_manager = ScrollSyncManager(self.panels)
        
    def sync_scroll(self, value: int):
        """Synchronize vertical scrolling across panels"""
        for panel in self.panels:
            if panel != self.sender():
                panel.verticalScrollBar().setValue(value)
```

### 2. Data Loading
```python
def load_configurations(self):
    """Load last 3 configurations with NautilusTrader types"""
    configs = ConfigurationManager.get_last_n(3)
    
    for panel, config in zip(self.panels, configs):
        panel.load_config(config)
        
        # Validate Money types
        assert isinstance(config.stop_loss, Money)
        assert isinstance(config.take_profit, Money)
        
        # Validate Quantity types
        assert isinstance(config.position_size, Quantity)
```

### 3. Difference Highlighting
```python
def highlight_differences(self):
    """Color-code value changes with statistical significance"""
    base_config = self.panels[0].config
    
    for panel in self.panels[1:]:
        diffs = self.calculate_differences(base_config, panel.config)
        
        for key, diff in diffs.items():
            if diff.is_significant:
                if diff.is_improvement:
                    color = SUCCESS_COLOR
                else:
                    color = ERROR_COLOR
            else:
                color = NEUTRAL_COLOR
                
            panel.highlight_value(key, color)
```

### 4. Statistical Analysis
```python
def analyze_significance(self, base_value: Decimal, 
                        compare_value: Decimal) -> bool:
    """Determine if difference is statistically significant"""
    from scipy import stats
    
    t_stat, p_value = stats.ttest_ind(base_value, compare_value)
    return p_value < Decimal('0.05')  # 95% confidence
```

## 📊 METRICS DISPLAY

### 1. Performance Metrics
```python
class PerformanceMetrics(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(TABLE_STYLE)
        
    def format_metric(self, value: Union[Money, Decimal, int]):
        """Format metrics with proper precision"""
        if isinstance(value, Money):
            return f"${value:,.2f}"
        elif isinstance(value, Decimal):
            if value < 1:
                return f"{value:.4f}"
            return f"{value:.2f}"
        return str(value)
```

### 2. Charts & Visualizations
```python
class ComparisonCharts(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(CHART_STYLE)
        
    def create_overlay_chart(self, datasets: List[pd.DataFrame]):
        """Create overlaid performance charts"""
        fig = Figure(figsize=(8, 4))
        ax = fig.add_subplot(111)
        
        for i, data in enumerate(datasets):
            color = CHART_COLORS[i]
            ax.plot(data.index, data.values, color=color)
```

## 🔍 VALIDATION

### 1. Type Safety Tests
```python
def test_type_safety():
    """Verify NautilusTrader type usage"""
    view = CompareView()
    view.load_configurations()
    
    for panel in view.panels:
        config = panel.get_config()
        assert isinstance(config.stop_loss, Money)
        assert isinstance(config.position_size, Quantity)
        assert isinstance(config.win_rate, Decimal)
```

### 2. Style Validation
```python
def test_styling():
    """Verify zero hardcoded styles"""
    view = CompareView()
    
    # Check style imports
    source = inspect.getsource(CompareView)
    assert 'from src.strategy_builder.ui.styles import' in source
    
    # Verify no hardcoded colors
    assert '#' not in source
    assert 'rgb' not in source.lower()
```

### 3. Performance Tests
```python
def test_performance():
    """Verify responsive UI"""
    view = CompareView()
    
    # Test scroll sync performance
    start = time.time()
    view.sync_scroll(500)
    assert time.time() - start < 0.1  # 100ms max
    
    # Test memory usage
    import psutil
    process = psutil.Process()
    mem_before = process.memory_info().rss
    view.load_configurations()
    mem_after = process.memory_info().rss
    assert mem_after - mem_before < 50 * 1024 * 1024  # 50MB max
```

## 📝 MAINTENANCE

1. **Style Updates**
   - Modify styles.py only
   - Run validation tests
   - Update dark theme
   - Verify consistency

2. **Type Safety**
   - Use mypy static checking
   - Validate Money formatting
   - Verify Decimal precision
   - Test edge cases

3. **Performance**
   - Monitor memory usage
   - Profile scroll performance
   - Optimize chart rendering
   - Cache configurations

## 🎯 VERIFICATION

Before each commit:
- [ ] Run type safety tests
- [ ] Verify style compliance
- [ ] Check performance metrics
- [ ] Test dark theme
- [ ] Validate statistical analysis
- [ ] Review memory usage
- [ ] Update documentation

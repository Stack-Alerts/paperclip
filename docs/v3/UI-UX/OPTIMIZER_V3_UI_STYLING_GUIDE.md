# OPTIMIZER V3 UI STYLING GUIDE
**Central Stylesheet Enforcement - Zero Hardcoded Styles**

## 📋 OVERVIEW

This document outlines the mandatory styling protocol for Optimizer V3, ensuring all UI components use the central `src/strategy_builder/ui/styles.py` stylesheet.

## 🔒 CRITICAL RULES

1. **ZERO HARDCODED STYLES**
   - No inline styles anywhere
   - No hardcoded colors
   - No hardcoded fonts
   - No style dictionaries in components

2. **SINGLE SOURCE OF TRUTH**
   - All styles from `src/strategy_builder/ui/styles.py`
   - All components must import styles
   - No style duplication
   - No local style overrides

## 🎨 STYLE CONSTANTS

### Colors
```python
# In styles.py
PRIMARY_COLOR = "#007ACC"
SECONDARY_COLOR = "#F3F3F3"
SUCCESS_COLOR = "#28A745"
ERROR_COLOR = "#DC3545"
WARNING_COLOR = "#FFC107"
INFO_COLOR = "#17A2B8"
NEUTRAL_COLOR = "#6C757D"

# Dark theme colors
DARK_BG = "#1E1E1E"
DARK_TEXT = "#CCCCCC"
DARK_BORDER = "#404040"
```

### Spacing
```python
# In styles.py
SPACING_UNIT = 8  # Base unit for all spacing
MARGIN_SMALL = SPACING_UNIT
MARGIN_MEDIUM = SPACING_UNIT * 2
MARGIN_LARGE = SPACING_UNIT * 3
PADDING_SMALL = SPACING_UNIT
PADDING_MEDIUM = SPACING_UNIT * 2
PADDING_LARGE = SPACING_UNIT * 3
```

### Typography
```python
# In styles.py
FONT_FAMILY = "Segoe UI"
FONT_SIZE_SMALL = 12
FONT_SIZE_BASE = 14
FONT_SIZE_LARGE = 16
FONT_SIZE_XLARGE = 18
FONT_WEIGHT_NORMAL = 400
FONT_WEIGHT_BOLD = 600
```

### Component Styles
```python
# In styles.py
# Tab styles for configuration windows
TAB_STYLE = f"""
    QTabWidget::pane {{
        border: 1px solid {NEUTRAL_COLOR};
        border-radius: {SPACING_UNIT/2}px;
        padding: {SPACING_UNIT}px;
    }}
    QTabBar::tab {{
        background-color: white;
        border: 1px solid {NEUTRAL_COLOR};
        border-bottom: none;
        border-top-left-radius: {SPACING_UNIT/2}px;
        border-top-right-radius: {SPACING_UNIT/2}px;
        padding: {SPACING_UNIT}px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {PRIMARY_COLOR};
        color: white;
    }}
"""

# Form styles for configuration inputs
FORM_STYLE = f"""
    QFormLayout {{
        spacing: {SPACING_UNIT}px;
    }}
"""

# Input styles for configuration fields
INPUT_STYLE = f"""
    QSpinBox, QDoubleSpinBox, QLineEdit {{
        background-color: white;
        border: 1px solid {NEUTRAL_COLOR};
        border-radius: {SPACING_UNIT/4}px;
        padding: {SPACING_UNIT/2}px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
        border-color: {PRIMARY_COLOR};
    }}
    QCheckBox {{
        spacing: {SPACING_UNIT}px;
    }}
    QCheckBox::indicator {{
        width: {SPACING_UNIT*2}px;
        height: {SPACING_UNIT*2}px;
    }}
    QCheckBox::indicator:checked {{
        background-color: {PRIMARY_COLOR};
    }}
"""

# GroupBox styles for configuration sections
GROUPBOX_STYLE = f"""
    QGroupBox {{
        background-color: white;
        border: 1px solid {NEUTRAL_COLOR};
        border-radius: {SPACING_UNIT/2}px;
        margin-top: {SPACING_UNIT*2}px;
        padding-top: {SPACING_UNIT*2}px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 {SPACING_UNIT}px;
    }}
"""

BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {PRIMARY_COLOR};
        color: white;
        border: none;
        padding: {PADDING_MEDIUM}px;
        font-family: {FONT_FAMILY};
        font-size: {FONT_SIZE_BASE}px;
    }}
"""

TABLE_STYLE = f"""
    QTableView {{
        background-color: white;
        alternate-background-color: {SECONDARY_COLOR};
        border: 1px solid {NEUTRAL_COLOR};
    }}
"""

# Add more component styles...
```

## 🔧 IMPLEMENTATION

### 1. System Configuration Window
```python
from src.strategy_builder.ui.styles import (
    WINDOW_STYLE,
    TAB_STYLE,
    FORM_STYLE,
    INPUT_STYLE,
    GROUPBOX_STYLE,
    BUTTON_STYLE,
    SPACING_UNIT,
    create_font
)

class SystemConfigWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(WINDOW_STYLE)
        
        # Create tabbed interface
        tabs = QTabWidget()
        tabs.setStyleSheet(TAB_STYLE)
        tabs.setFont(create_font())
        
        # Add configuration tabs
        for tab_name in ['Block Optimization', 'Signal Logic', 'Market Conditions']:
            tab = QWidget()
            layout = QVBoxLayout()
            layout.setSpacing(SPACING_UNIT)
            
            # Add configuration groups
            group = QGroupBox(tab_name + " Settings")
            group.setStyleSheet(GROUPBOX_STYLE)
            group.setFont(create_font(bold=True))
            
            # Add form layout
            form = QFormLayout()
            form.setSpacing(SPACING_UNIT)
            
            # Add configuration inputs
            spinbox = QSpinBox()
            spinbox.setStyleSheet(INPUT_STYLE)
            spinbox.setFont(create_font())
            form.addRow("Parameter:", spinbox)
            
            group.setLayout(form)
            layout.addWidget(group)
            tab.setLayout(layout)
            tabs.addTab(tab, tab_name)
        
        self.setCentralWidget(tabs)
```

### 2. Style Import
```python
from src.strategy_builder.ui.styles import (
    PRIMARY_COLOR,
    BUTTON_STYLE,
    TABLE_STYLE,
    FONT_SIZE_BASE,
    create_font
)
```

### 2. Style Application
```python
class OptimizerControl(QWidget):
    def __init__(self):
        super().__init__()
        
        # Use style constants
        self.setStyleSheet(BUTTON_STYLE)
        
        # Use spacing constants
        self.layout().setSpacing(SPACING_UNIT)
        self.layout().setContentsMargins(
            MARGIN_MEDIUM,
            MARGIN_MEDIUM,
            MARGIN_MEDIUM,
            MARGIN_MEDIUM
        )
        
        # Use font helper
        self.label.setFont(create_font(FONT_SIZE_BASE))
```

### 3. Dynamic Styling
```python
def update_status(self, status: str):
    if status == 'success':
        color = SUCCESS_COLOR
    elif status == 'error':
        color = ERROR_COLOR
    else:
        color = NEUTRAL_COLOR
        
    self.status_label.setStyleSheet(f"color: {color};")
```

## 🔍 VALIDATION

### 1. Style Check Command
```bash
# Must return 0 violations
grep -r "setStyleSheet\|QFont\|#[0-9A-Fa-f]\{6\}" \
    src/optimizer_v3/ui/ \
    --include="*.py" \
    --exclude="styles.py" | wc -l
```

### 2. Import Check
```bash
# Must find style imports in all UI files
grep -r "from src.strategy_builder.ui.styles import" \
    src/optimizer_v3/ui/ \
    --include="*.py" \
    --exclude="styles.py"
```

### 3. Unit Tests
```python
def test_no_hardcoded_styles():
    """Verify no hardcoded styles in components"""
    result = subprocess.run([
        'grep', '-r',
        'setStyleSheet.*"|QFont\\(|#[0-9A-Fa-f]',
        'src/optimizer_v3/ui/',
        '--include=*.py',
        '--exclude=styles.py'
    ], capture_output=True)
    
    violations = [l for l in result.stdout.decode().split('\n')
                 if l and 'from src.strategy_builder.ui.styles' not in l]
    
    assert len(violations) == 0, f"Found {len(violations)} hardcoded styles!"
```

## 📋 STYLE CHECKLIST

For each UI component:

1. **Imports**
   - [ ] Imports from styles.py
   - [ ] No hardcoded values
   - [ ] No local style constants

2. **Colors**
   - [ ] Uses COLOR_* constants
   - [ ] No hex values
   - [ ] No color names
   - [ ] Dark theme compatible

3. **Typography**
   - [ ] Uses FONT_* constants
   - [ ] Uses create_font helper
   - [ ] No QFont creation
   - [ ] No hardcoded sizes

4. **Spacing**
   - [ ] Uses SPACING_* constants
   - [ ] No pixel values
   - [ ] Consistent margins
   - [ ] Consistent padding

5. **Components**
   - [ ] Uses *_STYLE constants
   - [ ] No inline styles
   - [ ] No style dictionaries
   - [ ] Proper style inheritance

## 🔄 WORKFLOW

1. **New Component**
   - Add styles to styles.py
   - Export constants/helpers
   - Import in component
   - Apply styles

2. **Style Updates**
   - Modify styles.py only
   - Never modify component
   - Test dark theme
   - Verify consistency

3. **Validation**
   - Run style check command
   - Verify imports
   - Run unit tests
   - Visual inspection

## 🎯 ENFORCEMENT

### Pre-commit Hook
```bash
#!/bin/bash

# Check for hardcoded styles
STYLE_VIOLATIONS=$(grep -r "setStyleSheet\|QFont\|#[0-9A-Fa-f]\{6\}" \
    src/optimizer_v3/ui/ \
    --include="*.py" \
    --exclude="styles.py" | wc -l)

if [ $STYLE_VIOLATIONS -gt 0 ]; then
    echo "Error: Found $STYLE_VIOLATIONS hardcoded styles"
    exit 1
fi

# Check for style imports
MISSING_IMPORTS=$(find src/optimizer_v3/ui/ -name "*.py" \
    ! -name "styles.py" \
    -exec grep -L "from src.strategy_builder.ui.styles import" {} \;)

if [ ! -z "$MISSING_IMPORTS" ]; then
    echo "Error: Missing style imports in:"
    echo "$MISSING_IMPORTS"
    exit 1
fi
```

## 📝 MAINTENANCE

1. **Style Additions**
   - Add to styles.py
   - Document constants
   - Update tests
   - Verify usage

2. **Style Updates**
   - Update styles.py
   - Test changes
   - Verify components
   - Update documentation

3. **Regular Audits**
   - Run validation
   - Check consistency
   - Update documentation
   - Review dark theme

## 🔍 VERIFICATION

Before each commit:
- [ ] Run style check command
- [ ] Verify style imports
- [ ] Run unit tests
- [ ] Visual inspection
- [ ] Dark theme check
- [ ] Documentation update

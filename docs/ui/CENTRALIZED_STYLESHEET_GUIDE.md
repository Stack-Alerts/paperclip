# Centralized Stylesheet System Guide

**Author**: Strategy Builder Team  
**Date**: 2026-01-18  
**Location**: `src/strategy_builder/ui/styles.py`

---

## Overview

The centralized stylesheet system provides a **single source of truth** for all UI styling across the Strategy Builder application. This eliminates inconsistencies and makes theme updates effortless.

---

## Why Use Centralized Styles?

### **Problems Solved:**
- ❌ **Inconsistent styling** between windows/dialogs
- ❌ **Duplicate CSS** scattered across files
- ❌ **Theme updates require** changing dozens of files
- ❌ **Font size mismatches** between components

### **Benefits:**
- ✅ **Single source of truth** for all styling
- ✅ **Instant consistency** across all UI components
- ✅ **Easy theme updates** - change once, applies everywhere
- ✅ **Standardized patterns** for labels, buttons, radio buttons

---

## Quick Start

### **1. Import the styles module:**

```python
from src.strategy_builder.ui.styles import (
    get_main_stylesheet,
    get_label_style,
    get_radio_button_style,
    get_primary_button_stylesheet,
    get_color
)
```

### **2. Apply main stylesheet to window/dialog:**

```python
class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Apply centralized dark theme
        self.setStyleSheet(get_main_stylesheet())
```

### **3. Style individual components:**

```python
# Labels
label = QLabel("Test Mode:")
label.setStyleSheet(get_label_style('muted'))  # Soft gray color

# Radio buttons
radio1 = QRadioButton("Bullish")
radio1.setStyleSheet(get_radio_button_style('bullish'))  # Green

radio2 = QRadioButton("Bearish")
radio2.setStyleSheet(get_radio_button_style('bearish'))  # Red

# Buttons
button = QPushButton("Run Test")
button.setStyleSheet(get_primary_button_stylesheet())  # Blue primary button
```

---

## Available Functions

### **Core Stylesheets**

#### `get_main_stylesheet() -> str`
Returns the complete application stylesheet (extracted from main window).

**Usage:**
```python
self.setStyleSheet(get_main_stylesheet())
```

**Includes styling for:**
- QMainWindow, QWidget, QDialog
- QGroupBox, QLabel, QLineEdit, QComboBox, QTextEdit
- QSpinBox, QProgressBar, QPushButton
- QScrollBar, QSplitter, QMenuBar, QMenu, QToolBar, QStatusBar

---

### **Label Styles**

#### `get_label_style(style_type: str = 'default') -> str`
Get standardized label styling.

**Available Types:**
- `'default'` - White text `#E8EAED`
- `'muted'` - Gray text `#A0AEC0` (used for field labels)
- `'secondary'` - Light gray `#BDC1C6`
- `'error'` - Red `#EF4444`
- `'success'` - Green `#10B981`
- `'warning'` - Orange `#FFA500`

**Example:**
```python
label = QLabel("Lookback Days:")
label.setStyleSheet(get_label_style('muted'))
```

---

### **Radio Button Styles**

#### `get_radio_button_style(style_type: str = 'default') -> str`
Get standardized radio button styling.

**Available Types:**
- `'bullish'` - Green `#10B981` (matches main window Bullish)
- `'bearish'` - Red `#EF4444` (matches main window Bearish)
- `'default'` - White `#E8EAED`
- `'info'` - Blue `#2070FF`

**Example:**
```python
mode1_radio = QRadioButton("Mode 1 (Historical)")
mode1_radio.setStyleSheet(get_radio_button_style('bullish'))  # Green

mode2_radio = QRadioButton("Mode 2 (Live Replay)")
mode2_radio.setStyleSheet(get_radio_button_style('default'))  # White
```

---

### **Button Stylesheets**

#### `get_primary_button_stylesheet() -> str`
Blue primary action button (like "Run Test", "Save").

**Example:**
```python
run_btn = QPushButton("▶️ Run Test")
run_btn.setStyleSheet(get_primary_button_stylesheet())
```

#### `get_success_button_stylesheet() -> str`
Green success/confirm button.

**Example:**
```python
confirm_btn = QPushButton("✓ Confirm")
confirm_btn.setStyleSheet(get_success_button_stylesheet())
```

#### `get_danger_button_stylesheet() -> str`
Red danger/delete button.

**Example:**
```python
delete_btn = QPushButton("🗑️ Delete")
delete_btn.setStyleSheet(get_danger_button_stylesheet())
```

---

### **Tab Widget Styling**

#### `get_tab_widget_stylesheet() -> str`
Stepper-like tab styling (matches stepper ribbon).

**Example:**
```python
tab_widget = QTabWidget()
tab_widget.setStyleSheet(get_tab_widget_stylesheet())
```

---

### **Color Access**

#### `get_color(color_name: str) -> str`
Get any color from the centralized palette.

**Available Colors:**

**Backgrounds:**
- `'bg_dark'` - `#15191E`
- `'bg_medium'` - `#1E2128`
- `'bg_light'` - `#2A2F3A`
- `'bg_input'` - `#2A2F3A`

**Borders:**
- `'border'` - `#3C4149`
- `'border_focus'` - `#2070FF`

**Text:**
- `'text_primary'` - `#E8EAED`
- `'text_secondary'` - `#BDC1C6`
- `'text_muted'` - `#9AA0A6`
- `'text_label'` - `#A0AEC0`

**Status:**
- `'success'` - `#10B981`
- `'warning'` - `#FFA500`
- `'error'` - `#EF4444`
- `'info'` - `#2070FF`

**Buttons:**
- `'button_primary'` - `#2070FF`
- `'button_primary_hover'` - `#1557CC`
- `'button_success'` - `#10B981`
- `'button_danger'` - `#DC2626`

**Stepper/Tabs:**
- `'stepper_inactive'` - `#374151`
- `'stepper_active'` - `#2070FF`
- `'stepper_hover'` - `#4B5563`
- `'stepper_complete'` - `#10B981`
- `'stepper_error'` - `#DC2626`

**Example:**
```python
label = QLabel("Status:")
label.setStyleSheet(f"color: {get_color('success')};")
```

---

## Complete Example

### **Before (inconsistent, hardcoded):**

```python
class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Hardcoded styling (inconsistent with main window)
        self.setStyleSheet("""
            QDialog {
                background-color: #15191E;
            }
        """)
        
        label = QLabel("Test Mode:")
        label.setStyleSheet("color: #888888;")  # Wrong shade!
        
        radio = QRadioButton("Option 1")
        radio.setStyleSheet("QRadioButton { color: #00FF00; background: transparent; }")  # Wrong green!
```

### **After (consistent, centralized):**

```python
from src.strategy_builder.ui.styles import (
    get_main_stylesheet,
    get_label_style,
    get_radio_button_style
)

class MyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Centralized styling (matches main window exactly)
        self.setStyleSheet(get_main_stylesheet())
        
        label = QLabel("Test Mode:")
        label.setStyleSheet(get_label_style('muted'))  # Correct shade!
        
        radio = QRadioButton("Option 1")
        radio.setStyleSheet(get_radio_button_style('bullish'))  # Correct green!
```

---

## Best Practices

### ✅ **DO:**

1. **Always import and use centralized styles:**
   ```python
   from src.strategy_builder.ui.styles import get_main_stylesheet
   self.setStyleSheet(get_main_stylesheet())
   ```

2. **Use helper functions for components:**
   ```python
   label.setStyleSheet(get_label_style('muted'))
   radio.setStyleSheet(get_radio_button_style('bullish'))
   ```

3. **Use color constants:**
   ```python
   bg_color = get_color('bg_dark')
   text_color = get_color('text_primary')
   ```

4. **Document which style type you're using:**
   ```python
   # Use muted label style for field labels
   label.setStyleSheet(get_label_style('muted'))
   ```

### ❌ **DON'T:**

1. **Don't hardcode colors:**
   ```python
   # BAD
   label.setStyleSheet("color: #A0AEC0;")
   
   # GOOD
   label.setStyleSheet(get_label_style('muted'))
   ```

2. **Don't duplicate the main stylesheet:**
   ```python
   # BAD
   self.setStyleSheet("""
       QWidget {
           background-color: #15191E;
           color: #E8EAED;
       }
       ...
   """)
   
   # GOOD
   self.setStyleSheet(get_main_stylesheet())
   ```

3. **Don't mix centralized and hardcoded styles:**
   ```python
   # BAD
   self.setStyleSheet(get_main_stylesheet())
   label.setStyleSheet("color: #FF0000;")  # Hardcoded!
   
   # GOOD
   self.setStyleSheet(get_main_stylesheet())
   label.setStyleSheet(get_label_style('error'))  # Centralized!
   ```

---

## Updating the Theme

To change colors globally, edit `src/strategy_builder/ui/styles.py`:

```python
COLORS = {
    'success': '#10B981',  # Change this green
    'error': '#EF4444',    # Change this red
    # ... etc
}
```

All UI components using `get_label_style('success')` or `get_color('success')` will automatically update!

---

## Migration Guide

### **Migrating Existing UI Components:**

1. **Add import at top of file:**
   ```python
   from src.strategy_builder.ui.styles import (
       get_main_stylesheet,
       get_label_style,
       get_radio_button_style
   )
   ```

2. **Replace dialog/window stylesheet:**
   ```python
   # OLD
   self.setStyleSheet("""
       QDialog {
           background-color: #15191E;
       }
   """)
   
   # NEW
   self.setStyleSheet(get_main_stylesheet())
   ```

3. **Replace label styles:**
   ```python
   # OLD
   label.setStyleSheet("color: #A0AEC0;")
   
   # NEW
   label.setStyleSheet(get_label_style('muted'))
   ```

4. **Replace radio button styles:**
   ```python
   # OLD
   radio.setStyleSheet("QRadioButton { color: #10B981; background: transparent; }")
   
   # NEW
   radio.setStyleSheet(get_radio_button_style('bullish'))
   ```

5. **Replace button styles:**
   ```python
   # OLD
   btn.setStyleSheet("""
       QPushButton {
           background-color: #2070FF;
           color: white;
           ...
       }
   """)
   
   # NEW
   btn.setStyleSheet(get_primary_button_stylesheet())
   ```

---

## Files Updated

**✅ Completed:**
- `src/strategy_builder/ui/styles.py` - Centralized stylesheet module (NEW)
- `src/strategy_builder/ui/backtest_config_panel.py` - Uses centralized styles
- `src/strategy_builder/ui/backtest_config_dialog.py` - Uses centralized styles

**⏳ To Do:**
- Other dialogs and panels (as needed)

---

## Support

If you have questions or need help with styling:

1. Check this guide first
2. Look at `backtest_config_panel.py` for a working example
3. Review `styles.py` to see all available options
4. Test your changes to ensure consistency

---

## Summary

The centralized stylesheet system:
- ✅ Eliminates inconsistencies
- ✅ Makes theme updates easy
- ✅ Provides standardized patterns
- ✅ Matches main window exactly
- ✅ Reduces code duplication

**Always use centralized styles for new UI components!**

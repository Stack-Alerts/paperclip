# Strategy Builder - Phase 4 Build Plan: PyQt6 Professional UI

**Version:** 1.0  
**Date:** 2026-01-10  
**Status:** Planning  
**Estimated Time:** 8-12 hours  

---

## Overview

Phase 4 delivers a **professional-grade graphical user interface** using PyQt6. This provides an advanced, polished experience with drag-and-drop functionality, live previews, and modern UI patterns.

### Why PyQt6?

- ✅ **Modern:** Latest Qt6 framework
- ✅ **Professional:** Industry-standard GUI toolkit
- ✅ **Powerful:** Advanced widgets and features
- ✅ **Beautiful:** Native look and feel, custom styling
- ✅ **Feature-rich:** Drag-and-drop, animations, charts
- ✅ **Scalable:** Large fonts (32-40pt), dark mode

---

## Goals

### Primary Goals

1. **Drag-and-Drop Block Builder:** Visual block composition
2. **Real-time Validation:** Live feedback as you build
3. **Code Preview:** Syntax-highlighted preview
4. **Block Library:** Searchable, categorized blocks
5. **Professional Polish:** Modern, polished interface
6. **VSCode Dark Theme:** Consistent with user preference
7. **Large Fonts:** 4x standard size (32-40pt)

### Features

- Modern ribbon-style toolbar
- Split-pane drag-and-drop editor
- Live confluence calculator
- Syntax-highlighted code preview
- Block library with search
- Context-sensitive help
- Keyboard shortcuts
- Undo/redo functionality

---

## Architecture

### Main Window Structure

```
┌──────────────────────────────────────────────────────────────┐
│  Strategy Builder v3.0 - Professional                [_][□][X]│
├──────────────────────────────────────────────────────────────┤
│  🏠 File  ✏️ Edit  👁️ View  🔧 Tools  ❓ Help                │
├──────────────────────────────────────────────────────────────┤
│  ┌────────── Ribbon Toolbar ──────────┐                      │
│  │ ➕ New  💾 Save  ✓ Validate  ⚙ Generate  🔄 Refresh │     │
│  └───────────────────────────────────┘                       │
├──────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌────────────────┐ ┌───────────────────┐    │
│ │ Block       │ │ Canvas         │ │ Properties        │    │
│ │ Library     │ │                │ │                   │    │
│ │             │ │ Drag blocks    │ │ Selected block:   │    │
│ │ 🔍 Search   │ │ here to build  │ │ Name: [____]      │    │
│ │             │ │ strategy       │ │ Weight: [__]      │    │
│ │ Patterns    │ │                │ │ Signals: [____]   │    │
│ │ - M Pattern │ │ ┌─────────┐    │ │                   │    │
│ │ - W Pattern │ │ │M Pattern│    │ │ Confluence: 75    │    │
│ │             │ │ └─────────┘    │ │ Status: ✅ Valid  │    │
│ │ Oscillators │ │      ↓         │ │                   │    │
│ │ - RSI Div   │ │ ┌─────────┐    │ │ [Preview Code]    │    │
│ │             │ │ │RSI Div  │    │ │ [Generate Files]  │    │
│ └─────────────┘ │ └─────────┘    │ └───────────────────┘    │
│                 └────────────────┘                           │
├──────────────────────────────────────────────────────────────┤
│  Ready  |  Confluence: 75 pts  |  Slots: 0/150               │
└──────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Main Window (PyQt6)

**File:** `src/utils/Strategy_Builder/qt_gui/main_window.py`

**Features:**
- QMainWindow with menu bar
- Ribbon-style toolbar
- Multi-pane MDI interface
- Status bar with indicators
- Dark theme styling

**Key Classes:**
```python
class StrategyBuilderMainWindow(QMainWindow):
    def __init__(self):
        # Setup main window
        # Create menu bar
        # Create ribbon toolbar
        # Create central widget (3-pane)
        # Apply dark theme
        
    def create_menu_bar(self):
        # File, Edit, View, Tools, Help
        
    def create_ribbon_toolbar(self):
        # Large icons with text
        # Grouped by function
        
    def apply_dark_theme(self):
        # VSCode color scheme
        # Custom QSS stylesheet
```

---

### 2. Block Library Panel

**File:** `src/utils/Strategy_Builder/qt_gui/block_library.py`

**Features:**
- Tree view of blocks by category
- Search/filter box
- Drag source for blocks
- Block details on hover
- Large fonts (32pt)

**Key Classes:**
```python
class BlockLibraryPanel(QWidget):
    def __init__(self):
        # Create tree view
        # Load blocks from registry
        # Setup drag-and-drop
        
    def create_block_tree(self):
        # Category → Blocks hierarchy
        
    def filter_blocks(self, search_term):
        # Live search filtering
        
    def start_drag(self, block):
        # Initiate drag operation
```

---

### 3. Canvas Editor (Drag-and-Drop)

**File:** `src/utils/Strategy_Builder/qt_gui/canvas_editor.py`

**Features:**
- Drop target for blocks
- Visual block representation
- Connection lines (optional)
- Context menu (right-click)
- Reordering via drag

**Key Classes:**
```python
class CanvasEditor(QGraphicsView):
    def __init__(self):
        # Setup QGraphicsScene
        # Enable drop events
        # Setup selection
        
    def dragEnterEvent(self, event):
        # Accept block drops
        
    def dropEvent(self, event):
        # Add block to strategy
        # Update confluence
        
    def create_block_item(self, block):
        # Visual block representation
```

---

### 4. Block Item Widget

**File:** `src/utils/Strategy_Builder/qt_gui/block_item.py`

**Features:**
- Custom QGraphicsItem
- Shows block name, weight
- Visual indicator (icon)
- Selectable, movable
- Large text (32pt)

**Key Classes:**
```python
class BlockItem(QGraphicsWidget):
    def __init__(self, block_config):
        # Create visual representation
        # Setup geometry
        # Add text labels
        
    def paint(self, painter, option, widget):
        # Draw block rectangle
        # Draw background
        # Draw text
        
    def mousePressEvent(self, event):
        # Handle selection
```

---

### 5. Properties Panel

**File:** `src/utils/Strategy_Builder/qt_gui/properties_panel.py`

**Features:**
- Shows selected block details
- Edit block weight
- Select signals
- Live confluence display
- Validation status
- Large fonts (32pt)

**Key Classes:**
```python
class PropertiesPanel(QWidget):
    def __init__(self):
        # Create form layout
        # Add weight spinbox
        # Add signal selector
        # Add validation display
        
    def update_for_block(self, block):
        # Load block properties
        # Display current values
        
    def on_property_changed(self):
        # Update block
        # Recalculate confluence
        # Validate
```

---

### 6. Code Preview Dialog

**File:** `src/utils/Strategy_Builder/qt_gui/code_preview.py`

**Features:**
- Tabbed view (Strategy, Test, Config)
- Syntax highlighting
- Line numbers
- Copy to clipboard
- Save to file
- Large fonts (28pt)

**Key Classes:**
```python
class CodePreviewDialog(QDialog):
    def __init__(self, generated_code):
        # Create tab widget
        # Add QTextEdit for each file
        # Add syntax highlighter
        
    def create_code_tab(self, title, code, language):
        # QTextEdit with syntax highlighting
        
    def copy_to_clipboard(self):
        # Copy active tab
```

---

### 7. Syntax Highlighter

**File:** `src/utils/Strategy_Builder/qt_gui/syntax_highlighter.py`

**Features:**
- Python syntax highlighting
- YAML syntax highlighting
- Keywords, strings, comments
- Custom color scheme (VSCode)

**Key Classes:**
```python
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        # Define highlighting rules
        # VSCode color scheme
        
    def highlightBlock(self, text):
        # Apply highlighting rules
```

---

### 8. Dark Theme Stylesheet

**File:** `src/utils/Strategy_Builder/qt_gui/dark_theme.qss`

**Features:**
- VSCode color palette
- Custom widget styling
- Consistent appearance
- Large fonts throughout

**Colors:**
```css
/* VSCode Dark Theme */
QMainWindow {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-size: 28pt;
}

QPushButton {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3e3e42;
    padding: 15px;
    font-size: 28pt;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #007acc;
    color: #ffffff;
}

QListWidget, QTreeWidget {
    background-color: #252526;
    color: #d4d4d4;
    font-size: 32pt;
}
```

---

## Implementation Plan

### Step 1: Setup & Dependencies (30 min)

1. Install PyQt6
   ```bash
   pip install PyQt6 PyQt6-QScintilla
   ```

2. Create project structure
   ```
   src/utils/Strategy_Builder/qt_gui/
   ├── __init__.py
   ├── main_window.py
   ├── block_library.py
   ├── canvas_editor.py
   ├── block_item.py
   ├── properties_panel.py
   ├── code_preview.py
   ├── syntax_highlighter.py
   ├── dark_theme.qss
   └── resources/
       └── icons/
   ```

### Step 2: Main Window (1.5 hours)

- Create QMainWindow
- Add menu bar
- Add ribbon toolbar
- Apply dark theme
- Setup status bar
- Test launch

### Step 3: Block Library (1.5 hours)

- Create tree view
- Load blocks from registry
- Implement search
- Setup drag source
- Add tooltips

### Step 4: Canvas Editor (2 hours)

- Create QGraphicsView
- Implement drag-and-drop
- Add block items
- Handle selection
- Context menu

### Step 5: Block Item Widget (1 hour)

- Custom QGraphicsWidget
- Visual design
- Mouse events
- Selection handling

### Step 6: Properties Panel (1.5 hours)

- Form layout
- Weight editor
- Signal selector
- Confluence display
- Validation display

### Step 7: Code Preview (1.5 hours)

- Tabbed dialog
- Syntax highlighting
- Copy/save functionality
- Large fonts

### Step 8: Integration & Polish (2 hours)

- Connect all components
- Add keyboard shortcuts
- Add icons
- Test workflows
- Fix bugs

### Step 9: Documentation (30 min)

- User guide for Qt GUI
- Screenshots
- Feature showcase

---

## Testing Plan

### Manual Testing Checklist

- [ ] Window launches correctly
- [ ] Dark theme applied
- [ ] Large fonts visible
- [ ] Can drag blocks from library
- [ ] Can drop blocks on canvas
- [ ] Properties update on selection
- [ ] Confluence calculates correctly
- [ ] Validation works
- [ ] Code preview shows correct code
- [ ] Can save strategy
- [ ] Can generate files
- [ ] Keyboard shortcuts work

---

## Dependencies

### Required

- PyQt6 >= 6.0
- PyQt6-QScintilla (for code editor - optional)

### Optional Enhancements

- PyQtChart (for charting)
- PyQt6-WebEngine (for embedded docs)

---

## Success Criteria

- Professional, polished appearance
- Smooth drag-and-drop functionality
- Large, readable fonts (32-40pt)
- VSCode dark theme throughout
- Real-time validation feedback
- Syntax-highlighted code preview
- No crashes on valid input
- Intuitive user experience

---

## Timeline

**Total Estimate:** 8-12 hours

- Setup: 30 min
- Main components: 8 hours
- Testing: 2 hours
- Polish: 1 hour
- Documentation: 30 min

---

## Launch Script

**File:** `scripts/strategy_builder_qt.py`

```python
#!/usr/bin/env python3
import sys
from PyQt6.QtWidgets import QApplication
from src.utils.Strategy_Builder.qt_gui import StrategyBuilderMainWindow

def main():
    app = QApplication(sys.argv)
    window = StrategyBuilderMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
```

---

## Comparison: Tkinter vs PyQt6

| Feature | Tkinter (Phase 3) | PyQt6 (Phase 4) |
|---------|------------------|-----------------|
| Drag-and-drop | ❌ No | ✅ Yes |
| Syntax highlighting | ❌ Basic | ✅ Advanced |
| Custom widgets | ⚠️ Limited | ✅ Full |
| Themes | ⚠️ Basic | ✅ Professional |
| Graphics | ❌ No | ✅ QGraphicsView |
| Charts | ❌ No | ✅ PyQtChart |
| Performance | ✅ Good | ✅ Excellent |
| Learning curve | ✅ Easy | ⚠️ Moderate |

---

## Next Steps After Phase 4

### Future Enhancements

1. **Live Market Preview:** Show how strategy would have performed
2. **Optimization UI:** Visual parameter optimization
3. **Multi-strategy Manager:** Compare multiple strategies
4. **Cloud Sync:** Save configurations to cloud
5. **Collaboration:** Share strategies with team

---

**Status:** Ready to start Phase 4 implementation!  
**Start Date:** 2026-01-10 00:06  
**Target Completion:** 2026-01-10 12:00
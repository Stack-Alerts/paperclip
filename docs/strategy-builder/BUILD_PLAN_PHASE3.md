# Strategy Builder - Phase 3 Build Plan: Tkinter Basic UI

**Version:** 1.0  
**Date:** 2026-01-09  
**Status:** In Progress  
**Estimated Time:** 3-4 hours  

---

## Overview

Phase 3 delivers a **basic graphical user interface** using Python's built-in Tkinter library. This provides a visual, point-and-click experience for users who prefer not to write code or use the command line.

### Why Tkinter?

- ✅ **Built-in:** No additional dependencies
- ✅ **Cross-platform:** Works on Windows, Mac, Linux
- ✅ **Lightweight:** Fast startup, low resource usage
- ✅ **Familiar:** Standard Python GUI toolkit
- ✅ **Simple:** Good for MVP/prototype

---

## Goals

### Primary Goals

1. **Visual Strategy Creation:** Drag-and-drop or click-to-add blocks
2. **Real-time Validation:** See validation errors as you build
3. **Preview Generated Code:** View strategy before saving
4. **Strategy Management:** List, edit, delete strategies
5. **User-Friendly:** Intuitive for non-programmers

### Non-Goals (Save for Phase 4)

- Advanced themes/styling (basic is fine)
- Complex animations
- Plugin system
- Advanced charting
- Database integration

---

## Architecture

### Main Window Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Strategy Builder v2.0                            [_][□][X]  │
├─────────────────────────────────────────────────────────────┤
│  File   Edit   View   Help                                  │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌───────────────────────────────────┐  │
│ │ Strategies      │ │ Strategy Editor                   │  │
│ │                 │ │                                    │  │
│ │ 001. M Pattern  │ │  Name: [________________]         │  │
│ │ 002. W Pattern  │ │  Number: [001]                    │  │
│ │                 │ │  Category: [Reversal ▼]           │  │
│ │ [+ New]         │ │                                    │  │
│ │ [✓ Validate]    │ │  Building Blocks:                 │  │
│ │ [⚙ Generate]    │ │  ┌─────────────────────────────┐  │  │
│ │ [× Delete]      │ │  │ □ Double Top (30 pts)       │  │  │
│ │                 │ │  │ ☑ RSI Divergence (25 pts)   │  │  │
│ │                 │ │  │ □ HOD (20 pts)              │  │  │
│ │                 │ │  └─────────────────────────────┘  │  │
│ │                 │ │                                    │  │
│ │                 │ │  [Add Block...]                   │  │
│ │                 │ │                                    │  │
│ │                 │ │  Confluence: 55 pts (Min: 70)     │  │
│ │                 │ │  Status: ⚠️ Below minimum         │  │
│ └─────────────────┘ └───────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│ Ready                                          0/150 slots  │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Main Application Window

**File:** `src/utils/Strategy_Builder/gui/main_window.py`

**Features:**
- Menu bar (File, Edit, View, Help)
- Toolbar with common actions
- Status bar showing slot usage
- Two-pane layout (list + editor)

**Key Methods:**
```python
class StrategyBuilderApp:
    def __init__(self):
        # Setup main window
        # Create menu bar
        # Create toolbar
        # Create panes
        
    def create_menu_bar(self):
        # File: New, Open, Save, Exit
        # Edit: Copy, Paste, Delete
        # View: Refresh
        # Help: About, Documentation
        
    def create_toolbar(self):
        # Quick access buttons
        
    def create_strategy_list(self):
        # Left pane: Listbox of strategies
        
    def create_editor_pane(self):
        # Right pane: Strategy editor
```

---

### 2. Strategy List Panel

**File:** `src/utils/Strategy_Builder/gui/strategy_list.py`

**Features:**
- Scrollable list of all strategies
- Search/filter box
- Sort by number/name/category
- Double-click to edit
- Right-click context menu

**Key Methods:**
```python
class StrategyListPanel:
    def __init__(self, parent):
        # Create listbox
        # Add scrollbar
        # Add search box
        # Bind events
        
    def refresh_list(self):
        # Reload from registry
        
    def on_select(self, event):
        # Load selected strategy
        
    def on_double_click(self, event):
        # Open in editor
        
    def on_right_click(self, event):
        # Show context menu
```

---

### 3. Strategy Editor Panel

**File:** `src/utils/Strategy_Builder/gui/strategy_editor.py`

**Features:**
- Form fields for basic info
- Block selection interface
- Real-time validation display
- Confluence calculator
- Save/Cancel buttons

**Key Methods:**
```python
class StrategyEditorPanel:
    def __init__(self, parent):
        # Create form fields
        # Create block selector
        # Create validation display
        
    def load_strategy(self, strategy_config):
        # Populate fields
        
    def save_strategy(self):
        # Validate and save
        
    def add_block(self):
        # Open block selector dialog
        
    def remove_block(self):
        # Remove selected block
        
    def update_confluence(self):
        # Calculate and display total
```

---

### 4. Block Selector Dialog

**File:** `src/utils/Strategy_Builder/gui/block_selector.py`

**Features:**
- Categorized block list
- Search functionality
- Preview of block details
- Signal configuration
- Weight adjustment slider

**Key Methods:**
```python
class BlockSelectorDialog:
    def __init__(self, parent):
        # Create category tabs
        # Create block list
        # Create detail pane
        
    def on_category_change(self, category):
        # Filter blocks by category
        
    def on_block_select(self, block):
        # Show block details
        # Show available signals
        
    def on_ok(self):
        # Return selected block config
```

---

### 5. Validation Display Panel

**File:** `src/utils/Strategy_Builder/gui/validation_panel.py`

**Features:**
- Traffic light indicator (🟢/🟡/🔴)
- Error list with descriptions
- Warning list
- Suggestion list
- Quick fix buttons

**Key Methods:**
```python
class ValidationPanel:
    def __init__(self, parent):
        # Create indicator
        # Create lists
        
    def validate(self, strategy_config):
        # Run validation
        # Display results
        
    def show_errors(self, errors):
        # Display error list
        
    def show_warnings(self, warnings):
        # Display warning list
```

---

### 6. Code Preview Dialog

**File:** `src/utils/Strategy_Builder/gui/code_preview.py`

**Features:**
- Tabbed view (Strategy, Test, Config)
- Syntax highlighting (optional)
- Line numbers
- Copy to clipboard button
- Save to file button

**Key Methods:**
```python
class CodePreviewDialog:
    def __init__(self, parent, generated_code):
        # Create notebook (tabs)
        # Create text widgets
        # Add code
        
    def copy_to_clipboard(self):
        # Copy active tab to clipboard
        
    def save_to_file(self):
        # Save files to disk
```

---

## Implementation Plan

### Step 1: Project Structure (15 min)

```
src/utils/Strategy_Builder/gui/
├── __init__.py
├── main_window.py       # Main application
├── strategy_list.py     # Left pane
├── strategy_editor.py   # Right pane
├── block_selector.py    # Block picker dialog
├── validation_panel.py  # Validation display
├── code_preview.py      # Generated code viewer
└── widgets/             # Custom widgets
    ├── __init__.py
    ├── labeled_entry.py
    ├── labeled_combobox.py
    └── block_card.py
```

### Step 2: Main Window (30 min)

- Create basic window
- Add menu bar
- Add toolbar
- Add two-pane layout
- Add status bar

### Step 3: Strategy List (30 min)

- Create listbox
- Load strategies from registry
- Handle selection events
- Add search/filter
- Add context menu

### Step 4: Strategy Editor (45 min)

- Create form fields
- Add block list display
- Add add/remove buttons
- Connect to validation
- Implement save logic

### Step 5: Block Selector (45 min)

- Create dialog window
- Add category tabs
- Create block list
- Add detail pane
- Implement signal config

### Step 6: Validation Panel (30 min)

- Create traffic light
- Add error/warning lists
- Connect to validator
- Real-time updates

### Step 7: Code Preview (30 min)

- Create tabbed dialog
- Add generated code
- Implement copy/save
- Add syntax highlighting (basic)

### Step 8: Integration & Polish (30 min)

- Connect all components
- Add keyboard shortcuts
- Add tooltips
- Test all workflows
- Fix bugs

### Step 9: Documentation (15 min)

- User guide for GUI
- Screenshots
- Video tutorial (optional)

---

## Testing Plan

### Manual Testing Checklist

- [ ] Window opens correctly
- [ ] Menu items work
- [ ] Can create new strategy
- [ ] Can load existing strategy
- [ ] Can add blocks
- [ ] Can remove blocks
- [ ] Validation updates in real-time
- [ ] Can generate files
- [ ] Can preview code
- [ ] Can save strategy
- [ ] Can delete strategy
- [ ] Search/filter works
- [ ] Keyboard shortcuts work
- [ ] Can close cleanly

### Edge Cases

- [ ] Handle empty strategy list
- [ ] Handle duplicate names
- [ ] Handle invalid input
- [ ] Handle file write errors
- [ ] Handle missing blocks
- [ ] Handle 150/150 slots

---

## Dependencies

**New Required:**
- tkinter (built-in to Python)

**Optional Enhancements:**
- ttkthemes (better themes)
- tkinter.scrolledtext (scrollable text)

---

## Deliverables

1. ✅ Functional GUI application
2. ✅ All core features working
3. ✅ Basic documentation
4. ✅ Screenshot examples
5. ✅ Launch script

---

## Success Criteria

- Non-coders can create strategies without CLI/code
- All validation rules enforced in UI
- Generated code matches CLI/API output
- Intuitive and easy to use
- No crashes on valid input
- Helpful error messages

---

## Timeline

**Total Estimate:** 3-4 hours

- Setup: 15 min
- Main components: 3 hours
- Testing: 30 min
- Documentation: 15 min

---

## Next Phase

**Phase 4: PyQt6 Professional UI**
- Modern, polished interface
- Advanced theming
- Drag-and-drop builder
- Live charting preview
- Advanced features

---

**Status:** Ready to start Phase 3 implementation!  
**Start Date:** 2026-01-09 23:55  
**Target Completion:** 2026-01-10 03:00
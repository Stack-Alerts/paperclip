# Strategy Builder Stepper Ribbon Design

## 📋 Feature Request
**Date**: 2026-01-17  
**Status**: Documented for Next Session  
**Priority**: High (Major UX Improvement)  
**Estimated Effort**: 2-3 hours

---

## 🎯 Objective

Replace the current Validation Panel with a **Stepper Ribbon** workflow guide at the top of the interface.

**Benefits**:
- ✅ Saves vertical real estate (~300px)
- ✅ Clear user flow guidance
- ✅ Visual progress tracking
- ✅ Professional workflow pattern
- ✅ Validation in modal (focused experience)

---

## 🎨 Proposed Design

### Stepper Ribbon Layout
```
┌─────────────────────────────────────────────────────────────────────────┐
│  ✓ Design Strategy  →  ⏺ Validate  →  ⏺ Generate  →  ⏺ Test  →  ⏺ Publish │
│    (Active/Green)      (Pending)      (Pending)      (Pending)   (Pending)│
└─────────────────────────────────────────────────────────────────────────┘
```

### Step States
1. **Active/Current**: Blue highlight, bold text
2. **Completed**: Green checkmark ✓, normal text
3. **Pending**: Gray circle ⏺, dimmed text
4. **Error**: Red X ✗, red text

---

## 📐 Implementation Plan

### Phase 1: Stepper Ribbon Component
**File**: `src/strategy_builder/ui/stepper_ribbon.py`

```python
class StepperRibbon(QWidget):
    """
    Stepper ribbon showing workflow progress.
    
    Steps:
    1. Design Strategy
    2. Validate
    3. Generate Code
    4. Test/Backtest
    5. Publish Status (Draft/Unpublished/Published)
    
    Signals:
        step_clicked(int): Emitted when step is clicked
    """
    
    step_clicked = pyqtSignal(int)
    
    STEPS = [
        {"name": "Design", "icon": "📝"},
        {"name": "Validate", "icon": "✓"},
        {"name": "Generate", "icon": "⚙️"},
        {"name": "Test", "icon": "🧪"},
        {"name": "Publish", "icon": "🚀"}
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_step = 0
        self.completed_steps = set()
        self._init_ui()
    
    def set_current_step(self, step: int):
        """Set the current active step."""
        self.current_step = step
        self._update_display()
    
    def mark_step_complete(self, step: int):
        """Mark a step as complete with checkmark."""
        self.completed_steps.add(step)
        self._update_display()
```

### Phase 2: Validation Modal Dialog
**File**: `src/strategy_builder/ui/validation_modal.py`

```python
class ValidationModal(QDialog):
    """
    Modal dialog for strategy validation.
    
    Shows:
    - Basic Validation (green border)
    - Standard Validation (blue border)
    - Strict Validation (purple border)
    - Validation errors/warnings
    - Action buttons: Run Validation, Close
    """
    
    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.setWindowTitle("Strategy Validation")
        self.setModal(True)
        self.resize(800, 600)
        self._init_ui()
```

### Phase 3: Integration with Main Window
**File**: `src/strategy_builder/ui/strategy_builder_main_window.py`

**Changes**:
1. Remove ValidationPanel from left column
2. Add StepperRibbon to top of window (below toolbar)
3. Connect step_clicked signal to show modal
4. Update step status based on actions

```python
# Add to _init_ui()
self.stepper = StepperRibbon()
self.stepper.step_clicked.connect(self._on_step_clicked)
main_layout.insertWidget(0, self.stepper)  # Add at top

# Remove validation panel
# left_layout.addWidget(self.validation_panel, stretch=1)
```

---

## 🎯 Step Progression Logic

### Step 1: Design Strategy
**Auto-complete when**: First block added  
**Current Step**: Always start here

### Step 2: Validate
**Action**: Click opens ValidationModal  
**Complete when**: All validations pass  
**Button**: Shows modal with validation results

### Step 3: Generate Code
**Action**: Click generates NautilusTrader code  
**Complete when**: Code generated successfully  
**Requires**: Step 2 complete

### Step 4: Test
**Action**: Click opens backtest configuration  
**Complete when**: Backtest run successfully  
**Requires**: Step 3 complete

### Step 5: Publish Status
**Action**: Click opens status dropdown  
**Options**:
- 📝 Draft (editable, not ready)
- 🔒 Unpublished (locked, reviewed, not live)
- 🚀 Published (locked, live trading)
**Complete when**: Status set

---

## 🎨 Visual Design

### Stepper Ribbon Styling
```python
stepper_style = """
QWidget#stepperRibbon {
    background-color: #1E2128;
    border-bottom: 2px solid #3C4149;
    padding: 15px 20px;
}

/* Step button - default */
QPushButton.step {
    background-color: transparent;
    border: none;
    color: #6B7280;
    font-size: 11pt;
    padding: 10px 20px;
}

/* Step button - active */
QPushButton.step.active {
    color: #2070FF;
    font-weight: bold;
}

/* Step button - completed */
QPushButton.step.completed {
    color: #10B981;
}

/* Arrow separator */
QLabel.arrow {
    color: #4A5568;
    font-size: 14pt;
}
"""
```

### Validation Modal Styling
```python
modal_style = """
QDialog {
    background-color: #15191E;
}

QGroupBox.basicValidation {
    border: 2px solid #10B981;
    border-radius: 8px;
}

QGroupBox.standardValidation {
    border: 2px solid #2070FF;
    border-radius: 8px;
}

QGroupBox.strictValidation {
    border: 2px solid #8B5CF6;
    border-radius: 8px;
}
"""
```

---

## 📊 Space Savings

### Current Layout
```
┌─────────────────┬──────────────────┐
│ Strategy Info   │ Block Search     │
│ (200px)         │ (600px)          │
├─────────────────┤                  │
│ Blocks Panel    │                  │
│ (400px)         │                  │
├─────────────────┤                  │
│ Validation      │                  │
│ (300px)         │  ← REMOVE THIS   │
└─────────────────┴──────────────────┘
```

### New Layout
```
┌──────────────────────────────────────┐
│ Stepper Ribbon (60px)               │
├─────────────────┬────────────────────┤
│ Strategy Info   │ Block Search       │
│ (200px)         │ (600px)            │
├─────────────────┤                    │
│ Blocks Panel    │                    │
│ (700px)         │  ← 300px MORE!     │
│                 │                    │
└─────────────────┴────────────────────┘
```

**Space Saved**: ~240px vertical space  
**Better UX**: Clear workflow progression

---

## 🚀 Implementation Steps

### Step 1: Create Stepper Ribbon (1 hour)
- [ ] Create `stepper_ribbon.py`
- [ ] Implement 5-step workflow
- [ ] Add step states (active, completed, pending, error)
- [ ] Add click handlers
- [ ] Style with dark theme

### Step 2: Create Validation Modal (45 min)
- [ ] Create `validation_modal.py`
- [ ] Move validation logic from panel
- [ ] Add 3 validation levels display
- [ ] Add "Validate Now" button
- [ ] Add error/warning display
- [ ] Style with dark theme

### Step 3: Integrate with Main Window (45 min)
- [ ] Remove validation panel
- [ ] Add stepper ribbon to top
- [ ] Connect step clicks to actions
- [ ] Update step status on actions
- [ ] Test complete workflow
- [ ] Update space allocation

### Step 4: Testing & Polish (30 min)
- [ ] Test all step transitions
- [ ] Test modal open/close
- [ ] Test validation in modal
- [ ] Verify space savings
- [ ] Polish animations/transitions

**Total Estimated Time**: 3 hours

---

## 📝 Next Session TODO

1. **Read this document first**
2. **Implement StepperRibbon component**
3. **Implement ValidationModal component**
4. **Integrate into main window**
5. **Remove old ValidationPanel**
6. **Test complete workflow**
7. **Commit and deploy**

---

## 🎯 Expected Outcome

**User Flow**:
1. User opens app → Step 1 (Design) is active
2. User adds blocks → Step 1 gets checkmark
3. User clicks Step 2 (Validate) → Modal opens
4. User clicks "Validate Now" → Shows results
5. All pass → Step 2 gets checkmark, modal closes
6. User clicks Step 3 (Generate) → Generates code
7. Success → Step 3 gets checkmark
8. User clicks Step 4 (Test) → Opens backtest config
9. Runs test → Step 4 gets checkmark
10. User clicks Step 5 (Publish) → Sets status

**Professional, guided workflow!** ✨

---

## 💡 Additional Enhancements (Future)

- [ ] Tooltips on each step explaining what it does
- [ ] Keyboard shortcuts (Ctrl+1, Ctrl+2, etc.)
- [ ] Progress percentage (e.g., "60% Complete")
- [ ] Estimated time to completion
- [ ] Undo/redo for workflow steps
- [ ] Save workflow state with strategy

---

**Created**: 2026-01-17 06:54  
**Status**: Ready for Implementation  
**Priority**: High  
**Effort**: 3 hours  
**Value**: Major UX improvement + 240px space savings

# Smart Content-Aware Resizable Details Panel - Design Specification

**Status**: DESIGN PHASE  
**Priority**: MEDIUM  
**Complexity**: HIGH  
**Estimated Implementation**: 4-6 hours  
**Target Sprint**: TBD  

---

## Problem Statement

### Current Behavior (Undesirable)
When user drags the details panel divider up to expand the panel:
- **All 3 columns resize proportionally** using fixed `setRowStretch()` values
- Sections with text that already fits get excessive white space
- Sections with cut-off text that need expansion get minimal additional space
- Results in poor UX and wasted screen real estate

### User Requirement
**Smart Content-Aware Resizing:**
1. When dragging panel UP: **Only sections with cutoff text should resize**
2. Sections where text already fits: **Should stay at current size**
3. Once ALL text fits in all sections: **Then resize all equally**
4. Maximum height: **50% of window OR when all content fits perfectly**

---

## Current Implementation Analysis

### File
`src/strategy_builder/ui/strategy_browser_dialog.py`

### Details Panel Structure
```
QFrame (details_frame)
  └─ QGridLayout (details_layout)
      ├─ Row 0: Column titles (3 columns)
      ├─ Row 1: Primary content (stretch=2)
      ├─ Row 2: Secondary content (stretch=2)
      └─ Row 3: Metadata (stretch=1)
```

### Current Row Stretches (STATIC)
```python
details_layout.setRowStretch(1, 2)  # Always 2x
details_layout.setRowStretch(2, 2)  # Always 2x
details_layout.setRowStretch(3, 1)  # Always 1x
```

**Problem**: These are STATIC. They never change based on content.

---

## Solution Architecture

### Overview
Implement **Dynamic Content-Aware Layout Management** that:
- Measures actual content height vs allocated space
- Detects text overflow/cutoff
- Dynamically adjusts row stretch factors
- Recalculates on resize events

### Components Needed

#### 1. Content Measurement Utility
```python
class ContentMeasurement:
    """Measures QLabel content height and detects overflow"""
    
    @staticmethod
    def get_content_height(label: QLabel) -> int:
        """
        Calculate actual height needed to display all text
        
        Returns:
            int: Height in pixels required for all content
        """
        # Use QTextDocument to measure HTML content
        doc = QTextDocument()
        doc.setHtml(label.text())
        doc.setTextWidth(label.width())
        return int(doc.size().height())
    
    @staticmethod
    def is_text_cutoff(label: QLabel) -> bool:
        """
        Detect if text is being cut off (content > allocated space)
        
        Returns:
            bool: True if text is cut off, False if fits
        """
        content_height = ContentMeasurement.get_content_height(label)
        allocated_height = label.height()
        return content_height > allocated_height
    
    @staticmethod
    def calculate_overflow_pixels(label: QLabel) -> int:
        """
        Calculate how many pixels are being cut off
        
        Returns:
            int: Pixels of overflow (0 if fits)
        """
        content_height = ContentMeasurement.get_content_height(label)
        allocated_height = label.height()
        return max(0, content_height - allocated_height)
```

#### 2. Dynamic Layout Controller
```python
class SmartResizableDetailsPanel(QFrame):
    """
    Details panel with smart content-aware resizing
    
    Dynamically adjusts row stretches based on content overflow
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.detail_labels = {}
        self.details_layout = QGridLayout(self)
        self._init_ui()
        
        # Install resize event filter
        self.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Intercept resize events to recalculate layout"""
        if event.type() == QEvent.Resize:
            self._recalculate_stretches()
        return super().eventFilter(obj, event)
    
    def _recalculate_stretches(self):
        """
        Dynamically adjust row stretches based on content overflow
        
        Algorithm:
        1. Measure overflow in each row
        2. If ANY row has overflow: Distribute stretch based on overflow amount
        3. If NO row has overflow: Equal stretch (all fit)
        4. Apply new stretch factors
        """
        # Map row index to labels
        row_labels = {
            1: [self.detail_labels['name'], self.detail_labels['blocks'], 
                self.detail_labels['tests']],
            2: [self.detail_labels['description'], self.detail_labels['blocks'],  # blocks spans 2 rows
                self.detail_labels['performance']],
            3: [self.detail_labels['meta'], self.detail_labels['signals'], 
                self.detail_labels['status']]
        }
        
        # Calculate overflow for each row
        row_overflows = {}
        for row_idx, labels in row_labels.items():
            max_overflow = 0
            for label in labels:
                overflow = ContentMeasurement.calculate_overflow_pixels(label)
                max_overflow = max(max_overflow, overflow)
            row_overflows[row_idx] = max_overflow
        
        # Determine stretch factors
        total_overflow = sum(row_overflows.values())
        
        if total_overflow == 0:
            # All text fits - equal stretch
            for row_idx in [1, 2, 3]:
                self.details_layout.setRowStretch(row_idx, 1)
        else:
            # Distribute stretch based on overflow
            # Rows with more overflow get more stretch
            for row_idx, overflow in row_overflows.items():
                if overflow > 0:
                    # Proportional to overflow amount
                    stretch = max(1, int(overflow / 50))  # 50px overflow = 1 unit stretch
                else:
                    # Fits - minimum stretch (stay small)
                    stretch = 0  # Don't grow
                
                self.details_layout.setRowStretch(row_idx, stretch)
```

#### 3. Maximum Height Constraint
```python
def _calculate_max_height(self) -> int:
    """
    Calculate maximum allowed height for details panel
    
    Returns min of:
    1. 50% of window height
    2. Content-fit height (height when all text fits perfectly)
    """
    # Option 1: 50% of window
    window_height = self.window().height()
    fifty_percent = window_height // 2
    
    # Option 2: Content-fit
    content_fit = self._calculate_content_fit_height()
    
    return min(fifty_percent, content_fit)

def _calculate_content_fit_height(self) -> int:
    """
    Calculate height needed for all content to fit perfectly
    
    Measures all labels and sums required heights + margins
    """
    total_height = 0
    
    # Measure each label
    for label in self.detail_labels.values():
        content_height = ContentMeasurement.get_content_height(label)
        total_height += content_height
    
    # Add margins and spacing
    total_height += self.details_layout.spacing() * 4  # Between rows
    total_height += self.details_layout.contentsMargins().top()
    total_height += self.details_layout.contentsMargins().bottom()
    
    return total_height

def resizeEvent(self, event):
    """Handle resize events to enforce max height"""
    super().resizeEvent(event)
    
    max_height = self._calculate_max_height()
    if self.height() > max_height:
        # Prevent further expansion
        self.setMaximumHeight(max_height)
    else:
        # Allow shrinking
        self.setMaximumHeight(16777215)  # Qt max
```

---

## Implementation Plan

### Phase 1: Foundation (2 hours)
1. Create `ContentMeasurement` utility class
2. Add unit tests for content measurement
3. Verify QTextDocument height calculation accuracy

### Phase 2: Dynamic Layout Controller (2 hours)
1. Create `SmartResizableDetailsPanel` class
2. Implement `_recalculate_stretches()` algorithm
3. Install event filter for resize events
4. Test with sample data (varying text lengths)

### Phase 3: Max Height Constraint (1 hour)
1. Implement `_calculate_max_height()`
2. Implement `_calculate_content_fit_height()`
3. Add `resizeEvent()` override
4. Test 50% window constraint
5. Test content-fit constraint

### Phase 4: Integration & Testing (1 hour)
1. Replace current QFrame with SmartResizableDetailsPanel
2. Verify all label references work
3. Test edge cases:
   - Very long text in one section
   - All sections with short text
   - Mix of long and short text
   - Window resize behavior
4. Performance profiling (resize smoothness)

---

## Edge Cases to Handle

### 1. Very Long Text in Single Section
**Scenario**: Description has 500 lines, others have 3 lines
**Expected**: Description gets most stretch, others stay small
**Test**: Verify other sections don't get white space

### 2. All Text Fits
**Scenario**: All sections have 2-3 lines, plenty of space
**Expected**: Equal stretch (no white space)
**Test**: Verify no section grows excessively

### 3. Window Resize
**Scenario**: User resizes window width or height
**Expected**: Max height recalculates, stretches recalculate
**Test**: Verify smooth reflow without flicker

### 4. Content Update
**Scenario**: User selects different strategy with different text lengths
**Expected**: Stretch factors recalculate immediately
**Test**: Verify instant adaptation

### 5. Minimum Height Enforcement
**Scenario**: Content-fit height < 450px
**Expected**: 450px minimum still enforced
**Test**: Verify panel doesn't shrink below 450px

---

## Performance Considerations

### Optimization Strategies
1. **Debounce resize events**: Max 60 FPS (16ms delay)
2. **Cache measurements**: Invalidate on content change only
3. **Lazy calculation**: Only recalculate when panel visible
4. **Batch layout updates**: Set all stretches in one pass

### Profiling Targets
- Resize event handling: < 5ms
- Stretch recalculation: < 10ms
- Total resize smoothness: 60 FPS maintained

---

## Testing Strategy

### Unit Tests
```python
def test_content_measurement_short_text():
    """Test measurement of text that fits"""
    label = QLabel("Short text")
    height = ContentMeasurement.get_content_height(label)
    assert height < 50  # Should be small

def test_content_measurement_long_text():
    """Test measurement of very long text"""
    label = QLabel("Long text " * 100)
    label.setWordWrap(True)
    label.setFixedWidth(200)
    height = ContentMeasurement.get_content_height(label)
    assert height > 200  # Should be tall

def test_overflow_detection():
    """Test cutoff detection"""
    label = QLabel("Long text " * 100)
    label.setWordWrap(True)
    label.setFixedWidth(200)
    label.setFixedHeight(50)  # Force cutoff
    assert ContentMeasurement.is_text_cutoff(label) == True
```

### Integration Tests
```python
def test_smart_panel_resize_with_overflow():
    """Test panel resizing when text is cut off"""
    panel = SmartResizableDetailsPanel()
    panel.detail_labels['description'].setText("Long " * 200)
    panel.detail_labels['name'].setText("Short")
    
    panel._recalculate_stretches()
    
    # Description should get more stretch
    desc_stretch = panel.details_layout.rowStretch(2)
    name_stretch = panel.details_layout.rowStretch(1)
    assert desc_stretch > name_stretch
```

### Manual Testing
1. Load strategy with long description, short other fields
2. Drag panel up - verify only description expands
3. Drag panel down - verify shrinks smoothly
4. Load strategy with all short text
5. Drag panel up - verify equal expansion
6. Resize window - verify max height adjusts

---

## UI/UX Benefits

### Before (Current)
❌ All sections resize proportionally
❌ Excessive white space in sections that fit
❌ Insufficient space for sections with overflow
❌ Poor screen real estate usage

### After (With Smart Resizing)
✅ Only overflowing sections expand
✅ No wasted white space
✅ Maximum text visibility
✅ Efficient space usage
✅ Professional adaptive UX

---

## Success Criteria

1. ✅ Only sections with text cutoff resize when dragging up
2. ✅ Sections with fitting text stay at current size
3. ✅ Once all text fits, equal resize
4. ✅ Max height: 50% window or content-fit (whichever is smaller)
5. ✅ Minimum height: 450px enforced
6. ✅ Smooth resize at 60 FPS
7. ✅ No flicker or layout jumps
8. ✅ Instant adaptation to content changes

---

## Future Enhancements (Post-Implementation)

### Priority 2: Column-Level Granularity
Currently targets rows (across all 3 columns)
Could target individual cells for even finer control

### Priority 3: Animation
Smooth animated transitions when stretches change
Enhances perceived quality

### Priority 4: User Preferences
Allow user to toggle:
- Smart resizing ON/OFF
- Preferred max height %
- Minimum stretch thresholds

---

## References

### Qt Documentation
- QGridLayout: https://doc.qt.io/qt-5/qgridlayout.html
- QTextDocument: https://doc.qt.io/qt-5/qtextdocument.html
- QLabel sizing: https://doc.qt.io/qt-5/qlabel.html#minimumSizeHint

### Similar Implementations
- Slack message panels (adaptive height)
- VS Code sidebar sections (collapsible with smart sizing)
- Email clients (adaptive preview pane)

---

## Approval Checklist

- [ ] Design reviewed by lead developer
- [ ] UX requirements validated by product owner
- [ ] Performance targets agreed
- [ ] Testing strategy approved
- [ ] Implementation scheduled in sprint

---

**Document Version**: 1.0  
**Created**: 2026-01-26  
**Author**: Cline AI  
**Status**: Awaiting Approval

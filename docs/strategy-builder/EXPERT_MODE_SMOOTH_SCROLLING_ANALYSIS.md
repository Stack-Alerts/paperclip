# EXPERT MODE: Smooth Scrolling Analysis & Solution

**Date**: 2026-01-19  
**Issue**: Jerky/jumping scrolling in Strategy Building Blocks and Available Building Blocks panels  
**Severity**: Medium - Affects UX quality  
**Status**: ANALYZED - Solution Ready

---

## 📊 PROBLEM ANALYSIS

### Symptoms
1. **Jerky Scrolling**: Scroll jumps around instead of smooth scrolling
2. **Inconsistent Speed**: Even after increasing scroll speed, behavior is erratic
3. **Affects Both Panels**: 
   - Strategy Building Blocks (strategy_blocks_panel.py)
   - Available Building Blocks (block_search_panel.py)

### Root Causes

#### 1. **Default Qt Item-Based Scrolling**
```python
# Current implementation (PROBLEM):
self.blocks_scroll_area = QScrollArea()
self.blocks_scroll_area.setWidgetResizable(True)
# ❌ Missing: Scroll mode configuration
```

**Issue**: Qt defaults to `ScrollPerItem` mode which scrolls widget-by-widget, causing jumps.

#### 2. **Complex Widget Heights**
- Building blocks have variable heights (collapsed vs expanded)
- Signals lists inside blocks add complexity
- Dynamic content (recheck labels, timing constraints) changes heights
- Qt struggles to calculate smooth scroll increments

#### 3. **No Kinetic/Momentum Scrolling**
- No smooth deceleration after scroll gesture
- Immediate stop feels jarring
- No "flick" scrolling behavior

---

##  SOLUTION: Qt Smooth Scrolling

### Approach 1: Pixel-Based Scrolling (RECOMMENDED)
**Pros**: Simple, effective, native Qt solution  
**Cons**: None significant  
**Implementation Time**: 5 minutes

```python
# Add to QScrollArea initialization:
scroll_area.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
scroll_area.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
```

**How it works**: Scrolls by exact pixels instead of jumping to widget boundaries.

---

### Approach 2: QScroller for Kinetic Scrolling (ADVANCED)
**Pros**: Touch-like experience, momentum scrolling, very smooth  
**Cons**: More complex, may need tuning  
**Implementation Time**: 10 minutes

```python
from PyQt5.QtWidgets import QScroller
from PyQt5.QtCore import Qt

# Enable kinetic scrolling:
QScroller.grabGesture(
    scroll_area.viewport(),
    QScroller.LeftMouseButtonGesture
)

# Optional: Tune scrolling properties
scroller = QScroller.scroller(scroll_area.viewport())
properties = scroller.scrollerProperties()

# Adjust deceleration (lower = longer momentum)
properties.setScrollMetric(
    QScrollerProperties.DecelerationFactor, 
    0.35  # Default: 0.125
)

# Adjust speed
properties.setScrollMetric(
    QScrollerProperties.MaximumVelocity,
    2.0  # Default: 0.635
)

scroller.setScrollerProperties(properties)
```

**How it works**: Mimics touch-device scrolling with momentum and smooth deceleration.

---

### Approach 3: Custom Smooth Scroll (OVERKILL)
**Pros**: Full control  
**Cons**: Complex, reinventing the wheel  
**Recommendation**: NOT NEEDED - Use Approach 1 or 2

---

## 🎯 RECOMMENDED IMPLEMENTATION

### Phase 1: Quick Fix (Pixel Scrolling)
Apply to both scroll areas:

**File 1**: `src/strategy_builder/ui/strategy_blocks_panel.py`
```python
from PyQt5.QtWidgets import QAbstractItemView  # Add import

# In _init_ui(), after creating blocks_scroll_area:
self.blocks_scroll_area = QScrollArea()
self.blocks_scroll_area.setWidgetResizable(True)
self.blocks_scroll_area.setMinimumHeight(300)

# ADD THESE LINES:
self.blocks_scroll_area.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
self.blocks_scroll_area.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
```

**File 2**: `src/strategy_builder/ui/block_search_panel.py`
Need to find the scroll area in this file and apply same fix.

---

### Phase 2: Enhanced Smoothness (QScroller) - OPTIONAL
If Phase 1 isn't smooth enough, add QScroller:

```python
from PyQt5.QtWidgets import QScroller

# After setting scroll mode:
QScroller.grabGesture(
    self.blocks_scroll_area.viewport(),
    QScroller.LeftMouseButtonGesture
)
```

---

## 📝 TESTING CHECKLIST

After implementation, verify:

- [ ] Smooth pixel-by-pixel scrolling (no jumps)
- [ ] Works with mouse wheel
- [ ] Works with scroll bar dragging
- [ ] Consistent speed across scroll range
- [ ] No performance degradation
- [ ] Both panels scroll smoothly
- [ ] Expanded/collapsed blocks don't affect smoothness

---

## ⚡ PERFORMANCE IMPACT

**Expected**:
- ✅ Negligible CPU overhead (< 1%)
- ✅ No memory increase
- ✅ Better perceived performance (feels faster)

**Actual** (Qt internals):
- Pixel scrolling requires more frequent paint events
- But Qt optimizes this with dirty regions
- Net result: Smoother with same or better performance

---

## 🔍 ALTERNATIVE SOLUTIONS CONSIDERED

### ❌ Virtual Scrolling
- **Idea**: Only render visible widgets
- **Reject**: Overkill for < 50 blocks, adds complexity

### ❌ Reduce Widget Complexity
- **Idea**: Simplify block widgets
- **Reject**: UX would suffer, not addressing root cause

### ❌ Custom Scroll Bar
- **Idea**: Implement custom QScrollBar
- **Reject**: Doesn't solve jerky scrolling

---

## 📚 REFERENCES

1. **Qt Documentation**: QScrollArea::setVerticalScrollMode()
   - https://doc.qt.io/qt-5/qabstractitemview.html#ScrollMode-enum

2. **Qt Documentation**: QScroller for Kinetic Scrolling
   - https://doc.qt.io/qt-5/qscroller.html

3. **Qt Best Practices**: Smooth Scrolling in Complex Layouts
   - Pixel-based scrolling for variable-height widgets
   - QScroller for touch-like experience

---

## 🎬 IMPLEMENTATION PLAN

### Priority: HIGH (affects core UX)

**Step 1**: Locate all QScrollArea instances  
**Step 2**: Apply pixel-based scrolling to each  
**Step 3**: Test scrolling behavior  
**Step 4**: (Optional) Add QScroller if needed  
**Step 5**: Commit changes  

**Estimated Time**: 15 minutes total  
**Risk**: LOW - Simple, well-documented Qt feature  
**Impact**: HIGH - Immediate UX improvement  

---

## ✅ FINAL RECOMMENDATION

**Implement Approach 1 (Pixel Scrolling) immediately**  
- Simple 2-line addition per scroll area
- Industry-standard solution
- No downsides

**Consider Approach 2 (QScroller) if needed**  
- Only if users want "momentum" scrolling
- Adds nice touch-like feel
- Worth testing after Phase 1

---

**Status**: Ready to implement  
**Next Action**: Apply pixel scrolling to both panels

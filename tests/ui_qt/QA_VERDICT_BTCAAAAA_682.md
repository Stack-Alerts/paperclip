## QA: FAIL

### Executive Summary

**Issue**: BTCAAAAA-682 — BTCAAAAA-386 reopened: board's multi-monitor maximize/restore broken

**Verdict**: FAIL — `showMaximized()` called via `QTimer.singleShot(50)` does not execute on the board's real Linux window manager. Window state remains `WindowNoState (0)` after the deferred maximize fires.

**Status set to**: blocked

---

### Evidence: WindowGeometry Log Analysis

The board's `~/.btc-trade-engine/window-geometry.log` (real multi-monitor session, 4 screens: DP-1, DP-2, DP-3, HDMI-1) conclusively proves the bug:

#### strategyBrowser (QMainWindow, restored maximized)
```
[RESTORE] strategyBrowser: maximized=True max_screen=HDMI-1
[PRE-MAX MOVE] strategyBrowser: -> (4007,3439) screen=HDMI-1
[POST-MOVE] strategyBrowser: frameGeometry=(4007, 3439, 1200, 800) windowState=0
[TIMER] strategyBrowser: scheduling showMaximized in 50 ms
[MAXIMIZE FIRED] strategyBrowser: frameGeometry=(4006, 3364, 1200, 874) windowState=0
```

**Critical**: `windowState=0` (WindowNoState) after `showMaximized()` fires. Window stays at 1200x800 — not maximized. The only change is the frame y-offset shifting by ~75px (title bar compensation).

#### mainWindow (QMainWindow)
```
[POST-MOVE] mainWindow: frameGeometry=(835, 3389, 3068, 1255) windowState=0
[MAXIMIZE FIRED] mainWindow: frameGeometry=(834, 3314, 3070, 1330) windowState=0
```

Same pattern — `windowState=0` after `showMaximized()`. No actual maximize.

#### Offscreen Platform Test (passes — false negative)
```
QT_QPA_PLATFORM=offscreen -> showMaximized() works: isMax=True, int_state=2
```

The offscreen platform driver unconditionally honors maximize. Real window managers (X11/Wayland) may reject deferred `showMaximized()` after the window is already mapped.

---

### Root Cause

**`showMaximized()` deferred via `QTimer.singleShot(50)` fails** on the board's Linux window manager.

Location: `src/strategy_builder/ui/styles.py:1952-1959` (in `WindowGeometryMixin._restore_window_geometry()`):

```python
QTimer.singleShot(50, _do_maximize)
```

This timer fires *after* the window has completed its initial `show()` -> map -> expose cycle. Some Linux window managers reject maximize requests after the window is already displayed on screen. The correct approach is to set `setWindowState(Qt.WindowMaximized)` **synchronously** before or during `showEvent`, before the window manager commits the initial geometry.

The 50 ms deferral was introduced to work around Qt5 bugs (BTCAAAAA-474/475), but that workaround itself breaks on real multi-monitor setups.

#### Contradiction in the fix

Commit `a6408a9c` restructured `_restore_window_geometry()` to add a dedicated `if maximized:` branch that *skips* `saved_pos` positioning. This is correct in avoiding a double-move race. But the deferral pattern remains — `showMaximized()` still fires 50 ms later from a timer, which doesn't work on this WM.

---

### Acceptance Criteria Status

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Drag from title-bar — no resize as side effect | Untestable headless | Requires real WM drag interaction |
| 2 | Click maximize — window fills current screen | **FAIL** | `windowState=0` after `showMaximized()` in log |
| 3 | Maximize -> restore -> returns to pre-max size | **FAIL** (blocked on #2) | If maximize doesn't work, restore is moot |
| 4 | Move to screen N -> close -> reopen on screen N | **FAIL** (blocked on #2) | Maximized-window save/restore on specific screen fails |

---

### Test Results

- **Suite**: `QT_QPA_PLATFORM=offscreen pytest tests/ui_qt -v --tb=short`
- **Result**: 95/95 PASSED (false negative -- real WM behavior not tested)
- **Anti-mock-pollution**: CLEAN (no mock imports in `tests/ui_qt/`)
- **Coverage gap**: No tests exercise `showMaximized()` through the deferred timer path on a real window manager

---

### Required Fixes

1. **Remove the QTimer.singleShot deferral** for `showMaximized()` in `WindowGeometryMixin._restore_window_geometry()`. Call `setWindowState(Qt.WindowMaximized)` synchronously **before** or during `showEvent`, before `super().showEvent(event)` processes the initial map.

2. **Add a post-assertion**: After calling `showMaximized()`, verify `isMaximized() == True`. If false, fall back to synchronous `setWindowState(Qt.WindowMaximized)`.

3. **Window flag audit**: Verify `Qt.CustomizeWindowHint` is not missing on BacktestConfigDialog and all dialog windows. Some WMs require this for maximize to work.

4. **Add deferred-maximize regression test**: Create a test that hooks `QTimer.singleShot` to verify window state after deferred maximize fires (at minimum docs/qa: document that deferred maximize is known to fail on Wayland/GNOME).

---

### Checklist Items Verified

- [x] Anti-mock-pollution: CLEAN
- [x] pytest: 95/95 passed (offscreen)
- [x] Window flags present on BacktestConfigDialog
- [x] WindowGeometry log analysis complete
- [x] Root cause identified in styles.py
- [x] Acceptance criteria evaluated

---

### Bug Issue

Child bug report: **BUG: WindowGeometryMixin — deferred showMaximized() ignored by Linux WM on multi-monitor**

- **Failing test**: `tests/ui_qt/test_window_geometry.py::test_settings_dialog_can_maximize` (headless: passes, real: fails)
- **Component**: `src/strategy_builder/ui/styles.py::WindowGeometryMixin._restore_window_geometry`
- **Assignee**: UIEngineer (`9113b321-771b-481d-8ae7-33765ed9b1f5`)

---

### Status

- BTCAAAAA-682 -> **blocked**
- Blocked on child bug fix
- Will re-run full UI suite when `issue_blockers_resolved` wake fires

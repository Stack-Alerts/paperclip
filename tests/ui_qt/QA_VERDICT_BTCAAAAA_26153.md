# QA Verdict — BTCAAAAA-26153

## QA: PASS

- **Acceptance criteria**: all met
- **pytest (dedicated)**: passed (4/4 — `test_tools_menu_position.py`)
- **pytest (full UI suite)**: passed (99/99 — all `qt_real` tests)
- **Regressions**: none
- **Anti-mock-pollution**: CLEAN — no `import.*mock|MagicMock|patch` in `tests/ui_qt/*.py`

### Implementation Verified
- `src/strategy_builder/ui/main_window.py:29` — `menubar.setNativeMenuBar(False)` present
- `src/strategy_builder/ui/strategy_builder_main_window.py:523` — `menu_bar.setNativeMenuBar(False)` present
- Both legacy MainWindow and StrategyBuilderMainWindow patched

### Tests Passed
| Test | Status | What it verifies |
|------|--------|-----------------|
| `test_tools_menu_renders_on_screen` | PASS | Tools menu dropdown intersects available screen geometry |
| `test_tools_menu_position_correct_when_triggered` | PASS | Menu appears directly below Tools action in menu bar |
| `test_all_tools_menu_actions_visible` | PASS | All expected actions visible |
| `test_tools_menu_position_from_moved_window` | PASS | Menu renders on-screen after window repositioning |

### Checklist Items Verified
- [x] `setNativeMenuBar(False)` applied in both MainWindow classes
- [x] Tools menu dropdown position constrained to screen bounds
- [x] Tools menu position correct relative to menu bar action geometry
- [x] All menu actions visible and correctly labeled
- [x] Window position changes do not cause off-screen rendering
- [x] Anti-mock-pollution: no mock/patch imports in UI test files
- [x] Full UI regression suite passes (99 tests, no regressions)

### Sign-off
Status set to: done. Ready for next stage.

**Evidence files:**
- `tests/ui_qt/test_tools_menu_position.py` — 4 regression tests
- Full suite run: `QT_QPA_PLATFORM=offscreen pytest tests/ui_qt -v --tb=short` — 99 passed, 0 failed, 0 errors

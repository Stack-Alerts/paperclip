# UI Migration Assessment: PyQt5 → NextJS

**Issue**: BTCAAAAA-15  
**Author**: CTO  
**Date**: 2026-05-13  
**Status**: DRAFT — awaiting CEO/board review

---

## Executive Summary

Migrating the BTC Trade Engine UI from PyQt5 to NextJS is a **major re-platforming effort** (~4–6 months for a skilled 2-person team, ~$5K–$10K in AI token costs). The codebase has no existing web backend, meaning both a new API layer AND 42+ React components must be built from scratch. The requirement for pixel-identical reproduction and localhost-only deployment adds meaningful constraints.

**Bottom line**: This is not a lift-and-shift. It is a full rewrite of the presentation layer plus construction of a new backend API bridge.

---

## 1. Current Codebase Scope

### 1.1 Strategy Builder UI (`src/strategy_builder/ui/`)

| Metric | Count |
|--------|-------|
| Python files | 31 |
| Lines of code | ~35,000 |
| Widget/dialog/window classes | 28 |
| Stylesheet lines (QSS) | 2,023 |

**Key screens/windows** (28 distinct classes):

| Component | Type | LOC (approx) | Complexity |
|-----------|------|-------------|------------|
| `StrategyBuilderMainWindow` | QMainWindow | 2,700 | Very High — main workspace with 3-panel splitter, toolbar, menu, status bar, stepper ribbon, inter-component signals |
| `StrategyBlocksPanel` | QWidget | ~1,500 | High — dynamic block config items, combos, signal deps |
| `BlockSearchPanel` | QWidget | ~800 | Medium — search/filter with block registry integration |
| `StrategyInfoPanel` | QWidget | ~600 | Medium — form fields, metadata |
| `BacktestConfigDialog` | QDialog | ~1,200 | High — multi-tab config, validation integration |
| `BacktestConfigPanel` | QWidget | ~1,500 | High — auto-calibration, parameter grid |
| `ConfigPermutationEngine` | QWidget | ~1,500 | Very High — combinatoric config discovery |
| `ValidationDialog` | QDialog | ~800 | High — runs institutional validator, threaded |
| `ValidationPanel` | QWidget | ~500 | Medium — validation results display |
| `ValidationReportWindow` | QMainWindow | ~900 | Medium — report viewer |
| `ExitConditionDialog` | QMainWindow | ~1,200 | High — complex form with AND/OR logic |
| `TimingConstraintDialog` | QDialog | ~600 | Medium — within-N-candles config |
| `StepperRibbon` | QWidget | ~400 | Low-Medium — workflow stepper |
| `SystemConfigWindow` | QMainWindow | ~800 | Medium — system-level settings |
| `SettingsDialog` | QDialog | ~800 | Medium — secrets, admin pin, API keys |
| `NewStrategyDialog` | QDialog | ~400 | Low |
| `StrategyBrowserDialog` | QMainWindow | ~600 | Medium |
| `DataUpdateModal` | QDialog | ~500 | Medium — progress bar, threaded fetch |
| `DataVerifyDialog` | QDialog | ~400 | Medium |
| `LogViewerWindow` | QDialog | ~400 | Low |
| `AlertDialog` / `QuestionDialog` | QDialog | ~200 | Low |
| `AutoFixConfirmDialog` | QDialog | ~300 | Low |
| `ConfigDiscoveryResultsDialog` | QDialog | ~800 | Medium |
| `CustomTitleBar` | QWidget | ~300 | Medium — custom window chrome |
| `BlockConfigItem` | QWidget | ~400 | Low — per-block inline config |
| `BlockListItem` | QWidget | ~200 | Low |
| `QuickPreviewResultsDialog` | QDialog | ~300 | Low |
| `SecretFieldWidget` | QWidget | ~200 | Low |
| `MainWindow` (legacy wrapper) | QMainWindow | ~73 | Low |
| `AdminPinDialog` | QDialog | ~150 | Low |

### 1.2 Optimizer V3 UI (`src/optimizer_v3/ui/`)

| Metric | Count |
|--------|-------|
| Python files | 12 |
| Lines of code | ~42,500 |
| Widget classes | 14 |

**Key components**:

| Component | Type | LOC (approx) | Complexity |
|-----------|------|-------------|------------|
| `TrainingPanelUI` | QWidget | 888 | Medium — preserved/deprecated module |
| `TradesPanel` | QWidget | 1,128 | High — trade table, filtering, export |
| `TrainingResultsTable` | QWidget | ~2,000 | High — sortable multi-column table |
| `BacktestConfigurationPanel` | QWidget | ~3,000 | Very High — config grid, calibration |
| `BacktestProgressPanel` | QWidget | ~800 | Medium — progress, ETA |
| `MetricsDisplayPanel` | QWidget | ~1,500 | High — equity curve, drawdown, returns |
| `CompareViewPanel` | QWidget | ~1,200 | High — side-by-side run comparison |
| `OptimizerControls` | QWidget | ~800 | Medium — parameter grid, run controls |
| `AIRecommendationsPanel` | QWidget | ~1,000 | Medium — AI suggestion cards |
| `LiveOutputPanel` | QWidget | ~600 | Medium — streaming log output |
| `ui_config.py` | config | 500 | — style constants, layout cfg |
| `recommendation_worker.py` | worker | ~300 | Low — QThread worker |

### 1.3 Design System

The current UI has a **fully documented design system** across `docs/ui/`:
- `Color_pallet.md` — exact hex values, CSS variables already pre-specified
- `13_VISUAL_DESIGN_SYSTEM.md` — component specs, spacing, typography
- `14_RESPONSIVE_DESIGN.md` — responsive behavior specs
- `CENTRALIZED_STYLESHEET_GUIDE.md` — style organization
- `STRATEGY_BUILDER_DESIGN_ANALYSIS.md` — full UX flow analysis
- Expert assessment reports (20–24) — design quality, usability, implementation readiness

This is a **strong advantage** — the design tokens are already extracted into CSS-variable form in `Color_pallet.md`, reducing the design translation work.

---

## 2. Architecture Gap Analysis

### 2.1 What Exists Today

```
┌─────────────────────────────────────────────────┐
│  PyQt5 Application Process                       │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐ │
│  │ Strategy │  │ Optimizer│  │ Backtest      │ │
│  │ Builder  │  │ V3 UI    │  │ Config        │ │
│  │ MainWin  │  │ Panels   │  │ Dialogs       │ │
│  └────┬─────┘  └────┬─────┘  └───────┬───────┘ │
│       │             │               │          │
│  ┌────┴─────────────┴───────────────┴──────────┐│
│  │    Direct Python imports/calls               ││
│  │    (Orchestrator, Validator, Registry, etc.) ││
│  └────────────────────┬────────────────────────┘│
│                       │                         │
│  ┌────────────────────┴────────────────────────┐│
│  │  Business Logic Layer                        ││
│  │  (NautilusTrader, indicators, data mgr)      ││
│  └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

**Critical observation**: There is **zero API layer**. The PyQt UI calls Python business logic directly via imports and method calls. There is no REST, no WebSocket, no RPC bridge. Every `QPushButton.clicked -> orchestrator.do_something()` call is a direct in-process Python call.

### 2.2 What Must Be Built for NextJS

```
┌──────────────────────┐     HTTP/WS      ┌──────────────────────┐
│  NextJS Frontend     │ <--------------> │  Python Backend API  │
│  (localhost:3000)    │                  │  (localhost:8000)    │
│                      │                  │                      │
│  - 42+ React comps   │                  │  - FastAPI routes    │
│  - Tailwind/shadcn   │                  │  - WebSocket events  │
│  - State mgmt (Zust) │                  │  - Auth/session     │
│  - React Query       │                  │  - File I/O bridge  │
│  - shadcn/ui comps   │                  │  - Long-poll/SSE    │
└──────────────────────┘                  └──────────┬───────────┘
                                                     │
                                        ┌────────────┴───────────┐
                                        │  Business Logic Layer   │
                                        │  (existing — unchanged) │
                                        └────────────────────────┘
```

**New infrastructure required**:
1. **FastAPI backend** (~50–80 new API endpoints, ~15 WebSocket channels)
2. **Authentication layer** (currently handled by PyQt admin pin dialog — needs JWT/session equivalent)
3. **File I/O bridge** (QFileDialog -> browser file APIs or backend file serving)
4. **QSettings -> localStorage/server-side config bridge**
5. **Threading model rewrite** (QThread workers -> async/background tasks via FastAPI BackgroundTasks or Celery)

---

## 3. Phase Breakdown & Time Estimates

### Phase 0: Backend API Foundation (4–5 weeks)

Build the bridge between NextJS and the existing Python business logic.

| Task | Effort | Notes |
|------|--------|-------|
| FastAPI project scaffold + project structure | 2 days | Routes, middleware, CORS for localhost |
| Strategy CRUD endpoints (~12 routes) | 1 week | Create, read, update, delete, list, clone, validate, export |
| Block Registry endpoints (~8 routes) | 3 days | List, search, filter, get details, get parameters |
| Backtest execution endpoints (~10 routes) | 1 week | Start, progress (SSE/WS), results, cancel, list-history |
| Optimizer/training endpoints (~10 routes) | 1 week | Config, start, progress, results, compare, export |
| System config & settings endpoints (~6 routes) | 3 days | Read/write system config, API key management |
| WebSocket channels for real-time output | 3 days | Backtest progress, training output, live data streaming |
| Auth/session (if needed for multi-user localhost) | 2 days | JWT or session-based, admin pin equivalent |
| **Phase 0 subtotal** | **~5 weeks** | 1 senior backend dev |

### Phase 1: Component Library & Design System (2–3 weeks)

Translate the QSS stylesheet and design docs into a Tailwind + shadcn/ui system.

| Task | Effort | Notes |
|------|--------|-------|
| Tailwind config (colors, spacing, typography from Color_pallet.md) | 1 day | CSS vars already documented |
| shadcn/ui component customization (dark theme) | 3 days | Theme provider, base component overrides |
| Layout primitives (splitter, resizable panels, stepper) | 3 days | Custom React components; no native HTML splitter |
| Form component library (styled inputs, combos, spinners) | 2 days | Wrapping shadcn/ui form primitives |
| Table component (sortable, filterable, virtualized) | 3 days | For training results, trades table |
| Chart/visualization integration (recharts or lightweight-charts) | 2 days | Equity curve, drawdown, metrics display |
| Custom title bar / window chrome (for Electron wrapper) | 1 day | If Electron used; skip if browser native |
| **Phase 1 subtotal** | **~3 weeks** | 1 frontend dev |

### Phase 2: Strategy Builder UI — Screens & Dialogs (6–8 weeks)

Rebuild all 28 Strategy Builder components as React pages/components.

| Screen Group | Components | Effort (weeks) |
|-------------|-----------|---------------|
| **Core workspace** | Main window with 3-panel splitter, toolbar, menu, status bar, stepper ribbon | 1.5 |
| **Block management** | Block search panel, strategy blocks panel, block config items | 1.5 |
| **Strategy CRUD** | New strategy dialog, strategy browser, strategy info panel | 1.0 |
| **Backtest** | Backtest config dialog, backtest config panel, config permutation engine | 2.0 |
| **Validation** | Validation dialog, validation panel, validation report window | 1.0 |
| **Exit conditions** | Exit condition dialog, timing constraint dialog | 1.0 |
| **Settings & system** | Settings dialog, system config window, admin pin, secret fields | 0.5 |
| **Utilities** | Data update modal, data verify dialog, log viewer, alerts, auto-fix, config discovery | 1.0 |
| **Phase 2 subtotal** | | **~8 weeks** |

### Phase 3: Optimizer V3 UI (4–6 weeks)

| Screen Group | Components | Effort (weeks) |
|-------------|-----------|---------------|
| **Training & backtest** | Backtest config panel, backtest progress panel, training results table | 2.0 |
| **Results & analysis** | Metrics display panel, compare view, trades panel | 1.5 |
| **Controls & config** | Optimizer controls, parameter grid, AI recommendations panel | 1.0 |
| **Output** | Live output panel (streaming), recommendation worker bridge | 1.0 |
| **Phase 3 subtotal** | | **~5 weeks** |

### Phase 4: Integration, Polish & Packaging (4–5 weeks)

| Task | Effort | Notes |
|------|--------|-------|
| End-to-end flow testing (all user flows from design docs) | 1 week | |
| Pixel-level comparison with PyQt5 screenshots | 1 week | Side-by-side, component-by-component |
| Performance optimization (virtualized tables, lazy loading) | 3 days | Training results table with 10K+ rows |
| Error handling & loading states | 3 days | Every async operation |
| Localhost packaging (Electron or Tauri) | 1 week | Single-click launch; auto-starts Python backend |
| Build pipeline (NextJS build + Python backend bundle) | 3 days | |
| **Phase 4 subtotal** | **~5 weeks** | |

### Total Time: 21–27 weeks (~5–7 months) for a 2-person team (1 backend + 1 frontend)

**Critical path**: Backend API (Phase 0) and Core Workspace (Phase 2) are gating. Phase 3 (Optimizer) can partially overlap with late Phase 2.

---

## 4. AI Token Cost Estimate

Assumes AI-assisted development (Claude, GPT-4, Cursor, Copilot) for code generation, refactoring, and debugging.

### Methodology

- **LOC generated by AI**: ~60–70% of the new codebase will be AI-assisted (component scaffolding, API routes, Tailwind classes, boilerplate)
- **Token burn rate**: ~2–5 tokens per line of generated code (prompt + completion)
- **Iteration factor**: 2–3x for refinement, bug fixes, review cycles

### New Code to Write

| Layer | Estimated LOC | AI-Assisted % | AI Tokens (range) |
|-------|--------------|---------------|-------------------|
| FastAPI backend (routes, schemas, WS) | ~8,000–12,000 | 70% | 5.6M–18M tokens |
| React/NextJS components (~42 classes) | ~25,000–35,000 | 65% | 16M–52M tokens |
| Tailwind styles / theme config | ~2,000–3,000 | 80% | 1.6M–4.8M tokens |
| State management (Zustand stores) | ~2,000–3,000 | 60% | 1.2M–4.5M tokens |
| Tests (frontend + backend) | ~5,000–8,000 | 75% | 3.7M–12M tokens |
| Configuration, build, packaging | ~1,000–2,000 | 50% | 0.5M–2M tokens |
| **Total** | **~43,000–63,000** | | **~30M–95M tokens** |

### Cost at Current API Pricing (May 2026)

| Provider | Input $/1M tokens | Output $/1M tokens | Estimated Cost (30M–95M) |
|----------|-------------------|---------------------|--------------------------|
| Claude Opus 4 | $15/$75 | — | **$4,500–$14,250** |
| Claude Sonnet 4 | $3/$15 | — | **$900–$2,850** |
| GPT-4o | $2.50/$10 | — | **$750–$2,375** |
| Gemini 2.5 Pro | $1.25/$5 | — | **$375–$1,187** |

**Realistic blended estimate** (mixing Sonnet for scaffolding, Opus for complex logic, GPT-4o for boilerplate):  
→ **$3,000–$8,000 in AI API token costs**

Additional costs:
- Copilot/Cursor subscription: ~$200–400/month x 6 months = $1,200–$2,400
- **Total AI tooling cost: ~$5,000–$10,000**

> **Note**: This is API token cost only. It does NOT include developer salary, which is the dominant cost at 21–27 person-weeks.

---

## 5. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **No existing API layer** — entire backend bridge is greenfield | Critical | FastAPI is well-established; use code generation for route scaffolding |
| **Business logic coupling** — PyQt code directly imports orchestrator, validator, etc. | High | Phase 0 must build a clean API facade; do NOT refactor business logic |
| **Threading complexity** — QThread workers become async tasks; long-running backtests need new execution model | High | Use FastAPI BackgroundTasks + WebSocket progress; keep existing worker logic, wrap it |
| **Pixel-identical requirement** — CSS flexbox/grid behave differently than Qt layouts | Medium | Extensive screenshot comparison during Phase 4; accept 95% fidelity as success threshold |
| **Custom title bar / window chrome** — PyQt custom title bar needs Electron/Tauri equivalent | Medium | Browser-based title bars are simpler; consider dropping custom chrome for standard OS chrome |
| **QFileDialog / native dialogs** — no direct browser equivalent | Low | Use `<input type="file">` + backend file serving |
| **QSettings -> browser storage** — settings persistence model changes | Low | localStorage for UI prefs; backend for secrets/config |
| **Localhost-only constraint adds complexity** — need packaging for non-technical users | Medium | Electron or Tauri wrapper; alternatively, a simple launcher script that opens browser |
| **Scope creep** — "while we're at it" temptation to redesign flows | Medium | Freeze UX; this is a translation, not a redesign |

---

## 6. Alternatives to Full Migration

### 6.1 Hybrid Approach (Recommended for Incremental Value)

Instead of a full rewrite, build **new features** in NextJS while the PyQt5 app remains for existing screens:
- Build the NextJS backend API (Phase 0)
- Port ONE high-value screen (e.g., Strategy Browser) as a proof-of-concept
- If successful, progressively migrate screens over 12+ months
- **Cost**: ~$15K–$30K tokens, ~8–12 weeks for initial API + first screen
- **Risk**: Much lower; delivers value incrementally

### 6.2 WebView Embedding

Embed a NextJS web view inside the PyQt5 app using `QWebEngineView`:
- No packaging needed; stays in PyQt5 shell
- Allows gradual migration
- **Cost**: ~$5K tokens for prototype
- **Risk**: Lowest; provides path to eventual full migration

### 6.3 Desktop-as-Web (PWA)

Package the NextJS app as a PWA (Progressive Web App) without Electron/Tauri:
- Users open `http://localhost:3000` in their browser
- Backend starts via a simple Python script
- No native packaging overhead
- **Cost savings**: Eliminates Phase 4 packaging (~3 weeks)
- **Trade-off**: Less polished desktop experience (no system tray, no native menus)

---

## 7. Recommendation

**Do not pursue a full migration at this time.** The cost (~6 months, ~$5–10K AI tokens, 2 full-time developers) is high relative to the current state of the application. The PyQt5 UI is functional, signed-off, and meets all current requirements.

**Recommended incremental path**:
1. **Now**: Build the FastAPI backend (Phase 0, ~5 weeks, ~$2K tokens). This creates immediate value — the API can serve both the existing PyQt5 UI (via a refactored data layer) AND a future NextJS frontend.
2. **Next**: Port the Strategy Browser screen to NextJS as proof-of-concept (~3 weeks, ~$1K tokens). Validate the approach.
3. **Gate check**: After POC, re-assess whether full migration provides ROI.

---

## Appendix A: Component Mapping Quick Reference

| PyQt5 Widget | React Equivalent | Notes |
|-------------|-----------------|-------|
| `QMainWindow` | NextJS page/layout | Single-page app with routes |
| `QDialog` | Dialog/modal (shadcn/ui Dialog) | Modal overlay pattern |
| `QWidget` (panel) | React component | Standard component |
| `QSplitter` | Custom splitter (react-resizable-panels) | No native HTML equivalent |
| `QGroupBox` | Fieldset or Card with border | shadcn/ui Card |
| `QLineEdit` | `<Input>` (shadcn/ui) | Standard |
| `QComboBox` | `<Select>` (shadcn/ui) | Use cmdk for searchable selects |
| `QCheckBox` | `<Checkbox>` (shadcn/ui) | Standard |
| `QSpinBox` | `<Input type="number">` with stepper | Custom or shadcn |
| `QPushButton` | `<Button>` (shadcn/ui) | Standard |
| `QTableWidget`/`QTableView` | TanStack Table + shadcn/ui | Virtual scrolling for large datasets |
| `QTextEdit` | `<Textarea>` (shadcn/ui) | Standard |
| `QProgressBar` | `<Progress>` (shadcn/ui) | Standard |
| `QTabWidget` | `<Tabs>` (shadcn/ui) | Standard |
| `QMenuBar`/`QMenu` | Navigation menu or DropdownMenu | shadcn/ui |
| `QToolBar` | Fixed toolbar component | Custom |
| `QStatusBar` | Fixed footer component | Custom |
| `QFileDialog` | `<input type="file">` or custom | Browser-native |
| `QMessageBox` | Toast/sonner or AlertDialog | shadcn/ui |
| `QThread` (worker) | async/await + WebSocket | Architectural shift |

---

## Appendix B: Files Touched in Migration

### Must rewrite (43 files, ~77,500 LOC)

```
src/strategy_builder/ui/alert_dialog.py
src/strategy_builder/ui/auto_fix_confirm_dialog.py
src/strategy_builder/ui/backtest_config_dialog.py
src/strategy_builder/ui/backtest_config_panel.py
src/strategy_builder/ui/block_search_panel.py
src/strategy_builder/ui/combobox_fix.py
src/strategy_builder/ui/config_discovery_results_dialog.py
src/strategy_builder/ui/config_permutation_engine.py
src/strategy_builder/ui/content_measurement.py
src/strategy_builder/ui/custom_title_bar.py
src/strategy_builder/ui/data_update_modal.py
src/strategy_builder/ui/data_verify_dialog.py
src/strategy_builder/ui/exit_condition_dialog.py
src/strategy_builder/ui/log_viewer_window.py
src/strategy_builder/ui/main_window.py
src/strategy_builder/ui/new_strategy_dialog.py
src/strategy_builder/ui/settings_dialog.py
src/strategy_builder/ui/settings_service.py
src/strategy_builder/ui/stepper_ribbon.py
src/strategy_builder/ui/strategy_blocks_panel.py
src/strategy_builder/ui/strategy_browser_dialog.py
src/strategy_builder/ui/strategy_builder_main_window.py
src/strategy_builder/ui/strategy_info_panel.py
src/strategy_builder/ui/styles.py
src/strategy_builder/ui/system_config.py
src/strategy_builder/ui/timing_constraint_dialog.py
src/strategy_builder/ui/validation_dialog.py
src/strategy_builder/ui/validation_panel.py
src/strategy_builder/ui/validation_report_window.py
src/optimizer_v3/ui/ai_recommendations_panel.py
src/optimizer_v3/ui/backtest_panels.py
src/optimizer_v3/ui/compare_view_panel.py
src/optimizer_v3/ui/live_output_panel.py
src/optimizer_v3/ui/metrics_display_panel.py
src/optimizer_v3/ui/optimizer_controls.py
src/optimizer_v3/ui/recommendation_worker.py
src/optimizer_v3/ui/trades_panel.py
src/optimizer_v3/ui/training_panel.py
src/optimizer_v3/ui/training_results_table.py
src/optimizer_v3/ui/ui_config.py
src/optimizer_v3/core/training_thread.py
src/optimizer_v3/core/ai_request_preview_window.py
scripts/launch_strategy_builder.py
```

### Must NOT modify (business logic — stays unchanged)

```
src/strategy_builder/integration/strategy_builder_orchestrator.py
src/strategy_builder/registry/
src/strategy_builder/signals/
src/optimizer_v3/validation/
src/optimizer_v3/core/  (except UI-related files listed above)
src/strategies/
src/indicators/
src/data_manager/
src/itm/
src/detectors/
```

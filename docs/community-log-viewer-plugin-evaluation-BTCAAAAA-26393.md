# Community Log Viewer Plugin Evaluation

**Issue**: BTCAAAAA-26393 (P1.4)
**Author**: AutomationEngineer
**Date**: 2026-05-14
**Parent**: BTCAAAAA-26251 — Investigate this plugins
**Status**: COMPLETE — awaiting UIEngineer review

---

## Executive Summary

The community log viewer plugin from `git.freno.me/Mike/paperclip-plugins/plugin-log-viewer` is a **PaperClip agent activity monitor**, not a trade execution log viewer. It captures PaperClip platform events (agent run lifecycle, issue/goal/agent CRUD) and displays them in a React-based dashboard widget and full-page view within the PaperClip host UI.

**Bottom line**: The plugin does **not** meet our needs for trade execution log viewing. It cannot read local `.log` files, has no trade-event awareness, and lacks the filtering/analysis capabilities our built-in PyQt5 viewer provides. However, the plugin architecture is well-structured and could serve as a **reference pattern** for building a PaperClip-native trade log viewer.

**Recommendation**: **Adopt for agent activity monitoring** (low effort, immediate value). **Build from scratch** for trade execution log viewing as a separate PaperClip plugin (P2.1). Keep the existing PyQt5 `log_viewer_window.py` for desktop use.

---

## 1. Plugin Analysis

### 1.1 Architecture

| Component | Technology | LOC | Description |
|-----------|-----------|-----|-------------|
| `manifest.ts` | TypeScript | 53 | Plugin declaration: ID, capabilities, UI slots (dashboard widget + full page) |
| `worker.ts` | TypeScript | 130 | Event listeners for 7 PaperClip event types, in-memory log buffer (max 100), state persistence, data/action/health endpoints |
| `ui/index.tsx` | React/TSX | 187 | Two UI surfaces: `DashboardWidget` (3 most recent events) and `LogsPage` (full list with clear/refresh) |
| `tests/plugin.spec.ts` | Vitest | 26 | Single integration test via SDK test harness |

### 1.2 Capabilities

- **Event subscription**: Listens to `agent.run.started`, `agent.run.finished`, `agent.run.failed`, `issue.created`, `issue.updated`, `goal.created`, `agent.created`
- **State management**: Plugin-scoped state (key-value) via `ctx.state.set/get`
- **Data providers**: `logs` (returns LogEntry[]) and `health` (returns status + log count)
- **Actions**: `clear-logs` (reset buffer), `ping` (health-check action)
- **UI slots**: Dashboard widget (shows 3 recent events + total count) and full page at `/plugins/log-viewer`
- **UI launcher**: Global toolbar button "View Logs" linking to log viewer page

### 1.3 UI/UX Quality

| Criterion | Assessment |
|-----------|-----------|
| **Layout** | Simple grid-based layout, max-width 800px centered |
| **Styling** | Inline styles only, no theme integration with host PaperClip UI |
| **Event coloring** | 6 hardcoded color values for event types (failed=red, finished=green, etc.) |
| **Filtering** | None — all events shown, no search, no category filters |
| **Pagination** | None — capped at 100 entries, oldest dropped |
| **Responsiveness** | Basic — loading/error/empty states handled |
| **Accessibility** | None — no ARIA labels, no keyboard navigation |

### 1.4 Code Quality

| Dimension | Score | Notes |
|-----------|-------|-------|
| **TypeScript strictness** | Good | `strict: true` in tsconfig, clean interfaces |
| **Test coverage** | Minimal | Single integration test, no unit tests for UI components |
| **Error handling** | Adequate | Loading/error states in UI, try-catch in worker events |
| **Logging** | Basic | Uses plugin SDK logger at info level |
| **Dependencies** | Blocked | Requires unpublished SDK tarballs (`file:.paperclip-sdk/paperclipai-plugin-sdk-1.0.0.tgz`) — not installable from npm |

---

## 2. Gap Analysis: Trade Execution Log Viewing

### 2.1 Capability Comparison

| Feature | Community Plugin | Our Built-in Viewer (`log_viewer_window.py`) |
|---------|-----------------|---------------------------------------------|
| **Log source** | PaperClip API events (in-memory) | Local `.log` files on disk |
| **Event types** | 7 (agent run, issue, goal, agent CRUD) | 24 (TRADE_OPENED, TRADE_CLOSED, CONFIG_*, SIGNAL_DETECTED, etc.) |
| **File system access** | None | Full — directory scanning, rglob, file reads with line caps |
| **Multi-tab** | No | Yes — All Logs, per-type tabs, AI/Signal evaluator tabs |
| **Event filtering** | None | Per-event checkbox grid (6 columns), tab-aware filter presets |
| **Syntax highlighting** | No, plain text | QSyntaxHighlighter with regex-based color coding |
| **Search** | No | No (neither has it) |
| **Copy/paste** | No | Copy all + copy selection to clipboard |
| **Clear logs** | Yes (action) | Yes (with confirmation dialog, disk deletion) |
| **Lazy loading** | N/A (100 entries max) | Yes — tab content loaded on first activation |
| **Background worker** | Event-driven (passive) | QThreadPool directory scanner |
| **Max entries** | 100 (FIFO) | 5000 lines/file, 100 files max |
| **Persistence** | Plugin state (host-managed) | QSettings (window geometry, last tab) |
| **UI technology** | React (PaperClip host surface) | PyQt5 QDialog (standalone window) |
| **Tech stack** | TypeScript, React | Python, PyQt5 |

### 2.2 Critical Gaps

1. **No log file ingestion**: The plugin only captures PaperClip API events. It cannot read or tail local `.log` files, which is the primary requirement for trade execution log viewing.

2. **No trade event awareness**: Our 24 event patterns (trade opened/closed/updated, positions snapshot, signal detected, config validated, etc.) have no analog in the plugin's event model.

3. **No file management**: The plugin has no concept of rotating log files, multi-directory log scanning, or file truncation for performance.

4. **No structured log parsing**: Our viewer applies regex-based pattern matching with contextual detail lines (indented continuation lines for stack traces, trade metadata fields like `Side:`, `Size:`, `Entry Price:`).

5. **Insufficient scale**: 100-entry FIFO buffer vs our 5000 lines/file, 100-file ceiling. Trade sessions generate thousands of log lines.

---

## 3. Extensibility Assessment

### 3.1 What Could Be Extended

The PaperClip plugin SDK provides hooks that could theoretically support a trade log viewer:

- **Custom event listeners** (`ctx.events.on`): Could subscribe to custom events if we emit trade log events into the PaperClip event bus
- **Data providers** (`ctx.data.register`): Could expose log content from a file reader
- **Actions** (`ctx.actions.register`): Could add search, filter, copy actions
- **UI slots**: Could add custom React components for trade-specific views
- **Plugin state** (`ctx.state`): Could persist user preferences

### 3.2 Estimated Adaptation Effort

| Component | Effort | Notes |
|-----------|--------|-------|
| File-system log reader | **High** | Requires a worker that polls/tails log files, parses trade events, and pushes to plugin state. The SDK has no built-in fs module. |
| Trade event patterns | **Medium** | Port 24 regex patterns + color mapping from Python to TypeScript |
| Filtering UI | **High** | Rebuild ~450 lines of filter UI (checkbox grid, tab-aware presets, context-line logic) in React |
| Syntax highlighting | **Medium** | React-side regex highlighting on render or a lightweight code highlighter lib |
| Multi-tab | **Medium** | React tab component with lazy content loading |
| Copy/clear | **Low** | Browser clipboard API, action wiring |
| Performance at scale | **High** | Need virtualized list for 5000+ lines, debounced regex matching |

**Total adaptation estimate**: ~3–5 days for a skilled TypeScript/React developer, comparable to a from-scratch build.

---

## 4. Recommendation

### 4.1 For Agent Activity Monitoring

**ADOPT** the community plugin as-is for PaperClip agent run/event monitoring. It provides immediate value for:
- Tracking when agents start/finish/fail
- Monitoring issue/goal/agent creation
- A lightweight dashboard widget

**Action**: Build and install the plugin into the PaperClip instance. This requires obtaining the `@paperclipai/plugin-sdk` SDK (currently unpublished; blocked until available on npm or vendored from a local PaperClip checkout).

### 4.2 For Trade Execution Log Viewing

**BUILD FROM SCRATCH** as a separate PaperClip plugin (`plugin-trade-log-viewer`). Rationale:

1. The community plugin has **zero overlap** with trade log viewing requirements
2. Adapting it would require rewriting >80% of its code
3. A fresh plugin can be purpose-built for our domain: trade events, file watching, institutional log formats
4. The existing PyQt5 viewer (`src/strategy_builder/ui/log_viewer_window.py:279`) remains the primary desktop tool — no regression risk

**Reference patterns to reuse** from the community plugin:
- Plugin manifest structure (`manifest.ts`)
- Worker setup pattern (`definePlugin`, `runWorker`)
- Data provider + action registration patterns
- Test harness usage (`createTestHarness`)

### 4.3 Architecture Recommendation for P2.1

```
plugin-trade-log-viewer/
├── src/
│   ├── manifest.ts          # Plugin declaration
│   ├── worker.ts            # Log file watcher, event parser, state manager
│   ├── event_patterns.ts    # 24 trade event regex patterns (ported from Python)
│   ├── log_reader.ts        # File-system log ingestion (fs.watchFile or polling)
│   └── ui/
│       ├── DashboardWidget.tsx   # Recent trade events on dashboard
│       ├── LogsPage.tsx          # Full trade log viewer
│       ├── EventFilters.tsx      # Checkbox grid filter component
│       ├── TradeLogEntry.tsx     # Single log entry component with highlighting
│       └── useTradeLogs.ts       # Data hook for trade-specific state
└── tests/
    └── plugin.spec.ts
```

---

## 5. Dependencies & Blockers

| Blocker | Status | Resolution |
|---------|--------|------------|
| `@paperclipai/plugin-sdk` unpublished | **BLOCKED** | Must be published to npm or vendored from a local Paperclip checkout. Routes to **RepoSteward** for npm publish or **CTO** for local checkout access. |
| P1.1 dev environment (BTCAAAAA-26390) | Done | Environment ready |
| UI assessment | **PENDING** | Routes to **UIEngineer** per issue description for UI/UX quality review |

---

## 6. Next Actions

1. ~~Evaluate plugin source code~~ (this report)
2. UIEngineer reviews UI/UX section (Sections 1.3, 3.1) and adds their assessment
3. Resolve SDK availability blocker with RepoSteward/CTO
4. Create P2.1 child issue for `plugin-trade-log-viewer` implementation
5. Build and install the community plugin for agent activity monitoring (once SDK is available)

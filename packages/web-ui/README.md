# BTC Trade Engine - React UI Modules

React port of PyQt5 UI modules for integration with NautilusTrader backend.

**Status**: Phase 1 Complete ✅ | Phase 2 In Progress 🔄

---

## Project Overview

This is a Next.js 15 application that provides a modern React interface for the BTC Trade Engine, replacing the original PyQt5 desktop application. The application integrates with NautilusTrader for backtesting and strategy management.

### Tech Stack

- **Framework**: Next.js 16.2.6
- **Runtime**: React 19.2.4
- **Styling**: Tailwind CSS 4.x
- **Type Safety**: TypeScript 5.x
- **UI Components**: Custom component library + Lucide React icons
- **Charts**: Recharts
- **Date Utilities**: date-fns

---

## Modules Completed

### 1. Backtest Configuration ✅

**Component**: `src/components/backtest/BacktestConfigPanel.tsx`

Features:
- Lookback period & training window configuration
- Mode selection (Historical / Live Replay)
- Strategy & instrument selection
- Real-time progress tracking
- Results display with performance metrics
- Control buttons (Run/Stop)

### 2. Data Management ✅

**Component**: `src/components/data-management/DataManagementPanel.tsx`

Features:
- Data source listing & management
- Status indicators
- Gap detection & classification
- Repair capability for gaps
- Last updated tracking

### 3. Log Viewer ✅

**Component**: `src/components/log-viewer/LogViewerPanel.tsx`

Features:
- Real-time log streaming
- Event-based filtering with color coding
- Log level filtering
- Search functionality
- Auto-scroll to latest

### 4. Settings ✅ (P1 Skeleton)

**Component**: `src/components/settings/SettingsPanel.tsx`

Features:
- Tabbed settings interface
- Basic configuration (General, API)
- Form input types
- Save/Reset functionality
- Change detection

---

## Build Status

✅ **Compilation**: Successful
✅ **TypeScript**: Type checking passed
✅ **Production Build**: Generated

```bash
# Test build
npm run build
# Output: ✓ Compiled successfully
```

---

## Running the Application

### Development Server
```bash
npm run dev
# Opens at http://localhost:3000
```

### Production Build
```bash
npm run build
npm run start
```

### Linting
```bash
npm run lint
```

---

## Integration Points (Next Phase)

1. **NautilusTrader API** - Implement actual backend calls
2. **WebSocket** - Real-time log streaming & backtest updates
3. **Authentication** - User authentication layer
4. **Tooltip Registry** - Complete tooltip implementation
5. **Testing** - Unit & integration tests

---

## File Structure

```
packages/web-ui/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Main dashboard
│   │   └── layout.tsx
│   ├── components/
│   │   ├── backtest/
│   │   ├── data-management/
│   │   ├── log-viewer/
│   │   ├── settings/
│   │   └── ui/                   # Reusable UI components
│   ├── types/
│   │   └── index.ts              # Shared types
│   ├── hooks/
│   ├── utils/
│   └── lib/
├── package.json
├── tsconfig.json
└── next.config.js
```

---

## Acceptance Criteria Status

### Phase 1 - Core Implementation ✅
- [x] All 4 modules ported to React
- [x] Integrated into Next.js 15 app shell
- [x] Build succeeds without errors
- [x] TypeScript type checking passes

### Phase 2 - Integration & Testing 🔄
- [ ] NautilusTrader API integration
- [ ] Tooltip registry implementation
- [ ] Automated testing infrastructure
- [ ] CI/CD pipeline integration
- [ ] QA sign-off

---

**Last Updated**: 2026-05-16
**Version**: 0.1.0 (Phase 1 Complete)
**Status**: Ready for Integration Testing

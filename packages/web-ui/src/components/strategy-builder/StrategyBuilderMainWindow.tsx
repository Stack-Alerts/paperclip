'use client';

import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { NewStrategyDialog } from './NewStrategyDialog';
import { StrategyBrowserDialog } from './StrategyBrowserDialog';
import { BacktestConfigDialog } from './BacktestConfigDialog';
import { ValidationDialog } from './ValidationDialog';
import { DataUpdateModal } from './DataUpdateModal';
import { DataVerifyDialog, TimeframeVerifyResult } from './DataVerifyDialog';
import { SettingsDialog } from './SettingsDialog';
import { AlertDialog, QuestionDialog } from './AlertDialog';
import { AdminPinDialog } from './AdminPinDialog';
import { StepperRibbon } from './StepperRibbon';
import { StrategyInfoPanel } from './StrategyInfoPanel';
import { StrategyBlocksPanel } from './StrategyBlocksPanel';
import { BlockSearchPanel } from './BlockSearchPanel';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import * as api from '@/lib/strategy-builder/api';
import type { BacktestResult, BacktestConfig, Strategy, Block } from '@/lib/strategy-builder/types';
import { BlockType } from '@/lib/strategy-builder/types';
import { RichTooltip, TooltipContent } from './RichTooltip';
import { useTooltipSettings } from './TooltipSettingsContext';
import { ThemeSelector } from './ThemeSelector';
import { Plus, FolderOpen, Save, Play, ChevronDown } from 'lucide-react';
import { useSidebar } from '@/contexts/SidebarContext';
import { AppBrand } from '@/components/shared/AppBrand';

type DialogKey =
  | 'newStrategy'
  | 'strategyBrowser'
  | 'backtestConfig'
  | 'validation'
  | 'dataUpdate'
  | 'dataVerify'
  | 'settings'
  | 'alert'
  | 'question'
  | 'adminPin'
  | 'quickPreview'
  | 'logViewer'
  | null;

// ---------------------------------------------------------------------------
// QuickPreviewResultsDialog
// ---------------------------------------------------------------------------
interface QuickPreviewResultsDialogProps {
  open: boolean;
  result: BacktestResult | null;
  onClose: () => void;
}

function QuickPreviewResultsDialog({ open, result, onClose }: QuickPreviewResultsDialogProps) {
  if (!open || !result) return null;

  const winRate = result.winRate * 100;
  const rows: [string, string, string][] = [
    ['Win Rate',       `${winRate.toFixed(1)}%`,         winRate >= 50 ? 'var(--accent-green)' : 'var(--accent-red)'],
    ['Total Trades',   String(result.totalTrades),        'var(--text-primary)'],
    ['Winning Trades', String(result.winningTrades),      'var(--accent-green)'],
    ['Total Return',   `${result.returnPercentage >= 0 ? '+' : ''}${result.returnPercentage.toFixed(2)}%`,
      result.returnPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'],
    ['Max Drawdown',   `${result.maxDrawdown.toFixed(2)}%`,  'var(--accent-red)'],
    ['Sharpe Ratio',   result.sharpeRatio.toFixed(2),     'var(--text-primary)'],
    ['Profit Factor',  result.profitFactor.toFixed(2),    'var(--text-primary)'],
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg shadow-2xl w-96 p-6 border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>30-Day Backtest Summary</h2>
          <button onClick={onClose} className="text-xl leading-none" style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>✕</button>
        </div>
        <div className="space-y-1.5">
          {rows.map(([label, value, color]) => (
            <div key={label} className="flex items-center justify-between py-1">
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>{label}:</span>
              <span className="text-sm font-semibold" style={{ color }}>{value}</span>
            </div>
          ))}
        </div>
        {result.totalTrades === 0 && (
          <p className="mt-3 text-xs" style={{ color: 'var(--text-muted)' }}>
            No trades found in this 30-day period. Try lowering the confluence threshold.
          </p>
        )}
        <div className="mt-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm rounded transition-colors"
            style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--accent-blue-mid)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--accent-blue)')}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// StrategyBuilderMainWindow
// ---------------------------------------------------------------------------
export interface StrategyBuilderMainWindowProps {
  strategyId?: string;
}

export const StrategyBuilderMainWindow: React.FC<StrategyBuilderMainWindowProps> = ({
  strategyId,
}) => {
  const { collapsed } = useSidebar();
  const [prevCollapsed, setPrevCollapsed] = useState(collapsed);
  const [showHopAnimation, setShowHopAnimation] = useState(false);

  useEffect(() => {
    if (prevCollapsed === true && collapsed === false) {
      setShowHopAnimation(true);
      setTimeout(() => setShowHopAnimation(false), 400);
    }
    setPrevCollapsed(collapsed);
  }, [collapsed, prevCollapsed]);

  const {
    currentStrategy,
    isLoadingStrategy,
    strategyError,
    loadStrategy,
    loadBlockLibrary,
    saveStrategy,
    runBacktest,
    validateStrategy,
    setCurrentStrategy,
    backTestInProgress,
    hydrateFromLocalStorage,
  } = useStrategyStore();

  const [mounted, setMounted] = useState(false);
  const { settings: tooltipSettings, update: updateTooltipSettings } = useTooltipSettings();

  // Load specific strategy by URL param; block library always loaded on mount.
  // Default strategy is pre-initialized in the Zustand store so no createStrategy() needed here.
  useEffect(() => {
    // Hydrate store from localStorage after mount so SSR and initial client
    // renders are both null (no hydration mismatch).
    hydrateFromLocalStorage();
    setMounted(true);
    if (strategyId) {
      loadStrategy(strategyId).catch(console.error);
    }
    loadBlockLibrary().catch(console.error);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync clean snapshot whenever the strategy changes (from hydration or load).
  useEffect(() => {
    if (mounted) setCleanSnapshot(strategySnapshot);
  }, [currentStrategy?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Dialog state
  const [activeDialog, setActiveDialog] = useState<DialogKey>(null);
  const [quickPreviewResult, setQuickPreviewResult] = useState<BacktestResult | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<string[]>([]);
  const [consoleEnabled, setConsoleEnabled] = useState(false);

  // Stepper state
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [errorSteps, setErrorSteps] = useState<Set<number>>(new Set());

  // Dirty-flag
  const [cleanSnapshot, setCleanSnapshot] = useState<string>('');
  const strategySnapshot = useMemo(
    () =>
      currentStrategy
        ? JSON.stringify({ id: currentStrategy.id, blocks: currentStrategy.blocks, name: currentStrategy.name })
        : '',
    [currentStrategy]
  );
  const isModified = !!currentStrategy && strategySnapshot !== cleanSnapshot;
  const isSavingRef = useRef(false);

  // Status bar countdown — aligns to real 15-minute UTC candle boundaries (+0.2 s)
  const [statusText, setStatusText] = useState('Ready');
  const nextCheckRef = useRef<Date>(
    (() => {
      const now = Date.now();
      const interval = 15 * 60 * 1000;
      return new Date((Math.floor(now / interval) + 1) * interval + 200);
    })()
  );
  useEffect(() => {
    const timer = setInterval(() => {
      const diff = Math.max(0, nextCheckRef.current.getTime() - Date.now());
      if (diff < 500) {
        const interval = 15 * 60 * 1000;
        nextCheckRef.current = new Date((Math.floor(Date.now() / interval) + 1) * interval + 200);
        setStatusText('Checking data…');
        setTimeout(() => setStatusText('Data check complete'), 2000);
      } else {
        const mins = Math.floor(diff / 60000);
        const secs = Math.floor((diff % 60000) / 1000);
        setStatusText(`Next data check in ${mins}m ${secs}s`);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Resizable splitter — persists position to localStorage.
  // SPLIT_MIN: percentage floor (keeps right panel readable on very wide monitors).
  // LEFT_PANEL_MIN_PX: absolute floor for the left panel — measured against the
  // Strategy Info stats row "Time Constraint: Yes/No" wrap threshold (~605px). 620
  // gives a small buffer; below this the stat row wraps onto a second line.
  const SPLIT_MIN = 30;
  const SPLIT_MAX = 75;
  const LEFT_PANEL_MIN_PX = 620;
  const [leftPercent, setLeftPercent] = useState(30);
  const isDragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const clampSplit = useCallback((pct: number, containerWidth: number) => {
    const minFromPx = containerWidth > 0 ? (LEFT_PANEL_MIN_PX / containerWidth) * 100 : 0;
    const effectiveMin = Math.min(SPLIT_MAX, Math.max(SPLIT_MIN, minFromPx));
    return Math.min(SPLIT_MAX, Math.max(effectiveMin, pct));
  }, []);

  // Restore saved split position after mount (avoids SSR hydration mismatch) and
  // re-clamp against the current container width so a previously-saved narrow
  // position cannot survive a viewport change.
  useEffect(() => {
    const containerWidth = containerRef.current?.getBoundingClientRect().width ?? 0;
    let initial = leftPercent;
    try {
      const saved = localStorage.getItem('sb_panel_split');
      if (saved) {
        const val = parseFloat(saved);
        if (!isNaN(val)) initial = val;
      }
    } catch {}
    const clamped = clampSplit(initial, containerWidth);
    setLeftPercent(clamped);
    try { localStorage.setItem('sb_panel_split', String(clamped)); } catch {}
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-clamp when the container resizes (window resize, sidebar collapse, etc.).
  useEffect(() => {
    const node = containerRef.current;
    if (!node || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => {
      const w = node.getBoundingClientRect().width;
      if (w === 0) return;
      setLeftPercent(prev => {
        const next = clampSplit(prev, w);
        if (next !== prev) {
          try { localStorage.setItem('sb_panel_split', String(next)); } catch {}
        }
        return next;
      });
    });
    ro.observe(node);
    return () => ro.disconnect();
  }, [clampSplit]);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      const clamped = clampSplit(pct, rect.width);
      setLeftPercent(clamped);
      try { localStorage.setItem('sb_panel_split', String(clamped)); } catch {}
    };
    const onMouseUp = () => { isDragging.current = false; };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, [clampSplit]);

  const open = useCallback((key: DialogKey) => setActiveDialog(key), []);
  const close = useCallback(() => setActiveDialog(null), []);

  // -------------------------------------------------------------------------
  // Keyboard shortcuts
  // -------------------------------------------------------------------------
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S') {
      e.preventDefault();
      handleSaveAs();
    } else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      handleSave();
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
      e.preventDefault();
      open('newStrategy');
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'o') {
      e.preventDefault();
      open('strategyBrowser');
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // -------------------------------------------------------------------------
  // File menu handlers
  // -------------------------------------------------------------------------
  const handleSave = useCallback(async () => {
    if (isSavingRef.current) return;
    isSavingRef.current = true;
    try {
      await saveStrategy();
      setCleanSnapshot(strategySnapshot);
      setStatusText('Strategy saved');
      setTimeout(() => setStatusText('Ready'), 2000);
    } catch (e) {
      setStatusText('Save failed');
    } finally {
      isSavingRef.current = false;
    }
  }, [saveStrategy, strategySnapshot]);

  const handleSaveAs = useCallback(async () => {
    if (!currentStrategy) return;
    const newName = window.prompt('Save strategy as:', `${currentStrategy.name} (copy)`);
    if (!newName?.trim()) return;
    const saved = await api.post<Strategy>('/strategies', {
      ...currentStrategy,
      id: undefined,
      name: newName.trim(),
    });
    setCurrentStrategy(saved);
    setCleanSnapshot(JSON.stringify({ id: saved.id, blocks: saved.blocks, name: saved.name }));
  }, [currentStrategy, setCurrentStrategy]);

  const handleExit = useCallback(() => {
    if (isModified && !window.confirm('You have unsaved changes. Exit without saving?')) return;
    window.location.href = '/';
  }, [isModified]);

  // -------------------------------------------------------------------------
  // Edit handlers
  // -------------------------------------------------------------------------
  const handleClearBlocks = useCallback(() => {
    if (!currentStrategy) return;
    if (!window.confirm('Clear all blocks from this strategy?')) return;
    setCurrentStrategy({ ...currentStrategy, blocks: [] });
  }, [currentStrategy, setCurrentStrategy]);

  // -------------------------------------------------------------------------
  // Tools handlers
  // -------------------------------------------------------------------------
  const handleRefreshBlocks = useCallback(() => {
    loadBlockLibrary().catch(console.error);
  }, [loadBlockLibrary]);

  const handleUpdateData = useCallback(async (startDate: string, endDate: string): Promise<void> => {
    await api.post('/data/update', { startDate, endDate });
  }, []);

  const handleVerifyData = useCallback(async () => {
    return await api.post<Record<string, TimeframeVerifyResult>>('/data/verify', {});
  }, []);

  const handleRepairData = useCallback(async (timeframe: string): Promise<void> => {
    await api.post('/data/repair', { timeframe });
  }, []);

  const handleValidate = useCallback(async () => {
    try {
      await validateStrategy();
      setCompletedSteps(prev => new Set([...prev, 1]));
      setErrorSteps(prev => { const s = new Set(prev); s.delete(1); return s; });
      setCurrentStep(1);
    } catch {
      setErrorSteps(prev => new Set([...prev, 1]));
    }
  }, [validateStrategy]);

  const handleQuickPreview = useCallback(async () => {
    if (!currentStrategy || backTestInProgress) return;
    const endDate = new Date().toISOString().slice(0, 10);
    const startDate = new Date(Date.now() - 30 * 86_400_000).toISOString().slice(0, 10);
    const config: BacktestConfig = {
      strategyId: currentStrategy.id,
      startDate,
      endDate,
      initialCapital: 10_000,
      timeframe: currentStrategy.settings?.timeframe || '1h',
    };
    try {
      const result = await runBacktest(config);
      setQuickPreviewResult(result);
      open('quickPreview');
    } catch (e) {
      setStatusText('Quick preview failed');
    }
  }, [currentStrategy, runBacktest, open, backTestInProgress]);

  // -------------------------------------------------------------------------
  // Strategy browser
  // -------------------------------------------------------------------------
  const handleStrategySelect = useCallback(
    (strategy: Strategy) => {
      // BTCAAAAA-29995: the dialog fetches strategies from the strategy-builder
      // API, which returns blocks in the Python domain shape
      // `{name, logic, signals, ...}`. The frontend Block contract is
      // `{id, type, index, data}` — StrategyInfoPanel.computeStats reads
      // block.data.logic / block.data.signals and crashed on the raw shape
      // ("Cannot read properties of undefined (reading 'logic')"). Wrap each
      // raw block under .data so existing consumers see the expected shape.
      // type defaults to INDICATOR — computeStats only special-cases
      // EXIT_CONDITION; all other types fall through to the logic-based
      // branches (AND→required, OR→optional, EXIT→exit), which matches the
      // API payload's own `logic` field. Also Title-Case the API's snake_case
      // block names (`asia_session_50_percent` → `Asia Session 50 Percent`)
      // to match the block-library display names — StrategyBlocksPanel reads
      // block.data.name directly for the block title, so the prettification
      // has to happen here (formatSignalName is already applied to signals
      // inside the panel).
      const titleCase = (s: string) =>
        s.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
      const rawBlocks = Array.isArray(strategy.blocks) ? strategy.blocks : [];
      const normalized: Strategy = {
        ...strategy,
        blocks: rawBlocks.map((b, i): Block => {
          const isFrontendShape =
            b && typeof b === 'object' && 'data' in b && 'type' in b;
          if (isFrontendShape) return b as Block;
          const raw = b as unknown as Record<string, unknown>;
          const rawName = typeof raw.name === 'string' ? raw.name : '';
          return {
            id: `block-${strategy.versionId ?? strategy.id}-${i}`,
            type: BlockType.INDICATOR,
            index: i,
            data: rawName ? { ...raw, name: titleCase(rawName) } : raw,
          };
        }),
      };
      setCurrentStrategy(normalized);
      setCleanSnapshot(JSON.stringify({ id: normalized.id, blocks: normalized.blocks, name: normalized.name }));
      setCurrentStep(0);
      setCompletedSteps(new Set());
      setErrorSteps(new Set());
      close();
    },
    [close, setCurrentStrategy]
  );

  // Pop In: receive state from a popped-out Strategy Browser window and
  // re-open the inline dialog seeded with it. Remount the dialog by bumping
  // the rev so its useState initializers pick up the new initialXxx props
  // (BTCAAAAA-29371).
  type PopInSeed = {
    selectedId?: string | null;
    searchText?: string;
    typeFilter?: 'all' | 'bullish' | 'bearish';
    sortKey?: 'name' | 'blocks' | 'updated' | 'status' | 'created' | 'version';
    sortDir?: 'asc' | 'desc';
  };
  const [popInSeed, setPopInSeed] = useState<PopInSeed | null>(null);
  const [popInRev, setPopInRev] = useState(0);
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      const data = event.data as { type?: string; state?: PopInSeed } | null;
      if (!data || data.type !== 'strategy-browser:popin') return;
      setPopInSeed(data.state ?? null);
      setPopInRev(r => r + 1);
      setActiveDialog('strategyBrowser');
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  // -------------------------------------------------------------------------
  // Debug Logger helpers
  // -------------------------------------------------------------------------
  const handleDownloadLogs = useCallback(() => {
    const blob = new Blob([consoleLogs.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `strategy-builder-log-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [consoleLogs]);

  // -------------------------------------------------------------------------
  // Loading / error states
  // -------------------------------------------------------------------------
  if (isLoadingStrategy) {
    return (
      <div className="flex items-center justify-center h-full" style={{ background: 'var(--shell-bg)' }}>
        <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>Loading strategy…</div>
      </div>
    );
  }
  if (strategyError) {
    return (
      <div className="flex items-center justify-center h-full" style={{ background: 'var(--shell-bg)' }}>
        <div className="text-sm" style={{ color: 'var(--accent-red)' }}>Error: {strategyError}</div>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-full select-none"
      onKeyDown={handleKeyDown}
      tabIndex={-1}
      style={{ outline: 'none', background: 'var(--shell-bg)' }}
    >
      {/* ── Window title / Menu Bar ─────────────────────────────────────── */}
      <style>{`
        @keyframes sidebarHop {
          0% { transform: translateY(0); opacity: 0; }
          50% { transform: translateY(-4px); }
          100% { transform: translateY(0); opacity: 1; }
        }
        .hop-animation {
          animation: sidebarHop 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
      `}</style>
      <div className="flex items-center gap-2 border-b px-2 py-1 flex-shrink-0" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        {collapsed && (
          <div className={showHopAnimation ? 'hop-animation' : ''}>
            <AppBrand size={20} showWordmark={true} />
          </div>
        )}
        <MenuDropdown
          label="File"
          items={[
            { label: 'New Strategy',     onClick: () => open('newStrategy'),      shortcut: 'Ctrl+N' },
            { label: 'Open Strategy…',   onClick: () => open('strategyBrowser'),  shortcut: 'Ctrl+O' },
            { label: '—', onClick: () => {} },
            { label: 'Save',             onClick: handleSave,                     shortcut: 'Ctrl+S' },
            { label: 'Save As…',         onClick: handleSaveAs,                   shortcut: 'Ctrl+Shift+S' },
            { label: '—', onClick: () => {} },
            { label: 'Exit',             onClick: handleExit },
          ]}
        />
        <MenuDropdown
          label="Edit"
          items={[
            { label: 'Clear All Blocks', onClick: handleClearBlocks },
          ]}
        />
        <MenuDropdown
          label="Tools"
          items={[
            { label: 'Backtest…',      onClick: () => open('backtestConfig') },
            { label: 'Validate…',      onClick: handleValidate },
            { label: 'Update Data…',   onClick: () => open('dataUpdate') },
            { label: 'Verify Data…',   onClick: () => open('dataVerify') },
            { label: 'Refresh Blocks', onClick: handleRefreshBlocks },
            { label: '—', onClick: () => {} },
            { label: 'Settings…',      onClick: () => open('settings') },
            { label: '—', onClick: () => {} },
            { label: consoleEnabled ? '✓ Console Output' : 'Console Output',
              onClick: () => setConsoleEnabled(v => !v) },
            { label: 'Clear Logs',     onClick: () => setConsoleLogs([]) },
            { label: 'View Log…',      onClick: () => open('logViewer') },
            { label: 'Download Log…',  onClick: handleDownloadLogs },
          ]}
        />
        <MenuDropdown
          label="Help"
          items={[
            { label: 'About', onClick: () => open('alert') },
          ]}
        />

        {/* Strategy name + dirty indicator */}
        {mounted && currentStrategy && (
          <span className="ml-auto text-xs truncate max-w-xs pr-2" style={{ color: 'var(--text-secondary)' }}>
            BTC Trade Engine — Strategy Builder —{' '}
            <span style={{ color: 'var(--text-primary)' }}>{currentStrategy.name}</span>
            {isModified && <span className="ml-1" style={{ color: 'var(--accent-orange)' }} title="Unsaved changes">●</span>}
          </span>
        )}
      </div>

      {/* ── Toolbar + Stepper (3-column: left tools | center stepper | right spacer) ── */}
      <div className="flex items-center border-b px-3 py-1.5 flex-shrink-0" style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)' }}>
        {/* Left: toolbar buttons */}
        <div className="flex items-center gap-1">
          <ToolbarButton label="New"  icon={<Plus size={13} strokeWidth={1.5} />} tooltip={TT_NEW}  onClick={() => open('newStrategy')} />
          <ToolbarButton label="Open" icon={<FolderOpen size={13} strokeWidth={1.5} />} tooltip={TT_OPEN} onClick={() => open('strategyBrowser')} />
          <ToolbarButton
            label="Save"
            icon={<Save size={13} strokeWidth={1.5} />}
            trailing={<ChevronDown size={11} strokeWidth={1.5} />}
            tooltip={TT_SAVE}
            onClick={handleSave}
          />
          <div className="w-px h-5 mx-1 flex-shrink-0" style={{ background: 'var(--border)' }} />
          <ToolbarButton
            label={backTestInProgress ? 'Running…' : 'Quick Preview'}
            icon={<Play size={13} strokeWidth={1.5} />}
            tooltip={TT_QUICK_PREVIEW}
            onClick={handleQuickPreview}
            disabled={!currentStrategy || backTestInProgress}
          />
        </div>
        {/* Center: stepper ribbon */}
        <div className="flex-1 flex justify-center items-center gap-2">
          <StepperRibbon
            currentStep={currentStep}
            completedSteps={completedSteps}
            errorSteps={errorSteps}
            onStepClick={setCurrentStep}
            inline
          />
        </div>
        {/* Right: theme selector + tooltip settings — muted to blend with toolbar chrome */}
        <div className="flex items-center gap-3 flex-shrink-0 text-xs" style={{ minWidth: 260, justifyContent: 'flex-end', color: 'var(--text-faint)' }}>
          <ThemeSelector />
          <div className="w-px h-4" style={{ background: 'var(--border)' }} />
          <label className="flex items-center gap-1 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={tooltipSettings.enabled}
              onChange={e => updateTooltipSettings({ enabled: e.target.checked })}
              style={{ accentColor: 'var(--toolbar-accent)', width: 11, height: 11 }}
            />
            Tooltips
          </label>
          {tooltipSettings.enabled && (
            <>
              <input
                type="range"
                min={300}
                max={3000}
                step={100}
                value={tooltipSettings.delayMs}
                onChange={e => updateTooltipSettings({ delayMs: Number(e.target.value) })}
                style={{ width: 54, accentColor: 'var(--toolbar-accent)', cursor: 'pointer', opacity: 0.75 }}
              />
              <span style={{ minWidth: 24, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                {(tooltipSettings.delayMs / 1000).toFixed(1)}s
              </span>
            </>
          )}
        </div>
      </div>

      {/* ── Main Content Area (40% left / 60% right) ────────────────────── */}
      <div ref={containerRef} className="flex flex-1 overflow-hidden min-h-0">
        {/* LEFT PANEL: Strategy Info + Blocks */}
        <div
          className="flex flex-col overflow-hidden border-r"
          style={{ width: `${leftPercent}%`, borderColor: 'var(--border)' }}
        >
          {/* Section 1: Strategy Information (compact top) */}
          <div className="flex-shrink-0 border-b" style={{ borderColor: 'var(--border)' }}>
            <StrategyInfoPanel compact />
          </div>

          {/* Section 2+3: Strategy Blocks + Exit Conditions (scrollable) */}
          <div className="flex-1 overflow-hidden min-h-0">
            <StrategyBlocksPanel />
          </div>
        </div>

        {/* Drag handle */}
        <div
          className="w-2 transition-colors cursor-col-resize flex-shrink-0 flex flex-col items-center justify-center gap-0.5"
          style={{ background: 'var(--bg-card)' }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--accent-blue)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-card)')}
          onMouseDown={() => { isDragging.current = true; }}
        >
          {[0, 1, 2].map(i => (
            <div key={i} className="w-0.5 h-3 bg-[var(--border)] rounded-full" />
          ))}
        </div>

        {/* RIGHT PANEL: Block Library */}
        <div className="flex flex-col overflow-hidden flex-1 min-w-0">
          <BlockSearchPanel />
        </div>
      </div>

      {/* ── Status Bar ──────────────────────────────────────────────────── */}
      <div className="h-6 border-t px-3 flex items-center flex-shrink-0" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{statusText}</span>
      </div>

      {/* ── Dialogs ─────────────────────────────────────────────────────── */}
      <NewStrategyDialog open={activeDialog === 'newStrategy'} onClose={close} />

      <StrategyBrowserDialog
        key={`strategyBrowser-${popInRev}`}
        open={activeDialog === 'strategyBrowser'}
        onSelect={handleStrategySelect}
        onClose={close}
        initialSelectedId={popInSeed?.selectedId ?? null}
        initialSearchText={popInSeed?.searchText}
        initialTypeFilter={popInSeed?.typeFilter}
        initialSortKey={popInSeed?.sortKey}
        initialSortDir={popInSeed?.sortDir}
      />

      <BacktestConfigDialog open={activeDialog === 'backtestConfig'} onClose={close} />

      <ValidationDialog open={activeDialog === 'validation'} onClose={close} />

      <DataUpdateModal
        open={activeDialog === 'dataUpdate'}
        onUpdate={handleUpdateData}
        onSkip={close}
      />

      <DataVerifyDialog
        open={activeDialog === 'dataVerify'}
        onVerify={handleVerifyData}
        onRepair={handleRepairData}
        onClose={close}
      />

      <SettingsDialog open={activeDialog === 'settings'} onClose={close} />

      <QuickPreviewResultsDialog
        open={activeDialog === 'quickPreview'}
        result={quickPreviewResult}
        onClose={close}
      />

      {activeDialog === 'logViewer' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="rounded-lg shadow-2xl w-2/3 max-h-[70vh] flex flex-col p-6 border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Debug Log Viewer</h2>
              <div className="flex gap-2 items-center">
                <button onClick={() => setConsoleLogs([])} className="text-xs px-2 py-1 rounded transition-colors" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}>Clear</button>
                <button onClick={handleDownloadLogs} className="text-xs px-2 py-1 rounded transition-colors" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}>Download</button>
                <button onClick={close} className="text-xl leading-none ml-2" style={{ color: 'var(--text-muted)' }}
                  onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
                  onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>✕</button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto rounded p-3 font-mono text-xs border" style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
              {consoleLogs.length === 0
                ? <span style={{ color: 'var(--text-faintest)' }}>No log entries.</span>
                : consoleLogs.map((line, i) => <div key={i}>{line}</div>)
              }
            </div>
          </div>
        </div>
      )}

      <AlertDialog
        open={activeDialog === 'alert'}
        title="BTC Trade Engine"
        heading="Strategy Builder"
        message="Institutional-grade algorithmic trading platform."
        icon="ℹ️"
        onClose={close}
      />

      <QuestionDialog
        open={activeDialog === 'question'}
        title="Confirm"
        heading="Are you sure?"
        message="This action cannot be undone."
        onResult={() => close()}
      />

      <AdminPinDialog
        open={activeDialog === 'adminPin'}
        onSuccess={() => { close(); open('settings'); }}
        onCancel={close}
      />
    </div>
  );
};

// ---------------------------------------------------------------------------
// ToolbarButton tooltip content
// ---------------------------------------------------------------------------
const TT_NEW: TooltipContent = {
  title: 'New Strategy (Ctrl+N)',
  body: 'Create a blank strategy from scratch. The current strategy will remain saved.',
  sections: [
    { header: 'Shortcut:', items: ['Ctrl+N'] },
    { header: 'Note:', items: ['Any unsaved changes will be lost — save first if needed'] },
  ],
};
const TT_OPEN: TooltipContent = {
  title: 'Open Strategy (Ctrl+O)',
  body: 'Browse and load a previously saved strategy from the strategy library.',
  sections: [
    { header: 'Shortcut:', items: ['Ctrl+O'] },
    { header: 'Tip:', items: ['Use the search in the browser to filter by name or tags'] },
  ],
};
const TT_SAVE: TooltipContent = {
  title: 'Save Strategy (Ctrl+S)',
  body: 'Persist the current strategy state to storage. The amber dot (●) indicates unsaved changes.',
  sections: [
    { header: 'Shortcut:', items: ['Ctrl+S'] },
    { header: 'Auto-save:', items: ['Strategy name changes are auto-saved on blur — all other edits require a manual save'] },
  ],
};
const TT_QUICK_PREVIEW: TooltipContent = {
  title: 'Quick Preview Backtest',
  body: 'Run a fast 30-day backtest on the current strategy using default capital and risk settings.',
  sections: [
    { header: 'Purpose:', items: [
      'Rapid signal quality check before committing to a full configuration',
      'Reveals entry frequency, basic win-rate, and gross P&L over the last 30 days',
    ]},
    { header: 'Limitations:', items: [
      'Uses simplified slippage and fee model',
      'Full backtest via the Backtest Config dialog provides granular control over capital, risk, and timeframe',
    ]},
  ],
};

// ---------------------------------------------------------------------------
// ToolbarButton
// ---------------------------------------------------------------------------
interface ToolbarButtonProps {
  label: string;
  tooltip: TooltipContent;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  accent?: boolean;
  icon?: React.ReactNode;
  trailing?: React.ReactNode;
}

const ToolbarButton: React.FC<ToolbarButtonProps> = ({ label, tooltip, onClick, disabled, active, accent, icon, trailing }) => (
  <RichTooltip content={tooltip}>
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded transition-colors border ${
        disabled
          ? 'text-[var(--text-muted)] bg-[rgba(255,255,255,0.02)] border-[rgba(255,255,255,0.05)] cursor-not-allowed'
          : accent
          ? 'font-medium border-[var(--accent-blue-dark)] bg-[var(--accent-blue)] text-[var(--btn-primary-text)] hover:bg-[var(--accent-blue-mid)]'
          : active
          ? 'text-[var(--text-primary)] bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.12)] hover:bg-[rgba(255,255,255,0.10)]'
          : 'text-[var(--text-secondary)] bg-[rgba(255,255,255,0.04)] border-[rgba(255,255,255,0.08)] hover:bg-[rgba(255,255,255,0.08)] hover:text-[var(--text-primary)] hover:border-[rgba(255,255,255,0.15)]'
      }`}
    >
      {icon}
      {label}
      {trailing}
    </button>
  </RichTooltip>
);

// ---------------------------------------------------------------------------
// MenuDropdown
// ---------------------------------------------------------------------------
interface MenuItem {
  label: string;
  shortcut?: string;
  onClick: () => void;
}

const MenuDropdown: React.FC<{ label: string; items: MenuItem[] }> = ({ label, items }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="px-3 py-1 text-sm text-[var(--text-dim)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] rounded transition-colors"
      >
        {label}
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-0.5 border rounded shadow-xl z-50 min-w-max" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
          {items.map((item, i) =>
            item.label === '—' ? (
              <div key={i} className="border-t my-0.5" style={{ borderColor: 'var(--border)' }} />
            ) : (
              <button
                key={i}
                onClick={() => { setOpen(false); item.onClick(); }}
                className="flex items-center justify-between w-full px-4 py-1.5 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-card)] transition-colors text-left gap-8 whitespace-nowrap"
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <span className="text-xs text-[var(--text-muted)]">{item.shortcut}</span>
                )}
              </button>
            )
          )}
        </div>
      )}
    </div>
  );
};

export default StrategyBuilderMainWindow;

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
import type { BacktestResult, BacktestConfig, Strategy } from '@/lib/strategy-builder/types';

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
    ['Win Rate',       `${winRate.toFixed(1)}%`,         winRate >= 50 ? 'text-emerald-400' : 'text-red-400'],
    ['Total Trades',   String(result.totalTrades),        'text-zinc-100'],
    ['Winning Trades', String(result.winningTrades),      'text-emerald-400'],
    ['Total Return',   `${result.returnPercentage >= 0 ? '+' : ''}${result.returnPercentage.toFixed(2)}%`,
      result.returnPercentage >= 0 ? 'text-emerald-400' : 'text-red-400'],
    ['Max Drawdown',   `${result.maxDrawdown.toFixed(2)}%`,  'text-red-400'],
    ['Sharpe Ratio',   result.sharpeRatio.toFixed(2),     'text-zinc-100'],
    ['Profit Factor',  result.profitFactor.toFixed(2),    'text-zinc-100'],
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-96 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-zinc-100">30-Day Backtest Summary</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-xl leading-none">✕</button>
        </div>
        <div className="space-y-1.5">
          {rows.map(([label, value, color]) => (
            <div key={label} className="flex items-center justify-between py-1">
              <span className="text-sm text-zinc-500">{label}:</span>
              <span className={`text-sm font-semibold ${color}`}>{value}</span>
            </div>
          ))}
        </div>
        {result.totalTrades === 0 && (
          <p className="mt-3 text-xs text-zinc-500">
            No trades found in this 30-day period. Try lowering the confluence threshold.
          </p>
        )}
        <div className="mt-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm bg-blue-700 hover:bg-blue-600 text-white rounded transition-colors"
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
  } = useStrategyStore();

  const [mounted, setMounted] = useState(false);

  // Load specific strategy by URL param; block library always loaded on mount.
  // Default strategy is pre-initialized in the Zustand store so no createStrategy() needed here.
  useEffect(() => {
    setMounted(true);
    if (strategyId) {
      loadStrategy(strategyId).catch(console.error);
    }
    loadBlockLibrary().catch(console.error);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

  // Status bar countdown
  const [statusText, setStatusText] = useState('Ready');
  const nextCheckRef = useRef<Date>(new Date(Date.now() + 15 * 60 * 1000));
  useEffect(() => {
    const timer = setInterval(() => {
      const diff = Math.max(0, nextCheckRef.current.getTime() - Date.now());
      if (diff === 0) {
        nextCheckRef.current = new Date(Date.now() + 15 * 60 * 1000);
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

  // Resizable splitter
  const [leftPercent, setLeftPercent] = useState(60);
  const isDragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setLeftPercent(Math.max(22, Math.min(75, pct)));
    };
    const onMouseUp = () => { isDragging.current = false; };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

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
      setCleanSnapshot(JSON.stringify({ id: strategy.id, blocks: strategy.blocks, name: strategy.name }));
      setCurrentStep(0);
      setCompletedSteps(new Set());
      setErrorSteps(new Set());
      close();
    },
    [close]
  );

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
      <div className="flex items-center justify-center h-full" style={{ background: '#15191E' }}>
        <div className="text-sm" style={{ color: '#9AA0A6' }}>Loading strategy…</div>
      </div>
    );
  }
  if (strategyError) {
    return (
      <div className="flex items-center justify-center h-full" style={{ background: '#15191E' }}>
        <div className="text-red-400 text-sm">Error: {strategyError}</div>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col h-full select-none"
      onKeyDown={handleKeyDown}
      tabIndex={-1}
      style={{ outline: 'none', background: '#0F1117' }}
    >
      {/* ── Window title / Menu Bar ─────────────────────────────────────── */}
      <div className="flex items-center gap-0.5 border-b px-2 py-1 flex-shrink-0" style={{ background: '#1E2128', borderColor: '#3C4149' }}>
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
          <span className="ml-auto text-xs truncate max-w-xs pr-2" style={{ color: '#9AA0A6' }}>
            BTC Trade Engine — Strategy Builder —{' '}
            <span style={{ color: '#E8EAED' }}>{currentStrategy.name}</span>
            {isModified && <span className="text-amber-400 ml-1" title="Unsaved changes">●</span>}
          </span>
        )}
      </div>

      {/* ── Toolbar + Stepper (3-column: left tools | center stepper | right spacer) ── */}
      <div className="flex items-center border-b px-3 py-1.5 flex-shrink-0" style={{ background: '#1E2128', borderColor: '#3C4149' }}>
        {/* Left: toolbar buttons */}
        <div className="flex items-center gap-1">
          <ToolbarButton label="New"  title="New Strategy (Ctrl+N)"  onClick={() => open('newStrategy')} />
          <ToolbarButton label="Open" title="Open Strategy (Ctrl+O)" onClick={() => open('strategyBrowser')} />
          <ToolbarButton
            label={isModified ? 'Save ●' : 'Save'}
            title="Save (Ctrl+S)"
            onClick={handleSave}
            active={isModified}
          />
          <div className="w-px h-5 mx-1 flex-shrink-0" style={{ background: '#3C4149' }} />
          <ToolbarButton
            label={backTestInProgress ? '▶ Running…' : '▶ Quick Preview'}
            title="Run Quick Preview backtest (30 days)"
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
        {/* Right: spacer to balance left side (approx same width) */}
        <div style={{ minWidth: 200 }} />
      </div>

      {/* ── Main Content Area (40% left / 60% right) ────────────────────── */}
      <div ref={containerRef} className="flex flex-1 overflow-hidden min-h-0">
        {/* LEFT PANEL: Strategy Info + Blocks */}
        <div
          className="flex flex-col overflow-hidden border-r"
          style={{ width: `${leftPercent}%`, borderColor: '#3C4149' }}
        >
          {/* Section 1: Strategy Information (compact top) */}
          <div className="flex-shrink-0 border-b" style={{ borderColor: '#3C4149' }}>
            <StrategyInfoPanel compact />
          </div>

          {/* Section 2+3: Strategy Blocks + Exit Conditions (scrollable) */}
          <div className="flex-1 overflow-hidden min-h-0">
            <StrategyBlocksPanel />
          </div>
        </div>

        {/* Drag handle */}
        <div
          className="w-2 bg-[#2A2F3A] hover:bg-blue-700 transition-colors cursor-col-resize flex-shrink-0 flex flex-col items-center justify-center gap-0.5"
          onMouseDown={() => { isDragging.current = true; }}
        >
          {[0, 1, 2].map(i => (
            <div key={i} className="w-0.5 h-3 bg-[#3C4149] rounded-full" />
          ))}
        </div>

        {/* RIGHT PANEL: Block Library */}
        <div className="flex flex-col overflow-hidden flex-1 min-w-0">
          <BlockSearchPanel />
        </div>
      </div>

      {/* ── Status Bar ──────────────────────────────────────────────────── */}
      <div className="h-6 border-t px-3 flex items-center flex-shrink-0" style={{ background: '#1E2128', borderColor: '#3C4149' }}>
        <span className="text-xs" style={{ color: '#9AA0A6' }}>{statusText}</span>
      </div>

      {/* ── Dialogs ─────────────────────────────────────────────────────── */}
      <NewStrategyDialog open={activeDialog === 'newStrategy'} onClose={close} />

      <StrategyBrowserDialog
        open={activeDialog === 'strategyBrowser'}
        onSelect={handleStrategySelect}
        onClose={close}
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
          <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-2/3 max-h-[70vh] flex flex-col p-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold text-zinc-100">Debug Log Viewer</h2>
              <div className="flex gap-2 items-center">
                <button onClick={() => setConsoleLogs([])} className="text-xs px-2 py-1 bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded">Clear</button>
                <button onClick={handleDownloadLogs} className="text-xs px-2 py-1 bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded">Download</button>
                <button onClick={close} className="text-zinc-500 hover:text-zinc-300 text-xl leading-none ml-2">✕</button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto bg-zinc-950 rounded border border-zinc-800 p-3 font-mono text-xs text-zinc-400">
              {consoleLogs.length === 0
                ? <span className="text-zinc-600">No log entries.</span>
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
// ToolbarButton
// ---------------------------------------------------------------------------
interface ToolbarButtonProps {
  label: string;
  title: string;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  accent?: boolean;
}

const ToolbarButton: React.FC<ToolbarButtonProps> = ({ label, title, onClick, disabled, active, accent }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    title={title}
    className={`px-2.5 py-1 text-xs rounded transition-colors border ${
      disabled
        ? 'text-[#6B7280] bg-[#1E2128] border-[#3C4149] cursor-not-allowed'
        : accent
        ? 'text-white bg-blue-700 border-blue-600 hover:bg-blue-600 font-medium'
        : active
        ? 'text-amber-300 bg-[#2A2F3A] border-[#3C4149] hover:bg-[#3C4149]'
        : 'text-[#A0AEC0] bg-[#2A2F3A] border-[#3C4149] hover:bg-[#3C4149] hover:text-[#E8EAED]'
    }`}
  >
    {label}
  </button>
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
        className="px-3 py-1 text-sm text-[#A0AEC0] hover:text-[#E8EAED] hover:bg-[#2A2F3A] rounded transition-colors"
      >
        {label}
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-0.5 border rounded shadow-xl z-50 min-w-max" style={{ background: '#1E2128', borderColor: '#3C4149' }}>
          {items.map((item, i) =>
            item.label === '—' ? (
              <div key={i} className="border-t my-0.5" style={{ borderColor: '#3C4149' }} />
            ) : (
              <button
                key={i}
                onClick={() => { setOpen(false); item.onClick(); }}
                className="flex items-center justify-between w-full px-4 py-1.5 text-sm text-[#E8EAED] hover:bg-[#2A2F3A] transition-colors text-left gap-8 whitespace-nowrap"
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <span className="text-xs text-[#6B7280]">{item.shortcut}</span>
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

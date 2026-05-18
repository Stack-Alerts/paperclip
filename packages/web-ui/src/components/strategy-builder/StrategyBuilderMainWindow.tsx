'use client';

import React, { useState, useCallback, useMemo, useRef } from 'react';
import { StrategyBuilder } from './StrategyBuilder';
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
// QuickPreviewResultsDialog — inline, does not exist as a standalone component
// ---------------------------------------------------------------------------
interface QuickPreviewResultsDialogProps {
  open: boolean;
  result: BacktestResult | null;
  onClose: () => void;
}

function QuickPreviewResultsDialog({ open, result, onClose }: QuickPreviewResultsDialogProps) {
  if (!open || !result) return null;

  const rows: [string, string][] = [
    ['Win Rate',       `${(result.winRate * 100).toFixed(1)}%`],
    ['Total Return',   `${result.returnPercentage >= 0 ? '+' : ''}${result.returnPercentage.toFixed(2)}%`],
    ['Total Trades',   String(result.totalTrades)],
    ['Winning Trades', String(result.winningTrades)],
    ['Max Drawdown',   `${result.maxDrawdown.toFixed(2)}%`],
    ['Sharpe Ratio',   result.sharpeRatio.toFixed(2)],
    ['Profit Factor',  result.profitFactor.toFixed(2)],
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-96 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-zinc-100">Quick Preview Results</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-xl leading-none">✕</button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {rows.map(([label, value]) => (
            <div key={label} className="bg-zinc-800 rounded p-3">
              <div className="text-xs text-zinc-500 mb-1">{label}</div>
              <div className="text-sm font-semibold text-zinc-100">{value}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded transition-colors"
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
    saveStrategy,
    loadBlockLibrary,
    runBacktest,
    setCurrentStrategy,
    backTestInProgress,
  } = useStrategyStore();

  const [activeDialog, setActiveDialog] = useState<DialogKey>(null);
  const [quickPreviewResult, setQuickPreviewResult] = useState<BacktestResult | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<string[]>([]);
  const [consoleEnabled, setConsoleEnabled] = useState(false);

  // Stepper state: tracks Design→Validate→Test/Optimize→Publish workflow
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [errorSteps, setErrorSteps] = useState<Set<number>>(new Set());

  // Dirty-flag: snapshot-based, reset on load or save.
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

  const open = useCallback((key: DialogKey) => setActiveDialog(key), []);
  const close = useCallback(() => setActiveDialog(null), []);

  // -------------------------------------------------------------------------
  // File menu handlers
  // -------------------------------------------------------------------------
  const handleSave = useCallback(async () => {
    isSavingRef.current = true;
    try {
      await saveStrategy();
      setCleanSnapshot(strategySnapshot);
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
  // Edit menu handlers
  // -------------------------------------------------------------------------
  const handleClearBlocks = useCallback(() => {
    if (!currentStrategy) return;
    if (!window.confirm('Clear all blocks from this strategy?')) return;
    setCurrentStrategy({ ...currentStrategy, blocks: [] });
  }, [currentStrategy, setCurrentStrategy]);

  // -------------------------------------------------------------------------
  // Tools menu handlers
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

  const handleQuickPreview = useCallback(async () => {
    if (!currentStrategy) return;
    const endDate = new Date().toISOString().slice(0, 10);
    const startDate = new Date(Date.now() - 30 * 86_400_000).toISOString().slice(0, 10);
    const config: BacktestConfig = {
      strategyId: currentStrategy.id,
      startDate,
      endDate,
      initialCapital: 10_000,
      timeframe: currentStrategy.settings?.timeframe || '1h',
    };
    const result = await runBacktest(config);
    setQuickPreviewResult(result);
    open('quickPreview');
  }, [currentStrategy, runBacktest, open]);

  // -------------------------------------------------------------------------
  // Strategy browser: record clean snapshot on load, clear workspace on delete
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

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* ── Menu Bar ────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1 bg-zinc-900 border-b border-zinc-800 px-4 py-1.5 flex-shrink-0">
        <MenuDropdown
          label="File"
          items={[
            { label: 'New Strategy',     onClick: () => open('newStrategy') },
            { label: 'Open Strategy…',   onClick: () => open('strategyBrowser') },
            { label: 'Save',             onClick: handleSave, shortcut: 'Ctrl+S' },
            { label: 'Save As…',         onClick: handleSaveAs, shortcut: 'Ctrl+Shift+S' },
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
            { label: 'Backtest…',          onClick: () => open('backtestConfig') },
            { label: 'Validate…',          onClick: () => open('validation') },
            { label: 'Update Data…',       onClick: () => open('dataUpdate') },
            { label: 'Verify Data…',       onClick: () => open('dataVerify') },
            { label: 'Refresh Blocks',     onClick: handleRefreshBlocks },
            { label: '—', onClick: () => {} },
            { label: 'Settings…',          onClick: () => open('settings') },
            { label: '—', onClick: () => {} },
            { label: consoleEnabled ? '✓ Console Output' : 'Console Output',
              onClick: () => setConsoleEnabled(v => !v) },
            { label: 'Clear Logs',         onClick: () => setConsoleLogs([]) },
            { label: 'View Log…',          onClick: () => open('logViewer') },
            { label: 'Download Log…',      onClick: handleDownloadLogs },
          ]}
        />
        <MenuDropdown
          label="Help"
          items={[
            { label: 'About', onClick: () => open('alert') },
          ]}
        />

        {/* Modified indicator + strategy name */}
        {currentStrategy && (
          <span className="ml-auto text-xs text-zinc-400 truncate max-w-xs">
            {isModified && <span className="text-amber-400 mr-1" title="Unsaved changes">●</span>}
            {currentStrategy.name}
          </span>
        )}
      </div>

      {/* ── Toolbar ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-1 bg-zinc-900 border-b border-zinc-700 px-3 py-1 flex-shrink-0">
        <ToolbarButton label="New"  title="New Strategy (Ctrl+N)"  onClick={() => open('newStrategy')} />
        <ToolbarButton label="Open" title="Open Strategy (Ctrl+O)" onClick={() => open('strategyBrowser')} />
        <ToolbarButton
          label={isModified ? 'Save ●' : 'Save'}
          title="Save (Ctrl+S)"
          onClick={handleSave}
          active={isModified}
        />
        <div className="w-px h-5 bg-zinc-700 mx-1" />
        <ToolbarButton
          label={backTestInProgress ? '▶ Running…' : '▶ Quick Preview'}
          title="Run Quick Preview backtest (30 days)"
          onClick={handleQuickPreview}
          disabled={!currentStrategy || backTestInProgress}
          accent
        />
      </div>

      {/* ── StepperRibbon ───────────────────────────────────────────── */}
      <StepperRibbon
        currentStep={currentStep}
        completedSteps={completedSteps}
        errorSteps={errorSteps}
        onStepClick={setCurrentStep}
      />

      {/* ── Main content ────────────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden">
        <StrategyBuilder strategyId={strategyId} />
      </div>

      {/* ── Dialogs ─────────────────────────────────────────────────── */}
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

      {/* Log Viewer Dialog */}
      {activeDialog === 'logViewer' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-2/3 max-h-[70vh] flex flex-col p-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-zinc-100">Debug Log Viewer</h2>
              <div className="flex gap-2 items-center">
                <button
                  onClick={() => setConsoleLogs([])}
                  className="text-xs px-2 py-1 bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded"
                >
                  Clear
                </button>
                <button
                  onClick={handleDownloadLogs}
                  className="text-xs px-2 py-1 bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded"
                >
                  Download
                </button>
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
        ? 'text-zinc-600 bg-zinc-900 border-zinc-800 cursor-not-allowed'
        : accent
        ? 'text-white bg-blue-700 border-blue-600 hover:bg-blue-600'
        : active
        ? 'text-amber-300 bg-zinc-800 border-zinc-600 hover:bg-zinc-700'
        : 'text-zinc-300 bg-zinc-800 border-zinc-700 hover:bg-zinc-700 hover:text-zinc-100'
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
        onClick={() => setOpen((v) => !v)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="px-3 py-1 text-sm text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800 rounded transition-colors"
      >
        {label}
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-0.5 bg-zinc-800 border border-zinc-700 rounded shadow-xl z-50 min-w-max">
          {items.map((item, i) =>
            item.label === '—' ? (
              <div key={i} className="border-t border-zinc-700 my-1" />
            ) : (
              <button
                key={i}
                onClick={() => { setOpen(false); item.onClick(); }}
                className="flex items-center justify-between w-full px-4 py-1.5 text-sm text-zinc-200 hover:bg-zinc-700 transition-colors text-left gap-8"
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <span className="text-xs text-zinc-500">{item.shortcut}</span>
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

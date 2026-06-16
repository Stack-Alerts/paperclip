'use client';

import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { StrategyBrowserDialog, type StrategySelectOptions } from './StrategyBrowserDialog';
import { SaveStrategyModeDialog } from './SaveStrategyModeDialog';
import { BacktestConfigDialog } from './BacktestConfigDialog';
import { ValidationDialog } from './ValidationDialog';
import { DataUpdateModal } from './DataUpdateModal';
import { DataVerifyDialog, TimeframeVerifyResult } from './DataVerifyDialog';
import { SettingsDialog } from './SettingsDialog';
import { AlertDialog, QuestionDialog } from './AlertDialog';
import { AdminPinDialog } from './AdminPinDialog';
import { StepperRibbon } from './StepperRibbon';
import { StrategyInfoPanel, STRATEGY_NAME_INPUT_ID } from './StrategyInfoPanel';
import { StrategyBlocksPanel } from './StrategyBlocksPanel';
import { BlockSearchPanel } from './BlockSearchPanel';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import * as api from '@/lib/strategy-builder/api';
import type { BacktestResult, BacktestConfig, Strategy, Block } from '@/lib/strategy-builder/types';
import { BlockType, StrategyStatus } from '@/lib/strategy-builder/types';
import { RichTooltip, TooltipContent } from './RichTooltip';
import { useTooltipSettings } from './TooltipSettingsContext';
import { ThemeSelector } from './ThemeSelector';
import { Plus, FolderOpen, Save, Play, ChevronDown } from 'lucide-react';
import { useSidebar } from '@/contexts/SidebarContext';
import { AppBrand } from '@/components/shared/AppBrand';
import { status } from '@/lib/status';

type DialogKey =
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
  | 'validationRequiredAlert'
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
    ['Total Trades',   String(result.totalTrades),        'var(--text-secondary)'],
    ['Winning Trades', String(result.winningTrades),      'var(--accent-green)'],
    ['Total Return',   `${result.returnPercentage >= 0 ? '+' : ''}${result.returnPercentage.toFixed(2)}%`,
      result.returnPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'],
    ['Max Drawdown',   `${(result.maxDrawdown * 100).toFixed(2)}%`,  'var(--accent-red)'],
    ['Sharpe Ratio',   result.sharpeRatio.toFixed(2),     'var(--text-secondary)'],
    ['Profit Factor',  result.profitFactor.toFixed(2),    'var(--text-secondary)'],
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg shadow-2xl w-96 p-6 border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold" style={{ color: 'var(--text-secondary)' }}>30-Day Backtest Summary</h2>
          <button onClick={onClose} className="text-xl leading-none" style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
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
      // eslint-disable-next-line react-hooks/set-state-in-effect
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
    saveStrategyAsNew,
    runBacktest,
    validateStrategy,
    setCurrentStrategy,
    backTestInProgress,
    hydrateFromLocalStorage,
    restoreBacktestSession,
  } = useStrategyStore();

  const [mounted, setMounted] = useState(false);
  const { settings: tooltipSettings, update: updateTooltipSettings } = useTooltipSettings();

  // Load specific strategy by URL param; block library always loaded on mount.
  // Default strategy is pre-initialized in the Zustand store so no createStrategy() needed here.
  useEffect(() => {
    // Hydrate store from localStorage after mount so SSR and initial client
    // renders are both null (no hydration mismatch).
    hydrateFromLocalStorage();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
    if (strategyId) {
      loadStrategy(strategyId).catch(console.error);
    }
    loadBlockLibrary().catch(console.error);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // BTCAAAAA-35963: after the initial hydrate (or any strategy change),
  // try to fetch a fresh result + logs for the persisted runId from the
  // backend. If the server still has the in-memory run, this refreshes
  // the cached snapshot. If the run is gone (server restart, 404), the
  // cached snapshot stays as the source of truth so the user still sees
  // the last test/result/config.
  useEffect(() => {
    if (!mounted) return;
    restoreBacktestSession().catch(() => {
      // restoreBacktestSession swallows 404s internally; anything else is
      // non-fatal (we still have the cached snapshot).
    });
  }, [mounted, currentStrategy?.id, restoreBacktestSession]);

  // Sync clean snapshot whenever the strategy changes (from hydration or load).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/immutability
    if (mounted) setCleanSnapshot(strategySnapshot);
  }, [currentStrategy?.id, mounted]); // eslint-disable-line react-hooks/exhaustive-deps

  // Dialog state
  const [activeDialog, setActiveDialog] = useState<DialogKey>(null);
  const [quickPreviewResult, setQuickPreviewResult] = useState<BacktestResult | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<string[]>([]);
  const [consoleEnabled, setConsoleEnabled] = useState(false);

  // Stepper state
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [errorSteps, setErrorSteps] = useState<Set<number>>(new Set());

  // Tracks whether the currently-loaded strategy is a non-latest version
  // selected via the Strategy Browser. Persists across the panel so the
  // toolbar Validate button also runs the local validator (the backend
  // endpoint always validates against latest — BTCAAAAA-33738 Bug 2).
  const [loadedHistoricalVersion, setLoadedHistoricalVersion] = useState(false);

  // Dirty-flag
  const [cleanSnapshot, setCleanSnapshot] = useState<string>('');
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const strategySnapshot = useMemo(
    () =>
      currentStrategy
        ? JSON.stringify({ id: currentStrategy.id, blocks: currentStrategy.blocks, name: currentStrategy.name })
        : '',
    [currentStrategy]
  );
  const isModified = !!currentStrategy && strategySnapshot !== cleanSnapshot;
  const isSavingRef = useRef(false);

  // BTCAAAAA-36689: snapshot of the strategy the last time validation actually
  // passed. While `strategySnapshot === validationPassedSnapshot`, the user has
  // not modified the strategy since validation succeeded — so the Validate step
  // can render as already-complete (green) and Test/Optimize can open without a
  // re-prompt. Any block / name change invalidates this match and forces a
  // re-validate before backtest.
  const [validationPassedSnapshot, setValidationPassedSnapshot] = useState<string>('');
  // Ref mirrors currentStrategy so async `.then()` callbacks (e.g. the post-load
  // re-validate in handleStrategySelect) read the freshest strategy object
  // instead of the closure-captured one from the moment the callback was queued.
  const currentStrategyRef = useRef<Strategy | null>(currentStrategy);
  useEffect(() => {
    currentStrategyRef.current = currentStrategy;
  }, [currentStrategy]);
  const isValidatedAndPristine =
    !!currentStrategy &&
    validationPassedSnapshot !== '' &&
    strategySnapshot === validationPassedSnapshot;

  // The "Next data check" status-bar countdown was removed (BTCAAAAA-36517):
  // it duplicated the next-candle countdown already shown under the connection
  // bar, and as a persistent global entry it froze on other pages after unmount.

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
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      // eslint-disable-next-line react-hooks/immutability
      handleSave();
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
      e.preventDefault();
      // eslint-disable-next-line react-hooks/immutability
      handleNewStrategy();
    } else if ((e.ctrlKey || e.metaKey) && e.key === 'o') {
      e.preventDefault();
      open('strategyBrowser');
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // -------------------------------------------------------------------------
  // File menu handlers
  // -------------------------------------------------------------------------

  // BTCAAAAA-30023: when Save is clicked on a backend-loaded strategy
  // (id starts with "strategy_") whose name has changed since load/last
  // save, ask whether to rename the existing strategy or fork a new one
  // at v1. Plain rename or plain content edit (no name change) saves
  // directly without the modal.
  const [pendingSaveMode, setPendingSaveMode] = useState<{
    originalName: string;
    newName: string;
  } | null>(null);
  const [saveModeBusy, setSaveModeBusy] = useState(false);

  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const finalizeSavedAsRename = useCallback(() => {
    setCleanSnapshot(strategySnapshot);
    status.emit('Strategy saved', { duration: 2000 });
  }, [strategySnapshot]);

  const handleSave = useCallback(async () => {
    if (!isModified) return;
    if (isSavingRef.current) return;
    if (!currentStrategy) return;
    const id = currentStrategy.id as unknown as string;
    const isBackend = typeof id === 'string' && id.startsWith('strategy_');
    if (isBackend) {
      const loadedName = (() => {
        try { return JSON.parse(cleanSnapshot || '{}').name as string | undefined; }
        catch { return undefined; }
      })();
      if (loadedName != null && loadedName !== currentStrategy.name) {
        setPendingSaveMode({ originalName: loadedName, newName: currentStrategy.name });
        return;
      }
    }
    isSavingRef.current = true;
    try {
      await saveStrategy();
      setCleanSnapshot(strategySnapshot);
      status.emit('Strategy saved', { duration: 2000 });
    } catch {
      status.emit('Save failed', { duration: 2000, variant: 'error' });
    } finally {
      isSavingRef.current = false;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saveStrategy, strategySnapshot, currentStrategy, cleanSnapshot]);

  const handleSaveModeRenameExisting = useCallback(async () => {
    if (saveModeBusy) return;
    setSaveModeBusy(true);
    try {
      await saveStrategy();
      finalizeSavedAsRename();
      setPendingSaveMode(null);
    } catch {
      status.emit('Save failed', { duration: 2000, variant: 'error' });
    } finally {
      setSaveModeBusy(false);
    }
  }, [saveStrategy, finalizeSavedAsRename, saveModeBusy]);

  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const handleSaveModeSaveAsNew = useCallback(async () => {
    if (saveModeBusy || !pendingSaveMode) return;
    setSaveModeBusy(true);
    try {
      const forked = await saveStrategyAsNew(pendingSaveMode.newName);
      setCleanSnapshot(JSON.stringify({ id: forked.id, blocks: forked.blocks, name: forked.name }));
      // BTCAAAAA-36689: the new fork has a fresh strategy id — the previous
      // pristine-validation stamp was for the prior id and must not carry over.
      setValidationPassedSnapshot('');
      status.emit(`Saved as new strategy v${(forked as { versionNumber?: number }).versionNumber ?? 1}`, { duration: 2500 });
      setPendingSaveMode(null);
    } catch {
      status.emit('Save-as-new failed', { duration: 2000, variant: 'error' });
    } finally {
      setSaveModeBusy(false);
    }
  }, [saveStrategyAsNew, pendingSaveMode, saveModeBusy]);

  const handleSaveModeCancel = useCallback(() => {
    if (saveModeBusy) return;
    setPendingSaveMode(null);
  }, [saveModeBusy]);

  // BTCAAAAA-30520: File > New Strategy (and Ctrl+N / the toolbar New button)
  // clear the builder form silently — no modal, no confirm. The rename-then-Save
  // path still surfaces SaveStrategyModeDialog if the user edited a backend
  // strategy before clicking New, because pendingSaveMode is gated by the
  // existing handleSave flow (line ~333), not by this reset.
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const handleNewStrategy = useCallback(() => {
    const now = new Date().toISOString();
    const fresh: Strategy = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      name: '',
      description: '',
      status: StrategyStatus.DRAFT,
      strategyType: 'Bullish',
      blocks: [],
      settings: {
        timeframe: '1h',
        targetMarket: 'BTC/USDT',
        riskParameters: null,
        strategyExits: [],
      },
      validationStatus: null,
      createdAt: now,
      updatedAt: now,
    } as unknown as Strategy;
    setCurrentStrategy(fresh);
    setCleanSnapshot(JSON.stringify({ id: fresh.id, blocks: fresh.blocks, name: fresh.name }));
    setCurrentStep(0);
    setCompletedSteps(new Set());
    setErrorSteps(new Set());
    setValidationPassedSnapshot('');
    setLoadedHistoricalVersion(false);
    // Focus the Name input on the next paint after StrategyInfoPanel remounts
    // its uncontrolled input on the new strategy id.
    requestAnimationFrame(() => {
      const el = document.getElementById(STRATEGY_NAME_INPUT_ID) as HTMLInputElement | null;
      el?.focus();
      el?.select();
    });
  }, [setCurrentStrategy]);

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

  const handleBackfillData = useCallback(async (gaps: import('./DataVerifyDialog').DataGapEntry[], timeframe: string): Promise<void> => {
    if (!gaps.length) return;
    const starts = gaps.map(g => g.gapStart).sort();
    const ends = gaps.map(g => g.gapEnd).sort();
    await api.post('/data/backfill', {
      startDate: starts[0].slice(0, 10),
      endDate: ends[ends.length - 1].slice(0, 10),
      timeframe,
    });
  }, []);

  const handleValidate = useCallback(async () => {
    setCurrentStep(1);
    setActiveDialog('validation');
    // Capture the snapshot the user is validating *now*. After the async
    // validate resolves we compare this captured string against the *then-current*
    // strategySnapshot — if they match, no edit landed during the round-trip and
    // the strategy is still pristine. We must capture BEFORE the await because
    // otherwise the second read happens after React's commit, and an in-flight
    // edit during the await would compare post-edit vs post-edit (always equal)
    // and falsely mark the strategy as pristine-validated.
    const snapshotAtValidation = strategySnapshot;
    try {
      // Historical versions must use the local validator because the backend's
      // POST /validate endpoint always validates against the latest stored
      // version (BTCAAAAA-33738 Bug 2).
      await validateStrategy({ localOnly: loadedHistoricalVersion });
      setCompletedSteps(prev => new Set([...prev, 1]));
      setErrorSteps(prev => { const s = new Set(prev); s.delete(1); return s; });
      // Only mark the strategy as "validated & pristine" if validation actually
      // passed. validateStrategy throws on transport errors but may resolve with
      // a non-valid status when issues are found, so check the strategy state
      // directly. Read via ref so we see the post-validate object, not the
      // closure-captured pre-validate one.
      const statusAfter = currentStrategyRef.current?.status;
      if (statusAfter === StrategyStatus.VALID) {
        // Only stamp the snapshot if the strategy hasn't changed during the
        // round-trip. An in-flight block edit that lands between the capture
        // and the post-await check would otherwise let the user backtest a
        // never-validated modification.
        if (strategySnapshot === snapshotAtValidation) {
          setValidationPassedSnapshot(snapshotAtValidation);
        }
      } else {
        // Validation reported issues — clear any prior "pristine" stamp so the
        // Validate step visually reverts to needing-action and the Test/Optimize
        // gate re-engages.
        setValidationPassedSnapshot('');
      }
    } catch {
      setErrorSteps(prev => new Set([...prev, 1]));
      setValidationPassedSnapshot('');
    }
  }, [validateStrategy, loadedHistoricalVersion, strategySnapshot]);

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
    } catch {
      status.emit('Quick preview failed', { duration: 2000, variant: 'error' });
    }
  }, [currentStrategy, runBacktest, open, backTestInProgress]);

  // -------------------------------------------------------------------------
  // Strategy browser
  // -------------------------------------------------------------------------
  const handleStrategySelect = useCallback(
    // eslint-disable-next-line react-hooks/preserve-manual-memoization
    (strategy: Strategy, selectOpts?: StrategySelectOptions) => {
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
      // Normalize nested signal exit_condition + recheck_config to the
      // camelCase shape the panel renderer expects (StrategyBlocksPanel:334
      // reads cfg.signalName, line 339 reads cfg.recheckBarDelay/recheckEnabled).
      // Without this the per-signal exit pills and RCHK badges disappear,
      // which is the layout regression the board flagged vs the signed-off
      // rendering (board comment 2026-05-27 05:50 UTC on BTCAAAAA-29995).
      const normalizeExitCondition = (ec: Record<string, unknown>): Record<string, unknown> => {
        const out: Record<string, unknown> = { ...ec };
        if (typeof ec.signal_name === 'string') out.signalName = ec.signal_name;
        if (typeof ec.exit_mode === 'string') out.exitMode = ec.exit_mode;
        if (typeof ec.binding_level === 'string') out.bindingLevel = ec.binding_level;
        const rc = ec.recheck_config as Record<string, unknown> | undefined;
        if (rc && typeof rc === 'object') {
          if (typeof rc.enabled === 'boolean') out.recheckEnabled = rc.enabled;
          if (typeof rc.bar_delay === 'number') out.recheckBarDelay = rc.bar_delay;
          if (typeof rc.mode === 'string') out.recheckMode = rc.mode;
        }
        return out;
      };
      const normalizeSignal = (sig: Record<string, unknown>): Record<string, unknown> => {
        const out: Record<string, unknown> = { ...sig };
        const rc = sig.recheck_config as Record<string, unknown> | undefined;
        if (rc && typeof rc === 'object') {
          if (typeof rc.enabled === 'boolean') out.recheckEnabled = rc.enabled;
          if (typeof rc.bar_delay === 'number') out.recheckBarDelay = rc.bar_delay;
        }
        const exits = sig.exit_conditions as unknown;
        if (Array.isArray(exits)) {
          out.exit_conditions = exits.map((e) =>
            e && typeof e === 'object' ? normalizeExitCondition(e as Record<string, unknown>) : e
          );
        }
        return out;
      };
      const rawBlocks = Array.isArray(strategy.blocks) ? strategy.blocks : [];
      const mainBlocks: Block[] = rawBlocks.map((b, i): Block => {
        const isFrontendShape =
          b && typeof b === 'object' && 'data' in b && 'type' in b;
        if (isFrontendShape) return b as Block;
        const raw = b as unknown as Record<string, unknown>;
        const rawName = typeof raw.name === 'string' ? raw.name : '';
        const signals = raw.signals as unknown;
        const normalizedSignals = Array.isArray(signals)
          ? signals.map((s) =>
              s && typeof s === 'object' ? normalizeSignal(s as Record<string, unknown>) : s
            )
          : raw.signals;
        const dataCore: Record<string, unknown> = { ...raw, signals: normalizedSignals };
        // definitionId links the canvas block to its library entry (BlockSearchPanel
        // matches library.id). API gives raw snake_case (e.g. asia_session_50_percent)
        // and public/block-library.json entries use id=<same snake_case>, so the raw
        // name IS the join key. Without this, clicking a signal in the canvas can't
        // expand/highlight the matching block in the library panel — the UX feature
        // the board flagged as missing (BTCAAAAA-29995 comment 2026-05-27 06:24 UTC).
        const dataWithId: Record<string, unknown> = rawName
          ? { ...dataCore, name: titleCase(rawName), definitionId: rawName }
          : dataCore;
        return {
          id: `block-${strategy.versionId ?? strategy.id}-${i}`,
          type: BlockType.INDICATOR,
          index: i,
          data: dataWithId,
        };
      });
      // Flatten each signal.exit_conditions[] into synthetic EXIT_CONDITION
      // blocks at the top level. StrategyBlocksPanel renders the red ↳ exit
      // pills by walking blocks where type === EXIT_CONDITION (or data.logic
      // === 'EXIT'), keyed by `${blockName}::${parentSignalName}` and grouped
      // per signal via signalExitsByKey. Without this flatten the API's
      // nested exit_conditions never reach the renderer and the signed-off
      // rich rendering can't render — even with shape normalization in place.
      const exitBlocks: Block[] = [];
      mainBlocks.forEach((parent) => {
        const parentName = (parent.data.name as string | undefined) ?? '';
        const sigs = parent.data.signals as Array<Record<string, unknown>> | undefined;
        if (!Array.isArray(sigs)) return;
        sigs.forEach((sig) => {
          const parentSignalName = typeof sig.name === 'string' ? sig.name : '';
          const exits = sig.exit_conditions as Array<Record<string, unknown>> | undefined;
          if (!Array.isArray(exits)) return;
          exits.forEach((ec, ei) => {
            const exitSignalRaw = typeof ec.signal_name === 'string' ? ec.signal_name : '';
            const exitSignalDisplay = exitSignalRaw
              ? exitSignalRaw.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ')
              : 'Exit';
            const rc = ec.recheck_config as Record<string, unknown> | undefined;
            const exitConfig: Record<string, unknown> = {
              signalName: exitSignalRaw,
              percentage: typeof ec.percentage === 'number' ? ec.percentage : undefined,
              exitMode: typeof ec.exit_mode === 'string' ? ec.exit_mode : undefined,
              bindingLevel: typeof ec.binding_level === 'string' ? ec.binding_level : 'SIGNAL',
              tpProximityThreshold: typeof ec.tp_proximity_threshold === 'number' ? ec.tp_proximity_threshold : undefined,
              reversalTrigger: typeof ec.reversal_trigger === 'number' ? ec.reversal_trigger : undefined,
              recheckEnabled: rc && typeof rc === 'object' && typeof rc.enabled === 'boolean' ? rc.enabled : undefined,
              recheckBarDelay: rc && typeof rc === 'object' && typeof rc.bar_delay === 'number' ? rc.bar_delay : undefined,
              blockName: parentName,
              parentSignalName,
            };
            // Inherit the parent block's library link so clicking the exit-pill
            // name highlights the same library entry the parent signal does
            // (parent.data.definitionId was set above to the raw snake_case API name).
            const parentDefinitionId = parent.data.definitionId as string | undefined;
            exitBlocks.push({
              id: `exit-${strategy.versionId ?? strategy.id}-${parentName}-${parentSignalName}-${ei}`,
              type: BlockType.EXIT_CONDITION,
              index: mainBlocks.length + exitBlocks.length,
              data: {
                name: exitSignalDisplay,
                logic: 'EXIT',
                exitConfig,
                ...(parentDefinitionId ? { definitionId: parentDefinitionId } : {}),
              },
            });
          });
        });
      });
      const normalized: Strategy = {
        ...strategy,
        blocks: [...mainBlocks, ...exitBlocks],
      };
      setCurrentStrategy(normalized);
      setCleanSnapshot(JSON.stringify({ id: normalized.id, blocks: normalized.blocks, name: normalized.name }));
      setCurrentStep(0);
      setCompletedSteps(new Set());
      setErrorSteps(new Set());
      setValidationPassedSnapshot('');
      close();
      // Re-run validation against the just-loaded version so the validation
      // panel shows live issues for *this* version, not stale issues from the
      // previously-loaded strategy (BTCAAAAA-33738 Bug 2). setCurrentStrategy
      // clears the prior validationReport so the dialog stays empty until
      // this re-validate resolves. For historical versions we force the local
      // validator because the backend's POST /validate endpoint always runs
      // against the strategy's *latest* stored version — running it on a
      // historical version would surface latest's findings, not the loaded
      // version's.
      const newId = normalized.id as unknown as string;
      const isHistorical = selectOpts?.historicalVersion === true;
      setLoadedHistoricalVersion(isHistorical);
      if (typeof newId === 'string' && newId.startsWith('strategy_')) {
        // BTCAAAAA-36689: when the post-load re-validate resolves, if validation
        // passed AND the user hasn't modified the strategy in the meantime, mark
        // it as "validated & pristine" so the Validate step renders green and the
        // Test/Optimize step opens without a re-prompt. Read the post-validate
        // status from the ref (the closure-captured `normalized` predates the
        // validate mutation) and compare the just-loaded snapshot against the
        // current strategySnapshot — they should match immediately after load
        // (cleanSnapshot was just set above), and a subsequent user edit would
        // cause the mismatch we want.
        const snapshotAtLoad = JSON.stringify({
          id: normalized.id,
          blocks: normalized.blocks,
          name: normalized.name,
        });
        validateStrategy({ localOnly: isHistorical })
          .then(() => {
            const statusAfter = currentStrategyRef.current?.status;
            if (statusAfter === StrategyStatus.VALID) {
              // Re-read strategySnapshot (closure value) at the time of decision.
              // Any edit landed between load and now would have changed the
              // strategySnapshot via the useMemo dep on currentStrategy, so
              // equality with snapshotAtLoad confirms pristine.
              // (We compare via the same JSON shape the useMemo uses.)
              if (strategySnapshot === snapshotAtLoad) {
                setValidationPassedSnapshot(snapshotAtLoad);
              }
            }
          })
          .catch(console.error);
      }
    },
    [close, setCurrentStrategy, validateStrategy, strategySnapshot]
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

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      const data = event.data as { type?: string } | null;
      if (!data || data.type !== 'validation-report:popin') return;
      setActiveDialog('validation');
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
        @keyframes amberPulse {
          0%, 100% {
            box-shadow: 0 0 8px rgba(251, 146, 60, 0.075), inset 0 0 8px rgba(251, 146, 60, 0.038);
          }
          50% {
            box-shadow: 0 0 16px rgba(251, 146, 60, 0.125), inset 0 0 12px rgba(251, 146, 60, 0.063);
          }
        }
        .button-amber-pulse {
          animation: amberPulse 1.8s ease-in-out infinite;
        }
        @media (prefers-reduced-motion: reduce) {
          .button-amber-pulse {
            animation: none;
            box-shadow: 0 0 8px rgba(251, 146, 60, 0.075), inset 0 0 8px rgba(251, 146, 60, 0.038);
          }
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
            { label: 'New Strategy',     onClick: handleNewStrategy,              shortcut: 'Ctrl+N' },
            { label: 'Open Strategy…',   onClick: () => open('strategyBrowser'),  shortcut: 'Ctrl+O' },
            { label: '—', onClick: () => {} },
            { label: 'Save',             onClick: handleSave,                     shortcut: 'Ctrl+S', disabled: !isModified },
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
            // BTCAAAAA-36689: Backtest… shares the same validation gate as
            // the stepper's Test/Optimize button. Without a clean validation
            // pass the user is routed through the alert dialog, not the
            // backtest config.
            { label: 'Backtest…',      onClick: () => {
                if (!isValidatedAndPristine) {
                  setActiveDialog('validationRequiredAlert');
                  return;
                }
                open('backtestConfig');
              } },
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
            <span style={{ color: 'var(--text-secondary)' }}>{currentStrategy.name}</span>
            {isModified && <span className="ml-1" style={{ color: 'var(--accent-orange)' }} title="Unsaved changes">●</span>}
          </span>
        )}
      </div>

      {/* ── Toolbar + Stepper (3-column: left tools | center stepper | right spacer) ── */}
      <div className="flex items-center border-b px-3 py-1.5 flex-shrink-0" style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)' }}>
        {/* Left: toolbar buttons */}
        <div className="flex items-center gap-1">
          <ToolbarButton label="New"  icon={<Plus size={13} strokeWidth={1.5} />} tooltip={TT_NEW}  onClick={handleNewStrategy} />
          <ToolbarButton label="Open" icon={<FolderOpen size={13} strokeWidth={1.5} />} tooltip={TT_OPEN} onClick={() => open('strategyBrowser')} />
          <ToolbarButton
            label="Save"
            icon={<Save size={13} strokeWidth={1.5} />}
            trailing={<ChevronDown size={11} strokeWidth={1.5} />}
            tooltip={TT_SAVE}
            onClick={handleSave}
            disabled={!isModified}
            pulse={isModified}
            testId="strategy-builder-save"
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
            // BTCAAAAA-36689: when the strategy is validated AND pristine (no
            // edits since validation passed), force the Validate step green so
            // it visually communicates "no action needed" and Test/Optimize
            // becomes a one-click open. Any block/name edit invalidates the
            // match (see useMemo on currentStrategy) and the step reverts to
            // needing attention.
            forceCompleteStepIds={isValidatedAndPristine ? new Set([1]) : undefined}
            onStepClick={(id) => {
              setCurrentStep(id);
              if (id === 1) {
                handleValidate();
              } else if (id === 2) {
                // BTCAAAAA-36689: Test/Optimize requires a clean validation
                // pass. If the user has modified the strategy since the last
                // successful validation, route them through the validation
                // page with a message instead of opening the backtest config.
                if (!isValidatedAndPristine) {
                  setActiveDialog('validationRequiredAlert');
                  return;
                }
                open('backtestConfig');
              }
            }}
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

      {/* ── Dialogs ─────────────────────────────────────────────────────── */}
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
        onBackfill={handleBackfillData}
        onClose={close}
      />

      <SettingsDialog open={activeDialog === 'settings'} onClose={close} />

      <SaveStrategyModeDialog
        open={pendingSaveMode !== null}
        originalName={pendingSaveMode?.originalName ?? ''}
        newName={pendingSaveMode?.newName ?? ''}
        busy={saveModeBusy}
        onRenameExisting={handleSaveModeRenameExisting}
        onSaveAsNew={handleSaveModeSaveAsNew}
        onCancel={handleSaveModeCancel}
      />

      <QuickPreviewResultsDialog
        open={activeDialog === 'quickPreview'}
        result={quickPreviewResult}
        onClose={close}
      />

      {activeDialog === 'logViewer' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="rounded-lg shadow-2xl w-2/3 max-h-[70vh] flex flex-col p-6 border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-semibold" style={{ color: 'var(--text-secondary)' }}>Debug Log Viewer</h2>
              <div className="flex gap-2 items-center">
                <button onClick={() => setConsoleLogs([])} className="text-xs px-2 py-1 rounded transition-colors" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}>Clear</button>
                <button onClick={handleDownloadLogs} className="text-xs px-2 py-1 rounded transition-colors" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-card)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}>Download</button>
                <button onClick={close} className="text-xl leading-none ml-2" style={{ color: 'var(--text-muted)' }}
                  onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
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

      {/* BTCAAAAA-36689: shown when the user attempts to open Test/Optimize
          (via the stepper or Tools > Backtest…) without a clean validation
          pass. Closing the alert drops them on the Validate step with the
          validation dialog open so the re-validate is a single click away. */}
      <AlertDialog
        open={activeDialog === 'validationRequiredAlert'}
        title="Validation Required"
        heading="Validate before backtesting"
        message="This strategy has changes that have not been validated. Run validation first, then continue to backtest."
        icon="⚠️"
        onClose={() => {
          setActiveDialog(null);
          setCurrentStep(1);
          setActiveDialog('validation');
        }}
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
  body: 'Start a new strategy — clears the form (name, description, blocks) and focuses the Name field.',
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
  pulse?: boolean;
  icon?: React.ReactNode;
  trailing?: React.ReactNode;
  testId?: string;
}

const ToolbarButton: React.FC<ToolbarButtonProps> = ({ label, tooltip, onClick, disabled, active, accent, pulse, icon, trailing, testId }) => (
  <RichTooltip content={tooltip}>
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded transition-colors border ${
        disabled
          ? 'text-[var(--text-muted)] bg-[rgba(255,255,255,0.02)] border-[rgba(255,255,255,0.05)] cursor-not-allowed'
          : pulse
          ? 'text-[var(--text-secondary)] bg-[rgba(255,255,255,0.06)] border-[rgba(231,178,87,0.2)] button-amber-pulse hover:bg-[rgba(255,255,255,0.10)]'
          : accent
          ? 'font-medium border-[var(--accent-blue-dark)] bg-[var(--accent-blue)] text-[var(--btn-primary-text)] hover:bg-[var(--accent-blue-mid)]'
          : active
          ? 'text-[var(--text-secondary)] bg-[rgba(255,255,255,0.06)] border-[rgba(255,255,255,0.12)] hover:bg-[rgba(255,255,255,0.10)]'
          : 'text-[var(--text-secondary)] bg-[rgba(255,255,255,0.04)] border-[rgba(255,255,255,0.08)] hover:bg-[rgba(255,255,255,0.08)] hover:text-[var(--text-secondary)] hover:border-[rgba(255,255,255,0.15)]'
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
  disabled?: boolean;
}

const MenuDropdown: React.FC<{ label: string; items: MenuItem[] }> = ({ label, items }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="px-3 py-1 text-sm text-[var(--text-dim)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-card)] rounded transition-colors"
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
                disabled={item.disabled}
                className={`flex items-center justify-between w-full px-4 py-1.5 text-sm transition-colors text-left gap-8 whitespace-nowrap ${
                  item.disabled
                    ? 'text-[var(--text-muted)] cursor-not-allowed'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--bg-card)]'
                }`}
              >
                <span>{item.label}</span>
                {item.shortcut && (
                  <span className={`text-xs ${item.disabled ? 'text-[var(--text-muted)]' : 'text-[var(--text-muted)]'}`}>{item.shortcut}</span>
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

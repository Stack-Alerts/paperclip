// Zustand store for Strategy Builder state management
import { create } from 'zustand';
import {
  Strategy,
  StrategyStatus,
  Block,
  BlockType,
  BlockData,
  BlockDefinition,
  BlockCategory,
  ValidationMessage,
  ValidationLevel,
  ValidationReport,
  ValidationIssue,
  ValidationFixEvent,
  ValidationSeverity,
  BacktestConfig,
  BacktestConfigFull,
  BacktestResult,
  StrategySettings,
} from '@/lib/strategy-builder/types';
import { put as apiPut, post as apiPost, runBacktest as apiRunBacktest, getBacktestResults as apiGetBacktestResults, validateStrategy as validateStrategyAPI, autoFixStrategy as autoFixStrategyAPI, revertStrategy as revertStrategyAPI } from '@/lib/strategy-builder/api';
import { validateStrategyLocal, enrichReportWithNarrative } from '@/lib/strategy-builder/validation';

// Strategies loaded from the strategy-builder API have IDs of the form
// "strategy_<hex>" (see StrategyDatabaseManager.create_strategy); locally
// drafted strategies use a Date.now()-based ID. Save persists DB-backed
// strategies via the API so renames/edits survive a reload, and falls back
// to localStorage only for local drafts (BTCAAAAA-30023).
function isBackendStrategyId(id: string | undefined | null): boolean {
  return typeof id === 'string' && id.startsWith('strategy_');
}

const STORAGE_KEY = 'strategy_builder_strategies';

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function loadFromStorage(): Strategy[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveToStorage(strategies: Strategy[]) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(strategies));
}

function makeDefaultStrategy(name: string, description = ''): Strategy {
  const now = new Date().toISOString();
  return {
    id: generateId(),
    name,
    description,
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
}

// Eagerly initialize the current strategy so the UI never shows "No strategy loaded" on first render.
// On server (SSR) this returns null; on client it loads the most recently *modified* strategy
// (sorted by updatedAt DESC) so renames and edits persist across page reloads.
function initCurrentStrategy(): { current: Strategy | null; list: Strategy[] } {
  if (typeof window === 'undefined') return { current: null, list: [] };
  const saved = loadFromStorage();
  if (saved.length > 0) {
    const mostRecent = [...saved].sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    )[0];
    return { current: mostRecent, list: saved };
  }
  const fresh = makeDefaultStrategy('');
  saveToStorage([fresh]);
  return { current: fresh, list: [fresh] };
}

export interface FixedIssueEntry {
  key: string;
  issue: ValidationIssue;
  appliedAt: string;
  undoSnapshot: Strategy;
}

interface StrategyStoreState {
  // Strategy data
  currentStrategy: Strategy | null;
  strategyList: Strategy[];
  isLoadingStrategy: boolean;
  strategyError: string | null;

  // Block library
  blockLibrary: BlockDefinition[];
  blockCategories: BlockCategory[];
  isLoadingLibrary: boolean;

  // UI state
  selectedBlockIndex: number | null;
  validationMessages: ValidationMessage[];
  validationReport: ValidationReport | null;
  isValidating: boolean;
  backTestInProgress: boolean;
  backTestProgress: number;
  backTestResult: BacktestResult | null;
  fixedIssuesInSession: FixedIssueEntry[];

  // Actions
  hydrateFromLocalStorage: () => void;
  loadStrategy: (id: string) => Promise<void>;
  createStrategy: (name: string, description?: string) => Promise<void>;
  saveStrategy: () => Promise<Strategy>;
  saveStrategyAsNew: (newName: string) => Promise<Strategy>;
  deleteBlock: (index: number) => void;
  addBlock: (type: BlockType, position: number) => void;
  updateBlock: (index: number, data: BlockData) => void;
  reorderBlocks: (fromIdx: number, toIdx: number) => void;
  validateStrategy: (opts?: { localOnly?: boolean }) => Promise<void>;
  applyAutoFix: (ruleId: string, autoFixData: Record<string, unknown> | undefined) => Promise<boolean>;
  applyLocalAutoFix: (ruleId: string, data: Record<string, unknown>) => Promise<boolean>;
  undoAutoFix: (key: string) => Promise<void>;
  runBacktest: (config: BacktestConfig | BacktestConfigFull) => Promise<BacktestResult>;
  loadBlockLibrary: () => Promise<void>;
  clearValidation: () => void;
  selectBlock: (index: number | null) => void;
  setCurrentStrategy: (strategy: Strategy | null) => void;
  updateStrategySettings: (settings: Partial<StrategySettings>) => void;
  pollBacktestResult: (runId: string) => Promise<BacktestResult | undefined>;
  highlightedLibraryBlockId: string | null;
  highlightLibraryBlock: (definitionId: string | null) => void;
  duplicateBlock: (fromIndex: number, position: number) => void;
}

export const useStrategyStore = create<StrategyStoreState>((set, get) => ({
  // Initial state — always null so SSR and client initial render match (no hydration mismatch).
  // hydrateFromLocalStorage() is called after mount in StrategyBuilderMainWindow.
  currentStrategy: null,
  strategyList: [],
  isLoadingStrategy: false,
  strategyError: null,
  blockLibrary: [],
  blockCategories: [],
  isLoadingLibrary: true,
  selectedBlockIndex: null,
  validationMessages: [],
  validationReport: null,
  isValidating: false,
  backTestInProgress: false,
  backTestProgress: 0,
  backTestResult: null,
  fixedIssuesInSession: [],

  // Load localStorage state after client mount — keeps SSR/client renders in sync.
  hydrateFromLocalStorage: () => {
    const { current, list } = initCurrentStrategy();
    // Migrate legacy "New_Strategy" name to empty string
    const migrated = list.map(s => s.name === 'New_Strategy' ? { ...s, name: '' } : s);
    const migratedCurrent = current?.name === 'New_Strategy' ? { ...current, name: '' } : current;
    if (migrated.some((s, i) => s.name !== list[i].name)) saveToStorage(migrated);
    set({ currentStrategy: migratedCurrent, strategyList: migrated });
  },

  // Load existing strategy by ID
  loadStrategy: async (id: string) => {
    set({ isLoadingStrategy: true, strategyError: null });
    const strategies = loadFromStorage();
    const strategy = strategies.find((s) => s.id === id) ?? null;
    if (!strategy) {
      set({ isLoadingStrategy: false, strategyError: `Strategy ${id} not found` });
      return;
    }
    set({ currentStrategy: strategy, isLoadingStrategy: false });
  },

  // Create new strategy (stored in localStorage)
  createStrategy: async (name: string, description?: string) => {
    set({ isLoadingStrategy: true });
    const strategy = makeDefaultStrategy(name, description);
    const strategies = loadFromStorage();
    strategies.push(strategy);
    saveToStorage(strategies);
    set({
      currentStrategy: strategy,
      strategyList: strategies,
      isLoadingStrategy: false,
      validationMessages: [],
    });
  },

  // Save current strategy. For DB-backed strategies (loaded from the
  // Strategy Browser) this PUTs to /strategy-builder/strategies/{id} so the
  // rename + metadata edits round-trip to the backend; local drafts only hit
  // localStorage (BTCAAAAA-30023).
  //
  // Scope is intentionally metadata-only (name, description, strategyType,
  // tags). The block list uses the frontend Block contract
  // ({id,type,index,data,...synthetic exit blocks}) which does not match the
  // API's raw {name,logic,signals,exit_conditions} shape — sending blocks
  // back without a denormalizer corrupts the Strategy Browser list view.
  // Block-edit persistence is a follow-up once a denormalize step is in.
  saveStrategy: async () => {
    const { currentStrategy } = get();
    if (!currentStrategy) throw new Error('No strategy to save');

    let updated: Strategy = {
      ...currentStrategy,
      updatedAt: new Date().toISOString(),
    };

    if (isBackendStrategyId(updated.id)) {
      const saved = await apiPut<Strategy>(
        `/strategy-builder/strategies/${updated.id}`,
        {
          name: updated.name,
          description: updated.description ?? '',
          strategyType: (updated as { strategyType?: string }).strategyType,
          tags: updated.tags,
          validationHistory: updated.validationHistory,
        },
      );
      // Keep the locally-normalized blocks so the in-flight builder view
      // doesn't re-shape mid-session; merge server-authoritative metadata
      // (updated name/description/timestamp/version) over the local copy.
      updated = {
        ...updated,
        name: saved.name ?? updated.name,
        description: saved.description ?? updated.description,
        updatedAt: saved.updatedAt ?? updated.updatedAt,
        versionNumber: (saved as { versionNumber?: number }).versionNumber
          ?? (updated as { versionNumber?: number }).versionNumber,
        versionId: (saved as { versionId?: string }).versionId
          ?? (updated as { versionId?: string }).versionId,
        validationHistory: saved.validationHistory ?? updated.validationHistory,
      };
    }

    const strategies = loadFromStorage();
    const idx = strategies.findIndex((s) => s.id === updated.id);
    if (idx >= 0) {
      strategies[idx] = updated;
    } else {
      strategies.push(updated);
    }
    saveToStorage(strategies);
    set({ currentStrategy: updated, strategyList: strategies });
    return updated;
  },

  // Fork the currently-loaded strategy into a brand-new strategy_id with
  // the user-provided name. Backed by POST /strategy-builder/strategies/
  // {id}/duplicate?scope=strategy which copies the latest server version
  // under a new parent Strategy. The new strategy starts at version 1.
  // Returns the new Strategy so the caller can load it into the builder.
  // BTCAAAAA-30023 board feedback 2026-05-27: when Save is clicked after
  // renaming, the UI offers this fork as an alternative to "Rename existing".
  saveStrategyAsNew: async (newName: string) => {
    const { currentStrategy } = get();
    if (!currentStrategy) throw new Error('No strategy to fork');
    if (!isBackendStrategyId(currentStrategy.id)) {
      throw new Error('Cannot fork a local-only draft; save it first');
    }
    const cleanName = newName.trim();
    if (!cleanName) throw new Error('New strategy name is required');

    const forked = await apiPost<Strategy>(
      `/strategy-builder/strategies/${currentStrategy.id}/duplicate`,
      { scope: 'strategy', name: cleanName },
    );

    // The server response carries blocks in the raw API shape
    // ({name, logic, signals, ...}). Preserve the user's already-normalized
    // frontend Block objects in the live store — they correspond to the
    // same content because the fork copied the latest server version.
    // Swapping just the identifying metadata keeps the builder view valid
    // (computeStats reads block.data.logic which only exists on the
    // normalized shape) and avoids re-running the StrategyBrowserDialog
    // normalize transform here.
    const merged: Strategy = {
      ...currentStrategy,
      id: forked.id,
      name: forked.name,
      description: forked.description ?? currentStrategy.description,
      strategyType: (forked as { strategyType?: string }).strategyType
        ?? (currentStrategy as { strategyType?: string }).strategyType,
      versionNumber: (forked as { versionNumber?: number }).versionNumber
        ?? (currentStrategy as { versionNumber?: number }).versionNumber,
      versionId: (forked as { versionId?: string }).versionId
        ?? (currentStrategy as { versionId?: string }).versionId,
      createdAt: forked.createdAt ?? currentStrategy.createdAt,
      updatedAt: forked.updatedAt ?? currentStrategy.updatedAt,
      tags: forked.tags ?? currentStrategy.tags,
    };

    // Mirror the fork into localStorage so the Strategy Browser shows it
    // immediately on next open (the next list fetch will overwrite this
    // with the authoritative server list).
    const strategies = loadFromStorage();
    strategies.push(merged);
    saveToStorage(strategies);
    set({ currentStrategy: merged, strategyList: strategies });
    return merged;
  },

  // Add block to strategy
  addBlock: (type: BlockType, position: number = -1) => {
    const { currentStrategy } = get();
    if (!currentStrategy) return;

    const newBlock: Block = {
      id: `block-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      index: position >= 0 ? position : currentStrategy.blocks.length,
      data: {},
    };

    const updatedBlocks = [...currentStrategy.blocks];
    if (position >= 0) {
      updatedBlocks.splice(position, 0, newBlock);
      updatedBlocks.forEach((block, idx) => { block.index = idx; });
    } else {
      updatedBlocks.push(newBlock);
    }

    set({
      currentStrategy: {
        ...currentStrategy,
        blocks: updatedBlocks,
        status: StrategyStatus.DRAFT,
      },
    });
  },

  // Delete block from strategy
  deleteBlock: (index: number) => {
    const { currentStrategy } = get();
    if (!currentStrategy) return;

    const updatedBlocks = currentStrategy.blocks.filter((_, i) => i !== index);
    updatedBlocks.forEach((block, idx) => { block.index = idx; });

    set({
      currentStrategy: {
        ...currentStrategy,
        blocks: updatedBlocks,
        status: StrategyStatus.DRAFT,
      },
      selectedBlockIndex: null,
    });
  },

  // Update block data
  updateBlock: (index: number, data: BlockData) => {
    const { currentStrategy } = get();
    if (!currentStrategy || !currentStrategy.blocks[index]) return;

    const updatedBlocks = [...currentStrategy.blocks];
    updatedBlocks[index] = {
      ...updatedBlocks[index],
      data: { ...updatedBlocks[index].data, ...data },
      metadata: {
        ...updatedBlocks[index].metadata,
        updatedAt: new Date().toISOString(),
      },
    };

    set({
      currentStrategy: {
        ...currentStrategy,
        blocks: updatedBlocks,
        status: StrategyStatus.DRAFT,
      },
    });
  },

  // Reorder blocks via drag-and-drop
  reorderBlocks: (fromIdx: number, toIdx: number) => {
    const { currentStrategy } = get();
    if (!currentStrategy) return;

    const updatedBlocks = [...currentStrategy.blocks];
    const [removed] = updatedBlocks.splice(fromIdx, 1);
    updatedBlocks.splice(toIdx, 0, removed);
    updatedBlocks.forEach((block, idx) => { block.index = idx; });

    set({
      currentStrategy: {
        ...currentStrategy,
        blocks: updatedBlocks,
        status: StrategyStatus.DRAFT,
      },
    });
  },

  // Validate strategy via the backend InstitutionalValidator
  // (POST /strategy-builder/strategies/{id}/validate). The endpoint runs the
  // same Python validator the thick client uses; the web UI then layers its
  // own executionFlow/confluenceScoring/scenarios narrative on top of the
  // report. Falls back to the TypeScript structural checker only when the
  // backend is unreachable (e.g. dev with no API server). BTCAAAAA-32954.
  validateStrategy: async (opts) => {
    const { currentStrategy } = get();
    if (!currentStrategy) return;

    set({ isValidating: true, validationReport: null });

    // localOnly bypasses the backend (which always validates the *latest*
    // stored version) and runs the TypeScript structural checker against the
    // in-memory blocks. Required when the user loaded a non-latest version
    // via the Strategy Browser — backend's latest-only validation would
    // misreport pass/fail for the historical blocks (BTCAAAAA-33738 Bug 2).
    const localOnly = opts?.localOnly === true;

    if (!localOnly && isBackendStrategyId(currentStrategy.id)) {
      try {
        const apiReport = await validateStrategyAPI(currentStrategy.id) as ValidationReport;
        // The backend owns issues/complexity/timing; the executionFlow,
        // confluenceScoring, and scenarios narrative is a web-UI presentation
        // layer derived from the block tree. Merge it on so the
        // Execution Flow tab has content for API-sourced reports.
        const enriched = enrichReportWithNarrative(apiReport, currentStrategy);
        set({
          validationReport: enriched,
          isValidating: false,
          currentStrategy: {
            ...currentStrategy,
            status: enriched.is_valid ? StrategyStatus.VALID : StrategyStatus.INVALID,
          },
        });
        return;
      } catch {
        // Fall through to local validation below — the structural checks are
        // still useful when the backend is down (e.g. local dev w/o API).
      }
    }

    try {
      const report = validateStrategyLocal(currentStrategy);
      set({
        validationReport: report,
        isValidating: false,
        currentStrategy: {
          ...currentStrategy,
          status: report.is_valid ? StrategyStatus.VALID : StrategyStatus.INVALID,
        },
      });
    } catch (error) {
      const messages: ValidationMessage[] = [
        {
          id: 'validation-error',
          level: ValidationLevel.ERROR,
          text: `Validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
          code: 'VALIDATION_ERROR',
          timestamp: new Date().toISOString(),
        },
      ];

      set({
        validationMessages: messages,
        isValidating: false,
        currentStrategy: { ...currentStrategy, status: StrategyStatus.INVALID },
      });
    }
  },

  // Apply a validator auto-fix (TIMING_004, EXIT_009, LOGIC_003, DIRECTION_001)
  // via the backend. The endpoint creates a new strategy version with the
  // fix applied. We don't splice the raw API response into currentStrategy
  // — those blocks are in the {name, logic, signals} shape and the rest of
  // the builder expects the normalized {id, type, data} Block contract; the
  // un-normalized swap crashed StrategyInfoPanel::computeStats. Instead we
  // re-run validateStrategy, which re-reads from the DB and reflects the
  // fix in the validation panel directly. BTCAAAAA-32954.
  // After fix, track the issue as fixed so the row stays visible with undo.
  applyAutoFix: async (ruleId, autoFixData) => {
    const { currentStrategy, validationReport } = get();
    if (!currentStrategy || !isBackendStrategyId(currentStrategy.id)) {
      return false;
    }
    try {
      // Find the issue being fixed so we can track it as fixed
      const allIssues = [
        ...(validationReport?.critical_issues ?? []),
        ...(validationReport?.errors ?? []),
        ...(validationReport?.warnings ?? []),
        ...(validationReport?.notices ?? []),
        ...(validationReport?.info ?? []),
      ];
      const matchingIssue = allIssues.find((issue) => issue.rule_id === ruleId);

      await autoFixStrategyAPI(currentStrategy.id, ruleId, autoFixData);

      // Track the fixed issue before re-validation and persist to strategy
      if (matchingIssue) {
        const key = `${ruleId}-${matchingIssue.location || 'global'}`;
        const timestamp = new Date().toISOString();
        const fixEvent: ValidationFixEvent = {
          rule_id: matchingIssue.rule_id,
          rule_name: matchingIssue.rule_name,
          timestamp,
        };
        if (typeof autoFixData === 'object' && autoFixData !== null) {
          fixEvent.mode = (autoFixData as Record<string, unknown>).mode as string | undefined;
          fixEvent.targetIndex = (autoFixData as Record<string, unknown>).targetIndex as number | undefined;
          fixEvent.newName = (autoFixData as Record<string, unknown>).newName as string | undefined;
        }
        set((state) => {
          const strategy = state.currentStrategy;
          if (!strategy) return state;
          return {
            currentStrategy: {
              ...strategy,
              validationHistory: [
                ...(strategy.validationHistory ?? []),
                fixEvent,
              ],
            },
            fixedIssuesInSession: [
              ...state.fixedIssuesInSession,
              {
                key,
                issue: matchingIssue,
                appliedAt: timestamp,
                undoSnapshot: strategy,
              },
            ],
          };
        });
      }

      await (get().validateStrategy as () => Promise<void>)();
      return true;
    } catch (error) {
      console.error('Auto-fix failed:', error);
      return false;
    }
  },

  // Apply a local auto-fix for client-side validation issues (missing_timeframe,
  // missing_target_market). Mutates currentStrategy.settings directly, persists
  // to localStorage or backend, then re-runs validation so the panel reflects
  // the cleared warning. Track the issue as fixed so the row stays visible.
  applyLocalAutoFix: async (ruleId, data) => {
    const { currentStrategy, validationReport } = get();
    if (!currentStrategy) return false;

    try {
      const updated: Strategy = { ...currentStrategy };

      if (ruleId === 'missing_timeframe' && typeof data.value === 'string') {
        updated.settings.timeframe = data.value;
      } else if (ruleId === 'missing_target_market' && typeof data.value === 'string') {
        updated.settings.targetMarket = data.value;
      } else {
        return false;
      }

      // Find the issue being fixed so we can track it as fixed
      const allIssues = [
        ...(validationReport?.critical_issues ?? []),
        ...(validationReport?.errors ?? []),
        ...(validationReport?.warnings ?? []),
        ...(validationReport?.notices ?? []),
        ...(validationReport?.info ?? []),
      ];
      const matchingIssue = allIssues.find((issue) => issue.rule_id === ruleId);

      // Track the fixed issue before persisting and add to validationHistory
      if (matchingIssue) {
        const key = `${ruleId}-${matchingIssue.location || 'global'}`;
        const timestamp = new Date().toISOString();
        const fixEvent: ValidationFixEvent = {
          rule_id: matchingIssue.rule_id,
          rule_name: matchingIssue.rule_name,
          mode: 'auto_fix_local',
          timestamp,
        };
        updated.validationHistory = [
          ...(updated.validationHistory ?? []),
          fixEvent,
        ];
        set((state) => ({
          currentStrategy: updated,
          fixedIssuesInSession: [
            ...state.fixedIssuesInSession,
            {
              key,
              issue: matchingIssue,
              appliedAt: timestamp,
              undoSnapshot: currentStrategy,
            },
          ],
        }));
      } else {
        set({ currentStrategy: updated });
      }

      // For backend strategies, save the change so it persists across reload
      if (isBackendStrategyId(updated.id)) {
        await (get().saveStrategy as () => Promise<Strategy>)();
      } else {
        // For local drafts, saveStrategy will handle localStorage
        saveToStorage([...loadFromStorage().filter((s) => s.id !== updated.id), updated]);
      }

      // Re-run validation so the panel reflects the cleared warning
      await (get().validateStrategy as () => Promise<void>)();
      return true;
    } catch (error) {
      console.error('Local auto-fix failed:', error);
      return false;
    }
  },

  // Run backtest via backend API (BTCAAAAA-31183 / parent BTCAAAAA-31180):
  //   POST /strategies/{id}/backtest -> { runId }
  //   poll GET /strategies/{id}/backtest/{runId} until status in ('done','error')
  runBacktest: async (config: BacktestConfig | BacktestConfigFull) => {
    const strategyId = (config as { strategyId?: string }).strategyId;
    if (!strategyId) throw new Error('Backtest: missing strategyId in config');
    // The backend backtest route POST /strategies/{id}/backtest loads the
    // strategy from the strategy-builder DB by id (app.py start_backtest).
    // Local drafts use a Date.now()-based id that the backend doesn't know
    // about, which surfaces as a confusing "API error: 404 Not Found" in the
    // Live Output footer (BTCAAAAA-34610). Surface the real cause and stop
    // before issuing the request.
    if (!isBackendStrategyId(strategyId)) {
      throw new Error(
        'Run Test requires a saved strategy. Save this draft via Strategy Browser → New, then re-open it before running a backtest.',
      );
    }
    set({ backTestInProgress: true, backTestProgress: 0, backTestResult: undefined });
    try {
      const startResp = (await apiRunBacktest(strategyId, config)) as { runId: string; status: string };
      const runId = startResp.runId;
      if (!runId) throw new Error('Backtest: backend did not return a runId');

      // Poll loop: 1s cadence, 30 min ceiling.
      const deadline = Date.now() + 30 * 60_000;
       
      while (true) {
        if (Date.now() > deadline) throw new Error('Backtest timed out after 30 minutes');
        await new Promise((r) => setTimeout(r, 1000));
        const status = (await apiGetBacktestResults(strategyId, runId)) as {
          runId: string;
          status: string;
          progress: number;
          trades?: unknown[];
          metrics?: Record<string, unknown>;
          error?: string | null;
          startedAt?: string;
          completedAt?: string | null;
        };
        if (typeof status.progress === 'number') set({ backTestProgress: status.progress });
        if (status.status === 'error') {
          throw new Error(status.error || 'Backtest failed');
        }
        if (status.status === 'done') {
          const m = status.metrics ?? {};
          const result: BacktestResult = {
            id: runId,
            strategyId,
            runId,
            status: 'completed',
            startDate: (config as BacktestConfig).startDate ?? '',
            endDate: (config as BacktestConfig).endDate ?? '',
            initialCapital: (config as BacktestConfig).initialCapital ?? 10000,
            finalCapital: ((config as BacktestConfig).initialCapital ?? 10000) *
              (1 + Number(m.returnPercentage ?? 0) / 100),
            totalTrades: Number(m.totalTrades ?? 0),
            winningTrades: Number(m.winningTrades ?? 0),
            losingTrades: Number(m.losingTrades ?? 0),
            winRate: Number(m.winRate ?? 0),
            totalReturn: Number(m.returnPercentage ?? 0),
            returnPercentage: Number(m.returnPercentage ?? 0),
            maxDrawdown: Number(m.maxDrawdown ?? 0),
            sharpeRatio: Number(m.sharpeRatio ?? 0),
            sortino_ratio: Number(m.sortinoRatio ?? 0),
            profitFactor: Number(m.profitFactor ?? 0),
            averageWin: Number(m.averageWin ?? 0),
            averageLoss: Number(m.averageLoss ?? 0),
            trades: (status.trades as BacktestResult['trades']) ?? [],
            createdAt: status.startedAt ?? new Date().toISOString(),
            completedAt: status.completedAt ?? new Date().toISOString(),
          };
          set({ backTestResult: result, backTestInProgress: false, backTestProgress: 100 });
          return result;
        }
      }
    } catch (e) {
      set({ backTestInProgress: false });
      throw e;
    }
  },

  // Poll for backtest results (one-shot wrapper around GET)
  pollBacktestResult: async (runId: string) => {
    const strategyId = get().currentStrategy?.id;
    if (!strategyId) return undefined;
    try {
      const status = (await apiGetBacktestResults(strategyId, runId)) as {
        status: string;
        metrics?: Record<string, unknown>;
        trades?: unknown[];
      };
      if (status.status !== 'done') return undefined;
      // Return a minimal projection — callers that need the full shape go via runBacktest.
      return { runId, status: 'completed', trades: status.trades, metrics: status.metrics } as unknown as BacktestResult;
    } catch {
      return undefined;
    }
  },

  // Load block library from static file
  loadBlockLibrary: async () => {
    set({ isLoadingLibrary: true });
    try {
      const response = await fetch('/block-library.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('Failed to load block library');
      const data = await response.json() as {
        blocks: BlockDefinition[];
        categories: BlockCategory[];
      };
      set({
        blockLibrary: data.blocks,
        blockCategories: data.categories,
        isLoadingLibrary: false,
      });
    } catch (error) {
      set({ isLoadingLibrary: false });
      console.error('Failed to load block library:', error);
    }
  },

  // Clear validation messages
  clearValidation: () => {
    set({ validationMessages: [] });
  },

  // Select a block for editing
  selectBlock: (index: number | null) => {
    set({ selectedBlockIndex: index });
  },

  // Set current strategy directly. Also clears the previous strategy/version's
  // live validation surface (validationReport, validationMessages) so issues
  // from the prior load don't bleed through to the newly-loaded version —
  // callers (e.g. the Strategy Browser open path) re-run validateStrategy()
  // once the swap lands so the panel reflects the version actually loaded
  // (BTCAAAAA-33738 Bug 2).
  setCurrentStrategy: (strategy: Strategy | null) => {
    // Rehydrate fixedIssuesInSession from persisted validationHistory
    let fixedIssuesInSession: FixedIssueEntry[] = [];
    if (strategy?.validationHistory) {
      fixedIssuesInSession = strategy.validationHistory
        .filter((event) => !event.undone)
        .map((event) => ({
          key: `${event.rule_id}-${event.timestamp}`,
          issue: {
            rule_id: event.rule_id,
            rule_name: event.rule_name,
            severity: 'ERROR' as ValidationSeverity,
            category: '',
            message: `Fixed: ${event.rule_name}`,
            location: '',
          },
          appliedAt: event.timestamp,
          undoSnapshot: strategy,
        }));
    }
    set({
      currentStrategy: strategy,
      fixedIssuesInSession,
      validationReport: null,
      validationMessages: [],
    });
  },

  highlightedLibraryBlockId: null,
  highlightLibraryBlock: (definitionId) => {
    set({ highlightedLibraryBlockId: definitionId });
  },

  // Atomically clone block at fromIndex and insert at position with a deep-copied data object
  duplicateBlock: (fromIndex: number, position: number) => {
    const { currentStrategy } = get();
    if (!currentStrategy) return;
    const source = currentStrategy.blocks[fromIndex];
    if (!source) return;
    const newBlock: Block = {
      id: `block-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type: source.type,
      index: position,
      data: JSON.parse(JSON.stringify(source.data)) as BlockData,
    };
    const updatedBlocks = [...currentStrategy.blocks];
    updatedBlocks.splice(position, 0, newBlock);
    updatedBlocks.forEach((block, idx) => { block.index = idx; });
    set({ currentStrategy: { ...currentStrategy, blocks: updatedBlocks, status: StrategyStatus.DRAFT } });
  },

  // Update strategy settings
  updateStrategySettings: (settings: Partial<StrategySettings>) => {
    const { currentStrategy } = get();
    if (!currentStrategy) return;

    set({
      currentStrategy: {
        ...currentStrategy,
        settings: {
          ...currentStrategy.settings,
          ...settings,
        },
        status: StrategyStatus.DRAFT,
      },
    });
  },

  // Undo a fixed issue by restoring the pre-fix snapshot
  undoAutoFix: async (key) => {
    const { fixedIssuesInSession, currentStrategy } = get();
    const fixedEntry = fixedIssuesInSession.find((entry) => entry.key === key);
    if (!fixedEntry) return;

    const strategyId = fixedEntry.undoSnapshot.id;

    // For backend strategies, call the revert endpoint BEFORE clearing the fixed entry
    // so a failed revert leaves the FIXED state visible for retry
    if (isBackendStrategyId(strategyId)) {
      try {
        const versionId = fixedEntry.undoSnapshot.versionId;
        if (!versionId) {
          throw new Error('Cannot undo: pre-fix snapshot has no versionId');
        }
        await revertStrategyAPI(strategyId, versionId);
        // Restore the pre-fix snapshot (already in UI-format blocks) rather than
        // using the raw-blocks API response, which StrategyInfoPanel can't render.
        // validateStrategy() below re-validates the new DB version.
        set({ currentStrategy: fixedEntry.undoSnapshot });
      } catch (error) {
        console.error('Failed to revert strategy:', error);
        throw error;
      }
    } else {
      // For local drafts, restore the snapshot and persist to localStorage
      set({ currentStrategy: fixedEntry.undoSnapshot });
      saveToStorage([
        ...loadFromStorage().filter((s) => s.id !== strategyId),
        fixedEntry.undoSnapshot,
      ]);
    }

    // Mark the history entry as undone instead of deleting it (audit trail preservation)
    set((state) => {
      const strategy = state.currentStrategy ?? currentStrategy;
      if (!strategy || !strategy.validationHistory) return state;
      const ruleId = fixedEntry.issue.rule_id;
      const updatedHistory = strategy.validationHistory.map((event) =>
        event.rule_id === ruleId && !event.undone ? { ...event, undone: true } : event
      );
      return {
        currentStrategy: { ...strategy, validationHistory: updatedHistory },
        fixedIssuesInSession: state.fixedIssuesInSession.filter((entry) => entry.key !== key),
      };
    });

    // Re-run validation so the now-tripping issue re-appears in the LIVE list
    await (get().validateStrategy as () => Promise<void>)();
  },
}));

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
  BacktestConfig,
  BacktestConfigFull,
  BacktestResult,
  StrategySettings,
} from '@/lib/strategy-builder/types';

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
  isValidating: boolean;
  backTestInProgress: boolean;
  backTestProgress: number;
  backTestResult: BacktestResult | null;

  // Actions
  hydrateFromLocalStorage: () => void;
  loadStrategy: (id: string) => Promise<void>;
  createStrategy: (name: string, description?: string) => Promise<void>;
  saveStrategy: () => Promise<Strategy>;
  deleteBlock: (index: number) => void;
  addBlock: (type: BlockType, position: number) => void;
  updateBlock: (index: number, data: BlockData) => void;
  reorderBlocks: (fromIdx: number, toIdx: number) => void;
  validateStrategy: () => Promise<void>;
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
  isValidating: false,
  backTestInProgress: false,
  backTestProgress: 0,
  backTestResult: null,

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

  // Save current strategy to localStorage
  saveStrategy: async () => {
    const { currentStrategy } = get();
    if (!currentStrategy) throw new Error('No strategy to save');

    const updated: Strategy = {
      ...currentStrategy,
      updatedAt: new Date().toISOString(),
    };

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

  // Validate strategy client-side
  validateStrategy: async () => {
    const { currentStrategy } = get();
    if (!currentStrategy) return;

    set({ isValidating: true });
    const messages: ValidationMessage[] = [];

    if (!currentStrategy.name || currentStrategy.name.trim() === '') {
      messages.push({
        id: 'validation-name',
        level: ValidationLevel.ERROR,
        text: 'Strategy name is required',
        code: 'MISSING_NAME',
        timestamp: new Date().toISOString(),
      });
    }

    if (currentStrategy.blocks.length === 0) {
      messages.push({
        id: 'validation-blocks',
        level: ValidationLevel.WARNING,
        text: 'Strategy has no building blocks',
        code: 'NO_BLOCKS',
        timestamp: new Date().toISOString(),
      });
    }

    const hasErrors = messages.some((m) => m.level === ValidationLevel.ERROR);
    const newStatus = hasErrors ? StrategyStatus.INVALID : StrategyStatus.VALID;

    set({
      validationMessages: messages,
      isValidating: false,
      currentStrategy: { ...currentStrategy, status: newStatus },
    });
  },

  // Run backtest (stub — backend not available)
  runBacktest: async (_config: BacktestConfig | BacktestConfigFull) => {
    set({ backTestInProgress: true, backTestProgress: 0 });
    await new Promise((r) => setTimeout(r, 500));
    set({ backTestInProgress: false });
    throw new Error('Backtest backend not connected');
  },

  // Poll for backtest results (stub)
  pollBacktestResult: async (_runId: string) => {
    return undefined;
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

  // Set current strategy directly
  setCurrentStrategy: (strategy: Strategy | null) => {
    set({ currentStrategy: strategy });
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
}));

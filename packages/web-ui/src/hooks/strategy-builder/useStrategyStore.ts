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
import * as api from '@/lib/strategy-builder/api';

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
}

export const useStrategyStore = create<StrategyStoreState>((set, get) => ({
  // Initial state
  currentStrategy: null,
  strategyList: [],
  isLoadingStrategy: false,
  strategyError: null,
  blockLibrary: [],
  blockCategories: [],
  isLoadingLibrary: false,
  selectedBlockIndex: null,
  validationMessages: [],
  isValidating: false,
  backTestInProgress: false,
  backTestProgress: 0,
  backTestResult: null,

  // Load existing strategy by ID
  loadStrategy: async (id: string) => {
    set({ isLoadingStrategy: true, strategyError: null });
    try {
      const strategy = await api.get<Strategy>(`/strategies/${id}`);
      set({ currentStrategy: strategy, isLoadingStrategy: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load strategy';
      set({ isLoadingStrategy: false, strategyError: message });
      throw error;
    }
  },

  // Create new strategy
  createStrategy: async (name: string, description?: string) => {
    set({ isLoadingStrategy: true });
    try {
      const strategy = await api.post<Strategy>('/strategies', {
        name,
        description: description || '',
      });
      set({
        currentStrategy: strategy,
        isLoadingStrategy: false,
        validationMessages: [],
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create strategy';
      set({ isLoadingStrategy: false, strategyError: message });
      throw error;
    }
  },

  // Save current strategy
  saveStrategy: async () => {
    const { currentStrategy } = get();
    if (!currentStrategy) throw new Error('No strategy to save');

    try {
      const updated = await api.put<Strategy>(
        `/strategies/${currentStrategy.id}`,
        currentStrategy
      );
      set({ currentStrategy: updated });
      return updated;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to save strategy';
      set({ strategyError: message });
      throw error;
    }
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
      // Re-index all blocks after insertion point
      updatedBlocks.forEach((block, idx) => {
        block.index = idx;
      });
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
    // Re-index remaining blocks
    updatedBlocks.forEach((block, idx) => {
      block.index = idx;
    });

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

    // Re-index all blocks
    updatedBlocks.forEach((block, idx) => {
      block.index = idx;
    });

    set({
      currentStrategy: {
        ...currentStrategy,
        blocks: updatedBlocks,
        status: StrategyStatus.DRAFT,
      },
    });
  },

  // Validate strategy against rules
  validateStrategy: async () => {
    const { currentStrategy } = get();
    if (!currentStrategy) return;

    set({ isValidating: true });
    try {
      // Optimistic validation client-side first
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
          level: ValidationLevel.ERROR,
          text: 'Strategy must contain at least one block',
          code: 'NO_BLOCKS',
          timestamp: new Date().toISOString(),
        });
      }

      // Server-side validation
      const result = await api.post<{ messages: ValidationMessage[] }>(
        `/strategies/${currentStrategy.id}/validate`,
        currentStrategy
      );

      const allMessages = [
        ...messages,
        ...result.messages,
      ];

      const hasErrors = allMessages.some((m) => m.level === ValidationLevel.ERROR);
      const newStatus = hasErrors ? StrategyStatus.INVALID : StrategyStatus.VALID;

      set({
        validationMessages: allMessages,
        isValidating: false,
        currentStrategy: {
          ...currentStrategy,
          status: newStatus,
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Validation failed';
      set({
        isValidating: false,
        validationMessages: [
          {
            id: `validation-error-${Date.now()}`,
            level: ValidationLevel.ERROR,
            text: message,
            code: 'VALIDATION_ERROR',
            timestamp: new Date().toISOString(),
          },
        ],
      });
    }
  },

  // Run backtest
  runBacktest: async (config: BacktestConfig | BacktestConfigFull) => {
    set({ backTestInProgress: true, backTestProgress: 0 });
    try {
      const result = await api.post<BacktestResult>(
        `/strategies/${config.strategyId}/backtest`,
        config
      );

      set({
        backTestResult: result,
        backTestInProgress: false,
        backTestProgress: 100,
      });

      return result;
    } catch (error) {
      set({ backTestInProgress: false });
      const message = error instanceof Error ? error.message : 'Backtest failed';
      throw new Error(message);
    }
  },

  // Poll for backtest results
  pollBacktestResult: async (runId: string) => {
    const { currentStrategy } = get();
    if (!currentStrategy) return;

    try {
      const result = await api.get<BacktestResult>(
        `/strategies/${currentStrategy.id}/backtest/${runId}`
      );

      if (result.status === 'completed') {
        set({
          backTestResult: result,
          backTestInProgress: false,
          backTestProgress: 100,
        });
      } else if (result.status === 'running') {
        // Update progress if available
        if (result.completedAt) {
          set({ backTestProgress: result.totalTrades });
        }
      }

      return result;
    } catch (error) {
      set({ backTestInProgress: false });
      throw error;
    }
  },

  // Load block library from backend
  loadBlockLibrary: async () => {
    set({ isLoadingLibrary: true });
    try {
      const response = await api.get<{
        blocks: BlockDefinition[];
        categories: BlockCategory[];
      }>('/blocks');

      set({
        blockLibrary: response.blocks,
        blockCategories: response.categories,
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

  // Set current strategy directly (useful for tests/overrides)
  setCurrentStrategy: (strategy: Strategy | null) => {
    set({ currentStrategy: strategy });
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

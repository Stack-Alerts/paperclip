'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { BlockDefinition, BlockType, BlockSignal } from '@/lib/strategy-builder/types';
import {
  getSignalStatistics,
  saveFilterPreset,
  loadAllFilterPresets,
  deleteFilterPreset,
  FilterPreset,
} from '@/lib/strategy-builder/api';
import { InfoTooltip } from './InfoTooltip';
import { ExitConditionDialog } from './ExitConditionDialog';

const BLOCK_TYPE_LABELS: Record<BlockType, string> = {
  [BlockType.ENTRY_CONDITION]: 'Entry',
  [BlockType.EXIT_CONDITION]: 'Exit',
  [BlockType.RISK_MANAGEMENT]: 'Risk',
  [BlockType.TIME_CONSTRAINT]: 'Time',
  [BlockType.FILTER]: 'Filter',
  [BlockType.INDICATOR]: 'Indicator',
  [BlockType.POSITION_SIZING]: 'Sizing',
};

const TYPE_COLORS: Record<BlockType, string> = {
  [BlockType.ENTRY_CONDITION]: 'text-emerald-400 bg-emerald-950 border-emerald-800',
  [BlockType.EXIT_CONDITION]: 'text-red-400 bg-red-950 border-red-800',
  [BlockType.RISK_MANAGEMENT]: 'text-amber-400 bg-amber-950 border-amber-800',
  [BlockType.TIME_CONSTRAINT]: 'text-blue-400 bg-blue-950 border-blue-800',
  [BlockType.FILTER]: 'text-purple-400 bg-purple-950 border-purple-800',
  [BlockType.INDICATOR]: 'text-cyan-400 bg-cyan-950 border-cyan-800',
  [BlockType.POSITION_SIZING]: 'text-orange-400 bg-orange-950 border-orange-800',
};

interface SignalStatisticsCache {
  [blockId: string]: {
    [signalName: string]: {
      occurrences: number;
      percentage: number;
      total_candles: number;
    };
  };
}

interface BlockCardProps {
  block: BlockDefinition;
  onAddSignals: (blockName: string, signals: BlockSignal[], logic: 'AND' | 'OR') => void;
  onAddExit: (blockName: string, signal: BlockSignal) => void;
  onAddSimple: (block: BlockDefinition) => void;
  strategyBlocks: any[];
}

function BlockCard({
  block,
  onAddSignals,
  onAddExit,
  onAddSimple,
  strategyBlocks,
}: BlockCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [selectedSignals, setSelectedSignals] = useState<Set<string>>(new Set());
  const [statsLoading, setStatsLoading] = useState(false);
  const [addedSignals, setAddedSignals] = useState<Set<string>>(new Set());
  const [showExitDialog, setShowExitDialog] = useState(false);
  const [exitSignalName, setExitSignalName] = useState<string>('');

  const typeColor = TYPE_COLORS[block.type] ?? 'text-zinc-400 bg-zinc-800 border-zinc-700';
  const typeLabel = BLOCK_TYPE_LABELS[block.type] ?? block.type;
  const visibleSignals = (block.signals ?? []).filter((s) => s.ui_visible !== false);

  const strategyHasBlocks = strategyBlocks.length > 0;

  useEffect(() => {
    if (expanded && visibleSignals.length > 0 && !block.signals?.[0]?.occurrences) {
      loadSignalStats();
    }
  }, [expanded]);

  const loadSignalStats = async () => {
    if (!visibleSignals.length) return;
    setStatsLoading(true);
    try {
      const signalNames = visibleSignals.map((s) => s.name);
      const stats = await getSignalStatistics(block.name, signalNames);
      // Update block signals with stats (in place mutation)
      visibleSignals.forEach((signal) => {
        if (stats[signal.name]) {
          signal.occurrences = stats[signal.name].count;
          signal.occurrence_percentage = stats[signal.name].percentage;
          signal.total_candles = stats[signal.name].total_candles;
        }
      });
    } catch (error) {
      console.warn('Failed to load signal statistics:', error);
    } finally {
      setStatsLoading(false);
    }
  };

  const handleExpandClick = async () => {
    setExpanded(!expanded);
    if (!expanded && visibleSignals.length > 0 && !block.signals?.[0]?.occurrences) {
      await loadSignalStats();
    }
  };

  const toggleSignal = (signalName: string) => {
    if (addedSignals.has(signalName)) return;
    const newSelected = new Set(selectedSignals);
    if (newSelected.has(signalName)) {
      newSelected.delete(signalName);
    } else {
      newSelected.add(signalName);
    }
    setSelectedSignals(newSelected);
  };

  const handleAddAND = () => {
    if (selectedSignals.size === 0) return;
    const selected = visibleSignals.filter((s) => selectedSignals.has(s.name));
    onAddSignals(block.name, selected, 'AND');
    markSignalsAdded([...selectedSignals]);
    setSelectedSignals(new Set());
  };

  const handleAddOR = () => {
    if (!strategyHasBlocks || selectedSignals.size === 0) return;
    const selected = visibleSignals.filter((s) => selectedSignals.has(s.name));
    onAddSignals(block.name, selected, 'OR');
    markSignalsAdded([...selectedSignals]);
    setSelectedSignals(new Set());
  };

  const handleAddExit = () => {
    if (selectedSignals.size !== 1) return;
    const signalName = [...selectedSignals][0];
    setExitSignalName(signalName);
    setShowExitDialog(true);
  };

  const handleExitDialogSave = (config: any) => {
    const signal = visibleSignals.find((s) => s.name === exitSignalName);
    if (signal) {
      onAddExit(block.name, signal);
      markSignalsAdded([exitSignalName]);
      setSelectedSignals(new Set());
    }
    setShowExitDialog(false);
    setExitSignalName('');
  };

  const markSignalsAdded = (signalNames: string[]) => {
    setAddedSignals(new Set([...addedSignals, ...signalNames]));
  };

  const getExpandButtonText = () => {
    const total = visibleSignals.length;
    const added = addedSignals.size;
    const available = total - added;
    if (available === 0) return `✓ All Signals Added (${total})`;
    if (added > 0) return `Show/Hide Signals (${available} available, ${added} added)`;
    return `Show/Hide Signals (${total})`;
  };

  return (
    <div className="rounded border border-zinc-700 bg-zinc-900 mb-3">
      <button
        className="w-full text-left px-3 py-2 flex items-start gap-2 hover:bg-zinc-800 transition-colors"
        onClick={handleExpandClick}
        aria-expanded={expanded}
      >
        <span className={`text-xs px-1.5 py-0.5 rounded border font-mono flex-shrink-0 mt-0.5 ${typeColor}`}>
          {typeLabel}
        </span>
        <div className="flex-1">
          <span className="text-sm font-medium text-zinc-100">{block.name}</span>
        </div>
        <span className="text-zinc-500 text-xs flex-shrink-0">{expanded ? '▴' : '▾'}</span>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-zinc-800 bg-zinc-800/50">
          <p className="text-xs text-zinc-400 leading-relaxed">{block.description}</p>

          {visibleSignals.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold text-cyan-400">Select signals to add:</div>
              {statsLoading ? (
                <p className="text-xs text-zinc-500">Loading signal statistics…</p>
              ) : (
                <div className="space-y-1 max-h-64 overflow-y-auto">
                  {visibleSignals.map((signal) => (
                    <div key={signal.name}>
                      <label className="flex items-start gap-2 cursor-pointer hover:bg-zinc-700/50 p-1 rounded">
                        <input
                          type="checkbox"
                          checked={selectedSignals.has(signal.name)}
                          onChange={() => toggleSignal(signal.name)}
                          disabled={addedSignals.has(signal.name)}
                          className="mt-1 w-4 h-4 rounded accent-cyan-400 disabled:opacity-50"
                        />
                        <div className="flex-1 min-w-0">
                          <div
                            className={`text-xs font-medium ${
                              addedSignals.has(signal.name)
                                ? 'line-through text-zinc-600'
                                : 'text-zinc-100'
                            }`}
                          >
                            {signal.name}
                            {signal.occurrences !== undefined && (
                              <span className="text-zinc-500">
                                {' '}({signal.occurrences.toLocaleString()} found,{' '}
                                {(signal.occurrence_percentage || 0).toFixed(1)}%)
                              </span>
                            )}
                          </div>
                          {signal.description && (
                            <p className="text-xs text-zinc-500 italic ml-6 mt-0.5">
                              {signal.description}
                            </p>
                          )}
                        </div>
                      </label>
                    </div>
                  ))}
                </div>
              )}

              <div className="text-xs text-zinc-500 italic pt-2">
                Note: Signal counts based on last 180 days of BTC data
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  onClick={handleAddAND}
                  disabled={selectedSignals.size === 0}
                  className="flex-1 px-2 py-1.5 rounded text-xs font-medium bg-emerald-700 hover:bg-emerald-600 disabled:bg-zinc-700 disabled:text-zinc-600 text-white transition-colors"
                  title="Add as required signal (AND logic)"
                >
                  ➕ AND
                </button>
                <button
                  onClick={handleAddOR}
                  disabled={!strategyHasBlocks || selectedSignals.size === 0}
                  className="flex-1 px-2 py-1.5 rounded text-xs font-medium bg-amber-700 hover:bg-amber-600 disabled:bg-zinc-700 disabled:text-zinc-600 text-white transition-colors"
                  title="Add as optional signal (OR logic)"
                >
                  ➕ OR
                </button>
                <button
                  onClick={handleAddExit}
                  disabled={selectedSignals.size !== 1}
                  className="flex-1 px-2 py-1.5 rounded text-xs font-medium bg-red-700 hover:bg-red-600 disabled:bg-zinc-700 disabled:text-zinc-600 text-white transition-colors"
                  title="Add as exit condition"
                >
                  ➕ EXIT
                </button>
              </div>
            </div>
          )}

          {visibleSignals.length === 0 && (
            <button
              className="w-full py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors"
              onClick={() => onAddSimple(block)}
            >
              + Add to Strategy
            </button>
          )}
        </div>
      )}

      <ExitConditionDialog
        open={showExitDialog}
        signalName={exitSignalName}
        onClose={() => {
          setShowExitDialog(false);
          setExitSignalName('');
        }}
        onSave={handleExitDialogSave}
      />
    </div>
  );
}

export function BlockSearchPanel() {
  const { blockLibrary, blockCategories, isLoadingLibrary, addBlock, currentStrategy } =
    useStrategyStore();
  const updateBlock = useStrategyStore((s) => s.updateBlock);

  const [searchText, setSearchText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedType, setSelectedType] = useState<BlockType | 'all'>('all');
  const [presets, setPresets] = useState<FilterPreset[]>([]);

  useEffect(() => {
    setPresets(loadAllFilterPresets());
  }, []);

  const filteredBlocks = useMemo(() => {
    return blockLibrary.filter((b) => {
      const blockNameMatch = b.name.toLowerCase().includes(searchText.toLowerCase());
      const descMatch = b.description.toLowerCase().includes(searchText.toLowerCase());
      const signalMatch =
        (b.signals ?? []).some((s) => s.name.toLowerCase().includes(searchText.toLowerCase())) &&
        searchText.length > 0;
      const matchesSearch =
        !searchText || blockNameMatch || descMatch || signalMatch;
      const matchesCategory = selectedCategory === 'all' || b.category === selectedCategory;
      const matchesType = selectedType === 'all' || b.type === selectedType;
      return matchesSearch && matchesCategory && matchesType;
    });
  }, [blockLibrary, searchText, selectedCategory, selectedType]);

  const handleAddSignals = useCallback(
    (blockName: string, signals: BlockSignal[], logic: 'AND' | 'OR') => {
      const strategy = useStrategyStore.getState().currentStrategy;
      const position = strategy?.blocks.length ?? 0;
      addBlock(BlockType.ENTRY_CONDITION, position);
      useStrategyStore.getState().updateBlock(position, {
        name: blockName,
        logic,
        signals: signals.map((s) => ({ name: s.name, logic })),
      });
    },
    [addBlock]
  );

  const handleAddExit = useCallback(
    (blockName: string, signal: BlockSignal) => {
      const strategy = useStrategyStore.getState().currentStrategy;
      const position = strategy?.blocks.length ?? 0;
      addBlock(BlockType.EXIT_CONDITION, position);
      useStrategyStore.getState().updateBlock(position, {
        name: blockName,
        logic: 'AND',
        signals: [{ name: signal.name, logic: 'AND' }],
      });
    },
    [addBlock]
  );

  const handleAddSimple = useCallback(
    (block: BlockDefinition) => {
      const strategy = useStrategyStore.getState().currentStrategy;
      const position = strategy?.blocks.length ?? 0;
      addBlock(block.type, position);
    },
    [addBlock]
  );

  const handleSavePreset = () => {
    const name = prompt('Preset name:');
    if (!name) return;
    const preset: FilterPreset = {
      name,
      searchText,
      category: selectedCategory,
      blockType: selectedType,
    };
    saveFilterPreset(preset);
    setPresets(loadAllFilterPresets());
  };

  const handleLoadPreset = (preset: FilterPreset) => {
    setSearchText(preset.searchText);
    setSelectedCategory(preset.category);
    setSelectedType(preset.blockType as BlockType | 'all');
  };

  const handleDeletePreset = (name: string) => {
    if (confirm(`Delete preset "${name}"?`)) {
      deleteFilterPreset(name);
      setPresets(loadAllFilterPresets());
    }
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800 flex-shrink-0">
        <h2 className="text-sm font-semibold text-zinc-50">Available Building Blocks</h2>
      </div>

      {/* Filters */}
      <div className="px-3 py-2 space-y-2 flex-shrink-0 border-b border-zinc-800">
        <InfoTooltip id="block-search-input">
          <input
            type="text"
            placeholder="Search blocks or signals…"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-cyan-500"
          />
        </InfoTooltip>

        <div className="flex gap-1">
          <InfoTooltip id="block-category-filter">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="flex-1 px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 focus:outline-none"
            >
              <option value="all">All Categories</option>
              {blockCategories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </InfoTooltip>

          <InfoTooltip id="block-type-filter">
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value as BlockType | 'all')}
              className="flex-1 px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 focus:outline-none"
            >
              <option value="all">All Types</option>
              {Object.entries(BLOCK_TYPE_LABELS).map(([type, label]) => (
                <option key={type} value={type}>
                  {label}
                </option>
              ))}
            </select>
          </InfoTooltip>
        </div>

        <div className="flex gap-1">
          <button
            onClick={handleSavePreset}
            className="flex-1 px-2 py-1 rounded bg-zinc-700 hover:bg-zinc-600 text-xs text-zinc-100 transition-colors"
            title="Save current filters as preset"
          >
            💾 Save
          </button>
          <div className="relative flex-1">
            {presets.length > 0 ? (
              <select
                onChange={(e) => {
                  const preset = presets.find((p) => p.name === e.target.value);
                  if (preset) handleLoadPreset(preset);
                }}
                defaultValue=""
                className="w-full px-2 py-1 rounded bg-zinc-700 hover:bg-zinc-600 text-xs text-zinc-100 focus:outline-none cursor-pointer"
              >
                <option value="">📂 Load</option>
                {presets.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
            ) : (
              <button
                disabled
                className="w-full px-2 py-1 rounded bg-zinc-700 text-xs text-zinc-600 cursor-not-allowed"
              >
                📂 Load
              </button>
            )}
          </div>
          {presets.length > 0 && (
            <button
              onClick={() => {
                const name = prompt('Delete preset:');
                if (name && presets.find((p) => p.name === name)) {
                  handleDeletePreset(name);
                }
              }}
              className="flex-1 px-2 py-1 rounded bg-red-900 hover:bg-red-800 text-xs text-red-100 transition-colors"
              title="Delete a saved preset"
            >
              🗑 Del
            </button>
          )}
        </div>
      </div>

      {/* Block List */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {isLoadingLibrary ? (
          <p className="text-xs text-zinc-500 text-center py-4">Loading…</p>
        ) : filteredBlocks.length === 0 ? (
          <p className="text-xs text-zinc-500 text-center py-4">No blocks match filters</p>
        ) : (
          filteredBlocks.map((block) => (
            <BlockCard
              key={block.id}
              block={block}
              onAddSignals={handleAddSignals}
              onAddExit={handleAddExit}
              onAddSimple={handleAddSimple}
              strategyBlocks={currentStrategy?.blocks ?? []}
            />
          ))
        )}
      </div>

      {/* Footer count */}
      <div className="px-3 py-2 border-t border-zinc-800 flex-shrink-0">
        <p className="text-xs text-zinc-500">
          {filteredBlocks.length} / {blockLibrary.length} blocks
        </p>
      </div>
    </div>
  );
}

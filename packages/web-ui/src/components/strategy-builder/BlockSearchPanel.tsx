'use client';

import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { BlockDefinition, BlockType } from '@/lib/strategy-builder/types';
import { ExitConditionDialog, ExitConditionConfig, AvailableBlock } from './ExitConditionDialog';

const BLOCK_TYPE_LABELS: Record<string, string> = {
  [BlockType.ENTRY_CONDITION]:  'Entry Condition',
  [BlockType.EXIT_CONDITION]:   'Exit Condition',
  [BlockType.RISK_MANAGEMENT]:  'Risk Management',
  [BlockType.TIME_CONSTRAINT]:  'Time Constraint',
  [BlockType.FILTER]:           'Filter',
  [BlockType.INDICATOR]:        'Indicator',
  [BlockType.POSITION_SIZING]:  'Position Sizing',
};

// ui_visible=false signals are hidden in Standard mode (matches desktop app behaviour).
// Advanced mode shows all signals including ui_visible=false for debugging/exploration.

// Convert WAVE_1_BULLISH → Wave 1 Bullish
function formatSignalName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

interface FilterPreset {
  name: string;
  search: string;
  category: string;
  type: string;
}

const PRESETS_KEY = 'sb_filter_presets';

function loadPresets(): FilterPreset[] {
  try {
    return JSON.parse(localStorage.getItem(PRESETS_KEY) ?? '[]') as FilterPreset[];
  } catch {
    return [];
  }
}

function savePresets(presets: FilterPreset[]) {
  localStorage.setItem(PRESETS_KEY, JSON.stringify(presets));
}

// ─────────────────────────────────────────────
// SavePresetModal
// ─────────────────────────────────────────────
interface SavePresetModalProps {
  open: boolean;
  onSave: (name: string) => void;
  onCancel: () => void;
}

function SavePresetModal({ open, onSave, onCancel }: SavePresetModalProps) {
  const [value, setValue] = useState('');
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg shadow-2xl border p-5 w-80" style={{ background: '#1E2128', borderColor: '#3C4149' }}>
        <h3 className="text-sm font-semibold mb-3" style={{ color: '#A0AEC0' }}>Save Filter Preset</h3>
        <input
          autoFocus
          type="text"
          placeholder="Preset name…"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && value.trim()) onSave(value.trim()); if (e.key === 'Escape') onCancel(); }}
          className="w-full px-2.5 py-1.5 rounded border text-sm focus:outline-none mb-4"
          style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#E8EAED' }}
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="text-xs px-3 py-1.5 rounded border transition-colors"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#9AA0A6' }}
          >
            Cancel
          </button>
          <button
            onClick={() => { if (value.trim()) onSave(value.trim()); }}
            disabled={!value.trim()}
            className="text-xs px-3 py-1.5 rounded border transition-colors disabled:opacity-40"
            style={{ background: '#1a3a4a', borderColor: '#0ea5e9', color: '#38bdf8' }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// BlockItem
// ─────────────────────────────────────────────
interface BlockItemProps {
  definition: BlockDefinition;
  onAdd: (def: BlockDefinition, logic: 'AND' | 'OR', selectedSignals: string[]) => void;
  onAddExit: (def: BlockDefinition, selectedSignals: string[]) => void;
  advancedMode: boolean;
  isHighlighted?: boolean;
  onHighlightCleared?: () => void;
}

function BlockItem({ definition, onAdd, onAddExit, advancedMode, isHighlighted, onHighlightCleared }: BlockItemProps) {
  const itemRef = useRef<HTMLDivElement>(null);
  const [signalsOpen, setSignalsOpen] = useState(false);
  const [checkedSignals, setCheckedSignals] = useState<Set<string>>(new Set());
  const [addedSignals, setAddedSignals] = useState<Set<string>>(new Set());

  const signals = definition.signals ?? [];
  const visibleSignals = signals.filter(s => s.ui_visible !== false);

  // Auto-expand and scroll into view when highlighted from the strategy panel
  useEffect(() => {
    if (!isHighlighted) return;
    setSignalsOpen(true);
    setTimeout(() => {
      itemRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
    const t = setTimeout(() => onHighlightCleared?.(), 3500);
    return () => clearTimeout(t);
  }, [isHighlighted]); // eslint-disable-line react-hooks/exhaustive-deps
  const ext = definition as unknown as Record<string, unknown>;
  const weight = ext.weight as number | undefined;
  const typeLabel = BLOCK_TYPE_LABELS[definition.type] ?? (definition.type as string).replace('_', ' ').toUpperCase();

  const toggleSignal = (name: string) => {
    setCheckedSignals(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const handleAdd = (logic: 'AND' | 'OR') => {
    const selected = checkedSignals.size > 0 ? [...checkedSignals] : visibleSignals.map(s => s.name);
    if (!advancedMode) {
      setAddedSignals(prev => {
        const next = new Set(prev);
        selected.forEach(s => next.add(s));
        return next;
      });
    }
    setCheckedSignals(new Set());
    onAdd(definition, logic, selected);
  };

  const handleAddExit = () => {
    const selected = checkedSignals.size > 0 ? [...checkedSignals] : visibleSignals.map(s => s.name);
    if (!advancedMode) {
      setAddedSignals(prev => {
        const next = new Set(prev);
        selected.forEach(s => next.add(s));
        return next;
      });
    }
    setCheckedSignals(new Set());
    onAddExit(definition, selected);
  };

  return (
    <div
      ref={itemRef}
      className="rounded border mb-1.5 transition-all duration-300"
      style={{
        background: isHighlighted ? 'rgba(14,165,233,0.07)' : '#1E2128',
        borderColor: isHighlighted ? '#0ea5e9' : '#3C4149',
        boxShadow: isHighlighted ? '0 0 0 2px rgba(14,165,233,0.25)' : undefined,
      }}
    >
      {/* Block name + meta */}
      <div className="px-3 pt-2.5 pb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-semibold leading-tight" style={{ color: '#A0AEC0' }}>{definition.name}</span>
        </div>
        <div className="text-xs mt-0.5 ml-6" style={{ color: '#9AA0A6' }}>
          Category: {definition.category}
          {typeLabel && ` | Type: ${typeLabel}`}
          {weight != null && ` | Weight: ${weight} points`}
        </div>
      </div>

      {/* Full-width expand/collapse button (below meta, matches desktop) */}
      {visibleSignals.length > 0 && (
        <button
          onClick={() => setSignalsOpen(v => !v)}
          className="w-full px-5 py-2.5 text-left text-sm font-bold bg-[#2D3748] border-t border-[#374151] hover:bg-[#374151] hover:border-sky-400 transition-colors"
          style={{ color: '#A0AEC0' }}
        >
          {signalsOpen ? `▼ Hide Signals (${visibleSignals.length})` : `▶ Show Signals (${visibleSignals.length})`}
        </button>
      )}

      {/* Expanded: signals list + add buttons */}
      {signalsOpen && visibleSignals.length > 0 && (
        <div className="px-3 pb-2 bg-[#15191E]">
          {/* Header */}
          <p className="text-xs font-semibold text-sky-400 pt-2 pb-1">Select signals to add:</p>

          {/* Signal list with checkboxes */}
          <div className="space-y-2">
            {visibleSignals.map((sig, i) => {
              const isAdded = !advancedMode && addedSignals.has(sig.name);
              const isChecked = checkedSignals.has(sig.name);
              return (
                <div key={i} className={`pl-1 ${isAdded ? 'opacity-50' : ''}`}>
                  <label className={`flex items-start gap-2 ${isAdded ? 'cursor-default' : 'cursor-pointer'}`}>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      disabled={isAdded}
                      onChange={() => !isAdded && toggleSignal(sig.name)}
                      className="mt-0.5 flex-shrink-0 appearance-none w-3.5 h-3.5 rounded-sm border border-[#5A6070] cursor-pointer disabled:opacity-50"
                      style={isChecked ? {
                        background: '#0ea5e9',
                        borderColor: '#0ea5e9',
                        backgroundImage: "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='white'%3e%3cpath d='M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z'/%3e%3c/svg%3e\")",
                        backgroundSize: '100% 100%',
                      } : { background: 'transparent' }}
                    />
                    <div className="min-w-0">
                      <span
                        className={`text-xs font-semibold ${isAdded ? 'line-through' : ''}`}
                        style={{ color: isAdded ? '#6B7280' : '#9AA0A6' }}
                      >
                        {formatSignalName(sig.name)}
                      </span>
                      {sig.occurrences != null && (
                        <span className="font-normal text-xs ml-1.5" style={{ color: '#6B7280' }}>
                          ({sig.occurrences.toLocaleString()} found, {sig.occurrence_percentage != null ? sig.occurrence_percentage.toFixed(1) : '?'}%)
                        </span>
                      )}
                      {sig.description ? (
                        <div className="text-xs mt-0.5 italic leading-relaxed" style={{ color: '#9AA0A6' }}>{sig.description}</div>
                      ) : null}
                    </div>
                  </label>
                </div>
              );
            })}
          </div>

          {/* Add buttons */}
          <div className="flex gap-1.5 mt-3">
            <button
              onClick={() => handleAdd('AND')}
              className="flex-1 text-xs py-1.5 rounded border border-emerald-800 bg-emerald-900/40 hover:bg-emerald-900/70 text-emerald-300 font-medium transition-colors"
              title={`Add "${definition.name}" as required (AND)`}
            >
              ➕ Add as AND (Required)
            </button>
            <button
              onClick={() => handleAdd('OR')}
              className="flex-1 text-xs py-1.5 rounded border border-blue-800 bg-blue-900/30 hover:bg-blue-900/60 text-blue-300 font-medium transition-colors"
              title={`Add "${definition.name}" as optional (OR)`}
            >
              ➕ Add as OR (Optional)
            </button>
            <button
              onClick={handleAddExit}
              className="flex-1 text-xs py-1.5 rounded border border-red-800 bg-red-900/30 hover:bg-red-900/60 text-red-300 font-medium transition-colors"
              title={`Configure "${definition.name}" as exit condition`}
            >
              ➕ Add as Exit
            </button>
          </div>

          <p className="text-xs italic mt-2" style={{ color: '#6B7280' }}>
            Note: Signal counts based on last 180 days of BTC data
          </p>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// BlockSearchPanel (main export)
// ─────────────────────────────────────────────
export function BlockSearchPanel() {
  const {
    blockLibrary,
    blockCategories,
    isLoadingLibrary,
    addBlock,
    updateBlock,
    currentStrategy,
    highlightedLibraryBlockId,
    highlightLibraryBlock,
  } = useStrategyStore();

  const [searchText, setSearchText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedType, setSelectedType] = useState<BlockType | 'all'>('all');
  const [advancedMode, setAdvancedMode] = useState(false);

  // Exit condition dialog
  const [exitPending, setExitPending] = useState<{
    definition: BlockDefinition;
    selectedSignals: string[];
  } | null>(null);

  // When a block is highlighted from the strategy panel, clear filters so it's visible
  useEffect(() => {
    if (!highlightedLibraryBlockId) return;
    setSearchText('');
    setSelectedCategory('all');
    setSelectedType('all');
  }, [highlightedLibraryBlockId]);

  // Presets
  const [presets, setPresets] = useState<FilterPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState('');
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  useEffect(() => { setPresets(loadPresets()); }, []);

  const handleSavePreset = useCallback(() => {
    setSaveModalOpen(true);
  }, []);

  const handleConfirmSavePreset = useCallback((name: string) => {
    const preset: FilterPreset = { name, search: searchText, category: selectedCategory, type: selectedType };
    const updated = [...presets.filter(p => p.name !== preset.name), preset];
    savePresets(updated);
    setPresets(updated);
    setSelectedPreset(name);
    setSaveModalOpen(false);
  }, [searchText, selectedCategory, selectedType, presets]);

  const handleLoadPreset = useCallback(() => {
    const preset = presets.find(p => p.name === selectedPreset);
    if (!preset) return;
    setSearchText(preset.search);
    setSelectedCategory(preset.category);
    setSelectedType(preset.type as BlockType | 'all');
  }, [presets, selectedPreset]);

  const handleDeletePreset = useCallback(() => {
    if (!selectedPreset || !window.confirm(`Delete preset "${selectedPreset}"?`)) return;
    const updated = presets.filter(p => p.name !== selectedPreset);
    savePresets(updated);
    setPresets(updated);
    setSelectedPreset('');
  }, [presets, selectedPreset]);

  // Filtered blocks — flat, sorted by category then name
  const filteredBlocks = useMemo(() => {
    const q = searchText.toLowerCase();
    return blockLibrary
      .filter(b => {
        const matchSearch = !q ||
          b.name.toLowerCase().includes(q) ||
          b.description.toLowerCase().includes(q) ||
          (b.signals ?? []).some(s => s.name.toLowerCase().includes(q));
        const matchCat = selectedCategory === 'all' || b.category === selectedCategory;
        const matchType = selectedType === 'all' || b.type === selectedType;
        return matchSearch && matchCat && matchType;
      })
      .sort((a, b) => {
        if (a.category < b.category) return -1;
        if (a.category > b.category) return 1;
        return a.name.localeCompare(b.name);
      });
  }, [blockLibrary, searchText, selectedCategory, selectedType]);

  // All categories for dropdown — format SNAKE_CASE to Title Case for display
  const allCategories = useMemo(() => {
    if (blockCategories.length > 0) return blockCategories.map(c => ({ id: c.id, name: c.name }));
    const cats = new Set(blockLibrary.map(b => b.category));
    return [...cats].sort().map(c => ({
      id: c,
      name: c.replace(/_/g, ' ').replace(/\b\w/g, (ch: string) => ch.toUpperCase()),
    }));
  }, [blockCategories, blockLibrary]);

  // Show only types that actually exist in the library — matches desktop client
  // (hardcoding all 7 enum types shows empty results for most selections)
  const allTypes = useMemo(() => {
    const seen = new Set(blockLibrary.map(b => b.type));
    return [...seen].sort().map(t => ({
      value: t,
      label: BLOCK_TYPE_LABELS[t] ?? t.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
    }));
  }, [blockLibrary]);

  // Add block to strategy.
  // Standard mode: signals from the same block definition + logic are merged
  //   into the existing block card rather than creating a duplicate card.
  // Advanced mode: always creates a new separate block card (allows duplicates).
  const handleAdd = useCallback(
    (definition: BlockDefinition, logic: 'AND' | 'OR', selectedSignals: string[]) => {
      const state = useStrategyStore.getState();
      const allSignals = definition.signals ?? [];
      const signalsToAdd = selectedSignals.length > 0
        ? allSignals.filter(s => selectedSignals.includes(s.name))
        : allSignals;
      const newSignalData = signalsToAdd.map(s => ({
        name: s.name,
        description: s.description ?? '',
        recheckEnabled: false,
      }));

      if (!advancedMode) {
        const currentBlocks = state.currentStrategy?.blocks ?? [];
        const existingIdx = currentBlocks.findIndex(
          b =>
            (b.data as Record<string, unknown>).definitionId === definition.id &&
            (b.data as Record<string, unknown>).logic === logic
        );
        if (existingIdx >= 0) {
          const existingSignals =
            ((currentBlocks[existingIdx].data as Record<string, unknown>).signals as Array<Record<string, unknown>>) ?? [];
          updateBlock(existingIdx, { signals: [...existingSignals, ...newSignalData] });
          return;
        }
      }

      const position = state.currentStrategy?.blocks.length ?? 0;
      addBlock(definition.type, position);
      updateBlock(position, {
        name: definition.name,
        definitionId: definition.id,
        category: definition.category,
        logic,
        signals: newSignalData,
      });
    },
    [addBlock, updateBlock, advancedMode]
  );

  const handleAddExit = useCallback(
    (definition: BlockDefinition, selectedSignals: string[]) => {
      setExitPending({ definition, selectedSignals });
    },
    []
  );

  const handleExitSave = useCallback(
    (config: ExitConditionConfig) => {
      if (!exitPending) return;
      const { definition, selectedSignals } = exitPending;
      const state = useStrategyStore.getState();
      const allSignals = definition.signals ?? [];
      const signalsToAdd = selectedSignals.length > 0
        ? allSignals.filter(s => selectedSignals.includes(s.name))
        : allSignals;
      const newSignalData = signalsToAdd.map(s => ({
        name: s.name,
        description: s.description ?? '',
        recheckEnabled: false,
      }));

      const position = state.currentStrategy?.blocks.length ?? 0;
      addBlock(BlockType.EXIT_CONDITION, position);
      updateBlock(position, {
        name: definition.name,
        definitionId: definition.id,
        category: definition.category,
        logic: 'EXIT',
        signals: newSignalData,
        exitConfig: config,
      });
      setExitPending(null);
    },
    [exitPending, addBlock, updateBlock]
  );

  return (
    <div className="flex flex-col h-full border-l border-[#3C4149]" style={{ background: '#15191E' }}>
      {/* Panel header with Standard / Advanced toggle */}
      <div className="px-4 py-2 border-b border-[#3C4149] flex-shrink-0 flex items-center justify-between" style={{ background: '#1E2128' }}>
        <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#A0AEC0' }}>
          Available Building Blocks
        </h2>
        <div className="flex items-center" style={{ border: '1px solid #3C4149', borderRadius: 4, overflow: 'hidden' }}>
          <button
            onClick={() => setAdvancedMode(false)}
            title="Standard mode: each block can only be added once per signal"
            className="text-xs px-2.5 py-1 transition-colors"
            style={!advancedMode
              ? { background: '#1a3a4a', color: '#38bdf8', fontWeight: 600 }
              : { background: '#2A2F3A', color: '#6B7280' }}
          >
            Standard
          </button>
          <button
            onClick={() => setAdvancedMode(true)}
            title="Advanced mode: allows adding the same building block multiple times with different configurations"
            className="text-xs px-2.5 py-1 transition-colors border-l border-[#3C4149]"
            style={advancedMode
              ? { background: '#1a3a4a', color: '#38bdf8', fontWeight: 600 }
              : { background: '#2A2F3A', color: '#6B7280' }}
          >
            Advanced
          </button>
        </div>
      </div>

      {/* Search + Filters — 2 rows, labels fixed-width so inputs align */}
      <div className="px-3 pt-3 pb-2 space-y-1.5 flex-shrink-0 border-b border-[#3C4149]" style={{ background: '#1E2128' }}>
        {/* Row 1: Search */}
        <div className="flex items-center gap-2">
          <span className="text-xs flex-shrink-0 text-right" style={{ color: '#9AA0A6', width: 68 }}>🔍 Search:</span>
          <input
            type="text"
            placeholder="Search by block name, description, or signal…"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            className="flex-1 px-2.5 py-1.5 rounded border text-xs focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#E8EAED' }}
          />
        </div>

        {/* Row 2: Category + Type dropdowns — same label width so controls align with search input */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs flex-shrink-0 text-right" style={{ color: '#9AA0A6', width: 68 }}>🏷 Filter:</span>
          <select
            value={selectedCategory}
            onChange={e => setSelectedCategory(e.target.value)}
            title="Filter by category"
            className="flex-[2] min-w-0 px-1.5 py-1 rounded border text-xs focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#E8EAED' }}
          >
            <option value="all">All Categories</option>
            {allCategories.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <select
            value={selectedType}
            onChange={e => setSelectedType(e.target.value as BlockType | 'all')}
            title="Filter by block type"
            className="flex-[1.5] min-w-0 px-1.5 py-1 rounded border text-xs focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#E8EAED' }}
          >
            <option value="all">All Types</option>
            {allTypes.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <select
            value={selectedPreset}
            onChange={e => setSelectedPreset(e.target.value)}
            className="flex-1 min-w-0 px-1.5 py-1 rounded border text-xs focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#A0AEC0' }}
          >
            <option value="">— Preset —</option>
            {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
          </select>
          <button onClick={handleSavePreset} title="Save current filter as preset"
            className="text-xs px-1.5 py-1 rounded border flex-shrink-0 hover:opacity-80"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#A0AEC0' }}>💾</button>
          <button onClick={handleLoadPreset} disabled={!selectedPreset} title="Load selected preset"
            className="text-xs px-1.5 py-1 rounded border flex-shrink-0 disabled:opacity-40 hover:opacity-80"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#A0AEC0' }}>📂</button>
          <button onClick={handleDeletePreset} disabled={!selectedPreset} title="Delete selected preset"
            className="text-xs px-1.5 py-1 rounded border flex-shrink-0 disabled:opacity-40 hover:opacity-80"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#A0AEC0' }}>🗑</button>
        </div>
      </div>

      {/* Block list — flat, sorted */}
      <div className="flex-1 overflow-y-auto px-3 py-3" style={{ background: '#15191E', scrollbarWidth: 'thin', scrollbarColor: '#3C4149 transparent' }}>
        {isLoadingLibrary ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2">
            <div className="w-6 h-6 border-2 border-zinc-600 border-t-sky-400 rounded-full animate-spin" />
            <p className="text-xs" style={{ color: '#9AA0A6' }}>Loading block library…</p>
          </div>
        ) : filteredBlocks.length === 0 ? (
          <p className="text-xs text-center py-8" style={{ color: '#9AA0A6' }}>No blocks match the current filters</p>
        ) : (
          filteredBlocks.map(block => (
            <BlockItem
              key={block.id}
              definition={block}
              onAdd={handleAdd}
              onAddExit={handleAddExit}
              advancedMode={advancedMode}
              isHighlighted={highlightedLibraryBlockId === block.id}
              onHighlightCleared={() => highlightLibraryBlock(null)}
            />
          ))
        )}
      </div>

      {/* Footer count */}
      <div className="px-3 py-2 border-t border-[#3C4149] flex-shrink-0 flex items-center justify-between" style={{ background: '#1E2128' }}>
        <p className="text-xs" style={{ color: '#9AA0A6' }}>
          {filteredBlocks.length} / {blockLibrary.length} blocks
        </p>
        {currentStrategy && (
          <p className="text-xs" style={{ color: '#6B7280' }}>
            {currentStrategy.blocks.length} in strategy
          </p>
        )}
      </div>

      <SavePresetModal
        open={saveModalOpen}
        onSave={handleConfirmSavePreset}
        onCancel={() => setSaveModalOpen(false)}
      />

      {exitPending && (() => {
        const stratBlocks = currentStrategy?.blocks ?? [];
        const availableBlocks: AvailableBlock[] = stratBlocks
          .filter(b => b.type !== BlockType.EXIT_CONDITION && (b.data as Record<string, unknown>).logic !== 'EXIT')
          .map(b => ({
            id: b.id,
            name: (b.data as Record<string, unknown>).name as string ?? b.id,
            signals: ((b.data as Record<string, unknown>).signals as Array<{ name: string }> | undefined ?? []).map(s => s.name),
          }));
        const signalName = exitPending.selectedSignals.length === 1
          ? exitPending.selectedSignals[0]
          : exitPending.definition.name;
        return (
          <ExitConditionDialog
            open={true}
            signalName={signalName}
            availableBlocks={availableBlocks}
            onSave={handleExitSave}
            onCancel={() => setExitPending(null)}
          />
        );
      })()}
    </div>
  );
}

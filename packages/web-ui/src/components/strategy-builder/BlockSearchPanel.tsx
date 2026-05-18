'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { BlockDefinition, BlockType } from '@/lib/strategy-builder/types';

const BLOCK_TYPE_LABELS: Record<BlockType, string> = {
  [BlockType.ENTRY_CONDITION]:  'ENTRY',
  [BlockType.EXIT_CONDITION]:   'EXIT',
  [BlockType.RISK_MANAGEMENT]:  'RISK',
  [BlockType.TIME_CONSTRAINT]:  'TIME',
  [BlockType.FILTER]:           'FILTER',
  [BlockType.INDICATOR]:        'IND',
  [BlockType.POSITION_SIZING]:  'SIZE',
};

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
// BlockItem
// ─────────────────────────────────────────────
interface BlockItemProps {
  definition: BlockDefinition;
  onAdd: (def: BlockDefinition, logic: 'AND' | 'OR' | 'EXIT', selectedSignals: string[]) => void;
}

function BlockItem({ definition, onAdd }: BlockItemProps) {
  const [signalsOpen, setSignalsOpen] = useState(false);
  const [checkedSignals, setCheckedSignals] = useState<Set<string>>(new Set());
  const [addedSignals, setAddedSignals] = useState<Set<string>>(new Set());

  const signals = definition.signals ?? [];
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

  const handleAdd = (logic: 'AND' | 'OR' | 'EXIT') => {
    const selected = checkedSignals.size > 0 ? [...checkedSignals] : signals.map(s => s.name);
    // Mark selected signals as added
    setAddedSignals(prev => {
      const next = new Set(prev);
      selected.forEach(s => next.add(s));
      return next;
    });
    setCheckedSignals(new Set());
    onAdd(definition, logic, selected);
  };

  return (
    <div className="rounded border border-[#3C4149] bg-[#1E2128] mb-1.5">
      {/* Block name + meta */}
      <div className="px-3 pt-2.5 pb-1.5">
        <div className="flex items-center gap-1.5">
          {/* text_primary: #E8EAED — slightly off-white like desktop, not harsh pure-white */}
          <span className="text-sm font-semibold leading-tight" style={{ color: '#E8EAED' }}>{definition.name}</span>
        </div>
        {/* text_label: #A0AEC0 */}
        <div className="text-xs mt-0.5 ml-6" style={{ color: '#A0AEC0' }}>
          Category: {definition.category}
          {typeLabel && ` | Type: ${typeLabel}`}
          {weight != null && ` | Weight: ${weight} points`}
        </div>
      </div>

      {/* Full-width expand/collapse button (below meta, matches desktop) */}
      {signals.length > 0 && (
        <button
          onClick={() => setSignalsOpen(v => !v)}
          className="w-full px-5 py-2.5 text-left text-sm font-bold bg-[#2D3748] border-t border-[#374151] hover:bg-[#374151] hover:border-sky-400 transition-colors"
          style={{ color: '#A0AEC0' }}
        >
          {signalsOpen ? `▼ Hide Signals (${signals.length})` : `▶ Show Signals (${signals.length})`}
        </button>
      )}

      {/* Expanded: signals list + add buttons */}
      {signalsOpen && signals.length > 0 && (
        <div className="px-3 pb-2 bg-[#15191E]">
          {/* Header — text_primary cyan from desktop */}
          <p className="text-xs font-semibold text-sky-400 pt-2 pb-1">Select signals to add:</p>

          {/* Signal list with checkboxes */}
          <div className="space-y-2">
            {signals.map((sig, i) => {
              const isAdded = addedSignals.has(sig.name);
              const isChecked = checkedSignals.has(sig.name);
              return (
                <div key={i} className={`pl-1 ${isAdded ? 'opacity-50' : ''}`}>
                  <label className={`flex items-start gap-2 ${isAdded ? 'cursor-default' : 'cursor-pointer'}`}>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      disabled={isAdded}
                      onChange={() => !isAdded && toggleSignal(sig.name)}
                      className="mt-0.5 flex-shrink-0 accent-sky-400 w-3.5 h-3.5"
                    />
                    <div className="min-w-0">
                      {/* text_muted: #9AA0A6 for signal names, strikethrough when added */}
                      <span
                        className={`text-xs font-semibold ${isAdded ? 'line-through' : ''}`}
                        style={{ color: isAdded ? '#6B7280' : '#9AA0A6' }}
                      >
                        {sig.name}
                      </span>
                      {sig.occurrences != null && (
                        <span className="font-normal text-xs ml-1.5" style={{ color: '#6B7280' }}>
                          ({sig.occurrences.toLocaleString()} found, {sig.occurrence_percentage != null ? sig.occurrence_percentage.toFixed(1) : '?'}%)
                        </span>
                      )}
                      {/* Description always rendered when present — text_label #A0AEC0 italic */}
                      {sig.description ? (
                        <div className="text-xs mt-0.5 italic leading-relaxed" style={{ color: '#A0AEC0' }}>{sig.description}</div>
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
              onClick={() => handleAdd('EXIT')}
              className="flex-1 text-xs py-1.5 rounded border border-red-800 bg-red-900/30 hover:bg-red-900/60 text-red-300 font-medium transition-colors"
              title={`Add "${definition.name}" as exit condition`}
            >
              ➕ Add as Exit
            </button>
          </div>

          {/* Data note */}
          <p className="text-xs text-zinc-600 italic mt-2">
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
  } = useStrategyStore();

  const [searchText, setSearchText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedType, setSelectedType] = useState<BlockType | 'all'>('all');

  // Presets
  const [presets, setPresets] = useState<FilterPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState('');
  useEffect(() => { setPresets(loadPresets()); }, []);

  const handleSavePreset = useCallback(() => {
    const name = window.prompt('Save preset as:', '');
    if (!name?.trim()) return;
    const preset: FilterPreset = { name: name.trim(), search: searchText, category: selectedCategory, type: selectedType };
    const updated = [...presets.filter(p => p.name !== preset.name), preset];
    savePresets(updated);
    setPresets(updated);
    setSelectedPreset(preset.name);
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

  // All categories for dropdown
  const allCategories = useMemo(() => {
    if (blockCategories.length > 0) return blockCategories.map(c => ({ id: c.id, name: c.name }));
    const cats = new Set(blockLibrary.map(b => b.category));
    return [...cats].sort().map(c => ({ id: c, name: c }));
  }, [blockCategories, blockLibrary]);

  // Add block to strategy
  const handleAdd = useCallback(
    (definition: BlockDefinition, logic: 'AND' | 'OR' | 'EXIT', selectedSignals: string[]) => {
      const state = useStrategyStore.getState();
      const position = state.currentStrategy?.blocks.length ?? 0;
      const blockType = logic === 'EXIT' ? BlockType.EXIT_CONDITION : definition.type;
      addBlock(blockType, position);
      const allSignals = definition.signals ?? [];
      const signalsToAdd = selectedSignals.length > 0
        ? allSignals.filter(s => selectedSignals.includes(s.name))
        : allSignals;
      updateBlock(position, {
        name: definition.name,
        definitionId: definition.id,
        category: definition.category,
        logic: logic,
        signals: signalsToAdd.map(s => ({
          name: s.name,
          description: s.description ?? '',
          recheckEnabled: false,
        })),
      });
    },
    [addBlock, updateBlock]
  );

  return (
    <div className="flex flex-col h-full border-l border-[#3C4149]" style={{ background: '#15191E' }}>
      {/* Panel header */}
      <div className="px-4 py-2.5 border-b border-[#3C4149] flex-shrink-0" style={{ background: '#1E2128' }}>
        <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#A0AEC0' }}>
          Available Building Blocks
        </h2>
      </div>

      {/* Search + Filters — 2 rows */}
      <div className="px-3 pt-3 pb-2 space-y-2 flex-shrink-0 border-b border-[#3C4149]" style={{ background: '#1E2128' }}>
        {/* Row 1: Search */}
        <div className="flex items-center gap-2">
          <span className="text-xs flex-shrink-0" style={{ color: '#9AA0A6' }}>🔍 Search:</span>
          <input
            type="text"
            placeholder="Search by block name, description, or signal…"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            className="flex-1 px-2.5 py-1.5 rounded border text-sm focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#E8EAED' }}
          />
        </div>

        {/* Row 2: Category, Type, Preset buttons */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <label className="text-xs flex-shrink-0" style={{ color: '#9AA0A6' }}>Category:</label>
          <select
            value={selectedCategory}
            onChange={e => setSelectedCategory(e.target.value)}
            className="flex-1 min-w-[100px] max-w-[140px] px-1.5 py-1 rounded border text-xs focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#E8EAED' }}
          >
            <option value="all">All Categories</option>
            {allCategories.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <label className="text-xs flex-shrink-0" style={{ color: '#9AA0A6' }}>Type:</label>
          <select
            value={selectedType}
            onChange={e => setSelectedType(e.target.value as BlockType | 'all')}
            className="flex-1 min-w-[80px] max-w-[120px] px-1.5 py-1 rounded border text-xs focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#E8EAED' }}
          >
            <option value="all">All Types</option>
            {Object.entries(BLOCK_TYPE_LABELS).map(([type, label]) => (
              <option key={type} value={type}>{label}</option>
            ))}
          </select>
          <select
            value={selectedPreset}
            onChange={e => setSelectedPreset(e.target.value)}
            className="flex-1 min-w-[80px] max-w-[110px] px-1.5 py-1 rounded border text-xs focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#A0AEC0' }}
          >
            <option value="">— Preset —</option>
            {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
          </select>
          <button
            onClick={handleSavePreset}
            title="Save current filter as preset"
            className="text-xs px-2 py-1 rounded border transition-colors whitespace-nowrap hover:opacity-80"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#A0AEC0' }}
          >
            □ Save
          </button>
          <button
            onClick={handleLoadPreset}
            disabled={!selectedPreset}
            title="Load selected preset"
            className="text-xs px-2 py-1 rounded border transition-colors whitespace-nowrap disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-80"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#A0AEC0' }}
          >
            □ Load
          </button>
          <button
            onClick={handleDeletePreset}
            disabled={!selectedPreset}
            title="Delete selected preset"
            className="text-xs px-2 py-1 rounded border transition-colors whitespace-nowrap disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-80"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#A0AEC0' }}
          >
            🗑
          </button>
        </div>
      </div>

      {/* Block list — flat, sorted */}
      <div className="flex-1 overflow-y-auto px-3 py-3" style={{ background: '#15191E' }}>
        {isLoadingLibrary ? (
          <div className="flex flex-col items-center justify-center py-10 gap-2">
            <div className="w-6 h-6 border-2 border-zinc-600 border-t-sky-400 rounded-full animate-spin" />
            <p className="text-xs" style={{ color: '#9AA0A6' }}>Loading block library…</p>
          </div>
        ) : filteredBlocks.length === 0 ? (
          <p className="text-xs text-center py-8" style={{ color: '#9AA0A6' }}>No blocks match the current filters</p>
        ) : (
          filteredBlocks.map(block => (
            <BlockItem key={block.id} definition={block} onAdd={handleAdd} />
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
    </div>
  );
}

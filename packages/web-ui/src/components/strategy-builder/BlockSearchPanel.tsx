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

const TYPE_BADGE: Record<BlockType, string> = {
  [BlockType.ENTRY_CONDITION]:  'text-emerald-400 bg-emerald-950 border-emerald-800',
  [BlockType.EXIT_CONDITION]:   'text-red-400 bg-red-950 border-red-800',
  [BlockType.RISK_MANAGEMENT]:  'text-amber-400 bg-amber-950 border-amber-800',
  [BlockType.TIME_CONSTRAINT]:  'text-blue-400 bg-blue-950 border-blue-800',
  [BlockType.FILTER]:           'text-purple-400 bg-purple-950 border-purple-800',
  [BlockType.INDICATOR]:        'text-cyan-400 bg-cyan-950 border-cyan-800',
  [BlockType.POSITION_SIZING]:  'text-orange-400 bg-orange-950 border-orange-800',
};

// ─────────────────────────────────────────────
// Preset management (localStorage)
// ─────────────────────────────────────────────
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
  onAdd: (def: BlockDefinition, logic: 'AND' | 'OR' | 'EXIT') => void;
}

function BlockItem({ definition, onAdd }: BlockItemProps) {
  const [signalsOpen, setSignalsOpen] = useState(false);
  const signals = definition.signals ?? [];
  const typeBadge = TYPE_BADGE[definition.type] ?? 'text-zinc-400 bg-zinc-800 border-zinc-700';
  const typeLabel = BLOCK_TYPE_LABELS[definition.type] ?? definition.type;

  return (
    <div className="rounded border border-zinc-800 bg-zinc-900 mb-2">
      {/* Block header */}
      <div className="px-3 py-2 flex items-start gap-2">
        {/* Type badge */}
        <span className={`text-xs px-1.5 py-0.5 rounded border font-mono flex-shrink-0 mt-0.5 ${typeBadge}`}>
          {typeLabel}
        </span>
        {/* Name + meta */}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-zinc-100 leading-tight">{definition.name}</div>
          <div className="text-xs text-zinc-500 mt-0.5 truncate">
            {definition.category}
            {(definition as Record<string, unknown>).defaultWeight != null && (
              <span className="ml-1">· {String((definition as Record<string, unknown>).defaultWeight)} pts</span>
            )}
          </div>
        </div>
        {/* Show/Hide signals */}
        {signals.length > 0 && (
          <button
            onClick={() => setSignalsOpen(v => !v)}
            className="flex-shrink-0 text-xs px-2 py-0.5 rounded border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors whitespace-nowrap"
          >
            {signalsOpen ? `Hide Signals (${signals.length})` : `Show Signals (${signals.length})`}
          </button>
        )}
      </div>

      {/* Signals */}
      {signalsOpen && signals.length > 0 && (
        <div className="px-3 pb-2 space-y-1">
          {signals.map((sig, i) => (
            <div key={i} className="text-xs text-zinc-400 pl-2 border-l border-zinc-700 py-0.5">
              <div className="text-zinc-300">{sig.name}</div>
              {sig.description && (
                <div className="text-zinc-600 italic mt-0.5">{sig.description}</div>
              )}
              {sig.occurrences != null && (
                <div className="text-zinc-600 mt-0.5">
                  {sig.occurrences.toLocaleString()} occurrences
                  {sig.occurrence_percentage != null && ` (${sig.occurrence_percentage.toFixed(1)}%)`}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add buttons */}
      <div className="flex gap-1.5 px-3 pb-3 pt-1">
        <button
          onClick={() => onAdd(definition, 'AND')}
          className="flex-1 text-xs py-1 rounded border border-emerald-800 bg-emerald-900/30 hover:bg-emerald-900/60 text-emerald-300 transition-colors"
          title={`Add "${definition.name}" as a required (AND) block`}
        >
          + AND (Required)
        </button>
        <button
          onClick={() => onAdd(definition, 'OR')}
          className="flex-1 text-xs py-1 rounded border border-blue-800 bg-blue-900/30 hover:bg-blue-900/60 text-blue-300 transition-colors"
          title={`Add "${definition.name}" as an optional (OR) block`}
        >
          + OR (Optional)
        </button>
        <button
          onClick={() => onAdd(definition, 'EXIT')}
          className="flex-1 text-xs py-1 rounded border border-red-800 bg-red-900/30 hover:bg-red-900/60 text-red-300 transition-colors"
          title={`Add "${definition.name}" as an exit condition`}
        >
          + Exit
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// CategorySection
// ─────────────────────────────────────────────
interface CategorySectionProps {
  category: string;
  blocks: BlockDefinition[];
  onAdd: (def: BlockDefinition, logic: 'AND' | 'OR' | 'EXIT') => void;
}

function CategorySection({ category, blocks, onAdd }: CategorySectionProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="mb-2">
      <button
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-zinc-300 bg-zinc-800/60 hover:bg-zinc-800 rounded border border-zinc-700 transition-colors"
        onClick={() => setExpanded(v => !v)}
        aria-expanded={expanded}
      >
        <span className="flex items-center gap-1.5">
          <span>{expanded ? '▾' : '▸'}</span>
          <span>{category}</span>
        </span>
        <span className="text-zinc-500 font-normal">{blocks.length}</span>
      </button>
      {expanded && (
        <div className="mt-1 ml-1">
          {blocks.map(block => (
            <BlockItem key={block.id} definition={block} onAdd={onAdd} />
          ))}
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

  // Filtered blocks
  const filteredBlocks = useMemo(() => {
    const q = searchText.toLowerCase();
    return blockLibrary.filter(b => {
      const matchSearch = !q ||
        b.name.toLowerCase().includes(q) ||
        b.description.toLowerCase().includes(q) ||
        (b.signals ?? []).some(s => s.name.toLowerCase().includes(q));
      const matchCat = selectedCategory === 'all' || b.category === selectedCategory;
      const matchType = selectedType === 'all' || b.type === selectedType;
      return matchSearch && matchCat && matchType;
    });
  }, [blockLibrary, searchText, selectedCategory, selectedType]);

  // Group by category
  const grouped = useMemo(() => {
    const groups: Record<string, BlockDefinition[]> = {};
    for (const b of filteredBlocks) {
      if (!groups[b.category]) groups[b.category] = [];
      groups[b.category].push(b);
    }
    return groups;
  }, [filteredBlocks]);

  const categoryNames = useMemo(() => Object.keys(grouped).sort(), [grouped]);

  // All categories for dropdown (from library, not filtered)
  const allCategories = useMemo(() => {
    if (blockCategories.length > 0) return blockCategories.map(c => ({ id: c.id, name: c.name }));
    const cats = new Set(blockLibrary.map(b => b.category));
    return [...cats].sort().map(c => ({ id: c, name: c }));
  }, [blockCategories, blockLibrary]);

  // Add block to strategy
  const handleAdd = useCallback(
    (definition: BlockDefinition, logic: 'AND' | 'OR' | 'EXIT') => {
      const state = useStrategyStore.getState();
      const position = state.currentStrategy?.blocks.length ?? 0;
      const blockType = logic === 'EXIT' ? BlockType.EXIT_CONDITION : definition.type;
      addBlock(blockType, position);
      updateBlock(position, {
        name: definition.name,
        definitionId: definition.id,
        category: definition.category,
        logic: logic,
        signals: (definition.signals ?? []).map(s => ({
          name: s.name,
          description: s.description ?? '',
          recheckEnabled: false,
        })),
      });
    },
    [addBlock, updateBlock]
  );

  return (
    <div className="flex flex-col h-full bg-zinc-950 border-l border-zinc-800">
      {/* Panel header */}
      <div className="px-4 py-2.5 border-b border-zinc-800 bg-zinc-900/50 flex-shrink-0">
        <h2 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
          Available Building Blocks
        </h2>
      </div>

      {/* Search + Filters */}
      <div className="px-3 pt-3 pb-2 space-y-2 flex-shrink-0 border-b border-zinc-800">
        {/* Search input */}
        <input
          type="text"
          placeholder="Search by block name, description, or signal…"
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
          className="w-full px-2.5 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
        />

        {/* Category + Type row */}
        <div className="flex gap-2">
          <div className="flex-1 flex items-center gap-1.5">
            <label className="text-xs text-zinc-500 flex-shrink-0">Category:</label>
            <select
              value={selectedCategory}
              onChange={e => setSelectedCategory(e.target.value)}
              className="flex-1 min-w-0 px-2 py-1 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 focus:outline-none"
            >
              <option value="all">All Categories</option>
              {allCategories.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 flex items-center gap-1.5">
            <label className="text-xs text-zinc-500 flex-shrink-0">Type:</label>
            <select
              value={selectedType}
              onChange={e => setSelectedType(e.target.value as BlockType | 'all')}
              className="flex-1 min-w-0 px-2 py-1 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 focus:outline-none"
            >
              <option value="all">All Types</option>
              {Object.entries(BLOCK_TYPE_LABELS).map(([type, label]) => (
                <option key={type} value={type}>{label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Preset management row */}
        <div className="flex items-center gap-1.5">
          <select
            value={selectedPreset}
            onChange={e => setSelectedPreset(e.target.value)}
            className="flex-1 min-w-0 px-2 py-1 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-400 focus:outline-none"
          >
            <option value="">— Select preset —</option>
            {presets.map(p => (
              <option key={p.name} value={p.name}>{p.name}</option>
            ))}
          </select>
          <button
            onClick={handleSavePreset}
            title="Save current filter as preset"
            className="text-xs px-2 py-1 rounded border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors whitespace-nowrap"
          >
            Save
          </button>
          <button
            onClick={handleLoadPreset}
            disabled={!selectedPreset}
            title="Load selected preset"
            className="text-xs px-2 py-1 rounded border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
          >
            Load
          </button>
          <button
            onClick={handleDeletePreset}
            disabled={!selectedPreset}
            title="Delete selected preset"
            className="text-xs px-2 py-1 rounded border border-zinc-700 bg-zinc-800 hover:bg-red-900/40 hover:border-red-800 text-zinc-400 hover:text-red-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
          >
            Del
          </button>
        </div>
      </div>

      {/* Block list by category */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {isLoadingLibrary ? (
          <p className="text-xs text-zinc-500 text-center py-8">Loading block library…</p>
        ) : filteredBlocks.length === 0 ? (
          <p className="text-xs text-zinc-500 text-center py-8">No blocks match the current filters</p>
        ) : (
          categoryNames.map(cat => (
            <CategorySection
              key={cat}
              category={cat}
              blocks={grouped[cat]}
              onAdd={handleAdd}
            />
          ))
        )}
      </div>

      {/* Footer count */}
      <div className="px-3 py-2 border-t border-zinc-800 flex-shrink-0 flex items-center justify-between bg-zinc-900/40">
        <p className="text-xs text-zinc-500">
          {filteredBlocks.length} / {blockLibrary.length} blocks
        </p>
        {currentStrategy && (
          <p className="text-xs text-zinc-600">
            {currentStrategy.blocks.length} in strategy
          </p>
        )}
      </div>
    </div>
  );
}

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
  const ext = definition as unknown as Record<string, unknown>;
  const weight = ext.weight as number | undefined;
  const typeLabel = BLOCK_TYPE_LABELS[definition.type] ?? (definition.type as string).replace('_', ' ').toUpperCase();

  return (
    <div className="rounded border border-zinc-800 bg-zinc-900/80 mb-1.5">
      {/* Block header: icon + name + Show/Hide signals button */}
      <div className="px-3 pt-2.5 pb-1.5">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-zinc-500 text-sm flex-shrink-0">⬛</span>
            <span className="text-sm font-semibold text-zinc-100 leading-tight">{definition.name}</span>
          </div>
          {signals.length > 0 && (
            <button
              onClick={() => setSignalsOpen(v => !v)}
              className="flex-shrink-0 text-xs px-2 py-0.5 rounded border border-zinc-700 bg-zinc-800/80 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors whitespace-nowrap"
            >
              {signalsOpen ? `▼ Hide Signals (${signals.length})` : `▶ Show Signals (${signals.length})`}
            </button>
          )}
        </div>
        {/* Category | Type | Weight meta line */}
        <div className="text-xs text-zinc-500 mt-0.5 ml-5">
          Category: {definition.category}
          {typeLabel && ` | Type: ${typeLabel}`}
          {weight != null && ` | Weight: ${weight} points`}
        </div>
      </div>

      {/* Expanded: signals list + add buttons (only when signalsOpen) */}
      {signalsOpen && signals.length > 0 && (
        <div className="border-t border-zinc-800 px-3 pb-2">
          {/* Signal list */}
          <div className="pt-2 space-y-2">
            {signals.map((sig, i) => (
              <div key={i} className="text-xs pl-2 border-l border-zinc-700">
                <div className="text-zinc-300 font-medium">
                  {sig.name}
                  {sig.occurrences != null && (
                    <span className="text-zinc-500 font-normal ml-1.5">
                      ({sig.occurrences.toLocaleString()} found{sig.occurrence_percentage != null && `, ${sig.occurrence_percentage.toFixed(1)}%`})
                    </span>
                  )}
                </div>
                {sig.description && (
                  <div className="text-zinc-600 mt-0.5 leading-relaxed italic">{sig.description}</div>
                )}
              </div>
            ))}
          </div>

          {/* Add buttons — only visible when expanded */}
          <div className="flex gap-1.5 mt-3">
            <button
              onClick={() => onAdd(definition, 'AND')}
              className="flex-1 text-xs py-1 rounded border border-emerald-800 bg-emerald-900/30 hover:bg-emerald-900/60 text-emerald-300 transition-colors"
              title={`Add "${definition.name}" as required (AND)`}
            >
              + Add Required Signal
            </button>
            <button
              onClick={() => onAdd(definition, 'OR')}
              className="flex-1 text-xs py-1 rounded border border-blue-800 bg-blue-900/30 hover:bg-blue-900/60 text-blue-300 transition-colors"
              title={`Add "${definition.name}" as optional (OR)`}
            >
              + Add as OR (Optional)
            </button>
            <button
              onClick={() => onAdd(definition, 'EXIT')}
              className="flex-1 text-xs py-1 rounded border border-red-800 bg-red-900/30 hover:bg-red-900/60 text-red-300 transition-colors"
              title={`Add "${definition.name}" as exit condition`}
            >
              + Add as Exit
            </button>
          </div>
        </div>
      )}
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
        {/* Row 1 - Search only */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500 flex-shrink-0">🔍 Search:</span>
          <input
            type="text"
            placeholder="Search by block name, description, or signal…"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            className="flex-1 px-2.5 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
          />
        </div>

        {/* Row 2 - Category, Type, and Preset buttons all in one row */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <label className="text-xs text-zinc-500 flex-shrink-0">Category:</label>
          <select
            value={selectedCategory}
            onChange={e => setSelectedCategory(e.target.value)}
            className="flex-1 min-w-[100px] max-w-[140px] px-1.5 py-1 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 focus:outline-none"
          >
            <option value="all">All Categories</option>
            {allCategories.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <label className="text-xs text-zinc-500 flex-shrink-0">Type:</label>
          <select
            value={selectedType}
            onChange={e => setSelectedType(e.target.value as BlockType | 'all')}
            className="flex-1 min-w-[80px] max-w-[120px] px-1.5 py-1 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 focus:outline-none"
          >
            <option value="all">All Types</option>
            {Object.entries(BLOCK_TYPE_LABELS).map(([type, label]) => (
              <option key={type} value={type}>{label}</option>
            ))}
          </select>
          <select
            value={selectedPreset}
            onChange={e => setSelectedPreset(e.target.value)}
            className="flex-1 min-w-[80px] max-w-[110px] px-1.5 py-1 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-400 focus:outline-none"
          >
            <option value="">— Preset —</option>
            {presets.map(p => <option key={p.name} value={p.name}>{p.name}</option>)}
          </select>
          <button
            onClick={handleSavePreset}
            title="Save current filter as preset"
            className="text-xs px-2 py-1 rounded border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors whitespace-nowrap"
          >
            □ Save
          </button>
          <button
            onClick={handleLoadPreset}
            disabled={!selectedPreset}
            title="Load selected preset"
            className="text-xs px-2 py-1 rounded border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
          >
            □ Load
          </button>
          <button
            onClick={handleDeletePreset}
            disabled={!selectedPreset}
            title="Delete selected preset"
            className="text-xs px-2 py-1 rounded border border-zinc-700 bg-zinc-800 hover:bg-red-900/40 hover:border-red-800 text-zinc-400 hover:text-red-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
          >
            🗑
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

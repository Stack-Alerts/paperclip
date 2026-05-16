'use client';

import { useState, useMemo, useCallback } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { BlockDefinition, BlockType } from '@/lib/strategy-builder/types';
import { InfoTooltip } from './InfoTooltip';

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

interface BlockCardProps {
  block: BlockDefinition;
  onAdd: (block: BlockDefinition) => void;
}

function BlockCard({ block, onAdd }: BlockCardProps) {
  const [expanded, setExpanded] = useState(false);
  const typeColor = TYPE_COLORS[block.type] ?? 'text-zinc-400 bg-zinc-800 border-zinc-700';
  const typeLabel = BLOCK_TYPE_LABELS[block.type] ?? block.type;

  return (
    <div className="rounded border border-zinc-800 bg-zinc-900 mb-2">
      <button
        className="w-full text-left px-3 py-2 flex items-start gap-2"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <span className={`text-xs px-1.5 py-0.5 rounded border font-mono flex-shrink-0 mt-0.5 ${typeColor}`}>
          {typeLabel}
        </span>
        <span className="flex-1 text-sm font-medium text-zinc-100 leading-tight">
          {block.name}
        </span>
        <span className="text-zinc-500 text-xs flex-shrink-0">{expanded ? '▴' : '▾'}</span>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          <p className="text-xs text-zinc-400 leading-relaxed">{block.description}</p>
          <InfoTooltip id={`add-block-${block.id}`}>
            <button
              className="w-full py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition-colors"
              onClick={() => onAdd(block)}
            >
              + Add to Strategy
            </button>
          </InfoTooltip>
        </div>
      )}
    </div>
  );
}

export function BlockSearchPanel() {
  const { blockLibrary, blockCategories, isLoadingLibrary, addBlock } = useStrategyStore();

  const [searchText, setSearchText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedType, setSelectedType] = useState<BlockType | 'all'>('all');

  const filteredBlocks = useMemo(() => {
    return blockLibrary.filter((b) => {
      const matchesSearch =
        !searchText ||
        b.name.toLowerCase().includes(searchText.toLowerCase()) ||
        b.description.toLowerCase().includes(searchText.toLowerCase());
      const matchesCategory = selectedCategory === 'all' || b.category === selectedCategory;
      const matchesType = selectedType === 'all' || b.type === selectedType;
      return matchesSearch && matchesCategory && matchesType;
    });
  }, [blockLibrary, searchText, selectedCategory, selectedType]);

  const handleAdd = useCallback(
    (block: BlockDefinition) => {
      const strategy = useStrategyStore.getState().currentStrategy;
      const position = strategy?.blocks.length ?? 0;
      addBlock(block.type, position);
    },
    [addBlock],
  );

  return (
    <div className="flex flex-col h-full border-r border-zinc-800 bg-zinc-950">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800 flex-shrink-0">
        <h2 className="text-sm font-semibold text-zinc-50">Block Library</h2>
      </div>

      {/* Filters */}
      <div className="px-3 py-2 space-y-2 flex-shrink-0 border-b border-zinc-800">
        <InfoTooltip id="block-search-input">
          <input
            type="text"
            placeholder="Search blocks…"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
          />
        </InfoTooltip>

        <InfoTooltip id="block-category-filter">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 focus:outline-none"
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
            className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 focus:outline-none"
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

      {/* Block List */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        {isLoadingLibrary ? (
          <p className="text-xs text-zinc-500 text-center py-4">Loading…</p>
        ) : filteredBlocks.length === 0 ? (
          <p className="text-xs text-zinc-500 text-center py-4">No blocks match filters</p>
        ) : (
          filteredBlocks.map((block) => (
            <BlockCard key={block.id} block={block} onAdd={handleAdd} />
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

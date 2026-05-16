'use client';

import { useCallback } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block, BlockType } from '@/lib/strategy-builder/types';
import { InfoTooltip } from './InfoTooltip';

const BLOCK_TYPE_LABELS: Record<BlockType, string> = {
  [BlockType.ENTRY_CONDITION]: 'Entry Condition',
  [BlockType.EXIT_CONDITION]: 'Exit Condition',
  [BlockType.RISK_MANAGEMENT]: 'Risk Management',
  [BlockType.TIME_CONSTRAINT]: 'Time Constraint',
  [BlockType.FILTER]: 'Filter',
  [BlockType.INDICATOR]: 'Indicator',
  [BlockType.POSITION_SIZING]: 'Position Sizing',
};

const TYPE_ACCENT: Record<BlockType, string> = {
  [BlockType.ENTRY_CONDITION]: 'border-l-emerald-500',
  [BlockType.EXIT_CONDITION]: 'border-l-red-500',
  [BlockType.RISK_MANAGEMENT]: 'border-l-amber-500',
  [BlockType.TIME_CONSTRAINT]: 'border-l-blue-500',
  [BlockType.FILTER]: 'border-l-purple-500',
  [BlockType.INDICATOR]: 'border-l-cyan-500',
  [BlockType.POSITION_SIZING]: 'border-l-orange-500',
};

interface BlockItemProps {
  block: Block;
  index: number;
  total: number;
  isSelected: boolean;
  onSelect: (index: number) => void;
  onDelete: (index: number) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
}

function BlockItem({
  block,
  index,
  total,
  isSelected,
  onSelect,
  onDelete,
  onMoveUp,
  onMoveDown,
}: BlockItemProps) {
  const accent = TYPE_ACCENT[block.type] ?? 'border-l-zinc-600';
  const typeLabel = BLOCK_TYPE_LABELS[block.type] ?? block.type;

  return (
    <div
      className={`rounded border border-zinc-800 border-l-4 ${accent} bg-zinc-900 mb-3 cursor-pointer transition-colors ${
        isSelected ? 'ring-1 ring-blue-500' : 'hover:border-zinc-700'
      }`}
      onClick={() => onSelect(index)}
    >
      <div className="px-4 py-3 flex items-center gap-3">
        {/* Position badge */}
        <span className="text-sm font-bold text-blue-400 w-7 flex-shrink-0">#{index + 1}</span>

        {/* Block info */}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-zinc-100 truncate">
            {typeLabel}
          </div>
          <div className="text-xs text-zinc-400 mt-0.5 truncate">
            ID: {block.id.slice(0, 8)}…
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-1 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          <InfoTooltip id={`move-up-${block.id}`}>
            <button
              disabled={index === 0}
              onClick={() => onMoveUp(index)}
              className="px-2 py-1 rounded text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed text-xs transition-colors"
              aria-label="Move block up"
            >
              ▴
            </button>
          </InfoTooltip>
          <InfoTooltip id={`move-down-${block.id}`}>
            <button
              disabled={index === total - 1}
              onClick={() => onMoveDown(index)}
              className="px-2 py-1 rounded text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed text-xs transition-colors"
              aria-label="Move block down"
            >
              ▾
            </button>
          </InfoTooltip>
          <InfoTooltip id={`delete-block-${block.id}`}>
            <button
              onClick={() => onDelete(index)}
              className="px-2 py-1 rounded text-zinc-500 hover:text-red-400 hover:bg-red-950 text-xs transition-colors"
              aria-label="Remove block"
            >
              ✕
            </button>
          </InfoTooltip>
        </div>
      </div>
    </div>
  );
}

export function StrategyBlocksPanel() {
  const { currentStrategy, selectedBlockIndex, selectBlock, deleteBlock, reorderBlocks } =
    useStrategyStore();

  const blocks: Block[] = currentStrategy?.blocks ?? [];

  const handleMoveUp = useCallback(
    (index: number) => {
      if (index > 0) reorderBlocks(index, index - 1);
    },
    [reorderBlocks],
  );

  const handleMoveDown = useCallback(
    (index: number) => {
      if (index < blocks.length - 1) reorderBlocks(index, index + 1);
    },
    [blocks.length, reorderBlocks],
  );

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Header */}
      <div className="px-6 py-3 border-b border-zinc-800 flex items-center justify-between flex-shrink-0">
        <h2 className="text-sm font-semibold text-zinc-50">Strategy Blocks</h2>
        <span className="text-xs text-zinc-500">{blocks.length} block{blocks.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Block List */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {blocks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3 py-12">
            <div className="text-4xl opacity-20">📦</div>
            <p className="text-sm text-zinc-500">No blocks added yet</p>
            <p className="text-xs text-zinc-600">Search the Block Library on the left to add blocks</p>
          </div>
        ) : (
          blocks.map((block, index) => (
            <BlockItem
              key={block.id}
              block={block}
              index={index}
              total={blocks.length}
              isSelected={selectedBlockIndex === index}
              onSelect={selectBlock}
              onDelete={deleteBlock}
              onMoveUp={handleMoveUp}
              onMoveDown={handleMoveDown}
            />
          ))
        )}
      </div>
    </div>
  );
}

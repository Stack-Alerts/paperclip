'use client';

import { useCallback, useState } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block, BlockType } from '@/lib/strategy-builder/types';
import { TimingConstraintDialog, TimingConstraint } from './TimingConstraintDialog';

// Display label for block type (fallback when no name stored in data)
const BLOCK_TYPE_LABELS: Record<BlockType, string> = {
  [BlockType.ENTRY_CONDITION]:  'Entry Condition',
  [BlockType.EXIT_CONDITION]:   'Exit Condition',
  [BlockType.RISK_MANAGEMENT]:  'Risk Management',
  [BlockType.TIME_CONSTRAINT]:  'Time Constraint',
  [BlockType.FILTER]:           'Filter',
  [BlockType.INDICATOR]:        'Indicator',
  [BlockType.POSITION_SIZING]:  'Position Sizing',
};

interface BlockSignal {
  name: string;
  description?: string;
  recheckEnabled?: boolean;
  recheck_config?: { enabled: boolean; bar_delay?: number; mode?: string };
  timing_constraint?: { reference_signal: string; max_candles: number } | null;
}

// ─────────────────────────────────────────────
// BlockCard
// ─────────────────────────────────────────────
interface BlockCardProps {
  block: Block;
  index: number;
  total: number;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  onRemove: (index: number) => void;
  onConfig: (index: number) => void;
  onToggleRecheck: (blockIndex: number, signalIndex: number) => void;
}

function BlockCard({
  block,
  index,
  total,
  onMoveUp,
  onMoveDown,
  onRemove,
  onConfig,
  onToggleRecheck,
}: BlockCardProps) {
  const blockName = (block.data.name as string | undefined) || BLOCK_TYPE_LABELS[block.type] || block.type;
  const logic = (block.data.logic as string | undefined) ?? 'AND';
  const signals = (block.data.signals as BlockSignal[] | undefined) ?? [];
  const isExit = block.type === BlockType.EXIT_CONDITION || logic === 'EXIT';

  const badgeClass = isExit
    ? 'bg-red-900/60 text-red-300 border-red-700'
    : logic === 'OR'
    ? 'bg-blue-900/60 text-blue-300 border-blue-700'
    : 'bg-emerald-900/60 text-emerald-300 border-emerald-700';

  const badgeLabel = isExit ? 'EXIT' : logic === 'OR' ? 'OPTIONAL' : 'REQUIRED';

  const leftAccent = isExit
    ? 'border-l-red-600'
    : logic === 'OR'
    ? 'border-l-blue-600'
    : 'border-l-emerald-600';

  return (
    <div className={`rounded border border-zinc-800 border-l-4 ${leftAccent} bg-zinc-900 mb-3`}>
      {/* Header row */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-zinc-800/60">
        {/* Block number */}
        <span className="text-sm font-bold text-blue-400 w-7 flex-shrink-0">
          #{index + 1}
        </span>

        {/* Block name */}
        <span className="flex-1 text-sm font-semibold text-zinc-100 truncate" title={blockName}>
          {blockName}
        </span>

        {/* Logic badge */}
        <span className={`text-xs px-1.5 py-0.5 rounded border font-mono flex-shrink-0 ${badgeClass}`}>
          {badgeLabel}
        </span>

        {/* Move up/down */}
        <div className="flex items-center gap-0.5 flex-shrink-0" onClick={e => e.stopPropagation()}>
          <button
            onClick={() => onMoveUp(index)}
            disabled={index === 0}
            title="Move block up"
            className="px-1.5 py-0.5 rounded text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700 disabled:opacity-25 disabled:cursor-not-allowed text-sm transition-colors"
          >
            ▴
          </button>
          <button
            onClick={() => onMoveDown(index)}
            disabled={index === total - 1}
            title="Move block down"
            className="px-1.5 py-0.5 rounded text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700 disabled:opacity-25 disabled:cursor-not-allowed text-sm transition-colors"
          >
            ▾
          </button>
        </div>
      </div>

      {/* Signals section */}
      {signals.length > 0 && (
        <div className="px-3 py-2 space-y-1.5 border-b border-zinc-800/60">
          <div className="text-xs text-zinc-500 font-medium mb-1">Signals:</div>
          {signals.map((sig, si) => {
            const hasRecheck = sig.recheckEnabled || sig.recheck_config?.enabled;
            const hasTiming = !!sig.timing_constraint;
            return (
              <div key={si} className="flex items-center gap-2 text-xs">
                <span className="text-zinc-400 flex-1 truncate" title={sig.name}>
                  {si + 1}. {sig.name}
                  {hasTiming && (
                    <span className="text-amber-400 ml-1">
                      ⏱ within {sig.timing_constraint?.max_candles} bars
                    </span>
                  )}
                </span>
                {hasRecheck ? (
                  <span
                    className="text-emerald-400 text-xs px-1.5 py-0.5 rounded bg-emerald-900/40 border border-emerald-800 cursor-pointer hover:bg-emerald-900/60 transition-colors flex-shrink-0"
                    title="Recheck configured — click to toggle off"
                    onClick={() => onToggleRecheck(index, si)}
                  >
                    ✓ Recheck
                  </span>
                ) : (
                  <button
                    onClick={() => onToggleRecheck(index, si)}
                    title="Enable recheck on delayed candles"
                    className="text-zinc-500 hover:text-blue-400 hover:bg-zinc-800 text-xs px-1.5 py-0.5 rounded border border-zinc-700 hover:border-blue-700 transition-colors flex-shrink-0 whitespace-nowrap"
                  >
                    ⟳ Recheck
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {signals.length === 0 && (
        <div className="px-3 py-2 border-b border-zinc-800/60">
          <span className="text-xs text-zinc-600 italic">No signals — configure this block</span>
        </div>
      )}

      {/* Action row: Config + Remove */}
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          onClick={() => onConfig(index)}
          title="Configure timing constraint for this block"
          className="text-xs px-2.5 py-1 rounded border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-zinc-100 transition-colors"
        >
          ⚙ Config
        </button>
        <button
          onClick={() => onRemove(index)}
          title="Remove this block from strategy"
          className="text-xs px-2.5 py-1 rounded border border-zinc-700 bg-zinc-800 hover:bg-red-900/40 hover:border-red-800 text-zinc-400 hover:text-red-300 transition-colors ml-auto"
        >
          ✕ Remove
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// ExitConditionsSection
// ─────────────────────────────────────────────
interface ExitConditionsSectionProps {
  blocks: Block[];
  onRemove: (index: number) => void;
}

function ExitConditionsSection({ blocks, onRemove }: ExitConditionsSectionProps) {
  const exitBlocks = blocks
    .map((b, i) => ({ block: b, globalIndex: i }))
    .filter(({ block }) => block.type === BlockType.EXIT_CONDITION || (block.data.logic as string) === 'EXIT');

  return (
    <div className="border-t border-zinc-700 flex-shrink-0">
      <div className="px-4 py-2 flex items-center justify-between bg-zinc-900/60">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Strategy Exit Conditions
        </span>
        <span className="text-xs text-zinc-600">{exitBlocks.length} exit block{exitBlocks.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="px-4 pb-3">
        {exitBlocks.length === 0 ? (
          <p className="text-xs text-zinc-600 italic">
            No exit conditions configured. Add exit blocks from the library on the right.
          </p>
        ) : (
          <div className="space-y-1.5">
            {exitBlocks.map(({ block, globalIndex }) => {
              const name = (block.data.name as string | undefined) || 'Exit Condition';
              const signals = (block.data.signals as BlockSignal[] | undefined) ?? [];
              return (
                <div
                  key={block.id}
                  className="flex items-center justify-between text-xs py-1.5 px-2 rounded bg-zinc-800/60 border border-red-900/40"
                >
                  <div className="flex-1 min-w-0">
                    <span className="text-red-300 font-medium">{name}</span>
                    {signals.length > 0 && (
                      <span className="text-zinc-500 ml-2">({signals.length} signal{signals.length !== 1 ? 's' : ''})</span>
                    )}
                  </div>
                  <button
                    onClick={() => onRemove(globalIndex)}
                    className="text-zinc-500 hover:text-red-400 ml-2 flex-shrink-0"
                    title="Remove exit condition"
                  >
                    ✕
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// StrategyBlocksPanel (main export)
// ─────────────────────────────────────────────
export function StrategyBlocksPanel() {
  const {
    currentStrategy,
    deleteBlock,
    reorderBlocks,
    updateBlock,
  } = useStrategyStore();

  const blocks: Block[] = currentStrategy?.blocks ?? [];

  // Timing constraint dialog
  const [timingDialogIndex, setTimingDialogIndex] = useState<number | null>(null);

  const handleMoveUp = useCallback(
    (index: number) => { if (index > 0) reorderBlocks(index, index - 1); },
    [reorderBlocks]
  );

  const handleMoveDown = useCallback(
    (index: number) => { if (index < blocks.length - 1) reorderBlocks(index, index + 1); },
    [blocks.length, reorderBlocks]
  );

  const handleRemove = useCallback(
    (index: number) => { deleteBlock(index); },
    [deleteBlock]
  );

  const handleConfig = useCallback(
    (index: number) => { setTimingDialogIndex(index); },
    []
  );

  const handleToggleRecheck = useCallback(
    (blockIndex: number, signalIndex: number) => {
      const block = blocks[blockIndex];
      if (!block) return;
      const signals = [...((block.data.signals as BlockSignal[] | undefined) ?? [])];
      if (!signals[signalIndex]) return;
      const sig = { ...signals[signalIndex] };
      const current = sig.recheckEnabled || sig.recheck_config?.enabled;
      if (current) {
        sig.recheckEnabled = false;
        sig.recheck_config = { enabled: false };
      } else {
        sig.recheckEnabled = true;
        sig.recheck_config = { enabled: true, bar_delay: 3, mode: 'WITHIN' };
      }
      signals[signalIndex] = sig;
      updateBlock(blockIndex, { signals });
    },
    [blocks, updateBlock]
  );

  const handleTimingConstraintSave = useCallback(
    (constraint: TimingConstraint) => {
      if (timingDialogIndex === null) return;
      const block = blocks[timingDialogIndex];
      if (!block) return;
      updateBlock(timingDialogIndex, { ...block.data, timingConstraint: constraint });
      setTimingDialogIndex(null);
    },
    [timingDialogIndex, blocks, updateBlock]
  );

  const timingBlock = timingDialogIndex !== null ? blocks[timingDialogIndex] : null;
  const availableRefs = blocks
    .filter((_, i) => i !== timingDialogIndex)
    .map(b => ({
      displayName: `#${b.index + 1} ${(b.data.name as string | undefined) || BLOCK_TYPE_LABELS[b.type] || b.type}`,
      referenceId: b.id,
    }));

  // Split into main blocks vs exit blocks for display
  const mainBlocks = blocks.filter(
    b => b.type !== BlockType.EXIT_CONDITION && (b.data.logic as string) !== 'EXIT'
  );
  const blockCount = blocks.length;

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-zinc-800 flex items-center justify-between flex-shrink-0 bg-zinc-900/50">
        <h2 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">
          Strategy Building Blocks
        </h2>
        <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full border border-zinc-700">
          {blockCount}
        </span>
      </div>

      {/* Block list (scrollable, main area) */}
      <div className="flex-1 overflow-y-auto px-4 py-3 min-h-0">
        {mainBlocks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center gap-2">
            <div className="text-3xl opacity-20">📦</div>
            <p className="text-sm text-zinc-500">No building blocks added yet</p>
            <p className="text-xs text-zinc-600">Use the library on the right to add blocks</p>
          </div>
        ) : (
          blocks
            .filter(b => b.type !== BlockType.EXIT_CONDITION && (b.data.logic as string) !== 'EXIT')
            .map((block, displayIdx) => {
              // Find the global index of this block
              const globalIndex = blocks.indexOf(block);
              const mainCount = blocks.filter(
                b => b.type !== BlockType.EXIT_CONDITION && (b.data.logic as string) !== 'EXIT'
              ).length;
              return (
                <BlockCard
                  key={block.id}
                  block={block}
                  index={globalIndex}
                  total={blockCount}
                  onMoveUp={handleMoveUp}
                  onMoveDown={handleMoveDown}
                  onRemove={handleRemove}
                  onConfig={handleConfig}
                  onToggleRecheck={handleToggleRecheck}
                />
              );
            })
        )}
      </div>

      {/* Exit Conditions section at bottom */}
      <ExitConditionsSection blocks={blocks} onRemove={handleRemove} />

      {/* Timing Constraint Dialog */}
      {timingDialogIndex !== null && timingBlock && (
        <TimingConstraintDialog
          open={true}
          blockName={`Block #${timingDialogIndex + 1}`}
          signalName={(timingBlock.data.name as string | undefined) || BLOCK_TYPE_LABELS[timingBlock.type] || timingBlock.type}
          availableReferences={availableRefs}
          currentConstraint={(timingBlock.data.timingConstraint as TimingConstraint | undefined) ?? null}
          onSave={handleTimingConstraintSave}
          onCancel={() => setTimingDialogIndex(null)}
        />
      )}
    </div>
  );
}

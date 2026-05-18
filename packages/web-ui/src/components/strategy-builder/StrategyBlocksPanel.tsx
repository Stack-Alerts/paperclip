'use client';

import { useCallback, useState } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block, BlockType } from '@/lib/strategy-builder/types';
import { InfoTooltip } from './InfoTooltip';
import { TimingConstraintDialog, TimingConstraint } from './TimingConstraintDialog';
import { BlockConfigDialog } from './BlockConfigDialog';
import { ExitConditionDialog, ExitConditionConfig } from './ExitConditionDialog';

// ── Constants ─────────────────────────────────────────────────────────────────

const BLOCK_TYPE_LABELS: Record<BlockType, string> = {
  [BlockType.ENTRY_CONDITION]:  'Entry Condition',
  [BlockType.EXIT_CONDITION]:   'Exit Condition',
  [BlockType.RISK_MANAGEMENT]:  'Risk Management',
  [BlockType.TIME_CONSTRAINT]:  'Time Constraint',
  [BlockType.FILTER]:           'Filter',
  [BlockType.INDICATOR]:        'Indicator',
  [BlockType.POSITION_SIZING]:  'Position Sizing',
};

const TYPE_ACCENT: Record<BlockType, string> = {
  [BlockType.ENTRY_CONDITION]:  'border-l-emerald-500',
  [BlockType.EXIT_CONDITION]:   'border-l-red-500',
  [BlockType.RISK_MANAGEMENT]:  'border-l-amber-500',
  [BlockType.TIME_CONSTRAINT]:  'border-l-blue-500',
  [BlockType.FILTER]:           'border-l-purple-500',
  [BlockType.INDICATOR]:        'border-l-cyan-500',
  [BlockType.POSITION_SIZING]:  'border-l-orange-500',
};

// Signal shape stored in block.data.signals
interface BlockSignalEntry {
  name: string;
  logic?: 'AND' | 'OR';
  timingConstraint?: {
    enabled?: boolean;
    maxCandles?: number;
    referenceSignal?: string;
  };
  recheck?: {
    mode?: 'WITHIN' | 'AT';
    barDelay?: number;
    nestedRecheck?: {
      mode?: 'WITHIN' | 'AT';
      barDelay?: number;
      validationTarget?: 'original_signal' | 'previous_recheck';
    };
  };
  exits?: Array<{
    signalName: string;
    percentage?: number;
    exitMode?: string;
    recheck?: { mode?: string; barDelay?: number };
  }>;
}

interface BlockExitEntry {
  signalName: string;
  percentage?: number;
  exitMode?: string;
}

// ── Signal row ────────────────────────────────────────────────────────────────

function SignalRow({ sig, index }: { sig: BlockSignalEntry; index: number }) {
  const isAnd = (sig.logic ?? 'AND') === 'AND';
  return (
    <div className="space-y-0.5 pl-4 border-l border-zinc-800">
      {/* Signal line */}
      <div className="flex items-center gap-1.5 py-0.5">
        <span className="text-zinc-600 text-xs font-mono">{index + 1}.</span>
        <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${
          isAnd
            ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-800'
            : 'bg-blue-900/40 text-blue-400 border border-blue-800'
        }`}>
          {isAnd ? 'AND' : 'OR'}
        </span>
        <span className="text-xs text-zinc-300 font-medium">{sig.name}</span>
        {sig.timingConstraint?.enabled && (
          <span className="text-xs text-amber-400">
            ⏱ within {sig.timingConstraint.maxCandles}c of {sig.timingConstraint.referenceSignal ?? '?'}
          </span>
        )}
      </div>

      {/* RECHECK level 1 */}
      {sig.recheck && (
        <div className="pl-4 space-y-0.5">
          <div className="flex items-center gap-1.5 py-0.5">
            <span className="text-zinc-600 text-xs font-mono">└──</span>
            <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-900/30 text-emerald-400 border border-emerald-800">
              RECHECK
            </span>
            <span className="text-xs text-zinc-400">
              {sig.recheck.mode ?? 'WITHIN'} {sig.recheck.barDelay ?? '?'} bars
            </span>
          </div>

          {/* Nested RECHECK level 2 */}
          {sig.recheck.nestedRecheck && (
            <div className="pl-4">
              <div className="flex items-center gap-1.5 py-0.5">
                <span className="text-zinc-600 text-xs font-mono">└──</span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-900/20 text-emerald-500 border border-emerald-900">
                  RECHECK
                </span>
                <span className="text-xs text-zinc-500">
                  of {sig.recheck.nestedRecheck.validationTarget === 'previous_recheck' ? 'Previous RECHECK' : 'Original Signal'}{' '}
                  ({sig.recheck.nestedRecheck.mode ?? 'WITHIN'} {sig.recheck.nestedRecheck.barDelay ?? '?'} bars)
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Signal-level exits */}
      {sig.exits?.map((exit, ei) => (
        <div key={ei} className="pl-4 space-y-0.5">
          <div className="flex items-center gap-1.5 py-0.5">
            <span className="text-zinc-600 text-xs font-mono">└──</span>
            <span className="text-xs text-red-400 font-semibold">🔴 EXIT:</span>
            <span className="text-xs text-zinc-400">
              {exit.signalName}{exit.percentage != null ? ` (${exit.percentage}%)` : ''}
              {exit.exitMode ? ` — ${exit.exitMode}` : ''}
            </span>
          </div>
          {exit.recheck && (
            <div className="pl-8">
              <div className="flex items-center gap-1.5">
                <span className="text-zinc-600 text-xs font-mono">└──</span>
                <span className="text-xs px-1 rounded bg-emerald-900/20 text-emerald-500 border border-emerald-900">
                  RECHECK
                </span>
                <span className="text-xs text-zinc-500">
                  {exit.recheck.mode ?? 'WITHIN'} {exit.recheck.barDelay ?? '?'} bars
                </span>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Block item ────────────────────────────────────────────────────────────────

interface BlockItemProps {
  block: Block;
  index: number;
  total: number;
  isSelected: boolean;
  onSelect: (index: number) => void;
  onDelete: (index: number) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  onDuplicate: (index: number) => void;
  onTimingConstraint: (index: number) => void;
  onConfigure: (index: number) => void;
}

function BlockItem({
  block, index, total, isSelected,
  onSelect, onDelete, onMoveUp, onMoveDown, onDuplicate, onTimingConstraint, onConfigure,
}: BlockItemProps) {
  const accent    = TYPE_ACCENT[block.type] ?? 'border-l-zinc-600';
  const typeLabel = BLOCK_TYPE_LABELS[block.type] ?? block.type;
  const blockName = (block.data?.name as string | undefined) || typeLabel;
  const hasTimingConstraint = !!(block.data?.timingConstraint as TimingConstraint | undefined)?.enabled;
  const signals   = (block.data?.signals as BlockSignalEntry[] | undefined) ?? [];
  const blockExits = (block.data?.exits as BlockExitEntry[] | undefined) ?? [];
  const logicType = (block.data?.logic as string | undefined) ?? 'AND';
  const isRequired = block.type !== 'exit_condition' && logicType === 'AND';
  const isExit = block.type === 'exit_condition';

  return (
    <div
      className={`rounded border border-zinc-800 border-l-4 ${accent} bg-zinc-900 mb-3 cursor-pointer transition-colors ${
        isSelected ? 'ring-1 ring-blue-500' : 'hover:border-zinc-700'
      }`}
      onClick={() => onSelect(index)}
    >
      {/* Block header */}
      <div className="px-4 py-3 flex items-center gap-3">
        {/* Position badge */}
        <span className="text-sm font-bold text-blue-400 w-7 flex-shrink-0">#{index + 1}</span>

        {/* Block info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-zinc-100">{blockName}</span>
            {/* Logic / type badge */}
            <span className={`text-xs px-2 py-0.5 rounded font-semibold border ${
              isExit
                ? 'bg-red-900/30 text-red-400 border-red-800'
                : isRequired
                ? 'bg-emerald-900/30 text-emerald-400 border-emerald-800'
                : 'bg-blue-900/30 text-blue-400 border-blue-800'
            }`}>
              {isExit ? 'EXIT' : isRequired ? 'REQUIRED' : 'OPTIONAL'}
            </span>
          </div>
          <div className="text-xs text-zinc-500 mt-0.5 flex items-center gap-2 flex-wrap">
            <span>ID: {block.id.slice(0, 8)}…</span>
            {signals.length > 0 && (
              <span className="text-zinc-400">Signals: {signals.length}</span>
            )}
            {hasTimingConstraint && (
              <span className="text-blue-400">⏱ timing</span>
            )}
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
          <InfoTooltip id={`configure-block-${block.id}`}>
            <button
              onClick={() => onConfigure(index)}
              className="px-2 py-1 rounded text-zinc-400 hover:text-blue-300 hover:bg-blue-950 text-xs transition-colors"
              aria-label="Configure block"
              title="Config"
            >
              ⚙
            </button>
          </InfoTooltip>
          {index > 0 && (
            <InfoTooltip id={`timing-block-${block.id}`}>
              <button
                onClick={() => onTimingConstraint(index)}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  hasTimingConstraint
                    ? 'text-blue-400 hover:bg-blue-900'
                    : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700'
                }`}
                aria-label="Timing constraint"
                title="Timing Constraint"
              >
                ⏱
              </button>
            </InfoTooltip>
          )}
          <InfoTooltip id={`delete-block-${block.id}`}>
            <button
              onClick={() => onDelete(index)}
              className="px-2 py-1 rounded text-zinc-500 hover:text-red-400 hover:bg-red-950 text-xs transition-colors"
              aria-label="Remove block"
              title="Remove"
            >
              ✕
            </button>
          </InfoTooltip>
        </div>
      </div>

      {/* Signal list */}
      {signals.length > 0 && (
        <div
          className="px-4 pb-3 space-y-1"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="text-xs text-zinc-600 font-medium uppercase tracking-wide mb-1.5">Signals</p>
          {signals.map((sig, si) => (
            <SignalRow key={si} sig={sig} index={si} />
          ))}
        </div>
      )}

      {/* Block-level exits */}
      {blockExits.length > 0 && (
        <div
          className="px-4 pb-3"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="text-xs text-zinc-600 font-medium uppercase tracking-wide mb-1.5">Block-Level Exit Conditions</p>
          <div className="space-y-0.5 pl-4 border-l border-zinc-800">
            {blockExits.map((exit, ei) => (
              <div key={ei} className="flex items-center gap-1.5 py-0.5">
                <span className="text-xs text-red-400 font-semibold">🔴</span>
                <span className="text-xs text-zinc-400">
                  {exit.signalName}{exit.percentage != null ? ` (${exit.percentage}%)` : ''}
                  {exit.exitMode ? ` — ${exit.exitMode}` : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Strategy-level exits ──────────────────────────────────────────────────────

export interface StrategyExitEntry {
  signalName: string;
  percentage?: number;
  exitMode?: string;
  tpProximity?: number;
  reversalTrigger?: number;
  recheckEnabled?: boolean;
  recheckBarDelay?: number;
}

interface StrategyExitsSectionProps {
  exits: StrategyExitEntry[];
  onAdd: () => void;
  onEdit: (index: number) => void;
  onRemove: (index: number) => void;
}

function StrategyExitsSection({ exits, onAdd, onEdit, onRemove }: StrategyExitsSectionProps) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div>
      <div className="flex items-center justify-between px-4 py-2.5">
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center gap-1.5 text-xs font-semibold text-red-400 hover:text-red-300 transition-colors"
        >
          <span>{collapsed ? '▶' : '▼'}</span>
          <span>Strategy Exit Conditions ({exits.length})</span>
        </button>
        <button
          onClick={onAdd}
          className="text-xs px-2 py-0.5 rounded bg-red-900/40 hover:bg-red-900/70 text-red-400 border border-red-800 transition-colors"
          title="Add strategy-level exit condition"
        >
          + Add Exit
        </button>
      </div>
      {!collapsed && (
        <div className="px-4 pb-3 space-y-1.5">
          {exits.length === 0 ? (
            <p className="text-xs text-zinc-600 italic">No strategy-level exit conditions configured.</p>
          ) : (
            exits.map((exit, i) => (
              <div key={i} className="flex items-center gap-1.5 py-0.5 group">
                <span className="text-xs text-red-400 font-semibold flex-shrink-0">🔴</span>
                <span className="text-xs text-zinc-400 flex-1 min-w-0 truncate">
                  {exit.signalName}
                  {exit.percentage != null ? ` (${exit.percentage}%)` : ''}
                  {exit.exitMode ? ` — ${exit.exitMode}` : ''}
                </span>
                <button
                  onClick={() => onEdit(i)}
                  className="opacity-0 group-hover:opacity-100 px-1.5 py-0.5 rounded text-zinc-400 hover:text-blue-300 hover:bg-blue-950 text-xs transition-all"
                  title="Edit exit condition"
                >⚙</button>
                <button
                  onClick={() => onRemove(i)}
                  className="opacity-0 group-hover:opacity-100 px-1.5 py-0.5 rounded text-zinc-500 hover:text-red-400 hover:bg-red-950 text-xs transition-all"
                  title="Remove exit condition"
                >✕</button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export function StrategyBlocksPanel() {
  const {
    currentStrategy,
    selectedBlockIndex,
    selectBlock,
    deleteBlock,
    reorderBlocks,
    addBlock,
    updateBlock,
  } = useStrategyStore();


  const blocks: Block[] = currentStrategy?.blocks ?? [];
  const strategyExits = (currentStrategy?.settings as unknown as { strategyExits?: StrategyExitEntry[] })?.strategyExits ?? [];

  const [timingDialogIndex, setTimingDialogIndex] = useState<number | null>(null);
  const [configDialogIndex, setConfigDialogIndex] = useState<number | null>(null);
  const [exitDialogOpen, setExitDialogOpen] = useState(false);
  const [editingExitIndex, setEditingExitIndex] = useState<number | null>(null);

  const { updateStrategySettings } = useStrategyStore();

  const handleMoveUp = useCallback(
    (index: number) => { if (index > 0) reorderBlocks(index, index - 1); },
    [reorderBlocks],
  );

  const handleMoveDown = useCallback(
    (index: number) => { if (index < blocks.length - 1) reorderBlocks(index, index + 1); },
    [blocks.length, reorderBlocks],
  );

  const handleDuplicate = useCallback(
    (index: number) => {
      const source = blocks[index];
      if (!source) return;
      addBlock(source.type, index + 1);
      updateBlock(index + 1, { ...source.data });
    },
    [blocks, addBlock, updateBlock],
  );

  const handleTimingConstraint = useCallback((index: number) => {
    setTimingDialogIndex(index);
  }, []);

  const handleConfigure = useCallback((index: number) => {
    setConfigDialogIndex(index);
  }, []);

  const handleConfigSave = useCallback(
    (index: number, data: Record<string, unknown>) => {
      const block = blocks[index];
      if (!block) return;
      updateBlock(index, { ...block.data, ...data });
    },
    [blocks, updateBlock],
  );

  const handleStrategyExitAdd = useCallback(() => {
    setEditingExitIndex(null);
    setExitDialogOpen(true);
  }, []);

  const handleStrategyExitEdit = useCallback((index: number) => {
    setEditingExitIndex(index);
    setExitDialogOpen(true);
  }, []);

  const handleStrategyExitRemove = useCallback(
    (index: number) => {
      const updated = strategyExits.filter((_, i) => i !== index);
      updateStrategySettings({ strategyExits: updated } as never);
    },
    [strategyExits, updateStrategySettings],
  );

  const handleStrategyExitSave = useCallback(
    (config: ExitConditionConfig) => {
      const entry: StrategyExitEntry = {
        signalName: editingExitIndex !== null
          ? (strategyExits[editingExitIndex]?.signalName ?? 'Exit Signal')
          : 'Exit Signal',
        percentage: config.percentage,
        exitMode: config.exitMode,
        tpProximity: config.tpProximity,
        reversalTrigger: config.reversalTrigger,
        recheckEnabled: config.recheckEnabled,
        recheckBarDelay: config.recheckBarDelay,
      };
      let updated: StrategyExitEntry[];
      if (editingExitIndex !== null) {
        updated = strategyExits.map((e, i) => (i === editingExitIndex ? entry : e));
      } else {
        updated = [...strategyExits, entry];
      }
      updateStrategySettings({ strategyExits: updated } as never);
      setExitDialogOpen(false);
      setEditingExitIndex(null);
    },
    [editingExitIndex, strategyExits, updateStrategySettings],
  );

  const handleTimingConstraintSave = useCallback(
    (constraint: TimingConstraint) => {
      if (timingDialogIndex === null) return;
      const block = blocks[timingDialogIndex];
      if (!block) return;
      updateBlock(timingDialogIndex, { ...block.data, timingConstraint: constraint });
      setTimingDialogIndex(null);
    },
    [timingDialogIndex, blocks, updateBlock],
  );

  const timingBlock = timingDialogIndex !== null ? blocks[timingDialogIndex] : null;
  const availableReferences = blocks
    .filter((_, i) => i !== timingDialogIndex)
    .map((b) => ({
      displayName: `#${b.index + 1} ${BLOCK_TYPE_LABELS[b.type] ?? b.type}`,
      referenceId: b.id,
    }));

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between flex-shrink-0">
        <h2 className="text-sm font-semibold text-zinc-50">Strategy Building Blocks</h2>
        <span className="text-xs text-zinc-500">{blocks.length} block{blocks.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Block List */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {blocks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3 py-12">
            <div className="text-4xl opacity-20">📦</div>
            <p className="text-sm text-zinc-500">No blocks added yet</p>
            <p className="text-xs text-zinc-600">Use the library on the right to add blocks</p>
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
              onDuplicate={handleDuplicate}
              onTimingConstraint={handleTimingConstraint}
              onConfigure={handleConfigure}
            />
          ))
        )}
      </div>

      {/* Section 3: Strategy Exit Conditions — always visible footer */}
      <div className="flex-shrink-0 border-t border-zinc-800">
        <StrategyExitsSection
          exits={strategyExits}
          onAdd={handleStrategyExitAdd}
          onEdit={handleStrategyExitEdit}
          onRemove={handleStrategyExitRemove}
        />
      </div>

      {/* Strategy Exit Condition Dialog */}
      <ExitConditionDialog
        open={exitDialogOpen}
        signalName={editingExitIndex !== null ? strategyExits[editingExitIndex]?.signalName : undefined}
        existingConfig={editingExitIndex !== null ? {
          percentage: strategyExits[editingExitIndex]?.percentage ?? 50,
          exitMode: (strategyExits[editingExitIndex]?.exitMode as 'ABSOLUTE' | 'FLEXIBLE') ?? 'ABSOLUTE',
          tpProximity: strategyExits[editingExitIndex]?.tpProximity,
          reversalTrigger: strategyExits[editingExitIndex]?.reversalTrigger,
          recheckEnabled: strategyExits[editingExitIndex]?.recheckEnabled,
          recheckBarDelay: strategyExits[editingExitIndex]?.recheckBarDelay,
        } : undefined}
        onSave={handleStrategyExitSave}
        onClose={() => { setExitDialogOpen(false); setEditingExitIndex(null); }}
      />

      {/* Block Config Dialog */}
      <BlockConfigDialog
        open={configDialogIndex !== null}
        block={configDialogIndex !== null ? (blocks[configDialogIndex] ?? null) : null}
        blockIndex={configDialogIndex ?? 0}
        onSave={handleConfigSave}
        onClose={() => setConfigDialogIndex(null)}
      />

      {/* Timing Constraint Dialog */}
      {timingDialogIndex !== null && timingBlock && (
        <TimingConstraintDialog
          open={true}
          blockName={`Block #${timingDialogIndex + 1}`}
          signalName={BLOCK_TYPE_LABELS[timingBlock.type] ?? timingBlock.type}
          availableReferences={availableReferences}
          currentConstraint={(timingBlock.data?.timingConstraint as TimingConstraint | undefined) ?? null}
          onSave={handleTimingConstraintSave}
          onCancel={() => setTimingDialogIndex(null)}
        />
      )}
    </div>
  );
}

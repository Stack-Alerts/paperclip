'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block, BlockType } from '@/lib/strategy-builder/types';
import { TimingConstraintDialog, TimingConstraint } from './TimingConstraintDialog';

function formatSignalName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

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
  logic?: string;
  recheckEnabled?: boolean;
  recheck_config?: { enabled: boolean; bar_delay?: number; mode?: string };
  timing_constraint?: { reference_signal: string; max_candles: number } | null;
}

// ─────────────────────────────────────────────
// RecheckConfigModal
// ─────────────────────────────────────────────
interface RecheckConfigModalProps {
  open: boolean;
  signalName: string;
  barDelay: number;
  mode: string;
  onSave: (barDelay: number, mode: string) => void;
  onCancel: () => void;
}

function RecheckConfigModal({ open, signalName, barDelay, mode, onSave, onCancel }: RecheckConfigModalProps) {
  const [delay, setDelay] = useState(barDelay);
  const [recheckMode, setRecheckMode] = useState(mode);

  useEffect(() => {
    if (open) {
      setDelay(barDelay);
      setRecheckMode(mode);
    }
  }, [open, barDelay, mode]);

  if (!open) return null;

  const MODES = [
    { value: 'WITHIN', label: 'WITHIN bar window (signal reoccurs anywhere within N bars)' },
    { value: 'AT',     label: 'AT exact bar (signal reoccurs at exactly bar N)' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded border shadow-2xl w-[460px]" style={{ background: '#1E2128', borderColor: '#3C4149' }}>
        {/* Title bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b rounded-t" style={{ background: '#2A2F3A', borderColor: '#3C4149' }}>
          <span className="text-sm font-semibold" style={{ color: '#E8EAED' }}>Configure RECHECK Validation</span>
          <div className="flex items-center gap-1">
            <button className="w-5 h-5 rounded text-xs flex items-center justify-center hover:opacity-80" style={{ background: '#3C4149', color: '#9AA0A6' }}>─</button>
            <button className="w-5 h-5 rounded text-xs flex items-center justify-center hover:opacity-80" style={{ background: '#3C4149', color: '#9AA0A6' }}>□</button>
            <button onClick={onCancel} className="w-5 h-5 rounded text-xs flex items-center justify-center hover:opacity-80" style={{ background: '#5C2020', color: '#FCA5A5' }}>✕</button>
          </div>
        </div>

        {/* Body */}
        <div className="px-4 pt-4 pb-3 space-y-3">
          {/* Signal name */}
          <div className="text-base font-bold" style={{ color: '#E8EAED' }}>
            Signal: {signalName}
          </div>

          {/* Description */}
          <p className="text-xs" style={{ color: '#9AA0A6' }}>
            Enter number of bars within which signal must reoccur for validation:
          </p>

          {/* Bar count input */}
          <input
            type="number"
            min={1}
            max={200}
            value={delay}
            onChange={e => setDelay(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-full px-3 py-2 rounded border text-sm focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#E8EAED' }}
          />

          {/* Mode label */}
          <div className="text-sm font-bold" style={{ color: '#E8EAED' }}>RECHECK Mode:</div>

          {/* Radio options */}
          <div className="rounded border overflow-hidden" style={{ borderColor: '#3C4149' }}>
            {MODES.map((opt, i) => {
              const selected = recheckMode === opt.value;
              return (
                <label
                  key={opt.value}
                  className="flex items-center gap-3 px-3 py-3 cursor-pointer hover:opacity-90 transition-opacity"
                  style={{
                    background: selected ? 'rgba(16,185,129,0.08)' : '#2A2F3A',
                    borderBottom: i < MODES.length - 1 ? '1px solid #3C4149' : undefined,
                  }}
                  onClick={() => setRecheckMode(opt.value)}
                >
                  <div
                    className="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0"
                    style={{ borderColor: selected ? '#10B981' : '#6B7280' }}
                  >
                    {selected && <div className="w-2.5 h-2.5 rounded-full" style={{ background: '#10B981' }} />}
                  </div>
                  <span className="text-sm font-semibold" style={{ color: selected ? '#E8EAED' : '#9AA0A6' }}>
                    {opt.label}
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="flex border-t rounded-b overflow-hidden" style={{ borderColor: '#3C4149' }}>
          <button
            onClick={onCancel}
            className="flex-1 py-3 text-sm font-semibold transition-opacity hover:opacity-90"
            style={{ background: '#C35252', color: '#ffffff' }}
          >
            ✕ Cancel
          </button>
          <button
            onClick={() => onSave(delay, recheckMode)}
            className="flex-1 py-3 text-sm font-semibold transition-opacity hover:opacity-90"
            style={{ background: '#10B981', color: '#ffffff' }}
          >
            ✓ OK
          </button>
        </div>
      </div>
    </div>
  );
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
  onConfigRecheck: (blockIndex: number, signalIndex: number) => void;
  onRemoveRecheck: (blockIndex: number, signalIndex: number) => void;
  onDuplicateSignal: (blockIndex: number, signalIndex: number) => void;
}

const TEAL_BTN: React.CSSProperties = {
  background: '#0d7377',
  color: '#ffffff',
  border: '1px solid #14a0a5',
  width: 28,
  height: 28,
  borderRadius: 4,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 13,
  cursor: 'pointer',
  flexShrink: 0,
};

function BlockCard({
  block,
  index,
  total,
  onMoveUp,
  onMoveDown,
  onRemove,
  onConfig,
  onToggleRecheck,
  onConfigRecheck,
  onRemoveRecheck,
  onDuplicateSignal,
}: BlockCardProps) {
  const blockName = (block.data.name as string | undefined) || BLOCK_TYPE_LABELS[block.type] || block.type;
  const logic = (block.data.logic as string | undefined) ?? 'AND';
  const signals = (block.data.signals as BlockSignal[] | undefined) ?? [];
  const isExit = block.type === BlockType.EXIT_CONDITION || logic === 'EXIT';

  const badgeStyle: React.CSSProperties = isExit
    ? { background: 'rgba(153,27,27,0.6)', color: '#FCA5A5', border: '1px solid #7F1D1D' }
    : logic === 'OR'
    ? { background: '#007a51', color: '#ffffff', border: '1px solid #005a3c' }
    : { background: '#2a5eb8', color: '#ffffff', border: '1px solid #1a4a9a' };

  const badgeLabel = isExit ? 'EXIT' : logic === 'OR' ? 'OPTIONAL' : 'REQUIRED';
  const leftBorderColor = isExit ? '#DC2626' : logic === 'OR' ? '#3B82F6' : '#2a5eb8';

  return (
    <div
      className="rounded border border-[#3C4149] mb-3"
      style={{ background: '#1E2128', borderLeft: `4px solid ${leftBorderColor}` }}
    >
      {/* 1. Header: icon + name + badge + move arrows */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#3C4149]/60">
        <span className="flex-shrink-0 text-base" style={{ color: '#6B7280' }}>📊</span>
        <span className="flex-1 text-sm font-semibold truncate" style={{ color: '#A0AEC0' }} title={blockName}>
          {blockName}
        </span>
        <span className="text-xs px-2 py-0.5 rounded font-mono flex-shrink-0" style={badgeStyle}>
          {badgeLabel}
        </span>
        <div className="flex items-center gap-0.5 flex-shrink-0" onClick={e => e.stopPropagation()}>
          <button
            onClick={() => onMoveUp(index)}
            disabled={index === 0}
            title="Move block up"
            className="p-1 rounded hover:text-[#E8EAED] hover:bg-[#2A2F3A] disabled:opacity-25 disabled:cursor-not-allowed text-xs transition-colors"
            style={{ color: '#9AA0A6' }}
          >▲</button>
          <button
            onClick={() => onMoveDown(index)}
            disabled={index === total - 1}
            title="Move block down"
            className="p-1 rounded hover:text-[#E8EAED] hover:bg-[#2A2F3A] disabled:opacity-25 disabled:cursor-not-allowed text-xs transition-colors"
            style={{ color: '#9AA0A6' }}
          >▼</button>
        </div>
      </div>

      {/* 2. Position # + Config (blocks #2+) + Remove */}
      <div className="flex items-center gap-2 px-3 pt-2 pb-1">
        <span className="text-sm font-bold" style={{ color: '#2a5eb8' }}>#{index + 1}</span>
        <div className="flex-1" />
        {index > 0 && (
          <button
            onClick={() => onConfig(index)}
            title="Configure timing constraint between this block and the previous"
            className="text-xs px-3 py-1.5 rounded font-medium transition-colors hover:opacity-80 flex-shrink-0"
            style={{ background: '#2a5eb8', color: '#ffffff', border: '1px solid #1a4a9a' }}
          >
            ⚙ Config
          </button>
        )}
        <button
          onClick={() => onRemove(index)}
          title="Remove this block"
          className="text-xs px-3 py-1.5 rounded font-medium transition-colors hover:opacity-80 flex-shrink-0"
          style={{ background: 'rgba(153,27,27,0.7)', color: '#FCA5A5', border: '1px solid #C35252' }}
        >
          ✕ Remove
        </button>
      </div>

      {/* 3. Signals count */}
      <div className="px-3 pb-2 text-xs" style={{ color: '#9AA0A6' }}>
        Signals: {signals.length}
      </div>

      {/* 4. Signals inner box */}
      {signals.length > 0 && (
        <div className="mx-3 mb-3 rounded border border-[#3C4149]/60" style={{ background: '#15191E' }}>
          <div className="px-3 py-2.5 space-y-2">
            <div className="text-xs font-semibold mb-1" style={{ color: '#A0AEC0' }}>Signals:</div>
            {signals.map((sig, si) => {
              const sigLogic = (sig.logic as string | undefined) ?? logic;
              const hasRecheck = sig.recheckEnabled || sig.recheck_config?.enabled;
              const hasTiming = !!sig.timing_constraint;
              const logicColor = sigLogic === 'OR' ? '#60A5FA' : '#4ADE80';

              return (
                <div key={si} className="space-y-1">
                  {/* Signal row: name [LOGIC] timing | recheck button */}
                  <div className="flex items-center gap-2 text-xs">
                    <span className="flex-1 min-w-0">
                      <span style={{ color: '#E8EAED' }}>{si + 1}. {formatSignalName(sig.name)}</span>
                      <span className="font-mono font-semibold ml-1.5" style={{ color: logicColor }}>[{sigLogic}]</span>
                      {hasTiming && (
                        <span className="ml-2" style={{ color: '#FFA500' }}>
                          ⏱ Within {sig.timing_constraint?.max_candles} candles
                          {sig.timing_constraint?.reference_signal ? ` of ${sig.timing_constraint.reference_signal}` : ''}
                        </span>
                      )}
                    </span>
                    {!hasRecheck && (
                      <button
                        onClick={() => onToggleRecheck(index, si)}
                        title="Enable recheck on delayed candles"
                        className="text-xs px-2.5 py-1 rounded whitespace-nowrap flex-shrink-0 transition-colors hover:opacity-80"
                        style={{ background: '#0d7377', color: '#ffffff', border: '1px solid #14a0a5', fontSize: 11 }}
                      >
                        Recheck On Delayed Candles
                      </button>
                    )}
                  </div>

                  {/* Recheck sub-row when configured */}
                  {hasRecheck && (
                    <div className="flex items-center gap-1.5 ml-3 text-xs">
                      <span style={{ color: '#14a0a5' }}>↳</span>
                      <span className="flex-1 font-semibold" style={{ color: '#14a0a5' }}>
                        RECHECK ({sig.recheck_config?.mode ?? 'WITHIN'} {sig.recheck_config?.bar_delay ?? 3} bars)
                      </span>
                      <button onClick={() => onConfigRecheck(index, si)} title="Configure recheck settings" style={TEAL_BTN}>⚙</button>
                      <button onClick={() => onDuplicateSignal(index, si)} title="Duplicate this signal" style={TEAL_BTN}>📋</button>
                      <button onClick={() => onRemoveRecheck(index, si)} title="Remove recheck" style={TEAL_BTN}>✕</button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {signals.length === 0 && (
        <div className="px-3 pb-3">
          <span className="text-xs italic" style={{ color: '#6B7280' }}>No signals — configure this block</span>
        </div>
      )}
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
    <div className="border-t flex-shrink-0" style={{ borderColor: '#3C4149' }}>
      <div className="px-4 py-2 flex items-center justify-between" style={{ background: 'rgba(30,33,40,0.6)' }}>
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#9AA0A6' }}>
          Strategy Exit Conditions
        </span>
        <span className="text-xs" style={{ color: '#6B7280' }}>{exitBlocks.length} exit block{exitBlocks.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="px-4 pb-3">
        {exitBlocks.length === 0 ? (
          <p className="text-xs italic" style={{ color: '#6B7280' }}>
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
                  className="flex items-center justify-between text-xs py-1.5 px-2 rounded border border-red-900/40"
                  style={{ background: 'rgba(42,47,58,0.6)' }}
                >
                  <div className="flex-1 min-w-0">
                    <span className="text-red-300 font-medium">{name}</span>
                    {signals.length > 0 && (
                      <span className="ml-2" style={{ color: '#6B7280' }}>({signals.length} signal{signals.length !== 1 ? 's' : ''})</span>
                    )}
                  </div>
                  <button
                    onClick={() => onRemove(globalIndex)}
                    className="hover:text-red-400 ml-2 flex-shrink-0"
                    style={{ color: '#6B7280' }}
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

  // Recheck config modal
  const [recheckTarget, setRecheckTarget] = useState<{ blockIndex: number; signalIndex: number } | null>(null);

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

  const handleConfigRecheck = useCallback(
    (blockIndex: number, signalIndex: number) => {
      setRecheckTarget({ blockIndex, signalIndex });
    },
    []
  );

  const handleRemoveRecheck = useCallback(
    (blockIndex: number, signalIndex: number) => {
      const block = blocks[blockIndex];
      if (!block) return;
      const signals = [...((block.data.signals as BlockSignal[] | undefined) ?? [])];
      if (!signals[signalIndex]) return;
      signals[signalIndex] = {
        ...signals[signalIndex],
        recheckEnabled: false,
        recheck_config: { enabled: false },
      };
      updateBlock(blockIndex, { signals });
    },
    [blocks, updateBlock]
  );

  const handleDuplicateSignal = useCallback(
    (blockIndex: number, signalIndex: number) => {
      const block = blocks[blockIndex];
      if (!block) return;
      const signals = [...((block.data.signals as BlockSignal[] | undefined) ?? [])];
      if (!signals[signalIndex]) return;
      const copy = { ...signals[signalIndex] };
      signals.splice(signalIndex + 1, 0, copy);
      updateBlock(blockIndex, { signals });
    },
    [blocks, updateBlock]
  );

  const handleRecheckConfigSave = useCallback(
    (barDelay: number, mode: string) => {
      if (!recheckTarget) return;
      const { blockIndex, signalIndex } = recheckTarget;
      const block = blocks[blockIndex];
      if (!block) return;
      const signals = [...((block.data.signals as BlockSignal[] | undefined) ?? [])];
      if (!signals[signalIndex]) return;
      signals[signalIndex] = {
        ...signals[signalIndex],
        recheckEnabled: true,
        recheck_config: { enabled: true, bar_delay: barDelay, mode },
      };
      updateBlock(blockIndex, { signals });
      setRecheckTarget(null);
    },
    [recheckTarget, blocks, updateBlock]
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

  const blockCount = blocks.length;
  const mainBlockCount = blocks.filter(
    b => b.type !== BlockType.EXIT_CONDITION && (b.data.logic as string) !== 'EXIT'
  ).length;

  return (
    <div className="flex flex-col h-full" style={{ background: '#15191E' }}>
      {/* Header */}
      <div className="px-4 py-2.5 border-b flex items-center justify-between flex-shrink-0" style={{ borderColor: '#3C4149', background: 'rgba(30,33,40,0.5)' }}>
        <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#A0AEC0' }}>
          Strategy Building Blocks
        </h2>
        <span className="text-xs px-2 py-0.5 rounded-full border" style={{ color: '#9AA0A6', background: '#2A2F3A', borderColor: '#3C4149' }}>
          {blockCount}
        </span>
      </div>

      {/* Block list (scrollable, main area) */}
      <div className="flex-1 overflow-y-auto px-4 py-3 min-h-0" style={{ scrollbarWidth: 'thin', scrollbarColor: '#3C4149 transparent' }}>
        {mainBlockCount === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center gap-2">
            <div className="text-3xl opacity-20">📦</div>
            <p className="text-sm" style={{ color: '#9AA0A6' }}>No building blocks added yet</p>
            <p className="text-xs" style={{ color: '#6B7280' }}>Use the library on the right to add blocks</p>
          </div>
        ) : (
          blocks
            .filter(b => b.type !== BlockType.EXIT_CONDITION && (b.data.logic as string) !== 'EXIT')
            .map(block => {
              const globalIndex = blocks.indexOf(block);
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
                  onConfigRecheck={handleConfigRecheck}
                  onRemoveRecheck={handleRemoveRecheck}
                  onDuplicateSignal={handleDuplicateSignal}
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

      {/* Recheck Config Modal */}
      {recheckTarget && (() => {
        const sig = (blocks[recheckTarget.blockIndex]?.data.signals as BlockSignal[] | undefined)?.[recheckTarget.signalIndex];
        return (
          <RecheckConfigModal
            open={true}
            signalName={sig?.name ?? ''}
            barDelay={sig?.recheck_config?.bar_delay ?? 3}
            mode={sig?.recheck_config?.mode ?? 'WITHIN'}
            onSave={handleRecheckConfigSave}
            onCancel={() => setRecheckTarget(null)}
          />
        );
      })()}
    </div>
  );
}

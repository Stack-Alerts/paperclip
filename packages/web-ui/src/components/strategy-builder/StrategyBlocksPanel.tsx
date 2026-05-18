'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block, BlockType } from '@/lib/strategy-builder/types';
import { TimingConstraintDialog, TimingConstraint } from './TimingConstraintDialog';
import { ExitConditionDialog, ExitConditionConfig, AvailableBlock } from './ExitConditionDialog';

function formatSignalName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

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

interface StoredExitConfig {
  signalName?: string;
  percentage?: number;
  exitMode?: string;
  bindingLevel?: string;
  tpProximityThreshold?: number;
  reversalTrigger?: number;
  recheckEnabled?: boolean;
  recheckBarDelay?: number;
  blockName?: string;
  parentSignalName?: string;
}

// ─────────────────────────────────────────────
// RecheckConfigModal  (Issue #2: 620px wide)
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
    if (open) { setDelay(barDelay); setRecheckMode(mode); }
  }, [open, barDelay, mode]);

  if (!open) return null;

  const MODES = [
    { value: 'WITHIN', label: 'WITHIN bar window (signal reoccurs anywhere within N bars)' },
    { value: 'AT',     label: 'AT exact bar (signal reoccurs at exactly bar N)' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded border shadow-2xl w-[620px]" style={{ background: '#1E2128', borderColor: '#3C4149' }}>
        {/* Title bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b rounded-t" style={{ background: '#2A2F3A', borderColor: '#3C4149' }}>
          <span className="text-sm font-semibold" style={{ color: '#E8EAED' }}>Configure RECHECK Validation</span>
          <div className="flex items-center gap-1">
            <span className="w-5 h-5 rounded text-xs flex items-center justify-center" style={{ background: '#3C4149', color: '#9AA0A6' }}>─</span>
            <span className="w-5 h-5 rounded text-xs flex items-center justify-center" style={{ background: '#3C4149', color: '#9AA0A6' }}>□</span>
            <button onClick={onCancel} className="w-5 h-5 rounded text-xs flex items-center justify-center hover:opacity-80" style={{ background: '#5C2020', color: '#FCA5A5' }}>✕</button>
          </div>
        </div>

        {/* Body */}
        <div className="px-4 pt-4 pb-3 space-y-3">
          <div className="text-base font-bold" style={{ color: '#E8EAED' }}>Signal: {signalName}</div>
          <p className="text-xs" style={{ color: '#9AA0A6' }}>
            Enter number of bars within which signal must reoccur for validation:
          </p>
          <input
            type="number" min={1} max={200} value={delay}
            onChange={e => setDelay(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-full px-3 py-2 rounded border text-sm focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#E8EAED' }}
          />
          <div className="text-sm font-bold" style={{ color: '#E8EAED' }}>RECHECK Mode:</div>
          <div className="rounded border overflow-hidden" style={{ borderColor: '#3C4149' }}>
            {MODES.map((opt, i) => {
              const selected = recheckMode === opt.value;
              return (
                <div
                  key={opt.value}
                  className="flex items-center gap-3 px-3 py-3 cursor-pointer hover:opacity-90 transition-opacity"
                  style={{
                    background: selected ? 'rgba(16,185,129,0.08)' : '#2A2F3A',
                    borderBottom: i < MODES.length - 1 ? '1px solid #3C4149' : undefined,
                  }}
                  onClick={() => setRecheckMode(opt.value)}
                >
                  <div className="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0" style={{ borderColor: selected ? '#10B981' : '#6B7280' }}>
                    {selected && <div className="w-2.5 h-2.5 rounded-full" style={{ background: '#10B981' }} />}
                  </div>
                  <span className="text-sm font-semibold whitespace-nowrap" style={{ color: selected ? '#E8EAED' : '#9AA0A6' }}>{opt.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="flex border-t rounded-b overflow-hidden" style={{ borderColor: '#3C4149' }}>
          <button onClick={onCancel} className="flex-1 py-3 text-sm font-semibold transition-opacity hover:opacity-90" style={{ background: '#C35252', color: '#ffffff' }}>✕ Cancel</button>
          <button onClick={() => onSave(delay, recheckMode)} className="flex-1 py-3 text-sm font-semibold transition-opacity hover:opacity-90" style={{ background: '#10B981', color: '#ffffff' }}>✓ OK</button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// ExitPill — reusable inline exit display
// ─────────────────────────────────────────────
interface ExitPillProps {
  block: Block;
  globalIndex: number;
  onEdit: (index: number) => void;
  onRemove: (index: number) => void;
}

function ExitPill({ block, globalIndex, onEdit, onRemove }: ExitPillProps) {
  const name = (block.data.name as string | undefined) || 'Exit';
  const cfg = block.data.exitConfig as StoredExitConfig | undefined;
  const pct = cfg?.percentage != null ? `${Math.round(cfg.percentage * 100)}%` : '50%';
  const mode = cfg?.exitMode ?? 'ABSOLUTE';
  return (
    <div className="flex items-center gap-2 ml-4 mt-1 text-xs px-2 py-1 rounded border border-red-900/50" style={{ background: 'rgba(220,38,38,0.07)' }}>
      <span style={{ color: '#DC2626' }}>↳ 🔴</span>
      <span className="font-semibold flex-1 truncate" style={{ color: '#FCA5A5' }}>{name}</span>
      <span style={{ color: '#10B981' }}>{pct}</span>
      <span style={{ color: mode === 'FLEXIBLE' ? '#3B82F6' : '#9AA0A6' }}>{mode}</span>
      {cfg?.recheckEnabled && <span style={{ color: '#14a0a5' }}>RCHK:{cfg.recheckBarDelay ?? 3}</span>}
      <button onClick={() => onEdit(globalIndex)} title="Configure exit" className="hover:opacity-80 flex-shrink-0"
        style={{ background: '#0d7377', color: '#fff', border: '1px solid #14a0a5', width: 22, height: 22, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11 }}>⚙</button>
      <button onClick={() => onRemove(globalIndex)} title="Remove exit" className="hover:opacity-80 flex-shrink-0"
        style={{ background: 'rgba(153,27,27,0.7)', color: '#FCA5A5', border: '1px solid #C35252', width: 22, height: 22, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11 }}>✕</button>
    </div>
  );
}

// ─────────────────────────────────────────────
// BlockCard  (Issues #3, #6: exit hierarchy)
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
  // Exits bound to this block (BLOCK-level binding)
  blockExits: { block: Block; globalIndex: number }[];
  // Exits bound to a specific signal in this block: key = signal name
  signalExits: Map<string, { block: Block; globalIndex: number }[]>;
  onEditExit: (index: number) => void;
  onRemoveExit: (index: number) => void;
}

const TEAL_BTN: React.CSSProperties = {
  background: '#0d7377', color: '#ffffff', border: '1px solid #14a0a5',
  width: 28, height: 28, borderRadius: 4,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  fontSize: 13, cursor: 'pointer', flexShrink: 0,
};

function BlockCard({
  block, index, total,
  onMoveUp, onMoveDown, onRemove, onConfig,
  onToggleRecheck, onConfigRecheck, onRemoveRecheck, onDuplicateSignal,
  blockExits, signalExits, onEditExit, onRemoveExit,
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
    <div className="rounded border border-[#3C4149] mb-3" style={{ background: '#1E2128', borderLeft: `4px solid ${leftBorderColor}` }}>
      {/* Header: icon + name + badge + arrows */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[#3C4149]/60">
        <span className="flex-shrink-0 text-base" style={{ color: '#6B7280' }}>📊</span>
        <span className="flex-1 text-sm font-semibold truncate" style={{ color: '#A0AEC0' }} title={blockName}>{blockName}</span>
        <span className="text-xs px-2 py-0.5 rounded font-mono flex-shrink-0" style={badgeStyle}>{badgeLabel}</span>
        <div className="flex items-center gap-0.5 flex-shrink-0" onClick={e => e.stopPropagation()}>
          <button onClick={() => onMoveUp(index)} disabled={index === 0} title="Move block up"
            className="p-1 rounded hover:text-[#E8EAED] hover:bg-[#2A2F3A] disabled:opacity-25 disabled:cursor-not-allowed text-xs transition-colors"
            style={{ color: '#9AA0A6' }}>▲</button>
          <button onClick={() => onMoveDown(index)} disabled={index === total - 1} title="Move block down"
            className="p-1 rounded hover:text-[#E8EAED] hover:bg-[#2A2F3A] disabled:opacity-25 disabled:cursor-not-allowed text-xs transition-colors"
            style={{ color: '#9AA0A6' }}>▼</button>
        </div>
      </div>

      {/* Position # + Config (2+) + Remove */}
      <div className="flex items-center gap-2 px-3 pt-2 pb-1">
        <span className="text-sm font-bold" style={{ color: '#2a5eb8' }}>#{index + 1}</span>
        <div className="flex-1" />
        {index > 0 && (
          <button onClick={() => onConfig(index)} title="Configure timing constraint"
            className="text-xs px-3 py-1.5 rounded font-medium transition-colors hover:opacity-80 flex-shrink-0"
            style={{ background: '#2a5eb8', color: '#ffffff', border: '1px solid #1a4a9a' }}>⚙ Config</button>
        )}
        <button onClick={() => onRemove(index)} title="Remove this block"
          className="text-xs px-3 py-1.5 rounded font-medium transition-colors hover:opacity-80 flex-shrink-0"
          style={{ background: 'rgba(153,27,27,0.7)', color: '#FCA5A5', border: '1px solid #C35252' }}>✕ Remove</button>
      </div>

      {/* Signals count */}
      <div className="px-3 pb-2 text-xs" style={{ color: '#9AA0A6' }}>Signals: {signals.length}</div>

      {/* Signals inner box */}
      {signals.length > 0 && (
        <div className="mx-3 mb-2 rounded border border-[#3C4149]/60" style={{ background: '#15191E' }}>
          <div className="px-3 py-2.5 space-y-2">
            <div className="text-xs font-semibold mb-1" style={{ color: '#A0AEC0' }}>Signals:</div>
            {signals.map((sig, si) => {
              const sigLogic = (sig.logic as string | undefined) ?? logic;
              const hasRecheck = sig.recheckEnabled || sig.recheck_config?.enabled;
              const hasTiming = !!sig.timing_constraint;
              const logicColor = sigLogic === 'OR' ? '#60A5FA' : '#4ADE80';
              const sigExits = signalExits.get(sig.name) ?? [];

              return (
                <div key={si} className="space-y-1">
                  {/* Signal row */}
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
                      <button onClick={() => onToggleRecheck(index, si)} title="Enable recheck on delayed candles"
                        className="text-xs px-2.5 py-1 rounded whitespace-nowrap flex-shrink-0 transition-colors hover:opacity-80"
                        style={{ background: '#0d7377', color: '#ffffff', border: '1px solid #14a0a5', fontSize: 11 }}>
                        Recheck On Delayed Candles
                      </button>
                    )}
                  </div>

                  {/* Recheck sub-row */}
                  {hasRecheck && (
                    <div className="flex items-center gap-1.5 ml-3 text-xs">
                      <span style={{ color: '#14a0a5' }}>↳</span>
                      <span className="flex-1 font-semibold" style={{ color: '#14a0a5' }}>
                        RECHECK ({sig.recheck_config?.mode ?? 'WITHIN'} {sig.recheck_config?.bar_delay ?? 3} bars)
                      </span>
                      <button onClick={() => onConfigRecheck(index, si)} title="Configure recheck" style={TEAL_BTN}>⚙</button>
                      <button onClick={() => onDuplicateSignal(index, si)} title="Duplicate signal" style={TEAL_BTN}>📋</button>
                      <button onClick={() => onRemoveRecheck(index, si)} title="Remove recheck" style={TEAL_BTN}>✕</button>
                    </div>
                  )}

                  {/* Signal-level exit conditions (Issue #3 / #6) */}
                  {sigExits.map(({ block: eb, globalIndex: gi }) => (
                    <ExitPill key={gi} block={eb} globalIndex={gi} onEdit={onEditExit} onRemove={onRemoveExit} />
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {signals.length === 0 && (
        <div className="px-3 pb-2">
          <span className="text-xs italic" style={{ color: '#6B7280' }}>No signals — configure this block</span>
        </div>
      )}

      {/* Block-level exit conditions (Issue #6) */}
      {blockExits.length > 0 && (
        <div className="mx-3 mb-3 space-y-1">
          <div className="text-xs font-semibold" style={{ color: '#9AA0A6' }}>Block Exit Conditions:</div>
          {blockExits.map(({ block: eb, globalIndex: gi }) => (
            <ExitPill key={gi} block={eb} globalIndex={gi} onEdit={onEditExit} onRemove={onRemoveExit} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// ExitConditionsSection (Issue #4: add ⚙ edit button; only STRATEGY exits)
// ─────────────────────────────────────────────
interface ExitConditionsSectionProps {
  strategyExits: { block: Block; globalIndex: number }[];
  onRemove: (index: number) => void;
  onEdit: (index: number) => void;
}

function ExitConditionsSection({ strategyExits, onRemove, onEdit }: ExitConditionsSectionProps) {
  return (
    <div className="border-t flex-shrink-0" style={{ borderColor: '#3C4149' }}>
      <div className="px-4 py-2 flex items-center justify-between" style={{ background: 'rgba(30,33,40,0.6)' }}>
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#9AA0A6' }}>
          🔴 Strategy Exit Conditions
        </span>
        <span className="text-xs" style={{ color: '#6B7280' }}>{strategyExits.length} exit block{strategyExits.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="px-4 pb-3">
        {strategyExits.length === 0 ? (
          <p className="text-xs italic" style={{ color: '#6B7280' }}>
            No strategy-wide exit conditions. Add exit blocks with STRATEGY binding from the library.
          </p>
        ) : (
          <div className="space-y-2">
            {strategyExits.map(({ block, globalIndex }) => {
              const name = (block.data.name as string | undefined) || 'Exit Condition';
              const signals = (block.data.signals as BlockSignal[] | undefined) ?? [];
              const cfg = block.data.exitConfig as StoredExitConfig | undefined;
              const pct = cfg?.percentage != null ? `${Math.round(cfg.percentage * 100)}%` : '50%';
              const mode = cfg?.exitMode ?? 'ABSOLUTE';
              return (
                <div key={block.id} className="rounded border border-red-900/40 px-3 py-2" style={{ background: 'rgba(42,47,58,0.6)' }}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-red-300 font-semibold text-xs truncate">🔴 {name}</span>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <button onClick={() => onEdit(globalIndex)} title="Configure exit condition"
                        className="hover:opacity-80"
                        style={{ background: '#0d7377', color: '#fff', border: '1px solid #14a0a5', width: 22, height: 22, borderRadius: 3, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11 }}>⚙</button>
                      <button onClick={() => onRemove(globalIndex)} title="Remove exit condition"
                        className="hover:text-red-400 text-xs" style={{ color: '#6B7280' }}>✕</button>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 mt-1 flex-wrap text-xs" style={{ color: '#9AA0A6' }}>
                    <span><span style={{ color: '#6B7280' }}>Exit:</span> <span className="font-semibold" style={{ color: '#10B981' }}>{pct}</span></span>
                    <span><span style={{ color: '#6B7280' }}>Mode:</span> <span className="font-semibold" style={{ color: mode === 'FLEXIBLE' ? '#3B82F6' : '#E8EAED' }}>{mode}</span></span>
                    {cfg?.recheckEnabled && <span style={{ color: '#14a0a5' }}>RECHECK: {cfg.recheckBarDelay ?? 3} bars</span>}
                    {signals.length > 0 && <span style={{ color: '#6B7280' }}>({signals.length} signal{signals.length !== 1 ? 's' : ''})</span>}
                  </div>
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
  const { currentStrategy, deleteBlock, reorderBlocks, updateBlock } = useStrategyStore();

  const blocks: Block[] = currentStrategy?.blocks ?? [];

  const [timingDialogIndex, setTimingDialogIndex] = useState<number | null>(null);
  const [recheckTarget, setRecheckTarget] = useState<{ blockIndex: number; signalIndex: number } | null>(null);
  // Issue #4: editing an exit condition
  const [editingExitIndex, setEditingExitIndex] = useState<number | null>(null);

  const handleMoveUp = useCallback(
    (index: number) => { if (index > 0) reorderBlocks(index, index - 1); },
    [reorderBlocks]
  );
  const handleMoveDown = useCallback(
    (index: number) => { if (index < blocks.length - 1) reorderBlocks(index, index + 1); },
    [blocks.length, reorderBlocks]
  );
  const handleRemove = useCallback((index: number) => { deleteBlock(index); }, [deleteBlock]);
  const handleConfig = useCallback((index: number) => { setTimingDialogIndex(index); }, []);

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

  const handleConfigRecheck = useCallback((blockIndex: number, signalIndex: number) => {
    setRecheckTarget({ blockIndex, signalIndex });
  }, []);

  const handleRemoveRecheck = useCallback(
    (blockIndex: number, signalIndex: number) => {
      const block = blocks[blockIndex];
      if (!block) return;
      const signals = [...((block.data.signals as BlockSignal[] | undefined) ?? [])];
      if (!signals[signalIndex]) return;
      signals[signalIndex] = { ...signals[signalIndex], recheckEnabled: false, recheck_config: { enabled: false } };
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
      signals.splice(signalIndex + 1, 0, { ...signals[signalIndex] });
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
      signals[signalIndex] = { ...signals[signalIndex], recheckEnabled: true, recheck_config: { enabled: true, bar_delay: barDelay, mode } };
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

  // Issue #4: save edited exit config
  const handleExitConfigSave = useCallback(
    (config: ExitConditionConfig) => {
      if (editingExitIndex === null) return;
      updateBlock(editingExitIndex, { ...(blocks[editingExitIndex]?.data ?? {}), exitConfig: config });
      setEditingExitIndex(null);
    },
    [editingExitIndex, blocks, updateBlock]
  );

  // ── Exit bucket separation (Issues #3, #6) ──
  // Only EXIT_CONDITION blocks are displayed hierarchically based on bindingLevel.
  const exitBlocksAll = blocks
    .map((b, i) => ({ block: b, globalIndex: i }))
    .filter(({ block }) => block.type === BlockType.EXIT_CONDITION || (block.data.logic as string) === 'EXIT');

  const strategyExits = exitBlocksAll.filter(({ block }) => {
    const cfg = block.data.exitConfig as StoredExitConfig | undefined;
    return !cfg || cfg.bindingLevel === 'STRATEGY' || !cfg.bindingLevel;
  });

  // Per main block: BLOCK-bound exits (keyed by blockName)
  const blockExitsByName = new Map<string, { block: Block; globalIndex: number }[]>();
  // Per main block+signal: SIGNAL-bound exits (keyed by blockName::signalName)
  const signalExitsByKey = new Map<string, { block: Block; globalIndex: number }[]>();

  for (const entry of exitBlocksAll) {
    const cfg = entry.block.data.exitConfig as StoredExitConfig | undefined;
    if (!cfg) continue;
    if (cfg.bindingLevel === 'BLOCK' && cfg.blockName) {
      const arr = blockExitsByName.get(cfg.blockName) ?? [];
      arr.push(entry);
      blockExitsByName.set(cfg.blockName, arr);
    } else if (cfg.bindingLevel === 'SIGNAL' && cfg.blockName && cfg.parentSignalName) {
      const key = `${cfg.blockName}::${cfg.parentSignalName}`;
      const arr = signalExitsByKey.get(key) ?? [];
      arr.push(entry);
      signalExitsByKey.set(key, arr);
    }
  }

  const mainBlocks = blocks.filter(
    b => b.type !== BlockType.EXIT_CONDITION && (b.data.logic as string) !== 'EXIT'
  );

  const timingBlock = timingDialogIndex !== null ? blocks[timingDialogIndex] : null;
  const availableRefs = blocks
    .filter((_, i) => i !== timingDialogIndex)
    .map(b => ({
      displayName: `#${b.index + 1} ${(b.data.name as string | undefined) || BLOCK_TYPE_LABELS[b.type] || b.type}`,
      referenceId: b.id,
    }));

  // Build available blocks for exit edit dialog
  const availableBlocksForDialog: AvailableBlock[] = mainBlocks.map(b => ({
    id: b.id,
    name: (b.data.name as string | undefined) ?? b.id,
    signals: ((b.data.signals as Array<{ name: string }> | undefined) ?? []).map(s => s.name),
  }));

  // Existing config for the exit being edited
  const editingExitConfig: ExitConditionConfig | undefined = editingExitIndex !== null
    ? (() => {
        const cfg = blocks[editingExitIndex]?.data.exitConfig as StoredExitConfig | undefined;
        if (!cfg) return undefined;
        return {
          signalName: cfg.signalName ?? '',
          percentage: cfg.percentage ?? 0.5,
          exitMode: (cfg.exitMode as 'ABSOLUTE' | 'FLEXIBLE') ?? 'ABSOLUTE',
          bindingLevel: (cfg.bindingLevel as 'STRATEGY' | 'BLOCK' | 'SIGNAL') ?? 'STRATEGY',
          tpProximityThreshold: cfg.tpProximityThreshold ?? 2.0,
          reversalTrigger: cfg.reversalTrigger ?? 0.5,
          recheckEnabled: cfg.recheckEnabled ?? false,
          recheckBarDelay: cfg.recheckBarDelay ?? 3,
          blockName: cfg.blockName,
          parentSignalName: cfg.parentSignalName,
        };
      })()
    : undefined;

  return (
    <div className="flex flex-col h-full" style={{ background: '#15191E' }}>
      {/* Header */}
      <div className="px-4 py-2.5 border-b flex items-center justify-between flex-shrink-0" style={{ borderColor: '#3C4149', background: 'rgba(30,33,40,0.5)' }}>
        <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#A0AEC0' }}>Strategy Building Blocks</h2>
        <span className="text-xs px-2 py-0.5 rounded-full border" style={{ color: '#9AA0A6', background: '#2A2F3A', borderColor: '#3C4149' }}>{blocks.length}</span>
      </div>

      {/* Block list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 min-h-0" style={{ scrollbarWidth: 'thin', scrollbarColor: '#3C4149 transparent' }}>
        {mainBlocks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center gap-2">
            <div className="text-3xl opacity-20">📦</div>
            <p className="text-sm" style={{ color: '#9AA0A6' }}>No building blocks added yet</p>
            <p className="text-xs" style={{ color: '#6B7280' }}>Use the library on the right to add blocks</p>
          </div>
        ) : (
          mainBlocks.map(block => {
            const globalIndex = blocks.indexOf(block);
            const bName = (block.data.name as string | undefined) ?? '';
            const bExits = blockExitsByName.get(bName) ?? [];
            // Build per-signal exit map for this block
            const sigExitMap = new Map<string, { block: Block; globalIndex: number }[]>();
            for (const [key, entries] of signalExitsByKey.entries()) {
              if (key.startsWith(`${bName}::`)) {
                const sigName = key.slice(bName.length + 2);
                sigExitMap.set(sigName, entries);
              }
            }
            return (
              <BlockCard
                key={block.id}
                block={block}
                index={globalIndex}
                total={blocks.length}
                onMoveUp={handleMoveUp}
                onMoveDown={handleMoveDown}
                onRemove={handleRemove}
                onConfig={handleConfig}
                onToggleRecheck={handleToggleRecheck}
                onConfigRecheck={handleConfigRecheck}
                onRemoveRecheck={handleRemoveRecheck}
                onDuplicateSignal={handleDuplicateSignal}
                blockExits={bExits}
                signalExits={sigExitMap}
                onEditExit={setEditingExitIndex}
                onRemoveExit={handleRemove}
              />
            );
          })
        )}
      </div>

      {/* Strategy Exit Conditions (STRATEGY binding only) */}
      <ExitConditionsSection
        strategyExits={strategyExits}
        onRemove={handleRemove}
        onEdit={setEditingExitIndex}
      />

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

      {/* Exit Condition Edit Dialog (Issue #4) */}
      {editingExitIndex !== null && (
        <ExitConditionDialog
          open={true}
          signalName={editingExitConfig?.signalName ?? (blocks[editingExitIndex]?.data.name as string | undefined) ?? ''}
          availableBlocks={availableBlocksForDialog}
          existing={editingExitConfig}
          onSave={handleExitConfigSave}
          onCancel={() => setEditingExitIndex(null)}
        />
      )}
    </div>
  );
}

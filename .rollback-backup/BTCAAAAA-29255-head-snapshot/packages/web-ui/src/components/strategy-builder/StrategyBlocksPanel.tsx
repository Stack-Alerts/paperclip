'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block, BlockType } from '@/lib/strategy-builder/types';
import { TimingConstraintDialog, TimingConstraint } from './TimingConstraintDialog';
import { ExitConditionDialog, ExitConditionConfig, AvailableBlock } from './ExitConditionDialog';
import { RichTooltip, TooltipContent } from './RichTooltip';

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

// ─── Tooltip content constants ────────────────────────────────────────────────
const TT_MOVE_UP: TooltipContent = {
  title: 'Move Block Up',
  body: 'Shift this block earlier in the strategy evaluation sequence.',
  sections: [
    { header: 'Why order matters:', items: [
      'Blocks are evaluated in order — an AND block that fails early short-circuits later blocks',
      'Timing constraints reference prior blocks by position, so reordering can break them',
    ]},
    { header: 'Note:', items: ['A confirmation dialog appears if either block has timing constraints referencing the other'] },
  ],
};
const TT_MOVE_DOWN: TooltipContent = {
  title: 'Move Block Down',
  body: 'Shift this block later in the strategy evaluation sequence.',
  sections: [
    { header: 'Why order matters:', items: [
      'Later blocks can reference earlier blocks in timing constraints',
      'AND blocks evaluated later are checked only after all earlier required blocks pass',
    ]},
    { header: 'Note:', items: ['A confirmation dialog appears if either block has timing constraints referencing the other'] },
  ],
};
const TT_TIMING_CONFIG: TooltipContent = {
  title: 'Configure Timing Constraint',
  body: 'Links this block to a prior block by requiring its signal to fire within a specified candle window after the reference block\'s signal.',
  sections: [
    { header: 'How it works:', items: [
      'Select a reference block and set a max candle count',
      'This block\'s signals are only valid if the reference signal fired within N candles',
      'Enforces sequential confirmation — useful for pattern + oscillator setups',
    ]},
    { header: 'Example:', items: ['MACD cross must fire within 5 candles of a Break of Structure signal'] },
    { header: 'Requires:', items: ['At least one prior block in the strategy (first block cannot have a timing constraint)'] },
  ],
};
const TT_REMOVE_BLOCK: TooltipContent = {
  title: 'Remove Building Block',
  body: 'Removes this block and all its signals from the strategy.',
  sections: [
    { header: 'What is removed:', items: [
      'All signals and their RECHECK configurations',
      'Timing constraints referencing or originating from this block',
      'Block-level exit conditions bound to this block',
    ]},
    { header: 'Note:', items: ['Re-add from the library if removed by mistake — signal selections will need to be reconfigured'] },
  ],
};
const TT_RECHECK_CONFIG: TooltipContent = {
  title: 'Configure RECHECK Validation',
  body: 'Requires this signal to reoccur within a specified bar window after its initial fire before confirming the entry.',
  sections: [
    { header: 'Why use RECHECK:', items: [
      'Prevents acting on single-bar spikes or stale signals',
      'Demands that the condition persists — increasing confidence in the entry',
      'Especially useful for oscillator-based and pattern signals that can produce noise',
    ]},
    { header: 'RECHECK modes:', items: [
      'WITHIN N bars — signal must reoccur anywhere in the next N bars',
      'AT bar N — signal must reoccur at exactly bar N after the initial fire',
    ]},
    { header: 'Indicator (green dot):', items: ['The green dot means RECHECK is currently active on this signal'] },
  ],
};
const TT_DUPLICATE_SIGNAL: TooltipContent = {
  title: 'Duplicate Signal',
  body: 'Creates a copy of this signal within the same block with independent RECHECK and timing settings.',
  sections: [
    { header: 'Use when:', items: [
      'You need the same signal type with different RECHECK bar delays',
      'Building confirmation layers using the same indicator at different sensitivities',
    ]},
    { header: 'Note:', items: ['The duplicate starts with RECHECK disabled — configure it separately after duplication'] },
  ],
};
const TT_REMOVE_SIGNAL: TooltipContent = {
  title: 'Remove Signal',
  body: 'Removes this individual signal output from the block.',
  sections: [
    { header: 'Effect:', items: [
      'The block remains in the strategy — only this specific signal is removed',
      'If all signals are removed, the block contributes no entry conditions to the evaluation',
    ]},
    { header: 'Note:', items: ['Re-add by expanding the block in the library and selecting signals again'] },
  ],
};
const TT_REMOVE_RECHECK: TooltipContent = {
  title: 'Remove RECHECK',
  body: 'Disables the RECHECK validation requirement on this signal.',
  sections: [
    { header: 'Effect:', items: [
      'The signal fires on its first occurrence without requiring reoccurrence confirmation',
      'Increases signal frequency but may introduce more noise',
    ]},
    { header: 'Tip:', items: ['Click the ⚙ gear icon to re-enable or change the RECHECK configuration at any time'] },
  ],
};
const TT_EDIT_EXIT: TooltipContent = {
  title: 'Edit Exit Condition',
  body: 'Opens the Exit Condition dialog to modify this exit rule\'s percentage, mode, binding level, and recheck settings.',
  sections: [
    { header: 'Configurable fields:', items: [
      'Exit percentage — profit or loss threshold that triggers the close',
      'Mode: ABSOLUTE (fixed %) or FLEXIBLE (TP proximity + reversal trigger)',
      'Binding level: Strategy (all positions), Block (this block only), Signal (one signal)',
      'RECHECK — optionally require the exit signal to reconfirm before closing',
    ]},
  ],
};
const TT_DUPLICATE_EXIT: TooltipContent = {
  title: 'Duplicate Exit Condition',
  body: 'Creates an identical copy of this exit rule with all settings preserved.',
  sections: [
    { header: 'Use when:', items: [
      'Setting up tiered exits at different percentages (e.g. 25% and 50% targets)',
      'Creating exit rules for multiple binding levels from the same base configuration',
    ]},
    { header: 'Tip:', items: ['Edit the duplicate immediately after creation to adjust the percentage or binding'] },
  ],
};
const TT_REMOVE_EXIT: TooltipContent = {
  title: 'Remove Exit Condition',
  body: 'Permanently removes this exit rule from the strategy.',
  sections: [
    { header: 'Impact:', items: [
      'This position management rule will no longer apply during backtesting or live trading',
      'Other exit conditions at different binding levels remain unaffected',
    ]},
    { header: 'Caution:', items: ['Ensure at least one exit condition or risk management block remains to close positions'] },
  ],
};
const TT_FIND_IN_LIBRARY: TooltipContent = {
  title: 'Find in Library',
  body: 'Highlights and scrolls to this block\'s definition in the Available Building Blocks panel.',
  sections: [
    { header: 'Use when:', items: [
      'You want to review all available signals for this block',
      'Adding additional signals from the same block to the strategy',
      'Checking signal descriptions or occurrence statistics',
    ]},
  ],
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
// RecheckConfigModal — always opened via ⚙, includes enable/disable toggle
// ─────────────────────────────────────────────
interface RecheckConfigModalProps {
  open: boolean;
  signalName: string;
  enabled: boolean;
  barDelay: number;
  mode: string;
  onSave: (enabled: boolean, barDelay: number, mode: string) => void;
  onCancel: () => void;
}

function RecheckConfigModal({ open, signalName, enabled, barDelay, mode, onSave, onCancel }: RecheckConfigModalProps) {
  const [isEnabled, setIsEnabled] = useState(enabled);
  const [delay, setDelay] = useState(barDelay);
  const [recheckMode, setRecheckMode] = useState(mode);

  useEffect(() => {
    if (open) { setIsEnabled(enabled); setDelay(barDelay); setRecheckMode(mode); }
  }, [open, enabled, barDelay, mode]);

  if (!open) return null;

  const MODES = [
    { value: 'WITHIN', label: 'WITHIN bar window (signal reoccurs anywhere within N bars)' },
    { value: 'AT',     label: 'AT exact bar (signal reoccurs at exactly bar N)' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded border shadow-2xl w-[620px]" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        {/* Title bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b rounded-t" style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}>
          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Configure RECHECK Validation</span>
          <div className="flex items-center gap-1">
            <span className="w-5 h-5 rounded text-xs flex items-center justify-center" style={{ background: 'var(--border)', color: 'var(--text-secondary)' }}>─</span>
            <span className="w-5 h-5 rounded text-xs flex items-center justify-center" style={{ background: 'var(--border)', color: 'var(--text-secondary)' }}>□</span>
            <button onClick={onCancel} className="w-5 h-5 rounded text-xs flex items-center justify-center hover:opacity-80" style={{ background: 'var(--accent-red-dark)', color: 'var(--text-primary)' }}>✕</button>
          </div>
        </div>

        {/* Body */}
        <div className="px-4 pt-4 pb-3 space-y-3">
          <div className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>Signal: {formatSignalName(signalName)}</div>

          {/* Enable toggle */}
          <div
            className="flex items-center gap-3 px-3 py-2.5 rounded border cursor-pointer"
            style={{ background: isEnabled ? 'rgba(16,185,129,0.08)' : 'var(--bg-card)', borderColor: isEnabled ? 'var(--accent-green)' : 'var(--border)' }}
            onClick={() => setIsEnabled(v => !v)}
          >
            <div className="w-10 h-5 rounded-full flex items-center px-0.5 transition-colors flex-shrink-0"
              style={{ background: isEnabled ? 'var(--accent-green)' : 'var(--text-faint)' }}>
              <div className="w-4 h-4 rounded-full bg-white shadow transition-transform"
                style={{ transform: isEnabled ? 'translateX(20px)' : 'translateX(0)' }} />
            </div>
            <span className="text-sm font-semibold" style={{ color: isEnabled ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
              {isEnabled ? 'RECHECK Enabled' : 'RECHECK Disabled — click to enable'}
            </span>
          </div>

          {isEnabled && (
            <>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Enter number of bars within which signal must reoccur for validation:
              </p>
              <input
                type="number" min={1} max={200} value={delay}
                onChange={e => setDelay(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-full px-3 py-2 rounded border text-sm focus:outline-none"
                style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
              />
              <div className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>RECHECK Mode:</div>
              <div className="rounded border overflow-hidden" style={{ borderColor: 'var(--border)' }}>
                {MODES.map((opt, i) => {
                  const selected = recheckMode === opt.value;
                  return (
                    <div
                      key={opt.value}
                      className="flex items-center gap-3 px-3 py-3 cursor-pointer hover:opacity-90 transition-opacity"
                      style={{
                        background: selected ? 'rgba(16,185,129,0.08)' : 'var(--bg-card)',
                        borderBottom: i < MODES.length - 1 ? '1px solid var(--border)' : undefined,
                      }}
                      onClick={() => setRecheckMode(opt.value)}
                    >
                      <div className="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0" style={{ borderColor: selected ? 'var(--accent-green)' : 'var(--text-muted)' }}>
                        {selected && <div className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--accent-green)' }} />}
                      </div>
                      <span className="text-sm font-semibold whitespace-nowrap" style={{ color: selected ? 'var(--text-primary)' : 'var(--text-secondary)' }}>{opt.label}</span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex border-t rounded-b overflow-hidden" style={{ borderColor: 'var(--border)' }}>
          <button onClick={onCancel} className="flex-1 py-3 text-sm font-semibold transition-opacity hover:opacity-90" style={{ background: 'var(--accent-red)', color: 'var(--btn-primary-text)' }}>✕ Cancel</button>
          <button onClick={() => onSave(isEnabled, delay, recheckMode)} className="flex-1 py-3 text-sm font-semibold transition-opacity hover:opacity-90" style={{ background: 'var(--accent-green)', color: 'var(--btn-primary-text)' }}>✓ OK</button>
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
  onDuplicate: (index: number) => void;
  onHighlightInLibrary?: (definitionId: string) => void;
}

function ExitPill({ block, globalIndex, onEdit, onRemove, onDuplicate, onHighlightInLibrary }: ExitPillProps) {
  const name = (block.data.name as string | undefined) || 'Exit';
  const cfg = block.data.exitConfig as StoredExitConfig | undefined;
  const definitionId = block.data.definitionId as string | undefined;
  const canHighlight = !!(definitionId && onHighlightInLibrary);
  const pct = cfg?.percentage != null ? `${Math.round(cfg.percentage * 100)}%` : '50%';
  const mode = cfg?.exitMode ?? 'ABSOLUTE';
  return (
    <div className="flex items-center gap-2 ml-3 mt-1 text-xs pl-2 py-1 rounded border border-red-900/50" style={{ background: 'rgba(220,38,38,0.07)' }}>
      <span style={{ color: 'var(--accent-red)' }}>↳ 🔴</span>
      <span className="flex-1 min-w-0 truncate" style={{ color: 'var(--text-primary)' }}>
        <span
          className={`font-semibold${canHighlight ? ' hover:text-sky-300 transition-colors' : ''}`}
          style={{ cursor: canHighlight ? 'pointer' : 'default' }}
          onClick={() => { if (canHighlight) onHighlightInLibrary!(definitionId!); }}
        >{name}</span>
        {cfg?.signalName && cfg.signalName !== name && (
          <span
            className={`ml-1${canHighlight ? ' hover:text-sky-300 transition-colors' : ''}`}
            style={{ color: 'var(--text-dim)', cursor: canHighlight ? 'pointer' : 'default' }}
            onClick={() => { if (canHighlight) onHighlightInLibrary!(definitionId!); }}
          >→ {formatSignalName(cfg.signalName)}</span>
        )}
      </span>
      <span style={{ color: 'var(--accent-green)' }}>{pct}</span>
      <span style={{ color: mode === 'FLEXIBLE' ? 'var(--accent-blue)' : 'var(--text-secondary)' }}>{mode}</span>
      {cfg?.recheckEnabled && <span style={{ color: 'var(--accent-teal)' }}>RCHK:{cfg.recheckBarDelay ?? 3}</span>}
      <div style={BTN_GROUP}>
        <RichTooltip content={TT_EDIT_EXIT}>
          <button onClick={() => onEdit(globalIndex)} className="hover:opacity-80" style={GEAR_STYLE}><GearIcon /></button>
        </RichTooltip>
        <RichTooltip content={TT_DUPLICATE_EXIT}>
          <button onClick={() => onDuplicate(globalIndex)} className="hover:opacity-80" style={DUP_STYLE}><DupIcon /></button>
        </RichTooltip>
        <RichTooltip content={TT_REMOVE_EXIT}>
          <button onClick={() => onRemove(globalIndex)} className="hover:opacity-80" style={REM_STYLE}><XIcon /></button>
        </RichTooltip>
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
  mainIndex: number;
  mainTotal: number;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  onRemove: (index: number) => void;
  onConfig: (index: number) => void;
  onConfigRecheck: (blockIndex: number, signalIndex: number) => void;
  onRemoveRecheck: (blockIndex: number, signalIndex: number) => void;
  onDuplicateSignal: (blockIndex: number, signalIndex: number) => void;
  onRemoveSignal: (blockIndex: number, signalIndex: number) => void;
  onHighlightInLibrary: (definitionId: string) => void;
  blockExits: { block: Block; globalIndex: number }[];
  signalExits: Map<string, { block: Block; globalIndex: number }[]>;
  onEditExit: (index: number) => void;
  onRemoveExit: (index: number) => void;
  onDuplicateExit: (index: number) => void;
}

// Unified 20×20 icon button — all action buttons use this base
const ICON_BTN: React.CSSProperties = {
  width: 20, height: 20, borderRadius: 3, flexShrink: 0,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  cursor: 'pointer', border: 'none',
};

// Fixed-width container for 3-button icon groups: 3×20px + 2×6px gaps = 72px
// All rows use this so buttons align in a vertical grid across the panel
const BTN_GROUP: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 6,
  width: 72, flexShrink: 0, justifyContent: 'flex-end',
};

// Ghost-style button variants — subtle tint so action buttons don't compete with content
const GEAR_STYLE: React.CSSProperties = { ...ICON_BTN, background: 'rgba(13,115,119,0.14)', color: 'rgba(20,160,165,0.85)', border: '1px solid rgba(20,160,165,0.28)' };
const DUP_STYLE: React.CSSProperties  = { ...ICON_BTN, background: 'rgba(14,165,233,0.08)', color: 'rgba(56,189,248,0.75)', border: '1px solid rgba(14,165,233,0.22)' };
const REM_STYLE: React.CSSProperties  = { ...ICON_BTN, background: 'rgba(153,27,27,0.10)', color: 'rgba(252,165,165,0.70)', border: '1px solid rgba(195,82,82,0.22)' };

const BTN: React.CSSProperties = {
  height: 24, borderRadius: 3,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  fontSize: 11, cursor: 'pointer', flexShrink: 0, padding: '0 8px', fontWeight: 600,
};

function DupIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="3.5" y="0.5" width="8" height="8" rx="1.2" style={{ stroke: 'var(--accent-teal)', strokeWidth: 1.2, fill: 'none' }}/>
      <rect x="0.5" y="3.5" width="8" height="8" rx="1.2" style={{ stroke: 'var(--accent-sky)', strokeWidth: 1.2, fill: 'rgba(10,20,35,0.85)' }}/>
    </svg>
  );
}

function GearIcon({ size = 11 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 10.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" fill="currentColor"/>
      <path d="M6.5 1.5l-.8 1.6a5.5 5.5 0 00-1.1.65l-1.76-.4L1.5 5l1.2 1.4a5.6 5.6 0 000 1.2L1.5 9l1.34 1.65 1.76-.4c.33.25.7.47 1.1.65l.8 1.6h2l.8-1.6c.4-.18.77-.4 1.1-.65l1.76.4L14.5 9l-1.2-1.4c.04-.4.04-.8 0-1.2l1.2-1.4-1.34-1.65-1.76.4a5.5 5.5 0 00-1.1-.65L9.5 1.5h-3z"
        stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round" fill="none"/>
    </svg>
  );
}

function XIcon({ size = 8 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" fill="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="1.5" y1="1.5" x2="8.5" y2="8.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
      <line x1="8.5" y1="1.5" x2="1.5" y2="8.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    </svg>
  );
}

function BlockCard({
  block, index, mainIndex, mainTotal,
  onMoveUp, onMoveDown, onRemove, onConfig,
  onConfigRecheck, onRemoveRecheck, onDuplicateSignal, onRemoveSignal,
  onHighlightInLibrary,
  blockExits, signalExits, onEditExit, onRemoveExit, onDuplicateExit,
}: BlockCardProps) {
  const blockName = (block.data.name as string | undefined) || BLOCK_TYPE_LABELS[block.type] || block.type;
  const logic = (block.data.logic as string | undefined) ?? 'AND';
  const signals = (block.data.signals as BlockSignal[] | undefined) ?? [];
  const isExit = block.type === BlockType.EXIT_CONDITION || logic === 'EXIT';
  const definitionId = block.data.definitionId as string | undefined;

  const badgeStyle: React.CSSProperties = isExit
    ? { background: 'rgba(153,27,27,0.6)', color: 'var(--text-primary)', border: '1px solid var(--accent-red-deeper)' }
    : logic === 'OR'
    ? { background: 'var(--accent-green-mid)', color: 'var(--btn-primary-text)', border: '1px solid var(--accent-green-dark)' }
    : { background: 'var(--accent-blue-mid)', color: 'var(--btn-primary-text)', border: '1px solid var(--accent-blue-dark)' };

  const badgeLabel = isExit ? 'EXIT' : logic === 'OR' ? 'OPTIONAL' : 'REQUIRED';
  const leftBorderColor = isExit ? 'var(--accent-red)' : logic === 'OR' ? 'var(--accent-green)' : 'var(--accent-blue)';
  const cardBg = isExit
    ? 'color-mix(in srgb, var(--accent-red-dark) 80%, var(--bg-deep))'
    : logic === 'OR'
    ? 'color-mix(in srgb, var(--accent-green-dark) 80%, var(--bg-deep))'
    : 'color-mix(in srgb, var(--accent-blue-dark) 60%, var(--bg-deep))';

  return (
    <div className="rounded border border-[var(--border)] mb-3" style={{ background: cardBg, borderLeft: `4px solid ${leftBorderColor}` }}>
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[var(--border)]">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="flex-shrink-0">
          <rect x="1" y="9" width="4" height="6" rx="0.5" style={{ fill: 'var(--accent-blue)' }}/>
          <rect x="6" y="5" width="4" height="10" rx="0.5" style={{ fill: 'var(--accent-green)' }}/>
          <rect x="11" y="7" width="4" height="8" rx="0.5" style={{ fill: 'var(--accent-blue)', opacity: 0.55 }}/>
        </svg>
        <RichTooltip content={definitionId ? TT_FIND_IN_LIBRARY : { title: blockName }}>
          <span
            className="flex-1 text-sm font-semibold truncate hover:text-sky-300 transition-colors"
            style={{ color: 'var(--text-dim)', cursor: definitionId ? 'pointer' : 'default' }}
            onClick={() => { if (definitionId) onHighlightInLibrary(definitionId); }}
          >
            {blockName}
          </span>
        </RichTooltip>
        <span className="text-xs px-2 py-0.5 rounded font-mono flex-shrink-0" style={badgeStyle}>{badgeLabel}</span>
        <div className="flex items-center gap-0.5 flex-shrink-0" onClick={e => e.stopPropagation()}>
          <RichTooltip content={TT_MOVE_UP}>
            <button onClick={() => onMoveUp(index)} disabled={mainIndex === 0}
              className="p-1 rounded hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] disabled:opacity-25 disabled:cursor-not-allowed text-xs transition-colors"
              style={{ color: 'var(--text-secondary)' }}>▲</button>
          </RichTooltip>
          <RichTooltip content={TT_MOVE_DOWN}>
            <button onClick={() => onMoveDown(index)} disabled={mainIndex === mainTotal - 1}
              className="p-1 rounded hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)] disabled:opacity-25 disabled:cursor-not-allowed text-xs transition-colors"
              style={{ color: 'var(--text-secondary)' }}>▼</button>
          </RichTooltip>
        </div>
      </div>

      {/* Action row: # + Config (always shown) + Remove */}
      <div className="flex items-center gap-2 px-3 pt-2 pb-1">
        <span className="text-sm font-bold" style={{ color: 'var(--accent-blue-mid)' }}>#{mainIndex + 1}</span>
        <div className="flex-1" />
        <div className="flex items-center gap-1.5">
          <RichTooltip content={TT_TIMING_CONFIG}>
            <button
              onClick={() => onConfig(index)}
              disabled={mainIndex === 0}
              className="hover:opacity-80 disabled:opacity-30 disabled:cursor-not-allowed transition-opacity"
              style={{ ...BTN, background: 'var(--accent-blue-mid)', color: 'var(--btn-primary-text)', border: '1px solid var(--accent-blue-dark)', gap: 5 }}
            ><GearIcon size={11} /> Config</button>
          </RichTooltip>
          <RichTooltip content={TT_REMOVE_BLOCK}>
            <button
              onClick={() => onRemove(index)}
              className="hover:opacity-80 transition-opacity"
              style={{ ...BTN, background: 'rgba(153,27,27,0.7)', color: 'var(--text-primary)', border: '1px solid var(--accent-red)', gap: 5 }}
            ><XIcon size={9} /> Remove</button>
          </RichTooltip>
        </div>
      </div>

      <div className="px-3 pb-2 text-xs" style={{ color: 'var(--text-secondary)' }}>Signals: {signals.length}</div>

      {signals.length > 0 && (
        <div className="mx-3 mb-2 rounded border border-[var(--border)]" style={{ background: 'var(--bg-deep)' }}>
          <div className="px-3 py-2.5 space-y-2">
            <div className="text-xs font-semibold mb-1" style={{ color: 'var(--text-dim)' }}>Signals:</div>
            {signals.map((sig, si) => {
              const sigLogic = (sig.logic as string | undefined) ?? logic;
              const hasRecheck = sig.recheckEnabled || sig.recheck_config?.enabled;
              const hasTiming = !!sig.timing_constraint;
              const logicColor = sigLogic === 'OR' ? 'var(--accent-blue-bright)' : 'var(--accent-green-bright)';
              const sigExits = signalExits.get(sig.name) ?? [];

              return (
                <div key={si} className="space-y-1">
                  <div className="flex items-center gap-1.5 text-xs">
                    <span className="flex-1 min-w-0">
                      <span
                        className="hover:text-sky-300 transition-colors"
                        style={{ color: 'var(--text-primary)', cursor: definitionId ? 'pointer' : 'default' }}
                        onClick={() => { if (definitionId) onHighlightInLibrary(definitionId); }}
                      >
                        {si + 1}. {formatSignalName(sig.name)}
                      </span>
                      <span className="font-mono font-semibold ml-1.5" style={{ color: logicColor }}>[{sigLogic}]</span>
                      {hasTiming && (
                        <span className="ml-2" style={{ color: 'var(--accent-orange)' }}>
                          ⏱ Within {sig.timing_constraint?.max_candles} candles
                          {sig.timing_constraint?.reference_signal ? ` of ${sig.timing_constraint.reference_signal}` : ''}
                        </span>
                      )}
                    </span>
                    <div style={BTN_GROUP}>
                      <RichTooltip content={TT_RECHECK_CONFIG}>
                        <div className="relative" style={{ display: 'inline-flex' }}>
                          <button
                            onClick={() => onConfigRecheck(index, si)}
                            className="hover:opacity-80"
                            style={GEAR_STYLE}>
                            <GearIcon />
                          </button>
                          {hasRecheck && (
                            <span className="absolute -top-px -right-px w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent-green)', border: '1px solid var(--bg-deep)' }} />
                          )}
                        </div>
                      </RichTooltip>
                      <RichTooltip content={TT_DUPLICATE_SIGNAL}>
                        <button onClick={() => onDuplicateSignal(index, si)} className="hover:opacity-80"
                          style={DUP_STYLE}><DupIcon /></button>
                      </RichTooltip>
                      <RichTooltip content={TT_REMOVE_SIGNAL}>
                        <button onClick={() => onRemoveSignal(index, si)} className="hover:opacity-80"
                          style={REM_STYLE}><XIcon /></button>
                      </RichTooltip>
                    </div>
                  </div>

                  {sigExits.map(({ block: eb, globalIndex: gi }) => (
                    <ExitPill key={gi} block={eb} globalIndex={gi} onEdit={onEditExit} onRemove={onRemoveExit} onDuplicate={onDuplicateExit} onHighlightInLibrary={onHighlightInLibrary} />
                  ))}

                  {hasRecheck && (
                    <div className="flex items-center gap-1.5 ml-3 text-xs">
                      <span style={{ color: 'var(--accent-teal)' }}>↳</span>
                      <span className="flex-1 font-semibold" style={{ color: 'var(--accent-teal)' }}>
                        RECHECK ({sig.recheck_config?.mode ?? 'WITHIN'} {sig.recheck_config?.bar_delay ?? 3} bars)
                      </span>
                      <RichTooltip content={TT_REMOVE_RECHECK}>
                        <button onClick={() => onRemoveRecheck(index, si)} className="hover:opacity-80"
                          style={REM_STYLE}><XIcon /></button>
                      </RichTooltip>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {signals.length === 0 && (
        <div className="px-3 pb-2">
          <span className="text-xs italic" style={{ color: 'var(--text-muted)' }}>No signals — configure this block</span>
        </div>
      )}

      {blockExits.length > 0 && (
        <div className="mx-3 mb-3 rounded border border-[var(--border)] px-3 py-2 space-y-1" style={{ background: 'var(--bg-deep)' }}>
          <div className="text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>Block Exit Conditions:</div>
          {blockExits.map(({ block: eb, globalIndex: gi }) => (
            <ExitPill key={gi} block={eb} globalIndex={gi} onEdit={onEditExit} onRemove={onRemoveExit} onDuplicate={onDuplicateExit} onHighlightInLibrary={onHighlightInLibrary} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
// ExitConditionsSection
// ─────────────────────────────────────────────
interface ExitConditionsSectionProps {
  strategyExits: { block: Block; globalIndex: number }[];
  onRemove: (index: number) => void;
  onEdit: (index: number) => void;
  onDuplicate: (index: number) => void;
  onHighlightInLibrary: (definitionId: string) => void;
}

function ExitConditionsSection({ strategyExits, onRemove, onEdit, onDuplicate, onHighlightInLibrary }: ExitConditionsSectionProps) {
  return (
    <div className="border-t flex-shrink-0" style={{ borderColor: 'var(--border)' }}>
      <div className="px-4 py-2 flex items-center justify-between" style={{ background: 'color-mix(in srgb, var(--bg-panel) 60%, transparent)' }}>
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
          🔴 Strategy Exit Conditions
        </span>
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{strategyExits.length} exit block{strategyExits.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="px-4 pb-3">
        {strategyExits.length === 0 ? (
          <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>
            No strategy-wide exit conditions. Add exit blocks with STRATEGY binding from the library.
          </p>
        ) : (
          <div className="space-y-2">
            {strategyExits.map(({ block, globalIndex }) => {
              const name = (block.data.name as string | undefined) || 'Exit Condition';
              const signals = (block.data.signals as BlockSignal[] | undefined) ?? [];
              const cfg = block.data.exitConfig as StoredExitConfig | undefined;
              const defId = block.data.definitionId as string | undefined;
              const pct = cfg?.percentage != null ? `${Math.round(cfg.percentage * 100)}%` : '50%';
              const mode = cfg?.exitMode ?? 'ABSOLUTE';
              return (
                <div key={block.id} className="rounded border border-red-900/40 px-3 py-2" style={{ background: 'color-mix(in srgb, var(--bg-card) 60%, transparent)' }}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 min-w-0 flex-1">
                      <span
                        className={`font-semibold text-xs flex-shrink-0${defId ? ' transition-colors' : ''}`}
                        style={{ color: 'var(--accent-red)' }}
                        onMouseEnter={defId ? e => { (e.currentTarget as HTMLSpanElement).style.color = 'var(--accent-sky)'; } : undefined}
                        onMouseLeave={defId ? e => { (e.currentTarget as HTMLSpanElement).style.color = 'var(--accent-red)'; } : undefined}
                        style={{ cursor: defId ? 'pointer' : 'default' }}
                        onClick={() => { if (defId) onHighlightInLibrary(defId); }}
                      >🔴 {name}</span>
                      {cfg?.signalName && cfg.signalName !== name && (
                        <span
                          className={`text-xs truncate${defId ? ' hover:text-sky-300 transition-colors' : ''}`}
                          style={{ color: 'var(--text-dim)', cursor: defId ? 'pointer' : 'default' }}
                          onClick={() => { if (defId) onHighlightInLibrary(defId); }}
                        >→ {formatSignalName(cfg.signalName)}</span>
                      )}
                      {(cfg?.blockName) && (
                        <span className="text-xs px-1.5 py-0.5 rounded flex-shrink-0" style={{ background: 'color-mix(in srgb, var(--accent-blue) 10%, transparent)', color: 'var(--accent-blue-bright)', border: '1px solid color-mix(in srgb, var(--accent-blue) 20%, transparent)' }}>
                          {cfg.blockName}{cfg.parentSignalName ? ` → ${formatSignalName(cfg.parentSignalName)}` : ''}
                        </span>
                      )}
                    </div>
                    <div style={BTN_GROUP}>
                      <RichTooltip content={TT_EDIT_EXIT}>
                        <button onClick={() => onEdit(globalIndex)} className="hover:opacity-80" style={GEAR_STYLE}><GearIcon /></button>
                      </RichTooltip>
                      <RichTooltip content={TT_DUPLICATE_EXIT}>
                        <button onClick={() => onDuplicate(globalIndex)} className="hover:opacity-80" style={DUP_STYLE}><DupIcon /></button>
                      </RichTooltip>
                      <RichTooltip content={TT_REMOVE_EXIT}>
                        <button onClick={() => onRemove(globalIndex)} className="hover:opacity-80" style={REM_STYLE}><XIcon /></button>
                      </RichTooltip>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 mt-1 flex-wrap text-xs" style={{ color: 'var(--text-secondary)' }}>
                    <span><span style={{ color: 'var(--text-muted)' }}>Exit:</span> <span className="font-semibold" style={{ color: 'var(--accent-green)' }}>{pct}</span></span>
                    <span><span style={{ color: 'var(--text-muted)' }}>Mode:</span> <span className="font-semibold" style={{ color: mode === 'FLEXIBLE' ? 'var(--accent-blue)' : 'var(--text-primary)' }}>{mode}</span></span>
                    {cfg?.recheckEnabled && <span style={{ color: 'var(--accent-teal)' }}>RECHECK: {cfg.recheckBarDelay ?? 3} bars</span>}
                    {signals.length > 0 && <span style={{ color: 'var(--text-muted)' }}>({signals.length} signal{signals.length !== 1 ? 's' : ''})</span>}
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
// ReorderConfirmModal
// ─────────────────────────────────────────────
interface ReorderConfirmProps {
  fromName: string;
  toName: string;
  direction: 'up' | 'down';
  onConfirm: () => void;
  onCancel: () => void;
}

function ReorderConfirmModal({ fromName, toName, direction, onConfirm, onCancel }: ReorderConfirmProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded border shadow-2xl w-[480px]" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border)', background: 'var(--bg-card)' }}>
          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Reorder Building Blocks</span>
        </div>
        <div className="px-4 py-4 space-y-2.5">
          <p className="text-sm" style={{ color: 'var(--text-primary)' }}>
            Move <span className="font-semibold" style={{ color: 'var(--accent-sky)' }}>{fromName}</span>{' '}
            {direction === 'up' ? 'before' : 'after'}{' '}
            <span className="font-semibold" style={{ color: 'var(--accent-sky)' }}>{toName}</span>?
          </p>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            If either block has timing constraints that reference the other, those constraints will need to be reconfigured to maintain strategy integrity.
          </p>
        </div>
        <div className="flex border-t overflow-hidden" style={{ borderColor: 'var(--border)' }}>
          <button onClick={onCancel} className="flex-1 py-2.5 text-sm font-semibold hover:opacity-80" style={{ background: 'var(--accent-red)', color: 'var(--btn-primary-text)' }}>✕ Cancel</button>
          <button onClick={onConfirm} className="flex-1 py-2.5 text-sm font-semibold hover:opacity-80" style={{ background: 'var(--accent-green)', color: 'var(--btn-primary-text)' }}>✓ Confirm</button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// StrategyBlocksPanel (main export)
// ─────────────────────────────────────────────
export function StrategyBlocksPanel() {
  const { currentStrategy, deleteBlock, reorderBlocks, updateBlock, duplicateBlock, highlightLibraryBlock } = useStrategyStore();

  const blocks: Block[] = currentStrategy?.blocks ?? [];

  const [timingDialogIndex, setTimingDialogIndex] = useState<number | null>(null);
  const [recheckTarget, setRecheckTarget] = useState<{ blockIndex: number; signalIndex: number } | null>(null);
  const [editingExitIndex, setEditingExitIndex] = useState<number | null>(null);
  const [reorderConfirm, setReorderConfirm] = useState<{
    fromIndex: number; toIndex: number; fromName: string; toName: string; direction: 'up' | 'down';
  } | null>(null);

  // Compute main-block-only global indices for correct up/down behaviour
  const mainBlockIndices = blocks
    .map((b, i) => ({ b, i }))
    .filter(({ b }) => b.type !== BlockType.EXIT_CONDITION && (b.data.logic as string) !== 'EXIT')
    .map(({ i }) => i);

  const handleMoveUp = useCallback(
    (globalIndex: number) => {
      const latestBlocks = useStrategyStore.getState().currentStrategy?.blocks ?? [];
      const mbi = latestBlocks
        .map((b, i) => ({ b, i }))
        .filter(({ b }) => b.type !== BlockType.EXIT_CONDITION && (b.data.logic as string) !== 'EXIT')
        .map(({ i }) => i);
      const pos = mbi.indexOf(globalIndex);
      if (pos <= 0) return;
      const targetIndex = mbi[pos - 1];
      const fromName = (latestBlocks[globalIndex]?.data.name as string | undefined) || 'Block';
      const toName = (latestBlocks[targetIndex]?.data.name as string | undefined) || 'Block';
      setReorderConfirm({ fromIndex: globalIndex, toIndex: targetIndex, fromName, toName, direction: 'up' });
    },
    []
  );

  const handleMoveDown = useCallback(
    (globalIndex: number) => {
      const latestBlocks = useStrategyStore.getState().currentStrategy?.blocks ?? [];
      const mbi = latestBlocks
        .map((b, i) => ({ b, i }))
        .filter(({ b }) => b.type !== BlockType.EXIT_CONDITION && (b.data.logic as string) !== 'EXIT')
        .map(({ i }) => i);
      const pos = mbi.indexOf(globalIndex);
      if (pos < 0 || pos >= mbi.length - 1) return;
      const targetIndex = mbi[pos + 1];
      const fromName = (latestBlocks[globalIndex]?.data.name as string | undefined) || 'Block';
      const toName = (latestBlocks[targetIndex]?.data.name as string | undefined) || 'Block';
      setReorderConfirm({ fromIndex: globalIndex, toIndex: targetIndex, fromName, toName, direction: 'down' });
    },
    []
  );

  const handleConfirmReorder = useCallback(() => {
    if (!reorderConfirm) return;
    reorderBlocks(reorderConfirm.fromIndex, reorderConfirm.toIndex);
    setReorderConfirm(null);
  }, [reorderConfirm, reorderBlocks]);

  const handleRemove = useCallback((index: number) => { deleteBlock(index); }, [deleteBlock]);
  const handleConfig = useCallback((index: number) => { setTimingDialogIndex(index); }, []);

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
      signals.splice(signalIndex + 1, 0, {
        ...signals[signalIndex],
        recheckEnabled: false,
        recheck_config: { enabled: false },
      });
      updateBlock(blockIndex, { signals });
    },
    [blocks, updateBlock]
  );

  const handleRemoveSignal = useCallback(
    (blockIndex: number, signalIndex: number) => {
      const block = blocks[blockIndex];
      if (!block) return;
      const signals = [...((block.data.signals as BlockSignal[] | undefined) ?? [])];
      signals.splice(signalIndex, 1);
      updateBlock(blockIndex, { signals });
    },
    [blocks, updateBlock]
  );

  const handleDuplicateExit = useCallback(
    (exitGlobalIndex: number) => {
      duplicateBlock(exitGlobalIndex, exitGlobalIndex + 1);
    },
    [duplicateBlock]
  );

  const handleRecheckConfigSave = useCallback(
    (enabled: boolean, barDelay: number, mode: string) => {
      if (!recheckTarget) return;
      const { blockIndex, signalIndex } = recheckTarget;
      const block = blocks[blockIndex];
      if (!block) return;
      const signals = [...((block.data.signals as BlockSignal[] | undefined) ?? [])];
      if (!signals[signalIndex]) return;
      signals[signalIndex] = {
        ...signals[signalIndex],
        recheckEnabled: enabled,
        recheck_config: { enabled, ...(enabled ? { bar_delay: barDelay, mode } : {}) },
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

  const handleExitConfigSave = useCallback(
    (config: ExitConditionConfig) => {
      if (editingExitIndex === null) return;
      const latestBlocks = useStrategyStore.getState().currentStrategy?.blocks ?? [];
      updateBlock(editingExitIndex, { ...(latestBlocks[editingExitIndex]?.data ?? {}), exitConfig: config });
      setEditingExitIndex(null);
    },
    [editingExitIndex, updateBlock]
  );

  // Exit bucket separation
  const exitBlocksAll = blocks
    .map((b, i) => ({ block: b, globalIndex: i }))
    .filter(({ block }) => block.type === BlockType.EXIT_CONDITION || (block.data.logic as string) === 'EXIT');

  const strategyExits = exitBlocksAll.filter(({ block }) => {
    const cfg = block.data.exitConfig as StoredExitConfig | undefined;
    return !cfg || cfg.bindingLevel === 'STRATEGY' || !cfg.bindingLevel;
  });

  const blockExitsByName = new Map<string, { block: Block; globalIndex: number }[]>();
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

  const availableBlocksForDialog: AvailableBlock[] = mainBlocks.map(b => ({
    id: b.id,
    name: (b.data.name as string | undefined) ?? b.id,
    signals: ((b.data.signals as Array<{ name: string }> | undefined) ?? []).map(s => s.name),
  }));

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
    <div className="flex flex-col h-full" style={{ background: 'var(--bg-deep)' }}>
      {/* Header */}
      <div className="px-4 py-2.5 border-b flex items-center justify-between flex-shrink-0" style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--bg-panel) 50%, transparent)' }}>
        <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-dim)' }}>Strategy Building Blocks</h2>
        <span className="text-xs px-2 py-0.5 rounded-full border" style={{ color: 'var(--text-secondary)', background: 'var(--bg-card)', borderColor: 'var(--border)' }}>{blocks.length}</span>
      </div>

      {/* Block list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 min-h-0" style={{ scrollbarWidth: 'thin', scrollbarColor: 'var(--border) transparent' }}>
        {mainBlocks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center gap-2">
            <div className="text-3xl opacity-20">📦</div>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>No building blocks added yet</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Use the library on the right to add blocks</p>
          </div>
        ) : (
          mainBlocks.map((block, mi) => {
            const globalIndex = blocks.indexOf(block);
            const bName = (block.data.name as string | undefined) ?? '';
            const bExits = blockExitsByName.get(bName) ?? [];
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
                mainIndex={mi}
                mainTotal={mainBlocks.length}
                onMoveUp={handleMoveUp}
                onMoveDown={handleMoveDown}
                onRemove={handleRemove}
                onConfig={handleConfig}
                onConfigRecheck={handleConfigRecheck}
                onRemoveRecheck={handleRemoveRecheck}
                onDuplicateSignal={handleDuplicateSignal}
                onRemoveSignal={handleRemoveSignal}
                onHighlightInLibrary={highlightLibraryBlock}
                blockExits={bExits}
                signalExits={sigExitMap}
                onEditExit={setEditingExitIndex}
                onRemoveExit={handleRemove}
                onDuplicateExit={handleDuplicateExit}
              />
            );
          })
        )}
      </div>

      <ExitConditionsSection
        strategyExits={strategyExits}
        onRemove={handleRemove}
        onEdit={setEditingExitIndex}
        onDuplicate={handleDuplicateExit}
        onHighlightInLibrary={highlightLibraryBlock}
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
            enabled={!!(sig?.recheckEnabled || sig?.recheck_config?.enabled)}
            barDelay={sig?.recheck_config?.bar_delay ?? 3}
            mode={sig?.recheck_config?.mode ?? 'WITHIN'}
            onSave={handleRecheckConfigSave}
            onCancel={() => setRecheckTarget(null)}
          />
        );
      })()}

      {/* Exit Condition Edit Dialog */}
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

      {/* Reorder Confirmation Modal */}
      {reorderConfirm && (
        <ReorderConfirmModal
          fromName={reorderConfirm.fromName}
          toName={reorderConfirm.toName}
          direction={reorderConfirm.direction}
          onConfirm={handleConfirmReorder}
          onCancel={() => setReorderConfirm(null)}
        />
      )}
    </div>
  );
}

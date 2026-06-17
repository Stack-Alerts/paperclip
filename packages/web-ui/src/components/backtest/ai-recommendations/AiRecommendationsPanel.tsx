'use client';

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { ChevronDown, ChevronRight, Trash2, GripVertical, X } from 'lucide-react';
import { BacktestResult, Strategy, Trade } from '@/lib/strategy-builder/types';
import { useAiSettings } from '@/hooks/useAiSettings';
import { useAiRecsHistory, AiRecsHistoryEntry, AiRecsHistoryStatus } from '@/hooks/useAiRecsHistory';

type SendPhase =
  | 'idle'
  | 'building-request'
  | 'sending'
  | 'awaiting-provider'
  | 'done'
  | 'error';

interface PhaseInfo {
  percent: number;
  label: string;
}

const PHASE_INFO: Record<Exclude<SendPhase, 'idle' | 'error'>, PhaseInfo> = {
  'building-request': { percent: 15, label: 'Stage 1/4: Packaging request…' },
  sending: { percent: 35, label: 'Stage 2/4: Sending to AI provider…' },
  'awaiting-provider': { percent: 75, label: 'Stage 3/4: Awaiting provider response…' },
  done: { percent: 100, label: 'Stage 4/4: Complete' },
};

const ACTIVE_PHASES: ReadonlySet<SendPhase> = new Set([
  'building-request',
  'sending',
  'awaiting-provider',
]);

export interface AiRecommendationsPanelProps {
  result?: BacktestResult | null;
  strategy?: Strategy | null;
  backtestConfig?: Record<string, unknown> | null;
  disabled?: boolean;
  /**
   * Called with the updated strategy after a successful auto-apply. The
   * parent decides how to refresh the strategy view (e.g. re-fetch from
   * FastAPI, swap local state). Optional so the panel remains usable in
   * read-only / preview contexts.
   */
  onStrategyUpdated?: (strategy: Strategy) => void;
}

function CollapsibleSection({
  title,
  description,
  children,
  defaultOpen = true,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div
      className="rounded mb-2"
      style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
    >
      <button
        className="w-full flex items-center gap-2 px-3 py-2 text-left"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        {open ? (
          <ChevronDown size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
        ) : (
          <ChevronRight size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
        )}
        <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>
          {title}
        </span>
        <span className="text-xs ml-2" style={{ color: 'var(--text-faint)' }}>
          {description}
        </span>
      </button>
      {open && (
        <div className="px-3 pb-3">
          {children}
        </div>
      )}
    </div>
  );
}

function PreviewText({ text }: { text: string }) {
  return (
    <pre
      className="text-xs rounded p-2 overflow-auto max-h-48 whitespace-pre-wrap break-words"
      style={{
        background: 'var(--bg-elevated)',
        color: 'var(--text-muted)',
        border: '1px solid var(--border)',
        fontFamily: 'var(--font-mono, monospace)',
      }}
    >
      {text}
    </pre>
  );
}

function formatStrategyConfig(strategy: Strategy | null | undefined): string {
  if (!strategy) return 'No strategy loaded.';
  return JSON.stringify(
    {
      id: strategy.id,
      name: strategy.name,
      status: strategy.status,
      strategyType: strategy.strategyType,
      blocks: strategy.blocks?.map((b) => ({
        id: b.id,
        type: b.type,
        index: b.index,
        data: b.data,
      })) ?? [],
      settings: strategy.settings,
    },
    null,
    2,
  );
}

function formatBacktestConfig(config: Record<string, unknown> | null | undefined): string {
  if (!config) return 'No backtest configuration available.';
  return JSON.stringify(config, null, 2);
}

function formatTrades(trades: Trade[] | undefined): string {
  if (!trades || trades.length === 0) return '⚠ NO TRADES — AI cannot analyze 0 trades.';
  const preview = trades.slice(0, 10).map((t, i) => `Trade #${i + 1}:\n${JSON.stringify(t, null, 2)}`).join('\n\n');
  const suffix = trades.length > 10 ? `\n\n...and ${trades.length - 10} more trades` : '';
  return `Total Trades: ${trades.length}\n\n${preview}${suffix}`;
}

function formatMetrics(result: BacktestResult | null | undefined): string {
  if (!result) return 'No results yet.';
  return JSON.stringify(
    {
      totalTrades: result.totalTrades,
      winningTrades: result.winningTrades,
      losingTrades: result.losingTrades,
      winRate: result.winRate,
      returnPercentage: result.returnPercentage,
      profitFactor: result.profitFactor,
      sharpeRatio: result.sharpeRatio,
      sortino_ratio: result.sortino_ratio,
      calmar_ratio: result.calmar_ratio,
      maxDrawdown: result.maxDrawdown,
      averageWin: result.averageWin,
      averageLoss: result.averageLoss,
      initialCapital: result.initialCapital,
      finalCapital: result.finalCapital,
    },
    null,
    2,
  );
}

const STATUS_LABELS: Record<AiRecsHistoryStatus, string> = {
  new: 'NEW',
  applied: 'APPLIED',
  dismissed: 'DISMISSED',
};

const STATUS_COLORS: Record<AiRecsHistoryStatus, { bg: string; fg: string; border: string }> = {
  new: { bg: 'var(--bg-elevated)', fg: 'var(--text-muted)', border: 'var(--border)' },
  applied: { bg: 'rgba(34, 197, 94, 0.12)', fg: '#4ade80', border: '#4ade80' },
  dismissed: { bg: 'rgba(248, 113, 113, 0.12)', fg: '#f87171', border: '#f87171' },
};

function StatusBadge({ status }: { status: AiRecsHistoryStatus }) {
  const c = STATUS_COLORS[status];
  return (
    <span
      className="text-[10px] font-semibold uppercase tracking-wide rounded px-1.5 py-0.5"
      style={{ background: c.bg, color: c.fg, border: `1px solid ${c.border}` }}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch {
    return iso;
  }
}

function HistoryCard({
  entry,
  onUpdateStatus,
  onUpdateNotes,
  onRequestDelete,
  onLoadIntoCurrent,
}: {
  entry: AiRecsHistoryEntry;
  onUpdateStatus: (id: string, status: AiRecsHistoryStatus) => void;
  onUpdateNotes: (id: string, notes: string) => void;
  onRequestDelete: (id: string) => void;
  onLoadIntoCurrent: (entry: AiRecsHistoryEntry) => void;
}) {
  const [notesDraft, setNotesDraft] = useState(entry.notes);
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className="rounded p-3 flex flex-col gap-2"
      style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={entry.status} />
          {entry.strategyName && (
            <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
              {entry.strategyName}
            </span>
          )}
        </div>
        <span
          className="text-[10px]"
          style={{ color: 'var(--text-faint)', fontFamily: 'var(--font-mono, monospace)' }}
        >
          {formatTimestamp(entry.createdAt)}
        </span>
      </div>

      <p
        className="text-xs"
        style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono, monospace)' }}
      >
        Prompt: <span style={{ color: 'var(--text-muted)' }}>{entry.prompt}</span>
      </p>

      {entry.summary && (
        <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-muted)' }}>
          {entry.summary}
        </p>
      )}

      <details
        open={expanded}
        onToggle={(e) => setExpanded((e.target as HTMLDetailsElement).open)}
      >
        <summary
          className="text-[10px] cursor-pointer select-none"
          style={{ color: 'var(--text-faint)' }}
        >
          {expanded ? '− Hide details' : '+ Show details'}
        </summary>
        <div className="mt-2 flex flex-col gap-2">
          {entry.diagnosis && (
            <div>
              <p
                className="text-[10px] font-semibold uppercase tracking-wide mb-1"
                style={{ color: 'var(--text-muted)' }}
              >
                Diagnosis
              </p>
              <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                {entry.diagnosis}
              </p>
            </div>
          )}
          {entry.recommendations && (
            <div>
              <p
                className="text-[10px] font-semibold uppercase tracking-wide mb-1"
                style={{ color: 'var(--text-muted)' }}
              >
                Recommendations
              </p>
              <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                {entry.recommendations}
              </p>
            </div>
          )}
          {entry.raw && (
            <div>
              <p
                className="text-[10px] font-semibold uppercase tracking-wide mb-1"
                style={{ color: 'var(--text-muted)' }}
              >
                {entry.diagnosis || entry.recommendations ? 'Full response' : 'Model output'}
              </p>
              <PreviewText text={entry.raw} />
            </div>
          )}
        </div>
      </details>

      <div>
        <label
          className="text-[10px] font-semibold uppercase tracking-wide"
          style={{ color: 'var(--text-muted)' }}
          htmlFor={`notes-${entry.id}`}
        >
          Notes
        </label>
        <textarea
          id={`notes-${entry.id}`}
          value={notesDraft}
          onChange={(e) => setNotesDraft(e.target.value)}
          onBlur={() => {
            if (notesDraft !== entry.notes) onUpdateNotes(entry.id, notesDraft);
          }}
          placeholder="Add notes about this analysis…"
          rows={2}
          className="w-full mt-1 rounded p-2 text-xs"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-mono, monospace)',
            resize: 'vertical',
          }}
        />
      </div>

      <div className="flex items-center gap-2 justify-end flex-wrap">
        <button
          type="button"
          onClick={() => onLoadIntoCurrent(entry)}
          data-testid={`history-load-${entry.id}`}
          title="Load this analysis into the current view — diagnoses, recommendations, and the first rec become the active rec."
          className="px-2 py-1 rounded text-[10px] font-medium"
          style={{
            background: 'var(--accent-blue, #3b82f6)',
            color: '#fff',
            border: '1px solid var(--accent-blue, #3b82f6)',
            cursor: 'pointer',
          }}
        >
          Load into current analysis
        </button>
        <button
          type="button"
          onClick={() => onUpdateStatus(entry.id, 'applied')}
          disabled={entry.status === 'applied'}
          className="px-2 py-1 rounded text-[10px] font-medium"
          style={{
            background:
              entry.status === 'applied' ? 'rgba(34, 197, 94, 0.12)' : 'var(--bg-elevated)',
            color: entry.status === 'applied' ? '#4ade80' : 'var(--text-secondary)',
            border: '1px solid #4ade80',
            cursor: entry.status === 'applied' ? 'default' : 'pointer',
            opacity: entry.status === 'applied' ? 0.7 : 1,
          }}
        >
          Mark applied
        </button>
        <button
          type="button"
          onClick={() => onUpdateStatus(entry.id, 'dismissed')}
          disabled={entry.status === 'dismissed'}
          className="px-2 py-1 rounded text-[10px] font-medium"
          style={{
            background:
              entry.status === 'dismissed' ? 'rgba(248, 113, 113, 0.12)' : 'var(--bg-elevated)',
            color: entry.status === 'dismissed' ? '#f87171' : 'var(--text-secondary)',
            border: '1px solid #f87171',
            cursor: entry.status === 'dismissed' ? 'default' : 'pointer',
            opacity: entry.status === 'dismissed' ? 0.7 : 1,
          }}
        >
          Mark dismissed
        </button>
        <button
          type="button"
          onClick={() => onRequestDelete(entry.id)}
          className="px-2 py-1 rounded text-[10px] font-medium flex items-center gap-1"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--text-muted)',
            border: '1px solid var(--border)',
            cursor: 'pointer',
          }}
          title="Delete this entry"
        >
          <Trash2 size={12} />
          Delete
        </button>
      </div>
    </div>
  );
}

function HistoryView({
  entries,
  hydrated,
  onUpdateStatus,
  onUpdateNotes,
  onRequestDelete,
  onRequestClearAll,
  onLoadIntoCurrent,
}: {
  entries: AiRecsHistoryEntry[];
  hydrated: boolean;
  onUpdateStatus: (id: string, status: AiRecsHistoryStatus) => void;
  onUpdateNotes: (id: string, notes: string) => void;
  onRequestDelete: (id: string) => void;
  onRequestClearAll: () => void;
  onLoadIntoCurrent: (entry: AiRecsHistoryEntry) => void;
}) {
  if (!hydrated) {
    return (
      <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
        Loading history…
      </p>
    );
  }
  if (entries.length === 0) {
    return (
      <div
        className="rounded p-4 text-xs text-center"
        style={{
          background: 'var(--bg-card)',
          color: 'var(--text-faint)',
          border: '1px solid var(--border)',
        }}
      >
        No history yet. Run “Approve & Send to AI” to record your first analysis.
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <p
          className="text-[10px] font-semibold uppercase tracking-wide"
          style={{ color: 'var(--text-muted)' }}
        >
          {entries.length} {entries.length === 1 ? 'entry' : 'entries'} (most recent first)
        </p>
        <button
          type="button"
          onClick={onRequestClearAll}
          className="px-2 py-1 rounded text-[10px] font-medium"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--text-muted)',
            border: '1px solid var(--border)',
            cursor: 'pointer',
          }}
        >
          Clear all
        </button>
      </div>
      {entries.map((entry) => (
        <HistoryCard
          key={entry.id}
          entry={entry}
          onUpdateStatus={onUpdateStatus}
          onUpdateNotes={onUpdateNotes}
          onRequestDelete={onRequestDelete}
          onLoadIntoCurrent={onLoadIntoCurrent}
        />
      ))}
    </div>
  );
}

function ConfirmationModal({
  confirmation,
  onCancel,
  onConfirmClearAll,
  onConfirmDelete,
  onConfirmApplyAll,
}: {
  confirmation: { type: 'clear-all' | 'delete' | 'apply-all'; entryId?: string };
  onCancel: () => void;
  onConfirmClearAll: () => void;
  onConfirmDelete: () => void;
  onConfirmApplyAll: () => void;
}) {
  const isClearAll = confirmation.type === 'clear-all';
  const isApplyAll = confirmation.type === 'apply-all';
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0, 0, 0, 0.6)' }}
      onClick={onCancel}
    >
      <div
        className="rounded p-4 max-w-sm w-full mx-4"
        style={{
          background: 'var(--bg-card)',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-sm font-semibold mb-2">
          {isClearAll
            ? 'Clear all history?'
            : isApplyAll
              ? 'Apply all recommendations?'
              : 'Delete this entry?'}
        </p>
        <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
          {isClearAll
            ? 'This will permanently remove all stored AI recommendation analyses from this browser. This action cannot be undone.'
            : isApplyAll
              ? 'Send the current recommendation set to the AutoApply orchestrator. The Python service will classify each rec, snapshot the strategy, apply safe changes, and verify before persisting. The most recent history entry will be marked APPLIED.'
              : 'This will permanently remove the selected analysis from this browser. This action cannot be undone.'}
        </p>
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: 'var(--bg-elevated)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={
              isClearAll
                ? onConfirmClearAll
                : isApplyAll
                  ? onConfirmApplyAll
                  : onConfirmDelete
            }
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: isApplyAll
                ? 'var(--accent-blue, #3b82f6)'
                : 'var(--accent-red, #f87171)',
              color: '#fff',
              border: `1px solid ${
                isApplyAll
                  ? 'var(--accent-blue, #3b82f6)'
                  : 'var(--accent-red, #f87171)'
              }`,
              cursor: 'pointer',
            }}
          >
            {isClearAll ? 'Clear all' : isApplyAll ? 'Apply all' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Optimization goal (AC7) ──────────────────────────────────────────────

type OptimizationGoalId =
  | 'reduce-losses'
  | 'maximize-returns'
  | 'reduce-drawdown'
  | 'improve-win-rate'
  | 'custom';

interface OptimizationGoalOption {
  id: OptimizationGoalId;
  label: string;
  description: string;
  /** Pre-canned value sent in the payload when this option is chosen. */
  defaultValue: string;
}

const GOAL_OPTIONS: OptimizationGoalOption[] = [
  {
    id: 'reduce-losses',
    label: 'Reduce losses',
    description: 'Prioritize cutting losing trades and trimming risk per position.',
    defaultValue: 'reduce losses',
  },
  {
    id: 'maximize-returns',
    label: 'Maximize returns',
    description: 'Push for higher total return, even at the cost of more trades.',
    defaultValue: 'maximize returns',
  },
  {
    id: 'reduce-drawdown',
    label: 'Reduce drawdown',
    description: 'Cap the worst peak-to-trough equity drop.',
    defaultValue: 'reduce drawdown',
  },
  {
    id: 'improve-win-rate',
    label: 'Improve win rate',
    description: 'Filter for higher-confidence setups that win more often.',
    defaultValue: 'improve win rate',
  },
  {
    id: 'custom',
    label: 'Custom goal',
    description: 'Describe your own optimization target in your own words.',
    defaultValue: '',
  },
];

function OptimizationGoalModal({
  onCancel,
  onConfirm,
}: {
  onCancel: () => void;
  onConfirm: (goal: string) => void;
}) {
  const [selected, setSelected] = useState<OptimizationGoalId>('reduce-losses');
  const [customText, setCustomText] = useState('');
  const customOption = GOAL_OPTIONS.find((g) => g.id === 'custom');
  const selectedOption = GOAL_OPTIONS.find((g) => g.id === selected) ?? GOAL_OPTIONS[0];

  const resolved = selected === 'custom' ? customText.trim() : selectedOption.defaultValue;
  const canConfirm = resolved.length > 0;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="opt-goal-modal-title"
      data-testid="opt-goal-modal"
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0, 0, 0, 0.6)' }}
      onClick={onCancel}
    >
      <div
        className="rounded p-4 max-w-md w-full mx-4"
        style={{
          background: 'var(--bg-card)',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <p
          id="opt-goal-modal-title"
          className="text-sm font-semibold mb-1"
          style={{ color: 'var(--text-secondary)' }}
        >
          Choose an optimization goal
        </p>
        <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
          The AI provider will be told to prioritize this goal when shaping recommendations.
          Pick a preset or describe a custom target.
        </p>

        <div role="radiogroup" aria-label="Optimization goal" className="flex flex-col gap-2 mb-3">
          {GOAL_OPTIONS.map((opt) => {
            const isSelected = selected === opt.id;
            return (
              <label
                key={opt.id}
                className="flex items-start gap-2 rounded p-2 cursor-pointer"
                style={{
                  background: isSelected ? 'var(--bg-elevated)' : 'transparent',
                  border: `1px solid ${isSelected ? 'var(--accent-blue, #3b82f6)' : 'var(--border)'}`,
                }}
              >
                <input
                  type="radio"
                  name="optimization-goal"
                  value={opt.id}
                  checked={isSelected}
                  onChange={() => setSelected(opt.id)}
                  data-testid={`opt-goal-${opt.id}`}
                  className="mt-1"
                  style={{ accentColor: 'var(--accent-blue, #3b82f6)' }}
                />
                <span className="flex flex-col gap-0.5">
                  <span
                    className="text-xs font-semibold"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    {opt.label}
                  </span>
                  <span className="text-[11px]" style={{ color: 'var(--text-faint)' }}>
                    {opt.description}
                  </span>
                </span>
              </label>
            );
          })}
        </div>

        {selected === 'custom' && (
          <div className="mb-3">
            <label
              className="text-[10px] font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-muted)' }}
              htmlFor="opt-goal-custom-text"
            >
              {customOption?.label ?? 'Custom goal'}
            </label>
            <textarea
              id="opt-goal-custom-text"
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              data-testid="opt-goal-custom-text"
              rows={3}
              placeholder="e.g. Reduce overnight exposure while keeping at least 80% of the current total return."
              className="w-full mt-1 rounded p-2 text-xs"
              style={{
                background: 'var(--bg-elevated)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border)',
                fontFamily: 'var(--font-mono, monospace)',
                resize: 'vertical',
              }}
            />
          </div>
        )}

        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            data-testid="opt-goal-cancel"
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: 'var(--bg-elevated)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onConfirm(resolved)}
            disabled={!canConfirm}
            data-testid="opt-goal-confirm"
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: canConfirm ? 'var(--accent-blue, #3b82f6)' : 'var(--bg-elevated)',
              color: canConfirm ? '#fff' : 'var(--text-faint)',
              border: '1px solid var(--border)',
              opacity: canConfirm ? 1 : 0.5,
              cursor: canConfirm ? 'pointer' : 'not-allowed',
            }}
          >
            Send with this goal
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Recommendation parsing & rendering ───────────────────────────────────

interface ParsedRec {
  /** Stable id derived from the rec text (index + hash). */
  id: string;
  title: string;
  summary: string;
  raw: string;
  /** Optional fields extracted from "Confidence: …" / "Rationale: …" lines. */
  confidence?: string;
  rationale?: string;
  /** Key:value parameter suggestions extracted from the block. */
  suggestedParams: Array<{ key: string; value: string }>;
}

/**
 * Extract the value side of a "Label: value" or "**Label**: value" line from
 * a recommendation block. The match is line-bounded so we don't accidentally
 * pull a body paragraph in.
 */
function tryExtractField(block: string, label: string): string | undefined {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(
    `(?:^|\\n)\\s*(?:\\*\\*)?${escaped}(?:\\*\\*)?\\s*[:\\-]\\s*([^\\n]+)`,
    'i',
  );
  const m = block.match(re);
  if (!m) return undefined;
  const value = m[1].trim();
  return value.length === 0 ? undefined : value;
}

function parseSuggestedParams(block: string): Array<{ key: string; value: string }> {
  const params: Array<{ key: string; value: string }> = [];
  const seen = new Set<string>();
  const lines = block.split(/\r?\n/);
  for (const line of lines) {
    const m = line.match(/^\s*-\s*\*\*([^*]+)\*\*\s*[:=]\s*(.+?)\s*$/);
    if (!m) continue;
    const key = m[1].trim();
    const value = m[2].trim();
    if (!key || !value) continue;
    const dedupe = key.toLowerCase();
    if (seen.has(dedupe)) continue;
    seen.add(dedupe);
    params.push({ key, value });
  }
  return params;
}

function deriveTitle(block: string, index: number): string {
  // Try the first markdown heading inside the block.
  const heading = block.match(/^\s*#{1,6}\s+(.+?)\s*$/m);
  if (heading) {
    const t = heading[1].replace(/\*+/g, '').trim();
    if (t.length > 0 && t.length <= 120) return t;
  }
  // Try the first **Bold** prefix.
  const bold = block.match(/^\s*\*\*([^*]+)\*\*/);
  if (bold) {
    const t = bold[1].trim();
    if (t.length > 0 && t.length <= 120) return t;
  }
  // Try "1. Title" / "1) Title" prefix.
  const numbered = block.match(/^\s*\d+[.)]\s+([^\n]{1,120})/);
  if (numbered) {
    const t = numbered[1].replace(/[*_`]/g, '').trim();
    if (t.length > 0) return t;
  }
  // Fallback: first non-empty line, trimmed and capped.
  const firstLine =
    block
      .split(/\r?\n/)
      .map((l) => l.trim())
      .find((l) => l.length > 0) ?? '';
  return firstLine.length === 0
    ? `Recommendation #${index + 1}`
    : firstLine.replace(/[*_`#]/g, '').slice(0, 80) || `Recommendation #${index + 1}`;
}

function deriveSummary(block: string, maxLen = 220): string {
  // Strip headings, list markers, and inline markdown noise to get a one-liner.
  const stripped = block
    .replace(/^\s*#{1,6}\s+.+$/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+[.)]\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
  if (stripped.length === 0) return '';
  if (stripped.length <= maxLen) return stripped;
  return `${stripped.slice(0, maxLen - 1).trimEnd()}…`;
}

function parseSingleRec(block: string, index: number): ParsedRec {
  return {
    id: `rec-${index}-${simpleHash(block)}`,
    title: deriveTitle(block, index),
    summary: deriveSummary(block),
    raw: block.trim(),
    confidence: tryExtractField(block, 'Confidence'),
    rationale: tryExtractField(block, 'Rationale'),
    suggestedParams: parseSuggestedParams(block),
  };
}

function simpleHash(input: string): string {
  let h = 5381;
  for (let i = 0; i < input.length; i++) {
    h = ((h << 5) + h + input.charCodeAt(i)) | 0;
  }
  // Convert to unsigned hex so it's always a stable id substring.
  return (h >>> 0).toString(16);
}

/**
 * Split a free-form recommendations block into individual recs. The model
 * response format is not strictly defined, so we walk a heuristic chain:
 *   1. Numbered list (1., 2., …)
 *   2. Markdown headings (##, ###)
 *   3. Horizontal rule separators (--- / ***)
 *   4. Blank-line paragraph split
 *   5. Fallback: whole block as a single rec
 */
function parseRecommendations(text: string): ParsedRec[] {
  const trimmed = text.trim();
  if (!trimmed) return [];

  const trySplit = (re: RegExp): string[] | null => {
    const parts = trimmed.split(re);
    if (parts.length < 2) return null;
    const nonEmpty = parts.map((p) => p.trim()).filter((p) => p.length > 0);
    return nonEmpty.length >= 2 ? nonEmpty : null;
  };

  // 1) Numbered list: "1." / "1)" at the start of a line.
  const numbered = trySplit(/(?=^\s*\d+[.)]\s+)/gm);
  if (numbered) return numbered.map((b, i) => parseSingleRec(b, i));

  // 2) Markdown headings (##/###) at the start of a line.
  const headed = trySplit(/(?=^\s*#{2,6}\s+)/gm);
  if (headed) return headed.map((b, i) => parseSingleRec(b, i));

  // 3) Horizontal rule separators: --- or *** on their own line.
  const ruleSplit = trySplit(/^\s*(?:---|\*\*\*|___)\s*$/gm);
  if (ruleSplit) return ruleSplit.map((b, i) => parseSingleRec(b, i));

  // 4) Blank-line paragraph split: only treat as multiple recs when the
  //    paragraphs look like a list (each starts with - or *).
  const paragraphs = trimmed
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
  if (paragraphs.length >= 2 && paragraphs.every((p) => /^\s*[-*+]/.test(p))) {
    return paragraphs.map((b, i) => parseSingleRec(b, i));
  }

  // 5) Fallback: whole block as a single rec.
  return [parseSingleRec(trimmed, 0)];
}

function buildRequestPayload(
  result: BacktestResult | null | undefined,
  strategy: Strategy | null | undefined,
  backtestConfig: Record<string, unknown> | null | undefined,
  activeRec: ActiveRec | null = null,
  optimizationGoal: string | null = null,
): string {
  return JSON.stringify(
    {
      strategy_config: strategy
        ? {
            id: strategy.id,
            name: strategy.name,
            strategyType: strategy.strategyType,
            blocks: strategy.blocks ?? [],
            settings: strategy.settings,
          }
        : null,
      backtest_config: backtestConfig ?? null,
      trades: result?.trades ?? [],
      metrics: result
        ? {
            totalTrades: result.totalTrades,
            winRate: result.winRate,
            returnPercentage: result.returnPercentage,
            profitFactor: result.profitFactor,
            sharpeRatio: result.sharpeRatio,
            sortino_ratio: result.sortino_ratio,
            maxDrawdown: result.maxDrawdown,
            averageWin: result.averageWin,
            averageLoss: result.averageLoss,
          }
        : {},
      ...(activeRec
        ? {
            active_recommendation: {
              id: activeRec.id,
              title: activeRec.title,
              raw: activeRec.raw,
              confidence: activeRec.confidence ?? null,
              rationale: activeRec.rationale ?? null,
              suggested_params: activeRec.suggestedParams,
            },
          }
        : {}),
      ...(optimizationGoal
        ? { optimization_goal: optimizationGoal }
        : {}),
    },
    null,
    2,
  );
}

/** Split a model response into DIAGNOSIS / RECOMMENDATIONS sections. */
function parseAnalysisResponse(text: string): {
  diagnosis: string;
  recommendations: string;
  raw: string;
} {
  const diagnosisMatch = text.match(
    /DIAGNOSIS\s*:\s*([\s\S]*?)(?=\n\s*RECOMMENDATIONS\s*:|$)/i,
  );
  const recommendationsMatch = text.match(
    /RECOMMENDATIONS\s*:\s*([\s\S]*?)$/i,
  );
  return {
    diagnosis: diagnosisMatch?.[1]?.trim() ?? '',
    recommendations: recommendationsMatch?.[1]?.trim() ?? '',
    raw: text,
  };
}

interface ActiveRec {
  id: string;
  title: string;
  raw: string;
  confidence?: string;
  rationale?: string;
  suggestedParams: Array<{ key: string; value: string }>;
}

function RecommendationCard({
  rec,
  isActive,
  onApply,
  onClear,
}: {
  rec: ParsedRec;
  isActive: boolean;
  onApply: (rec: ParsedRec) => void;
  onClear: () => void;
}) {
  const [showFull, setShowFull] = useState(false);
  return (
    <div
      data-testid={`rec-card-${rec.id}`}
      className="rounded p-3 flex flex-col gap-2"
      style={{
        background: isActive ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-card)',
        border: `1px solid ${isActive ? 'var(--accent-blue, #3b82f6)' : 'var(--border)'}`,
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5 min-w-0">
          <p
            className="text-xs font-semibold"
            style={{ color: 'var(--text-secondary)' }}
            title={rec.title}
          >
            {rec.title}
          </p>
          {rec.confidence && (
            <span
              className="text-[10px] font-semibold uppercase tracking-wide rounded px-1.5 py-0.5 self-start"
              style={{
                background: 'var(--bg-elevated)',
                color: 'var(--text-muted)',
                border: '1px solid var(--border)',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              Confidence: {rec.confidence}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {isActive ? (
            <button
              type="button"
              onClick={onClear}
              data-testid={`rec-clear-${rec.id}`}
              className="px-2 py-1 rounded text-[10px] font-medium"
              style={{
                background: 'var(--bg-elevated)',
                color: 'var(--text-muted)',
                border: '1px solid var(--border)',
                cursor: 'pointer',
              }}
            >
              <X size={10} style={{ display: 'inline', marginRight: 4 }} />
              Clear
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onApply(rec)}
              data-testid={`rec-apply-${rec.id}`}
              title="Load this recommendation into the active analysis form. It will be included in the next send."
              className="px-2 py-1 rounded text-[10px] font-medium"
              style={{
                background: 'var(--accent-blue, #3b82f6)',
                color: '#fff',
                border: '1px solid var(--accent-blue, #3b82f6)',
                cursor: 'pointer',
              }}
            >
              Apply
            </button>
          )}
        </div>
      </div>

      {rec.summary && (
        <p
          className="text-xs whitespace-pre-wrap"
          style={{ color: 'var(--text-muted)' }}
        >
          {rec.summary}
        </p>
      )}

      {rec.suggestedParams.length > 0 && (
        <div
          className="rounded p-2"
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
          }}
        >
          <p
            className="text-[10px] font-semibold uppercase tracking-wide mb-1"
            style={{ color: 'var(--text-muted)' }}
          >
            Suggested parameters
          </p>
          <ul className="flex flex-col gap-0.5">
            {rec.suggestedParams.map((p) => (
              <li
                key={p.key}
                className="text-[11px]"
                style={{
                  color: 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono, monospace)',
                }}
              >
                <span style={{ color: 'var(--text-faint)' }}>{p.key}</span>
                <span style={{ color: 'var(--text-muted)' }}> = </span>
                <span>{p.value}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="button"
        onClick={() => setShowFull((v) => !v)}
        data-testid={`rec-show-full-${rec.id}`}
        className="text-[10px] cursor-pointer self-start"
        style={{ color: 'var(--text-faint)' }}
      >
        {showFull ? '− Hide full payload' : '+ Show full payload'}
      </button>

      {showFull && (
        <div className="flex flex-col gap-2">
          {rec.rationale && (
            <div>
              <p
                className="text-[10px] font-semibold uppercase tracking-wide mb-1"
                style={{ color: 'var(--text-muted)' }}
              >
                Rationale
              </p>
              <p
                className="text-xs whitespace-pre-wrap"
                style={{ color: 'var(--text-secondary)' }}
              >
                {rec.rationale}
              </p>
            </div>
          )}
          <div>
            <p
              className="text-[10px] font-semibold uppercase tracking-wide mb-1"
              style={{ color: 'var(--text-muted)' }}
            >
              Model output
            </p>
            <PreviewText text={rec.raw} />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Split layout (AC1) ───────────────────────────────────────────────────

const SPLIT_MIN = 30;
const SPLIT_MAX = 65;
const SPLIT_DEFAULT = 40;
const SPLIT_STORAGE_KEY = 'ai_recs_panel_split';
const LEFT_PANEL_MIN_PX = 360;

function SplitPanel({
  left,
  right,
}: {
  left: React.ReactNode;
  right: React.ReactNode;
}) {
  const [splitPercent, setSplitPercent] = useState<number>(SPLIT_DEFAULT);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const isDraggingRef = useRef(false);
  const [hydrated, setHydrated] = useState(false);

  // Load persisted split on mount.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const stored = window.localStorage.getItem(SPLIT_STORAGE_KEY);
      if (stored) {
        const parsed = Number.parseFloat(stored);
        if (Number.isFinite(parsed) && parsed >= SPLIT_MIN && parsed <= SPLIT_MAX) {
          setSplitPercent(parsed);
        }
      }
    } catch {
      // best effort
    }
    setHydrated(true);
  }, []);

  // Persist split on change.
  useEffect(() => {
    if (!hydrated || typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(SPLIT_STORAGE_KEY, String(splitPercent));
    } catch {
      // best effort
    }
  }, [splitPercent, hydrated]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const minPx = LEFT_PANEL_MIN_PX;
      const minPctFromPx = (minPx / rect.width) * 100;
      const effectiveMin = Math.max(SPLIT_MIN, minPctFromPx);
      const clamped = Math.min(
        Math.max((x / rect.width) * 100, effectiveMin),
        SPLIT_MAX,
      );
      setSplitPercent(clamped);
    };
    const onUp = () => {
      if (!isDraggingRef.current) return;
      isDraggingRef.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      data-testid="ai-recs-split-panel"
      className="flex w-full"
      style={{ minHeight: 360 }}
    >
      <div
        className="overflow-auto pr-2"
        style={{
          flexBasis: `${splitPercent}%`,
          flexGrow: 0,
          flexShrink: 0,
          minWidth: LEFT_PANEL_MIN_PX,
        }}
      >
        {left}
      </div>
      <div
        role="separator"
        aria-orientation="vertical"
        aria-valuenow={Math.round(splitPercent)}
        aria-valuemin={SPLIT_MIN}
        aria-valuemax={SPLIT_MAX}
        aria-label="Resize AI recommendations split panel"
        onMouseDown={handleMouseDown}
        data-testid="ai-recs-split-handle"
        className="w-2 cursor-col-resize flex-shrink-0 flex items-center justify-center"
        style={{
          background: 'var(--bg-elevated)',
          borderLeft: '1px solid var(--border)',
          borderRight: '1px solid var(--border)',
        }}
        title="Drag to resize"
      >
        <GripVertical size={12} style={{ color: 'var(--text-faint)' }} />
      </div>
      <div
        className="overflow-auto pl-2"
        style={{ flexBasis: `${100 - splitPercent}%`, flexGrow: 1, flexShrink: 1 }}
      >
        {right}
      </div>
    </div>
  );
}

type View = 'current' | 'history';

const VIEW_LABELS: Record<View, string> = {
  current: 'Current Analysis',
  history: 'History',
};

const AI_RECS_PROMPT =
  'Analyze this trading strategy backtest and return a diagnosis and concrete, actionable recommendations.';

export function AiRecommendationsPanel({
  result,
  strategy,
  backtestConfig,
  onStrategyUpdated,
}: AiRecommendationsPanelProps = {}) {
  const hasTrades = (result?.trades?.length ?? 0) > 0;
  const { settings, hydrated: aiSettingsHydrated } = useAiSettings();
  const history = useAiRecsHistory();

  const [view, setView] = useState<View>('current');
  const [phase, setPhase] = useState<SendPhase>('idle');
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisDetail, setAnalysisDetail] = useState<string | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<{
    diagnosis: string;
    recommendations: string;
    raw: string;
  } | null>(null);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applyDetail, setApplyDetail] = useState<string | null>(null);
  const [applySuccess, setApplySuccess] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
    detail?: string;
  } | null>(null);
  const [confirmation, setConfirmation] = useState<{
    type: 'clear-all' | 'delete' | 'apply-all';
    entryId?: string;
  } | null>(null);
  const [goalModalOpen, setGoalModalOpen] = useState(false);
  const [activeRec, setActiveRec] = useState<ActiveRec | null>(null);
  const [optimizationGoal, setOptimizationGoal] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const dismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
      if (dismissTimerRef.current) {
        clearTimeout(dismissTimerRef.current);
        dismissTimerRef.current = null;
      }
    };
  }, []);

  const analyzing = ACTIVE_PHASES.has(phase);

  const parsedRecs = useMemo(() => {
    if (!aiAnalysis?.recommendations) return [];
    return parseRecommendations(aiAnalysis.recommendations);
  }, [aiAnalysis?.recommendations]);

  const handleExport = useCallback(() => {
    const payload = buildRequestPayload(
      result,
      strategy,
      backtestConfig,
      activeRec,
      optimizationGoal,
    );
    const blob = new Blob([payload], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ai_request_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [result, strategy, backtestConfig, activeRec, optimizationGoal]);

  const handleTestConnection = useCallback(async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch('/api/ai/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: settings.provider,
          model: settings.model,
          apiKey: settings.apiKeys?.[settings.provider] ?? '',
          ollamaBaseUrl: settings.ollamaBaseUrl,
        }),
      });
      const data = await res.json().catch(() => ({}));
      setTestResult({
        ok: !!res.ok && data?.ok !== false,
        message: data?.message ?? (res.ok ? 'Connection succeeded.' : `Request failed (${res.status}).`),
        detail: data?.detail,
      });
    } catch (err) {
      setTestResult({
        ok: false,
        message: err instanceof Error ? err.message : 'Network error contacting /api/ai/test-connection.',
      });
    } finally {
      setTesting(false);
    }
  }, [settings]);

  const handleCancel = useCallback(() => {
    if (!analyzing) return;
    abortRef.current?.abort();
  }, [analyzing]);

  // Refactored to take the goal explicitly so AC7 can pipe the modal value
  // through, and so tests can drive a deterministic code path.
  const runApproveAndSend = useCallback(
    async (goal: string | null) => {
      if (!hasTrades || analyzing) return;
      setAnalysisError(null);
      setAnalysisDetail(null);
      setOptimizationGoal(goal);
      if (dismissTimerRef.current) {
        clearTimeout(dismissTimerRef.current);
        dismissTimerRef.current = null;
      }
      const controller = new AbortController();
      abortRef.current = controller;

      setPhase('building-request');
      await new Promise((r) => setTimeout(r, 0));

      let payload: unknown;
      try {
        const payloadJson = buildRequestPayload(
          result,
          strategy,
          backtestConfig,
          activeRec,
          goal,
        );
        payload = JSON.parse(payloadJson) as unknown;
      } catch (err) {
        setAnalysisError(
          err instanceof Error
            ? `Failed to package request: ${err.message}`
            : 'Failed to package request.',
        );
        setPhase('error');
        abortRef.current = null;
        return;
      }

      if (controller.signal.aborted) {
        setAnalysisError('Request cancelled.');
        setPhase('error');
        abortRef.current = null;
        return;
      }

      setPhase('sending');
      await new Promise((r) => setTimeout(r, 0));

      setPhase('awaiting-provider');

      try {
        const res = await fetch('/api/ai/analyze', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            provider: settings.provider,
            model: settings.model,
            apiKey: settings.apiKeys[settings.provider],
            ollamaBaseUrl: settings.ollamaBaseUrl,
            prompt: AI_RECS_PROMPT,
            payload,
            optimizationGoal: goal,
          }),
          signal: controller.signal,
        });
        const data = (await res.json()) as {
          ok: boolean;
          text?: string;
          error?: string;
          detail?: string;
        };
        if (!res.ok || !data.ok) {
          setAnalysisError(
            data.error ?? `The analyze endpoint returned HTTP ${res.status}.`,
          );
          setAnalysisDetail(data.detail ?? null);
          setPhase('error');
          abortRef.current = null;
          return;
        }
        const parsed = parseAnalysisResponse(data.text ?? '');
        setAiAnalysis(parsed);
        if (history.hydrated) {
          history.add({
            prompt: AI_RECS_PROMPT,
            diagnosis: parsed.diagnosis,
            recommendations: parsed.recommendations,
            raw: parsed.raw,
            ...(strategy?.name ? { strategyName: strategy.name } : {}),
          });
        }
        setPhase('done');
        abortRef.current = null;
        dismissTimerRef.current = setTimeout(() => {
          setPhase((current) => (current === 'done' ? 'idle' : current));
          dismissTimerRef.current = null;
        }, 1200);
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          setAnalysisError('Request cancelled.');
        } else {
          setAnalysisError(
            err instanceof Error ? err.message : 'The analyze request failed.',
          );
        }
        setPhase('error');
        abortRef.current = null;
      }
    },
    [
      hasTrades,
      analyzing,
      result,
      strategy,
      backtestConfig,
      activeRec,
      settings.provider,
      settings.model,
      settings.apiKeys,
      settings.ollamaBaseUrl,
      history,
    ],
  );

  // The Approve & Send button is the AC7 entry point — clicking it opens the
  // optimization-goal modal; the actual analyze fetch runs after the user
  // confirms a goal.
  const handleApproveAndSendClick = useCallback(() => {
    if (!hasTrades || analyzing) return;
    setGoalModalOpen(true);
  }, [hasTrades, analyzing]);

  const handleGoalConfirm = useCallback(
    (goal: string) => {
      setGoalModalOpen(false);
      void runApproveAndSend(goal);
    },
    [runApproveAndSend],
  );

  const handleGoalCancel = useCallback(() => {
    setGoalModalOpen(false);
  }, []);

  // AC2: per-rec Apply → loads into active form.
  const handleApplyRec = useCallback((rec: ParsedRec) => {
    setActiveRec({
      id: rec.id,
      title: rec.title,
      raw: rec.raw,
      ...(rec.confidence ? { confidence: rec.confidence } : {}),
      ...(rec.rationale ? { rationale: rec.rationale } : {}),
      suggestedParams: rec.suggestedParams,
    });
  }, []);

  const handleClearActiveRec = useCallback(() => {
    setActiveRec(null);
  }, []);

  // AC3: history Load → hydrate current analysis view AND set first parsed
  // rec as the active rec so the user can re-send with that context.
  const loadHistoryIntoCurrent = useCallback(
    (entry: AiRecsHistoryEntry) => {
      setAiAnalysis({
        diagnosis: entry.diagnosis,
        recommendations: entry.recommendations,
        raw: entry.raw,
      });
      const recs = parseRecommendations(entry.recommendations);
      const first = recs[0];
      if (first) {
        setActiveRec({
          id: first.id,
          title: first.title,
          raw: first.raw,
          ...(first.confidence ? { confidence: first.confidence } : {}),
          ...(first.rationale ? { rationale: first.rationale } : {}),
          suggestedParams: first.suggestedParams,
        });
      } else {
        setActiveRec(null);
      }
      setView('current');
      setAnalysisError(null);
      setAnalysisDetail(null);
    },
    [],
  );

  const canSend = hasTrades && !analyzing && aiSettingsHydrated;
  const showProgress = phase !== 'idle' && phase !== 'error';
  const progressPercent = phase === 'idle' || phase === 'error' ? 0 : PHASE_INFO[phase as Exclude<SendPhase, 'idle' | 'error'>].percent;
  const progressLabel =
    phase === 'idle' || phase === 'error'
      ? ''
      : PHASE_INFO[phase as Exclude<SendPhase, 'idle' | 'error'>].label;
  const canApply = Boolean(strategy?.id) && !applying;

  const requestClearAll = useCallback(() => {
    if (history.entries.length === 0) return;
    setConfirmation({ type: 'clear-all' });
  }, [history.entries.length]);

  const requestDelete = useCallback((id: string) => {
    setConfirmation({ type: 'delete', entryId: id });
  }, []);

  const cancelConfirmation = useCallback(() => setConfirmation(null), []);

  const confirmClearAll = useCallback(() => {
    history.clear();
    setConfirmation(null);
  }, [history]);

  const confirmDelete = useCallback(() => {
    if (confirmation?.entryId) {
      history.deleteEntry(confirmation.entryId);
    }
    setConfirmation(null);
  }, [confirmation, history]);

  const requestApplyAll = useCallback(() => {
    if (!strategy?.id || applying) return;
    setApplyError(null);
    setApplyDetail(null);
    setApplySuccess(null);
    setConfirmation({ type: 'apply-all' });
  }, [strategy?.id, applying]);

  // The orchestrator at src/optimizer_v3/ui/ai_recs_auto_apply.py is the
  // authority on which recs are safe/destructive/unsupported (BTCAAAAA-36744).
  // Today the webui does not surface a structured recs list yet (the panel
  // shows raw text), so we send `recs: []` and the orchestrator returns an
  // honest "applied_count == 0" / "Nothing to apply" response. The route
  // still has to be exercised end-to-end so the FastAPI proxy + the
  // rollback/verify pipeline stay wired up for the structured-rec UX that
  // is the next iteration.
  const handleApplyAll = useCallback(async () => {
    if (!strategy?.id || applying) return;
    const targetEntryId = history.hydrated ? history.entries[0]?.id : undefined;

    setApplying(true);
    setApplyError(null);
    setApplyDetail(null);
    setApplySuccess(null);

    const headers: Record<string, string> = {
      'content-type': 'application/json',
    };
    if (typeof window !== 'undefined') {
      const token = window.localStorage.getItem('auth_token');
      if (token) headers['authorization'] = `Bearer ${token}`;
    }

    try {
      const res = await fetch('/api/ai/auto-apply', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          strategyId: strategy.id,
          recs: [],
          optInDestructiveIds: null,
        }),
      });
      const data = (await res.json()) as {
        ok: boolean;
        strategy?: Strategy;
        dryRun?: { entries: unknown[]; applicable_count: number };
        apply?: { applied: Array<{ rec_id: string }>; applied_count: number };
        error?: string;
        detail?: string;
      };
      if (!res.ok || !data.ok) {
        setApplyError(data.error ?? `Auto-apply returned HTTP ${res.status}.`);
        setApplyDetail(data.detail ?? null);
        return;
      }
      const appliedCount = data.apply?.applied_count ?? 0;
      setApplySuccess(
        appliedCount > 0
          ? `Applied ${appliedCount} recommendation${appliedCount === 1 ? '' : 's'} to “${strategy.name ?? strategy.id}”.`
          : `Auto-apply ran with nothing to apply — the orchestrator returned 0 changes for “${strategy.name ?? strategy.id}”.`,
      );
      if (targetEntryId) {
        history.updateStatus(targetEntryId, 'applied');
      }
      if (data.strategy && onStrategyUpdated) {
        onStrategyUpdated(data.strategy);
      }
    } catch (err) {
      setApplyError(
        err instanceof Error ? err.message : 'The auto-apply request failed.',
      );
    } finally {
      setApplying(false);
    }
  }, [strategy, applying, history, onStrategyUpdated]);

  const confirmApplyAll = useCallback(() => {
    setConfirmation(null);
    void handleApplyAll();
  }, [handleApplyAll]);

  const currentView = view;

  // ── LEFT pane: config + active-form + Approve flow ──
  const leftPane = (
    <div className="flex flex-col gap-3">
      {/* Active rec banner (AC2 surface) */}
      {activeRec && (
        <div
          data-testid="active-rec-banner"
          className="rounded p-2 text-xs flex flex-col gap-1"
          style={{
            background: 'rgba(59, 130, 246, 0.08)',
            border: '1px solid var(--accent-blue, #3b82f6)',
            color: 'var(--text-secondary)',
          }}
        >
          <div className="flex items-center justify-between gap-2">
            <span
              className="text-[10px] font-semibold uppercase tracking-wide"
              style={{ color: 'var(--accent-blue, #3b82f6)' }}
            >
              Active recommendation
            </span>
            <button
              type="button"
              onClick={handleClearActiveRec}
              data-testid="active-rec-clear"
              className="px-1.5 py-0.5 rounded text-[10px] font-medium"
              style={{
                background: 'var(--bg-elevated)',
                color: 'var(--text-muted)',
                border: '1px solid var(--border)',
                cursor: 'pointer',
              }}
            >
              <X size={10} style={{ display: 'inline', marginRight: 4 }} />
              Clear
            </button>
          </div>
          <p className="text-xs font-semibold">{activeRec.title}</p>
          {activeRec.suggestedParams.length > 0 && (
            <p
              className="text-[11px]"
              style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono, monospace)' }}
            >
              {activeRec.suggestedParams
                .map((p) => `${p.key} = ${p.value}`)
                .join(', ')}
            </p>
          )}
        </div>
      )}

      {/* Optimization goal pill (AC7 surface) */}
      {optimizationGoal && (
        <div
          data-testid="optimization-goal-pill"
          className="rounded p-2 text-[11px]"
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          <span
            className="text-[10px] font-semibold uppercase tracking-wide mr-1"
            style={{ color: 'var(--text-muted)' }}
          >
            Optimization goal:
          </span>
          {optimizationGoal}
        </div>
      )}

      {/* Analysis error banner */}
      {analysisError && (
        <div
          className="rounded p-2 text-xs"
          role="alert"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--accent-red, #f87171)',
            border: '1px solid var(--accent-red, #f87171)',
          }}
        >
          <p className="font-semibold">AI analysis failed</p>
          <p className="mt-1">{analysisError}</p>
          {analysisDetail && (
            <p className="mt-1" style={{ color: 'var(--text-faint)' }}>
              {analysisDetail}
            </p>
          )}
        </div>
      )}

      {/* Auto-apply error banner */}
      {applyError && (
        <div
          className="rounded p-2 text-xs"
          role="alert"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--accent-red, #f87171)',
            border: '1px solid var(--accent-red, #f87171)',
          }}
        >
          <p className="font-semibold">Auto-apply failed</p>
          <p className="mt-1">{applyError}</p>
          {applyDetail && (
            <p className="mt-1" style={{ color: 'var(--text-faint)' }}>
              {applyDetail}
            </p>
          )}
        </div>
      )}

      {/* Auto-apply success banner */}
      {applySuccess && !applyError && (
        <div
          className="rounded p-2 text-xs"
          role="status"
          style={{
            background: 'rgba(34, 197, 94, 0.12)',
            color: '#4ade80',
            border: '1px solid #4ade80',
          }}
        >
          {applySuccess}
        </div>
      )}

      {/* Request Preview header */}
      <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
        REQUEST PREVIEW
      </p>

      <CollapsibleSection
        title="1. Strategy Configuration"
        description="Complete strategy setup including blocks and parameters"
      >
        <PreviewText text={formatStrategyConfig(strategy)} />
      </CollapsibleSection>

      <CollapsibleSection
        title="2. Backtest Configuration"
        description="How the backtest was configured (timeframe, SL/TP, position sizing)"
        defaultOpen={false}
      >
        <PreviewText text={formatBacktestConfig(backtestConfig)} />
      </CollapsibleSection>

      <CollapsibleSection
        title="3. Trade Results"
        description="All trades executed with entry/exit details"
        defaultOpen={false}
      >
        <PreviewText text={formatTrades(result?.trades)} />
      </CollapsibleSection>

      <CollapsibleSection
        title="4. Metrics & Ratings"
        description="Performance metrics"
        defaultOpen={false}
      >
        <PreviewText text={formatMetrics(result)} />
      </CollapsibleSection>

      <CollapsibleSection
        title="5. Available Building Blocks"
        description="Block catalog visible to AI for recommendations"
        defaultOpen={false}
      >
        <PreviewText text="Building blocks catalog is loaded server-side during AI analysis." />
      </CollapsibleSection>

      {/* Stats bar */}
      {result && (
        <div
          className="rounded p-2 text-xs"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--text-muted)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          {(() => {
            const payload = buildRequestPayload(
              result,
              strategy,
              backtestConfig,
              activeRec,
              optimizationGoal,
            );
            const kb = (payload.length / 1024).toFixed(1);
            const tokens = Math.round(payload.length / 4);
            return `Strategy blocks: ${strategy?.blocks?.length ?? 0} | Trades: ${result.totalTrades} | Request size: ${kb} KB (~${tokens} tokens)`;
          })()}
        </div>
      )}

      {/* Progress indicator */}
      {showProgress && (
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          data-testid="ai-recs-progress"
          className="rounded p-2 flex flex-col gap-1"
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
          }}
        >
          <div className="flex items-center justify-between text-xs">
            <span
              data-testid="ai-recs-progress-label"
              style={{ color: 'var(--text-secondary)' }}
            >
              {progressLabel}
            </span>
            <span
              data-testid="ai-recs-progress-percent"
              style={{
                color: 'var(--text-muted)',
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              {progressPercent}%
            </span>
          </div>
          <div
            role="progressbar"
            aria-valuenow={progressPercent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="AI recommendation request progress"
            className="w-full h-1.5 rounded overflow-hidden"
            style={{ background: 'var(--bg-card)' }}
          >
            <div
              data-testid="ai-recs-progress-bar"
              className="h-full rounded"
              style={{
                width: `${progressPercent}%`,
                background:
                  phase === 'done'
                    ? 'var(--accent-green, #10b981)'
                    : 'var(--accent-blue, #3b82f6)',
                transition: 'width 200ms ease-out',
              }}
            />
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 justify-end mt-1 flex-wrap">
        <button
          type="button"
          onClick={handleTestConnection}
          disabled={!aiSettingsHydrated || testing}
          title="Verifies the saved AI provider/model respond to a minimal live request."
          className="px-3 py-1.5 rounded text-xs font-medium"
          style={{
            background: 'var(--bg-card)',
            color: aiSettingsHydrated && !testing ? 'var(--text-secondary)' : 'var(--text-faint)',
            border: '1px solid var(--border)',
            opacity: aiSettingsHydrated && !testing ? 1 : 0.5,
            cursor: aiSettingsHydrated && !testing ? 'pointer' : 'not-allowed',
          }}
        >
          {testing ? 'Testing…' : 'Test Connection'}
        </button>
        <button
          type="button"
          onClick={handleExport}
          disabled={!hasTrades}
          className="px-3 py-1.5 rounded text-xs font-medium"
          style={{
            background: 'var(--bg-card)',
            color: hasTrades ? 'var(--text-secondary)' : 'var(--text-faint)',
            border: '1px solid var(--border)',
            opacity: hasTrades ? 1 : 0.5,
            cursor: hasTrades ? 'pointer' : 'not-allowed',
          }}
        >
          Export to JSON
        </button>
        {analyzing && (
          <button
            type="button"
            onClick={handleCancel}
            data-testid="ai-recs-cancel"
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}
            title="Cancel the in-flight AI request"
          >
            Cancel
          </button>
        )}
        <button
          type="button"
          onClick={handleApproveAndSendClick}
          disabled={!canSend}
          title={
            analyzing
              ? 'Sending the request preview to the configured AI provider…'
              : 'Pick an optimization goal and send the request preview to the configured AI provider.'
          }
          className="px-3 py-1.5 rounded text-xs font-medium"
          style={{
            background: canSend ? 'var(--accent-blue, #3b82f6)' : 'var(--bg-card)',
            color: canSend ? '#fff' : 'var(--text-faint)',
            border: '1px solid var(--border)',
            opacity: canSend ? 1 : 0.5,
            cursor: canSend ? 'pointer' : 'not-allowed',
          }}
        >
          {analyzing
            ? 'Sending…'
            : phase === 'done'
              ? 'Send Again'
              : phase === 'error'
                ? 'Retry'
                : 'Approve & Send to AI'}
        </button>
        <button
          type="button"
          onClick={requestApplyAll}
          disabled={!canApply}
          title={
            applying
              ? 'Sending the recommendation set to the AutoApply orchestrator…'
              : !strategy?.id
                ? 'Load a strategy first to enable auto-apply.'
                : 'Send the current recommendation set to the AutoApply orchestrator. Marks the most recent history entry as APPLIED on success.'
          }
          className="px-3 py-1.5 rounded text-xs font-medium"
          style={{
            background: canApply ? 'var(--accent-green, #4ade80)' : 'var(--bg-card)',
            color: canApply ? '#0a0a0a' : 'var(--text-faint)',
            border: `1px solid ${
              canApply ? 'var(--accent-green, #4ade80)' : 'var(--border)'
            }`,
            opacity: canApply ? 1 : 0.5,
            cursor: canApply ? 'pointer' : 'not-allowed',
          }}
        >
          {applying ? 'Applying…' : 'Apply all recommendations'}
        </button>
      </div>
      {testResult && (
        <div
          role="status"
          data-testid="ai-test-result"
          className="rounded p-2 text-xs"
          style={{
            background: testResult.ok
              ? 'rgba(34, 197, 94, 0.1)'
              : 'rgba(239, 68, 68, 0.1)',
            color: testResult.ok
              ? 'var(--accent-green, #22c55e)'
              : 'var(--accent-red, #ef4444)',
            border: `1px solid ${
              testResult.ok
                ? 'var(--accent-green, #22c55e)'
                : 'var(--accent-red, #ef4444)'
            }`,
          }}
        >
          <span className="font-semibold">
            {testResult.ok ? '✓ ' : '✗ '}
          </span>
          {testResult.message}
          {testResult.detail && (
            <span
              className="block mt-1"
              style={{ color: 'var(--text-muted)' }}
            >
              {testResult.detail}
            </span>
          )}
        </div>
      )}
    </div>
  );

  // ── RIGHT pane: diagnosis + per-rec cards ──
  const rightPane = (
    <div className="flex flex-col gap-3">
      {/* Strategy Diagnosis */}
      <div
        className="rounded p-3"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <p
          className="text-xs font-semibold uppercase tracking-wide mb-2"
          style={{ color: 'var(--text-muted)' }}
        >
          STRATEGY DIAGNOSIS
        </p>
        {aiAnalysis?.diagnosis ? (
          <p
            className="text-xs whitespace-pre-wrap"
            style={{ color: 'var(--text-secondary)' }}
          >
            {aiAnalysis.diagnosis}
          </p>
        ) : aiAnalysis?.raw ? (
          <p
            className="text-xs whitespace-pre-wrap"
            style={{ color: 'var(--text-secondary)' }}
          >
            {aiAnalysis.raw}
          </p>
        ) : (
          <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
            {result
              ? 'Awaiting AI analysis. Use “Approve & Send to AI” below once the request preview is verified.'
              : 'Run a backtest first, then use “Approve & Send to AI” to receive a strategy diagnosis.'}
          </p>
        )}
      </div>

      {/* Per-Recommendation cards (AC2 + AC4) */}
      <div className="flex flex-col gap-2">
        <p
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: 'var(--text-muted)' }}
        >
          RECOMMENDATIONS
          {parsedRecs.length > 0 && (
            <span
              className="ml-1.5 text-[10px] font-normal"
              style={{ color: 'var(--text-faint)' }}
            >
              ({parsedRecs.length})
            </span>
          )}
        </p>
        {parsedRecs.length === 0 ? (
          <p
            className="text-xs"
            style={{ color: 'var(--text-faint)' }}
          >
            {aiAnalysis
              ? aiAnalysis.recommendations
                ? 'No structured recommendations in the response. See Strategy Diagnosis above for the full reply.'
                : 'No recommendations yet. Recommendations appear here after AI analysis completes.'
              : result
                ? 'No recommendations yet. Recommendations appear here after AI analysis completes.'
                : 'No results yet. Run a backtest to generate recommendations.'}
          </p>
        ) : (
          parsedRecs.map((rec) => (
            <RecommendationCard
              key={rec.id}
              rec={rec}
              isActive={activeRec?.id === rec.id}
              onApply={handleApplyRec}
              onClear={handleClearActiveRec}
            />
          ))
        )}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-3">
      {/* Tabs */}
      <div
        role="tablist"
        aria-label="AI recommendations views"
        className="flex items-center gap-1 border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        {(Object.keys(VIEW_LABELS) as View[]).map((v) => {
          const isActive = view === v;
          return (
            <button
              key={v}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setView(v)}
              className="px-3 py-1.5 text-xs font-medium rounded-t"
              style={{
                background: isActive ? 'var(--bg-card)' : 'transparent',
                color: isActive ? 'var(--text-secondary)' : 'var(--text-faint)',
                border: '1px solid var(--border)',
                borderBottom: isActive ? '1px solid var(--bg-card)' : '1px solid var(--border)',
                marginBottom: isActive ? '-1px' : '0',
                cursor: 'pointer',
              }}
            >
              {VIEW_LABELS[v]}
              {v === 'history' && history.hydrated && history.entries.length > 0 && (
                <span className="ml-1.5 text-[10px]" style={{ color: 'var(--text-faint)' }}>
                  ({history.entries.length})
                </span>
              )}
            </button>
          );
        })}
      </div>

      {currentView === 'current' ? (
        <SplitPanel left={leftPane} right={rightPane} />
      ) : (
        <HistoryView
          entries={history.entries}
          hydrated={history.hydrated}
          onUpdateStatus={history.updateStatus}
          onUpdateNotes={history.updateNotes}
          onRequestDelete={requestDelete}
          onRequestClearAll={requestClearAll}
          onLoadIntoCurrent={loadHistoryIntoCurrent}
        />
      )}

      {confirmation && (
        <ConfirmationModal
          confirmation={confirmation}
          onCancel={cancelConfirmation}
          onConfirmClearAll={confirmClearAll}
          onConfirmDelete={confirmDelete}
          onConfirmApplyAll={confirmApplyAll}
        />
      )}

      {goalModalOpen && (
        <OptimizationGoalModal
          onCancel={handleGoalCancel}
          onConfirm={handleGoalConfirm}
        />
      )}
    </div>
  );
}

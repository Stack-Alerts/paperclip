'use client';

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { ChevronDown, ChevronRight, Trash2, GripVertical, X } from 'lucide-react';
import { BacktestResult, Strategy, Trade } from '@/lib/strategy-builder/types';
import { useAiSettings, getProviderMeta } from '@/hooks/useAiSettings';
import { useAiRecsHistory, AiRecsHistoryEntry, AiRecsHistoryStatus } from '@/hooks/useAiRecsHistory';
import { ReverseViewBanner } from './ReverseViewBanner';
import {
  buildDiagnoseRows,
  buildStagedRecsSentence,
  type DiagnoseMetricRow,
  type StagedRecSummary,
} from './diagnoseMetrics';
import {
  extractReverseViewPattern,
  ReverseViewInput,
} from './reverseViewPattern';
import { StrategyImpactKpiBar } from './StrategyImpactKpiBar';
import {
  AppliedRecImpact,
  ProjectedDelta,
  deriveBaselineKpis,
} from './strategyImpactKpi';

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

// AC8: rough ETA shown next to the percent while we are waiting for the
// provider to respond. 30s is a conservative default for first-token latency
// across the providers the webui currently routes through.
const AWAITING_PROVIDER_ETA_SECONDS = 30;

// AC10: how long the green "Applied" banner stays visible before fading out.
const APPLY_SUCCESS_DISMISS_MS = 3000;

// BTCAAAAA-36917 v4 UX: hardcoded sample payload for the empty-state
// "Preview the new layout" + "Load demo data" affordances. The preview card
// renders a single rec without touching aiAnalysis so the v3 cache stays
// clean; the demo path populates aiAnalysis but is guarded inside the cache
// persistence effect so the demo data never leaks into sessionStorage.
const SAMPLE_DIAGNOSIS =
  "Strategy shows modest profitability with a healthy win rate, but a long "
  + "drawdown between Apr-Jun suggests the trend filter is too tight in "
  + "ranging markets. Consider relaxing the EMA window or adding a "
  + "volatility regime detector.";

const SAMPLE_RECOMMENDATIONS =
  "1. Widen the EMA trend filter window\n"
  + "   Type: signal\n"
  + "   Rationale: 50-period EMA is too restrictive in the current chop; "
  + "wider window lets more setups through.\n"
  + "   Confidence: high\n"
  + "   - **ema_window**: 100\n"
  + "   - **min_atr**: 250\n"
  + "\n"
  + "2. Add volatility regime block\n"
  + "   Type: building-block\n"
  + "   Rationale: regime detector reduces whipsaw losses during low-vol "
  + "consolidation.\n"
  + "   Confidence: medium\n"
  + "   - **atr_period**: 14\n"
  + "   - **regime_threshold**: 0.6\n"
  + "\n"
  + "3. Tighten the stop loss to 1.5x ATR\n"
  + "   Type: risk\n"
  + "   Rationale: fixed-percent stop gives back too much during the recent "
  + "high-volatility leg.\n"
  + "   Confidence: high\n"
  + "   - **stop_atr_multiple**: 1.5\n";

// AC21: per-strategy AI recommendations cache. Lives in sessionStorage so the
// recs + applied-state survive tab navigation, parent re-renders, and the AI
// panel remounting. AC22: only cleared on explicit user rerun
// (handleApproveAndSendClick → runApproveAndSend, and loadHistoryIntoCurrent
// when the user explicitly loads a different history entry). Keyed by
// strategyId so switching strategies does not bleed stale recs.
const AI_RECS_CACHE_KEY = 'ai_recs_v3_cache_v1';
const AI_RECS_CACHE_VERSION = 1;

interface CachedAnalysis {
  version: number;
  strategyId: string | null;
  diagnosis: string;
  recommendations: string;
  raw: string;
  appliedRecIds: string[];
  // JSON-stringified Strategy per applied rec, so we can locally roll back
  // (AC18) without a server round-trip. Server-persisted rollback is a
  // follow-up backend ticket; this snapshot keeps the UX honest in the
  // meantime.
  preApplySnapshots: Array<[string, Strategy]>;
  analysisTimestamp: string;
}

function readRecsCache(): CachedAnalysis | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(AI_RECS_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<CachedAnalysis>;
    if (parsed.version !== AI_RECS_CACHE_VERSION) return null;
    if (
      typeof parsed.diagnosis !== 'string' ||
      typeof parsed.recommendations !== 'string' ||
      typeof parsed.raw !== 'string'
    ) {
      return null;
    }
    return {
      version: parsed.version,
      strategyId: parsed.strategyId ?? null,
      diagnosis: parsed.diagnosis,
      recommendations: parsed.recommendations,
      raw: parsed.raw,
      appliedRecIds: Array.isArray(parsed.appliedRecIds)
        ? parsed.appliedRecIds.filter((s): s is string => typeof s === 'string')
        : [],
      preApplySnapshots: Array.isArray(parsed.preApplySnapshots)
        ? (parsed.preApplySnapshots as Array<[string, Strategy]>)
        : [],
      analysisTimestamp:
        typeof parsed.analysisTimestamp === 'string'
          ? parsed.analysisTimestamp
          : new Date().toISOString(),
    };
  } catch {
    return null;
  }
}

function writeRecsCache(cache: CachedAnalysis | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (!cache) {
      window.sessionStorage.removeItem(AI_RECS_CACHE_KEY);
      return;
    }
    window.sessionStorage.setItem(AI_RECS_CACHE_KEY, JSON.stringify(cache));
  } catch {
    // Quota / private-mode failures are silent — the panel still works,
    // the recs just won't survive a refresh.
  }
}

/**
 * AC9: best-effort admin-role detection. The webui does not yet have a
 * server-issued roles endpoint, so we parse the auth_token (a JWT) for an
 * `admin` / `role` claim. Anything we cannot prove admin = locked out.
 */
function readIsAdminFromAuthToken(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const token = window.localStorage.getItem('auth_token');
    if (!token) return false;
    const parts = token.split('.');
    if (parts.length < 2) return false;
    const payload = parts[1];
    const padded = payload.replace(/-/g, '+').replace(/_/g, '/');
    const json = atob(padded + '==='.slice((padded.length + 3) % 4));
    const claims = JSON.parse(json) as Record<string, unknown>;
    if (claims.admin === true) return true;
    if (claims.is_admin === true) return true;
    const role = claims.role;
    if (typeof role === 'string' && role.toLowerCase() === 'admin') return true;
    const roles = claims.roles;
    if (Array.isArray(roles) && roles.some((r) => typeof r === 'string' && r.toLowerCase() === 'admin')) {
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

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
  applied: { bg: 'var(--accent-green-soft)', fg: 'var(--accent-green-on)', border: 'var(--accent-green-on)' },
  dismissed: { bg: 'var(--accent-red-soft)', fg: 'var(--accent-red-on)', border: 'var(--accent-red-on)' },
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
            background: 'var(--accent-blue)',
            color: 'var(--text-on-accent)',
            border: '1px solid var(--accent-blue)',
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
              entry.status === 'applied' ? 'var(--accent-green-soft)' : 'var(--bg-elevated)',
            color: entry.status === 'applied' ? 'var(--accent-green-on)' : 'var(--text-secondary)',
            border: '1px solid var(--accent-green-on)',
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
              entry.status === 'dismissed' ? 'var(--accent-red-soft)' : 'var(--bg-elevated)',
            color: entry.status === 'dismissed' ? 'var(--accent-red-on)' : 'var(--text-secondary)',
            border: '1px solid var(--accent-red-on)',
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
}: {
  confirmation: { type: 'clear-all' | 'delete'; entryId?: string };
  onCancel: () => void;
  onConfirmClearAll: () => void;
  onConfirmDelete: () => void;
}) {
  const isClearAll = confirmation.type === 'clear-all';
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'var(--overlay-scrim)' }}
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
          {isClearAll ? 'Clear all history?' : 'Delete this entry?'}
        </p>
        <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
          {isClearAll
            ? 'This will permanently remove all stored AI recommendation analyses from this browser. This action cannot be undone.'
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
            onClick={isClearAll ? onConfirmClearAll : onConfirmDelete}
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: 'var(--accent-red)',
              color: 'var(--text-on-negative)',
              border: '1px solid var(--accent-red)',
              cursor: 'pointer',
            }}
          >
            {isClearAll ? 'Clear all' : 'Delete'}
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
      style={{ background: 'var(--overlay-scrim)' }}
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
                  border: `1px solid ${isSelected ? 'var(--accent-blue)' : 'var(--border)'}`,
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
                  style={{ accentColor: 'var(--accent-blue)' }}
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
              background: canConfirm ? 'var(--accent-blue)' : 'var(--bg-elevated)',
              color: canConfirm ? 'var(--text-on-accent)' : 'var(--text-faint)',
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
  /** Structured type extracted from "Type:" line (e.g. ADJUST_PARAM, ADD_SIGNAL). */
  type: string;
  /** Optional fields extracted from "Confidence: …" / "Rationale: …" lines. */
  confidence?: string;
  rationale?: string;
  /** Key:value parameter suggestions extracted from the block. */
  suggestedParams: Array<{ key: string; value: string }>;
  // Structured fields forwarded to the auto-apply orchestrator.
  block?: string;
  signal?: string;
  parameter?: string;
  suggestedValue?: string;
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

function findParamInStrategy(strategy: Strategy, paramKey: string): string | undefined {
  for (const block of (strategy.blocks ?? [])) {
    const data = block.data;
    if (!data || typeof data !== 'object') continue;
    for (const [key, value] of Object.entries(data)) {
      if (key === paramKey && (typeof value === 'number' || typeof value === 'string')) {
        return String(value);
      }
    }
  }
  const settings = strategy.settings;
  if (settings && typeof settings === 'object') {
    for (const [key, value] of Object.entries(settings as unknown as Record<string, unknown>)) {
      if (key === paramKey && (typeof value === 'number' || typeof value === 'string')) {
        return String(value);
      }
    }
  }
  return undefined;
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

// BTCAAAAA-37774 Sprint A2 — optional projected-impact fields per rec block.
// Recognized labels (case-insensitive, "%" / "pp" treated as percentage-point
// fractions): "Projected Win Rate", "Projected Net Liquidity",
// "Projected Drawdown", "Projected Profit Factor", "Projected Entries".
function projectedImpactFromRecRaw(raw: string): ProjectedDelta {
  const pick = (label: string): number | undefined => {
    const v = tryExtractField(raw, label);
    if (v === undefined) return undefined;
    const m = v.match(/-?\d+(?:\.\d+)?/);
    if (!m) return undefined;
    const n = Number(m[0]);
    if (!Number.isFinite(n)) return undefined;
    if (/%|pp/i.test(v)) return n / 100;
    return n;
  };
  const out: ProjectedDelta = {};
  const wr = pick('Projected Win Rate') ?? pick('Projected WR');
  if (wr !== undefined) out.winRate = wr;
  const nl = pick('Projected Net Liquidity') ?? pick('Projected PnL');
  if (nl !== undefined) out.netLiquidity = nl;
  const dd = pick('Projected Drawdown') ?? pick('Projected DD');
  if (dd !== undefined) out.maxDrawdown = dd;
  const pf = pick('Projected Profit Factor') ?? pick('Projected PF');
  if (pf !== undefined) out.profitFactor = pf;
  const en = pick('Projected Entries');
  if (en !== undefined) out.entries = en;
  return out;
}

function parseSingleRec(block: string, index: number): ParsedRec {
  const rawSignal = tryExtractField(block, 'Signal');
  return {
    id: `rec-${index}-${simpleHash(block)}`,
    title: deriveTitle(block, index),
    summary: deriveSummary(block),
    raw: block.trim(),
    type: tryExtractField(block, 'Type') ?? 'recommendation',
    confidence: tryExtractField(block, 'Confidence'),
    rationale: tryExtractField(block, 'Rationale'),
    suggestedParams: parseSuggestedParams(block),
    block: tryExtractField(block, 'Block'),
    signal: rawSignal && !/^n\/a$/i.test(rawSignal) ? rawSignal : undefined,
    parameter: tryExtractField(block, 'Parameter'),
    suggestedValue: tryExtractField(block, 'Suggested Value'),
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
  blockCatalog: unknown[] | null = null,
): string {
  // Cap trades to 20 (first 10 + last 10) to avoid blowing provider token limits.
  const allTrades = result?.trades ?? [];
  const sampledTrades =
    allTrades.length <= 20
      ? allTrades
      : [...allTrades.slice(0, 10), ...allTrades.slice(-10)];

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
      available_blocks: blockCatalog ?? [],
      backtest_config: backtestConfig ?? null,
      trades: sampledTrades,
      trades_total_count: allTrades.length,
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

/** Split a model response into DIAGNOSIS / RECOMMENDATIONS sections.
 *
 * Handles the expected plain format as well as common AI deviations:
 * - Markdown bold: **DIAGNOSIS:** / **RECOMMENDATIONS:**
 * - Markdown headings: ## DIAGNOSIS / ## RECOMMENDATIONS
 * - No section headers: falls back to numbered-list split
 */
function parseAnalysisResponse(text: string): {
  diagnosis: string;
  recommendations: string;
  raw: string;
} {
  // Normalise markdown bold/italic/header decoration so the regex below only
  // needs to handle the plain-text `DIAGNOSIS:` / `RECOMMENDATIONS:` form.
  const normalized = text
    .replace(/\*{1,2}\s*(DIAGNOSIS)\s*\*{1,2}/gi, '$1:')
    .replace(/\*{1,2}\s*(RECOMMENDATIONS)\s*\*{1,2}/gi, '$1:')
    .replace(/^#{1,6}\s+(DIAGNOSIS)\s*[:\-]?\s*$/gim, 'DIAGNOSIS:')
    .replace(/^#{1,6}\s+(RECOMMENDATIONS)\s*[:\-]?\s*$/gim, 'RECOMMENDATIONS:');

  const diagnosisMatch = normalized.match(
    /DIAGNOSIS\s*:\s*([\s\S]*?)(?=\n\s*RECOMMENDATIONS\s*:|$)/i,
  );
  const recommendationsMatch = normalized.match(
    /RECOMMENDATIONS\s*:\s*([\s\S]*?)$/i,
  );

  let diagnosis = diagnosisMatch?.[1]?.trim() ?? '';
  let recommendations = recommendationsMatch?.[1]?.trim() ?? '';

  // Fallback A: neither header found — split at the first numbered list item.
  if (!diagnosis && !recommendations) {
    const idx = text.search(/(?:^|\n)\s*1[.)]\s+/);
    if (idx > 0) {
      diagnosis = text.slice(0, idx).trim();
      recommendations = text.slice(idx).trim();
    } else {
      diagnosis = text.trim();
    }
  }

  // Fallback B: DIAGNOSIS found but no RECOMMENDATIONS header — check if the
  // captured diagnosis text itself contains a numbered list and split it out.
  if (diagnosis && !recommendations) {
    const idx = diagnosis.search(/\n\s*1[.)]\s+/);
    if (idx > 0) {
      recommendations = diagnosis.slice(idx).trim();
      diagnosis = diagnosis.slice(0, idx).trim();
    }
  }

  return { diagnosis, recommendations, raw: text };
}

/**
 * A4 (BTCAAAAA-37777): map a model-emitted confidence label to a synthetic
 * uplift number used only to rank the top-quartile bucket. The numeric scale
 * is internal to the reverse-view banner — it never surfaces to the user.
 */
function confidenceToUplift(confidence: string | undefined): number {
  if (!confidence) return 0;
  switch (confidence.trim().toLowerCase()) {
    case 'high':
      return 3;
    case 'medium':
    case 'med':
      return 2;
    case 'low':
      return 1;
    default:
      return 0;
  }
}

interface ActiveRec {
  id: string;
  title: string;
  raw: string;
  confidence?: string;
  rationale?: string;
  suggestedParams: Array<{ key: string; value: string }>;
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
  const [splitPercent, setSplitPercent] = useState<number>(() => {
    if (typeof window === 'undefined') return SPLIT_DEFAULT;
    try {
      const stored = window.localStorage.getItem(SPLIT_STORAGE_KEY);
      if (stored) {
        const parsed = Number.parseFloat(stored);
        if (Number.isFinite(parsed) && parsed >= SPLIT_MIN && parsed <= SPLIT_MAX) return parsed;
      }
    } catch { /* best effort */ }
    return SPLIT_DEFAULT;
  });
  const containerRef = useRef<HTMLDivElement | null>(null);
  const isDraggingRef = useRef(false);
  const hasMountedRef = useRef(false);

  // Persist split on change (skip the initial mount so we don't echo
  // the value we just read from localStorage back immediately).
  useEffect(() => {
    if (!hasMountedRef.current) {
      hasMountedRef.current = true;
      return;
    }
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(SPLIT_STORAGE_KEY, String(splitPercent));
    } catch {
      // best effort
    }
  }, [splitPercent]);

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

// BTCAAAAA-37780 / Sprint A6 — minimal markdown renderer for the Diagnose
// pane. The rest of the panel renders diagnosis text with `whitespace-pre-wrap`,
// so we preserve that line-break convention and add light inline support
// for **bold**, _italic_, and `inline code` plus `- `/`* ` bullet lists.
// Anything fancier (tables, links, code blocks) falls back to plain text.
function renderInline(line: string, keyPrefix: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|_[^_]+_|`[^`]+`)/g;
  let last = 0;
  let i = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(line)) !== null) {
    if (m.index > last) out.push(line.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('**')) {
      out.push(<strong key={`${keyPrefix}:b:${i++}`}>{tok.slice(2, -2)}</strong>);
    } else if (tok.startsWith('_')) {
      out.push(<em key={`${keyPrefix}:i:${i++}`}>{tok.slice(1, -1)}</em>);
    } else if (tok.startsWith('`')) {
      out.push(
        <code
          key={`${keyPrefix}:c:${i++}`}
          style={{ fontFamily: 'var(--font-mono, monospace)' }}
        >
          {tok.slice(1, -1)}
        </code>,
      );
    }
    last = m.index + tok.length;
  }
  if (last < line.length) out.push(line.slice(last));
  return out;
}

function DiagnosisMarkdown({ text }: { text: string }) {
  if (!text.trim()) return null;
  const lines = text.split(/\r?\n/);
  const out: React.ReactNode[] = [];
  let bullets: string[] | null = null;
  let blockIdx = 0;

  const flushBullets = () => {
    if (!bullets) return;
    const items = bullets;
    out.push(
      <ul
        key={`ul:${blockIdx++}`}
        className="list-disc pl-5 text-xs"
        style={{ color: 'var(--text-secondary)' }}
      >
        {items.map((b, i) => (
          <li key={i}>{renderInline(b, `ul:${blockIdx}:${i}`)}</li>
        ))}
      </ul>,
    );
    bullets = null;
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    const bulletMatch = line.match(/^\s*[-*]\s+(.*)$/);
    if (bulletMatch) {
      if (!bullets) bullets = [];
      bullets.push(bulletMatch[1]);
      continue;
    }
    flushBullets();
    if (line.trim().length === 0) continue;
    out.push(
      <p
        key={`p:${blockIdx++}`}
        className="text-xs whitespace-pre-wrap"
        style={{ color: 'var(--text-secondary)' }}
      >
        {renderInline(line, `p:${blockIdx}`)}
      </p>,
    );
  }
  flushBullets();
  return <div className="flex flex-col gap-2">{out}</div>;
}

interface DiagnosePaneProps {
  diagnosis: string;
  rows: DiagnoseMetricRow[];
  stagedSentence: string;
  hasResult: boolean;
}

function DiagnosePane({ diagnosis, rows, stagedSentence, hasResult }: DiagnosePaneProps) {
  return (
    <div className="flex flex-col gap-3" data-testid="ai-recs-diagnose-pane">
      <div
        className="rounded p-3"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <p
          className="text-xs font-semibold uppercase tracking-wide mb-2"
          style={{ color: 'var(--text-muted)' }}
        >
          DIAGNOSIS
        </p>
        {diagnosis.trim() ? (
          <DiagnosisMarkdown text={diagnosis} />
        ) : (
          <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
            {hasResult
              ? 'Awaiting AI analysis. Use “Approve & Send to AI” once the request preview is verified.'
              : 'Run a backtest first, then use “Approve & Send to AI” to receive a strategy diagnosis.'}
          </p>
        )}
      </div>

      <div
        className="rounded"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <p
          className="text-xs font-semibold uppercase tracking-wide px-3 pt-3"
          style={{ color: 'var(--text-muted)' }}
        >
          METRICS — REPORTED vs PER-ENTRY
        </p>
        <table
          data-testid="ai-recs-diagnose-table"
          className="w-full text-xs mt-2"
          style={{ borderCollapse: 'collapse' }}
        >
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              <th
                className="text-left px-3 py-1.5 font-semibold"
                style={{ color: 'var(--text-muted)' }}
              >
                Metric
              </th>
              <th
                className="text-right px-3 py-1.5 font-semibold"
                style={{ color: 'var(--text-muted)' }}
              >
                Reported
              </th>
              <th
                className="text-right px-3 py-1.5 font-semibold"
                style={{ color: 'var(--text-muted)' }}
              >
                Per-entry
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.key}
                data-testid={`ai-recs-diagnose-row-${row.key}`}
                data-divergent={row.divergent ? 'true' : 'false'}
                style={{ borderBottom: '1px solid var(--border)' }}
              >
                <td className="px-3 py-1.5" style={{ color: 'var(--text-secondary)' }}>
                  {row.label}
                </td>
                <td
                  className="px-3 py-1.5 text-right"
                  style={{
                    color: 'var(--text-secondary)',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}
                >
                  {row.reported}
                </td>
                <td
                  className="px-3 py-1.5 text-right"
                  style={{
                    color: row.divergent ? 'var(--accent-orange)' : 'var(--text-secondary)',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}
                >
                  {row.perEntry}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div
        data-testid="ai-recs-staged-sentence"
        className="rounded p-3 text-xs"
        style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderLeft: '3px solid var(--accent-blue)',
          color: 'var(--text-secondary)',
        }}
      >
        {stagedSentence}
      </div>
    </div>
  );
}

export function AiRecommendationsPanel({
  result,
  strategy,
  backtestConfig,
  onStrategyUpdated,
}: AiRecommendationsPanelProps = {}) {
  const hasTrades = (result?.trades?.length ?? 0) > 0;
  const { settings, hydrated: aiSettingsHydrated } = useAiSettings();
  const providerMeta = aiSettingsHydrated ? getProviderMeta(settings.provider) : null;
  const hasProvider = aiSettingsHydrated && (
    !providerMeta?.requiresApiKey ||
    !!(settings.apiKeys?.[settings.provider]?.trim())
  );
  const history = useAiRecsHistory();

  const [blockCatalog, setBlockCatalog] = useState<unknown[] | null>(null);
  useEffect(() => {
    fetch('/api/strategy-builder/block-library')
      .then((r) => (r.ok ? r.json() : null))
      .then((data: unknown) => {
        if (data && typeof data === 'object' && Array.isArray((data as { blocks?: unknown }).blocks)) {
          setBlockCatalog((data as { blocks: unknown[] }).blocks);
        }
      })
      .catch(() => { /* best effort */ });
  }, []);

  const [view, setView] = useState<View>('current');
  // BTCAAAAA-37780 / Sprint A6: right-rail sub-tab. "recs" keeps the
  // existing diagnosis-summary + recommendations grid; "diagnose" renders
  // the orchestrator's diagnosis markdown plus the reported-vs-per-entry
  // metrics table and a pinned-impact sentence.
  const [rightTab, setRightTab] = useState<'recs' | 'diagnose'>('recs');
  const [phase, setPhase] = useState<SendPhase>('idle');
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisDetail, setAnalysisDetail] = useState<string | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<{
    diagnosis: string;
    recommendations: string;
    raw: string;
  } | null>(null);
  const [applySuccess, setApplySuccess] = useState<string | null>(null);
  const [applySuccessVisible, setApplySuccessVisible] = useState(true);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
    detail?: string;
  } | null>(null);
  const [confirmation, setConfirmation] = useState<{
    type: 'clear-all' | 'delete';
    entryId?: string;
  } | null>(null);
  const [goalModalOpen, setGoalModalOpen] = useState(false);
  const [activeRec, setActiveRec] = useState<ActiveRec | null>(null);
  const [optimizationGoal, setOptimizationGoal] = useState<string | null>(null);

  // BTCAAAAA-36917 v4 UX: empty-state preview/demo affordances.
  // previewMode renders a single static card inline (no aiAnalysis touch —
  // the v3 sessionStorage cache stays empty).
  // demoMode populates aiAnalysis with hardcoded sample data; the cache
  // persistence effect below early-returns while demoMode is true, so the
  // demo payload never leaks into sessionStorage.
  const [previewMode, setPreviewMode] = useState(false);
  const [demoMode, setDemoMode] = useState(false);

  // AC9: admin gate for Export to JSON. Computed once on mount from the
  // auth_token claim; a fresh login would remount the panel through key
  // changes elsewhere so we do not need to live-observe it.
  const [isAdmin, setIsAdmin] = useState(false);
  useEffect(() => {
    setIsAdmin(readIsAdminFromAuthToken());
  }, []);

  // AC15-AC22: per-tile toggle state. Each card knows whether its rec has
  // been applied (and thus should render in the "on" / enabled state), what
  // the strategy looked like right before that apply (so AC18 rollback can
  // restore it locally), and whether an apply is currently in flight for
  // that specific rec so we can show per-tile spinners. Per-tile errors
  // surface under the failing card rather than collapsing into a single
  // global banner.
  const [appliedRecIds, setAppliedRecIds] = useState<string[]>([]);
  const [preApplySnapshots, setPreApplySnapshots] = useState<Array<[string, Strategy]>>([]);
  const [perTileApplying, setPerTileApplying] = useState<string[]>([]);
  const [perTileError, setPerTileError] = useState<Record<string, string>>({});

  // AC21: hydrate from the sessionStorage cache on mount so the recs
  // survive a tab switch or a remount of the panel. The cache is also
  // keyed by strategyId so a different strategy does not bleed recs.
  // AC22: we do NOT clear on prop-driven re-renders — the only clear
  // paths are explicit user actions (rerun / load-different-history).
  const cacheHydratedRef = useRef(false);
  useEffect(() => {
    if (cacheHydratedRef.current) return;
    if (typeof window === 'undefined') return;
    cacheHydratedRef.current = true;
    const cached = readRecsCache();
    if (!cached) return;
    // If the cached strategy differs from the currently mounted strategy,
    // do not rehydrate — the recs are scoped to that other strategy.
    if (
      cached.strategyId !== null &&
      strategy?.id &&
      cached.strategyId !== strategy.id
    ) {
      return;
    }
    setAiAnalysis({
      diagnosis: cached.diagnosis,
      recommendations: cached.recommendations,
      raw: cached.raw,
    });
    setAppliedRecIds(cached.appliedRecIds);
    setPreApplySnapshots(cached.preApplySnapshots);
  }, [strategy?.id]);

  // AC21: persist recs + applied state to sessionStorage on change. Done in
  // a single effect so we only touch storage when something actually
  // changed. Errors are silent (readRecsCache handles the read side).
  // BTCAAAAA-36917 v4 UX: while demoMode is true we deliberately skip the
  // cache write so the demo payload never lands in sessionStorage. The
  // effect re-fires when demoMode flips back to false and resumes normal
  // persistence.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!cacheHydratedRef.current) return;
    if (demoMode) return;
    if (!aiAnalysis) {
      writeRecsCache(null);
      return;
    }
    writeRecsCache({
      version: AI_RECS_CACHE_VERSION,
      strategyId: strategy?.id ?? null,
      diagnosis: aiAnalysis.diagnosis,
      recommendations: aiAnalysis.recommendations,
      raw: aiAnalysis.raw,
      appliedRecIds,
      preApplySnapshots,
      analysisTimestamp: new Date().toISOString(),
    });
  }, [aiAnalysis, appliedRecIds, preApplySnapshots, strategy?.id, demoMode]);

  // AC8: countdown for the awaiting-provider phase. Resets to the full
  // ETA whenever we enter the phase, ticks once per second while we are
  // inside it, and clears when we leave.
  const [awaitingEta, setAwaitingEta] = useState<number | null>(null);
  useEffect(() => {
    if (phase !== 'awaiting-provider') {
      setAwaitingEta(null);
      return;
    }
    setAwaitingEta(AWAITING_PROVIDER_ETA_SECONDS);
    const interval = setInterval(() => {
      setAwaitingEta((prev) => (prev === null ? null : Math.max(0, prev - 1)));
    }, 1000);
    return () => clearInterval(interval);
  }, [phase]);

  const abortRef = useRef<AbortController | null>(null);
  const dismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const applySuccessTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const applySuccessFadeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
      if (applySuccessTimerRef.current) {
        clearTimeout(applySuccessTimerRef.current);
        applySuccessTimerRef.current = null;
      }
      if (applySuccessFadeTimerRef.current) {
        clearTimeout(applySuccessFadeTimerRef.current);
        applySuccessFadeTimerRef.current = null;
      }
    };
  }, []);

  // AC10: auto-dismiss the apply success banner after 3 seconds. We flip
  // the "visible" flag first to drive the opacity fade, then clear the
  // message on a second timer.
  useEffect(() => {
    if (!applySuccess) {
      setApplySuccessVisible(true);
      if (applySuccessTimerRef.current) {
        clearTimeout(applySuccessTimerRef.current);
        applySuccessTimerRef.current = null;
      }
      if (applySuccessFadeTimerRef.current) {
        clearTimeout(applySuccessFadeTimerRef.current);
        applySuccessFadeTimerRef.current = null;
      }
      return;
    }
    setApplySuccessVisible(true);
    if (applySuccessFadeTimerRef.current) {
      clearTimeout(applySuccessFadeTimerRef.current);
    }
    if (applySuccessTimerRef.current) {
      clearTimeout(applySuccessTimerRef.current);
    }
    // AC10: keep the banner fully opaque for the full 3s window, then flip
    // visibility to drive the 300ms CSS opacity fade, then clear the message
    // 300ms after that so the element is removed once the fade has had time
    // to play out.
    applySuccessFadeTimerRef.current = setTimeout(() => {
      setApplySuccessVisible(false);
    }, APPLY_SUCCESS_DISMISS_MS);
    applySuccessTimerRef.current = setTimeout(() => {
      setApplySuccess(null);
      setApplySuccessVisible(true);
    }, APPLY_SUCCESS_DISMISS_MS);
    return () => {
      if (applySuccessFadeTimerRef.current) {
        clearTimeout(applySuccessFadeTimerRef.current);
        applySuccessFadeTimerRef.current = null;
      }
      if (applySuccessTimerRef.current) {
        clearTimeout(applySuccessTimerRef.current);
        applySuccessTimerRef.current = null;
      }
    };
  }, [applySuccess]);

  const analyzing = ACTIVE_PHASES.has(phase);

  const parsedRecs = useMemo(() => {
    if (!aiAnalysis?.recommendations) return [];
    return parseRecommendations(aiAnalysis.recommendations);
  }, [aiAnalysis?.recommendations]);

  // BTCAAAAA-37780 / Sprint A6 — Diagnose tab data.
  const diagnoseRows: DiagnoseMetricRow[] = useMemo(
    () => buildDiagnoseRows(result ?? null, result?.trades ?? null),
    [result],
  );
  const stagedSummaries: StagedRecSummary[] = useMemo(
    () =>
      parsedRecs
        .filter((r) => appliedRecIds.includes(r.id))
        .map((r) => ({ id: r.id, title: r.title, suggestedParams: r.suggestedParams })),
    [parsedRecs, appliedRecIds],
  );
  const stagedSentence = useMemo(
    () => buildStagedRecsSentence(stagedSummaries, strategy ?? null),
    [stagedSummaries, strategy],
  );
  // A4 (BTCAAAAA-37777): map the same parsed recs into the minimal shape the
  // reverse-view extractor needs. Confidence drives the synthetic uplift so
  // the top-quartile ranking matches the model's own confidence ordering.
  const reverseViewInputs = useMemo<ReverseViewInput[]>(
    () =>
      parsedRecs.map((r) => ({
        id: r.id,
        uplift: confidenceToUplift(r.confidence),
        category: r.type,
        paramKeys: r.suggestedParams.map((p) => p.key),
      })),
    [parsedRecs],
  );

  // BTCAAAAA-37774 Sprint A2 — baseline + applied impacts feed the KPI bar.
  const baselineKpis = useMemo(() => deriveBaselineKpis(result ?? null), [result]);
  const appliedImpacts = useMemo<AppliedRecImpact[]>(() => {
    if (parsedRecs.length === 0 || appliedRecIds.length === 0) return [];
    const byId = new Map(parsedRecs.map((r) => [r.id, r] as const));
    return appliedRecIds
      .map((id) => {
        const rec = byId.get(id);
        if (!rec) return null;
        return { recId: id, delta: projectedImpactFromRecRaw(rec.raw) };
      })
      .filter((x): x is AppliedRecImpact => x !== null);
  }, [parsedRecs, appliedRecIds]);

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
          blockCatalog,
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
        // BTCAAAAA-36917 v4 UX: real AI response — clear any preview/demo
        // affordances so the user lands on the genuine analysis.
        setPreviewMode(false);
        setDemoMode(false);
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
      blockCatalog,
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
    if (!hasTrades || !hasProvider || analyzing) return;
    setGoalModalOpen(true);
  }, [hasTrades, hasProvider, analyzing]);

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


  const handleClearActiveRec = useCallback(() => {
    setActiveRec(null);
  }, []);

  // AC15-AC20: per-tile toggle. A click on an "off" card applies just that
  // rec through the orchestrator (one-element recs array), captures the
  // pre-apply strategy snapshot for AC18 rollback, and flips the card into
  // its enabled state. A click on an "on" card rolls back to the snapshot
  // locally (AC18) — server-side rollback is a follow-up backend ticket
  // since webui-only phase forbids backend touches.
  //
  // Apply runs are independent per-rec (AC19) so multiple cards can be
  // toggled in parallel; per-tile spinners and per-tile errors keep the UX
  // honest about which rec is in flight or failed.
  const handleToggleRec = useCallback(
    async (rec: ParsedRec) => {
      if (!strategy?.id) return;
      const isCurrentlyApplied = appliedRecIds.includes(rec.id);
      if (isCurrentlyApplied) {
        // AC18: rollback path. Locally restore the pre-apply strategy and
        // drop the rec from the applied set. The server still has the
        // applied state until the follow-up backend rollback endpoint
        // ships; we surface that in the card's tooltip so the user is not
        // misled about persistence.
        const snapshotEntry = preApplySnapshots.find(([id]) => id === rec.id);
        if (snapshotEntry && onStrategyUpdated) {
          onStrategyUpdated(snapshotEntry[1]);
        }
        setAppliedRecIds((prev) => prev.filter((id) => id !== rec.id));
        setPreApplySnapshots((prev) => prev.filter(([id]) => id !== rec.id));
        return;
      }

      // Apply path. Snapshot first so AC18 rollback is always reversible
      // even if the orchestrator fails or returns a malformed body.
      setPerTileApplying((prev) => [...prev, rec.id]);
      setPerTileError((prev) => {
        if (!(rec.id in prev)) return prev;
        const next = { ...prev };
        delete next[rec.id];
        return next;
      });
      setPreApplySnapshots((prev) => [...prev, [rec.id, strategy]]);

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
            strategy,
            recs: [
              {
                rec_id: rec.id,
                type: rec.type,
                ...(rec.raw ? { raw: rec.raw } : {}),
                ...(rec.block ? { block: rec.block } : {}),
                ...(rec.signal ? { signal: rec.signal } : {}),
                ...(rec.parameter ? { parameter: rec.parameter } : {}),
                ...(rec.suggestedValue ? { suggestedValue: rec.suggestedValue } : {}),
              },
            ],
            optInDestructiveIds: null,
          }),
        });
        const data = (await res.json()) as {
          ok: boolean;
          strategy?: Strategy;
          error?: string;
          detail?: string;
        };
        if (!res.ok || !data.ok) {
          // Drop the snapshot — apply failed, nothing to roll back from.
          setPreApplySnapshots((prev) =>
            prev.filter(([id]) => id !== rec.id),
          );
          setPerTileError((prev) => ({
            ...prev,
            [rec.id]:
              data.error ?? `Auto-apply returned HTTP ${res.status}.`,
          }));
          return;
        }
        setAppliedRecIds((prev) =>
          prev.includes(rec.id) ? prev : [...prev, rec.id],
        );
        if (data.strategy && onStrategyUpdated) {
          onStrategyUpdated(data.strategy);
        }
      } catch (err) {
        setPreApplySnapshots((prev) =>
          prev.filter(([id]) => id !== rec.id),
        );
        setPerTileError((prev) => ({
          ...prev,
          [rec.id]:
            err instanceof Error
              ? err.message
              : 'The auto-apply request failed.',
        }));
      } finally {
        setPerTileApplying((prev) => prev.filter((id) => id !== rec.id));
      }
    },
    [strategy, appliedRecIds, preApplySnapshots, onStrategyUpdated],
  );

  // AC22: explicit rerun invalidates the per-tile apply state because the
  // new analysis may have a different rec set / different rec ids. The
  // cache-write effect (above) will overwrite the sessionStorage entry on
  // the next render with the new aiAnalysis + empty applied state. We
  // track a ref of the previous aiAnalysis so the very first non-null
  // value (whether from cache hydration or the initial run) does not
  // trip the "reset" branch — only an actual transition from a prior
  // analysis to a different one should wipe the toggle state.
  const lastAiAnalysisRef = useRef<typeof aiAnalysis>(null);
  useEffect(() => {
    const prev = lastAiAnalysisRef.current;
    lastAiAnalysisRef.current = aiAnalysis;
    if (!aiAnalysis) return;
    if (prev === null) return;
    if (
      prev.diagnosis === aiAnalysis.diagnosis &&
      prev.recommendations === aiAnalysis.recommendations &&
      prev.raw === aiAnalysis.raw
    ) {
      return;
    }
    setAppliedRecIds([]);
    setPreApplySnapshots([]);
    setPerTileError({});
  }, [aiAnalysis]);

  // AC3: history Load → hydrate current analysis view AND set first parsed
  // rec as the active rec so the user can re-send with that context.
  const loadHistoryIntoCurrent = useCallback(
    (entry: AiRecsHistoryEntry) => {
      // BTCAAAAA-36917 v4 UX: user explicitly loaded a history entry —
      // dismiss any active preview/demo state first.
      setPreviewMode(false);
      setDemoMode(false);
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

  const canSend = hasTrades && hasProvider && !analyzing && aiSettingsHydrated;
  const showProgress = phase !== 'idle' && phase !== 'error';
  const progressPercent = phase === 'idle' || phase === 'error' ? 0 : PHASE_INFO[phase as Exclude<SendPhase, 'idle' | 'error'>].percent;
  const progressLabel =
    phase === 'idle' || phase === 'error'
      ? ''
      : PHASE_INFO[phase as Exclude<SendPhase, 'idle' | 'error'>].label;

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
            background: 'var(--accent-blue-soft)',
            border: '1px solid var(--accent-blue)',
            color: 'var(--text-secondary)',
          }}
        >
          <div className="flex items-center justify-between gap-2">
            <span
              className="text-[10px] font-semibold uppercase tracking-wide"
              style={{ color: 'var(--accent-blue)' }}
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
            color: 'var(--accent-red)',
            border: '1px solid var(--accent-red)',
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

      {/* Auto-apply success banner */}
      {applySuccess && (
        <div
          className="rounded p-2 text-xs"
          role="status"
          data-testid="ai-recs-apply-success"
          style={{
            background: 'var(--accent-green-soft)',
            color: 'var(--accent-green-on)',
            border: '1px solid var(--accent-green-on)',
            opacity: applySuccessVisible ? 1 : 0,
            transition: 'opacity 300ms ease-out',
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
        <PreviewText text={blockCatalog ? `${blockCatalog.length} blocks available` : 'Loading block catalog…'} />
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
            <span className="flex items-center gap-2">
              {phase === 'awaiting-provider' && awaitingEta !== null && (
                <span
                  data-testid="ai-recs-progress-eta"
                  aria-live="off"
                  style={{
                    color: 'var(--text-muted)',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}
                >
                  ~{awaitingEta}s
                </span>
              )}
              <span
                data-testid="ai-recs-progress-percent"
                style={{
                  color: 'var(--text-muted)',
                  fontFamily: 'var(--font-mono, monospace)',
                }}
              >
                {progressPercent}%
              </span>
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
                    ? 'var(--accent-green)'
                    : 'var(--accent-blue)',
                transition: 'width 200ms ease-out',
              }}
            />
          </div>
        </div>
      )}

      {/* Pre-flight validation banners */}
      {aiSettingsHydrated && !hasTrades && (
        <div
          className="rounded p-2 text-xs"
          role="status"
          data-testid="ai-recs-no-trades-warning"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--accent-orange)',
            border: '1px solid var(--accent-orange)',
          }}
        >
          No trades recorded — run a backtest first before sending to AI.
        </div>
      )}
      {aiSettingsHydrated && !hasProvider && (
        <div
          className="rounded p-2 text-xs"
          role="status"
          data-testid="ai-recs-no-provider-warning"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--accent-orange)',
            border: '1px solid var(--accent-orange)',
          }}
        >
          No AI provider configured — open Settings → AI to set one up.
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
          disabled={!hasTrades || !isAdmin}
          title={
            !isAdmin
              ? 'Export to JSON requires an admin login.'
              : !hasTrades
                ? 'Run a backtest with trades to enable Export to JSON.'
                : 'Download the request payload as JSON.'
          }
          className="px-3 py-1.5 rounded text-xs font-medium"
          style={{
            background: 'var(--bg-card)',
            color: hasTrades && isAdmin ? 'var(--text-secondary)' : 'var(--text-faint)',
            border: '1px solid var(--border)',
            opacity: hasTrades && isAdmin ? 1 : 0.5,
            cursor: hasTrades && isAdmin ? 'pointer' : 'not-allowed',
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
            background: canSend ? 'var(--accent-blue)' : 'var(--bg-card)',
            color: canSend ? 'var(--text-on-accent)' : 'var(--text-faint)',
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
      </div>
      {testResult && (
        <div
          role="status"
          data-testid="ai-test-result"
          className="rounded p-2 text-xs"
          style={{
            background: testResult.ok
              ? 'var(--accent-green-tint)'
              : 'var(--accent-red-tint)',
            color: testResult.ok
              ? 'var(--accent-green)'
              : 'var(--accent-red)',
            border: `1px solid ${
              testResult.ok
                ? 'var(--accent-green)'
                : 'var(--accent-red)'
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

  // ── RIGHT pane: per-rec Compare-style toggle cards (AC15-AC22) ──
  //
  // v3 redesign: each ParsedRec renders as its own card in the same
  // visual language as ComparePanel RunCard. Clicking the card toggles
  // the rec's apply state — applied cards have a green accent + ON badge;
  // unapplied cards are dimmed. Per-tile apply/rollback (AC18) goes
  // through the existing /api/ai/auto-apply orchestrator with a single
  // rec payload, so AC20 (real strategy save) is preserved. Rollback is
  // local-only against the snapshot we capture before each apply (server
  // rollback is a follow-up backend ticket; see AC18 inline notes).
  const rightPane = (
    <div className="flex flex-col gap-3">
      {/* BTCAAAAA-37780 / Sprint A6 — right-rail sub-tabs. The recs tab
          keeps the existing diagnosis-summary card + per-rec toggle grid;
          the diagnose tab renders the orchestrator markdown plus a
          reported-vs-per-entry metrics table and the pinned-impact
          sentence. */}
      <div
        role="tablist"
        aria-label="Right-rail views"
        data-testid="ai-recs-right-tabs"
        className="flex items-center gap-1 border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        {(['recs', 'diagnose'] as const).map((t) => {
          const isActive = rightTab === t;
          const label = t === 'recs' ? 'Recommendations' : 'Diagnose';
          return (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setRightTab(t)}
              data-testid={`ai-recs-right-tab-${t}`}
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
              {label}
            </button>
          );
        })}
      </div>

      {rightTab === 'recs' && (<>
      {/* Diagnosis card: compact summary at the top so the grid below has
          room. The detailed prose is still rendered in full; we just do
          not crowd it next to the per-rec cards. */}
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

      {/* BTCAAAAA-37774 Sprint A2 — Strategy Impact KPI bar. */}
      {result && (
        <StrategyImpactKpiBar
          baseline={baselineKpis}
          appliedImpacts={appliedImpacts}
        />
      )}

      {/* AC15: RECOMMENDATIONS header + card grid (ComparePanel layout). */}
      <div className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between">
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
                ({parsedRecs.length} · {appliedRecIds.length} applied)
              </span>
            )}
          </p>
          {/* BTCAAAAA-36917 v4 UX: surfaced only when demoMode is true so
              the user can return to a clean empty state without a page
              reload. Clicking it nulls aiAnalysis + resets both flags. */}
          {demoMode && (
            <button
              type="button"
              onClick={() => {
                setDemoMode(false);
                setPreviewMode(false);
                setAiAnalysis(null);
              }}
              className="text-[10px] underline"
              style={{
                background: 'transparent',
                color: 'var(--text-faint)',
                border: 'none',
                cursor: 'pointer',
                padding: 0,
              }}
              data-testid="ai-recs-exit-demo-btn"
              title="Clear the demo data and return to the empty state."
            >
              Exit demo
            </button>
          )}
        </div>
        {parsedRecs.length === 0 ? (
          <div
            className="rounded p-3"
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderTop: '3px solid var(--accent-blue)',
            }}
          >
            {/* When there IS recommendations text but parsing didn't split it
                into individual cards, show the raw text rather than an empty
                placeholder. The user gets readable content; the toggle-card
                feature message explains why cards aren't showing. */}
            {aiAnalysis?.recommendations ? (
              <div className="flex flex-col gap-2">
                <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                  Could not split into individual toggle-cards. Showing the raw recommendations below.
                </p>
                <pre
                  className="text-xs rounded p-2 overflow-auto max-h-64 whitespace-pre-wrap break-words"
                  style={{
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border)',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}
                >
                  {aiAnalysis.recommendations}
                </pre>
              </div>
            ) : (
              <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
                {aiAnalysis
                  ? 'No recommendations yet. Recommendations appear here after AI analysis completes.'
                  : result
                    ? 'No recommendations yet. Recommendations appear here after AI analysis completes.'
                    : 'No results yet. Run a backtest to generate recommendations.'}
              </p>
            )}

            {/* BTCAAAAA-36917 v4 UX: empty-state preview + demo affordances.
                Visible whenever parsedRecs is empty. Preview renders one
                static card inline without touching aiAnalysis; Demo
                populates aiAnalysis with the hardcoded sample payload
                (the cache persistence effect skips writes while demoMode
                is true, so neither path pollutes sessionStorage). */}
            {!previewMode && !demoMode && (
              <div
                className="mt-2 flex flex-wrap gap-2"
                data-testid="ai-recs-empty-actions"
              >
                <button
                  type="button"
                  onClick={() => setPreviewMode(true)}
                  className="px-2 py-1 text-[11px] rounded"
                  style={{
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border)',
                    cursor: 'pointer',
                  }}
                  data-testid="ai-recs-preview-btn"
                  title="Show one sample card so you can see the v3 layout without running a backtest."
                >
                  Preview the new layout
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setDemoMode(true);
                    setAiAnalysis({
                      diagnosis: SAMPLE_DIAGNOSIS,
                      recommendations: SAMPLE_RECOMMENDATIONS,
                      raw: `DIAGNOSIS: ${SAMPLE_DIAGNOSIS}\n\nRECOMMENDATIONS: ${SAMPLE_RECOMMENDATIONS}`,
                    });
                  }}
                  className="px-2 py-1 text-[11px] rounded"
                  style={{
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-secondary)',
                    border: '1px solid var(--border)',
                    cursor: 'pointer',
                  }}
                  data-testid="ai-recs-demo-btn"
                  title="Seed sample diagnosis + recommendations to explore the v3 toggle-card grid."
                >
                  Load demo data
                </button>
              </div>
            )}

            {previewMode && (
              <div className="mt-2 flex flex-col gap-2">
                <div
                  className="rounded p-2 text-left text-[11px] flex flex-col gap-1.5"
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    borderTop: '3px solid var(--accent-blue)',
                    opacity: 0.85,
                  }}
                  data-testid="ai-recs-preview-card"
                  data-preview-rec="1"
                  aria-label="Preview of a v3 toggle-card (sample data)"
                >
                  <div
                    className="flex items-center justify-between gap-2"
                    data-testid="ai-recs-preview-header"
                  >
                    <p
                      className="text-[10px] font-semibold uppercase tracking-wide"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      Request preview
                    </p>
                    <span
                      className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
                      style={{
                        background: 'var(--accent-blue-soft)',
                        color: 'var(--accent-blue)',
                        border: '1px solid var(--accent-blue)',
                      }}
                      data-testid="ai-recs-preview-outcome-pill"
                      title="Outcome of the request preview"
                    >
                      Request outcome · Ready
                    </span>
                  </div>
                  <div className="flex items-start justify-between gap-1.5">
                    <p
                      className="font-semibold truncate flex-1"
                      style={{ color: 'var(--text-secondary)' }}
                      title="Widen the EMA trend filter window"
                    >
                      Widen the EMA trend filter window
                    </p>
                    <span
                      className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
                      style={{
                        background: 'var(--bg-card)',
                        color: 'var(--text-faint)',
                        border: '1px solid var(--border)',
                      }}
                      data-testid="ai-recs-toggle-badge"
                    >
                      OFF
                    </span>
                  </div>
                  <p
                    className="text-[10px] truncate"
                    style={{ color: 'var(--text-faint)' }}
                    title="type: signal"
                  >
                    signal
                  </p>
                  <ul
                    className="flex flex-col gap-0.5"
                    data-testid="ai-recs-toggle-params"
                  >
                    <li
                      className="font-mono text-[10px] truncate"
                      style={{ color: 'var(--text-secondary)' }}
                      title="ema_window = 100"
                    >
                      ema_window = 100
                    </li>
                  </ul>
                  <p
                    className="text-[10px] line-clamp-2"
                    style={{ color: 'var(--text-faint)' }}
                    title="50-period EMA is too restrictive in the current chop; wider window lets more setups through."
                  >
                    50-period EMA is too restrictive in the current chop; wider window lets more setups through.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPreviewMode(false)}
                    className="px-2 py-1 text-[11px] rounded"
                    style={{
                      background: 'transparent',
                      color: 'var(--text-faint)',
                      border: '1px solid var(--border)',
                      cursor: 'pointer',
                    }}
                    data-testid="ai-recs-preview-close"
                  >
                    Hide preview
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setPreviewMode(false);
                      setDemoMode(true);
                      setAiAnalysis({
                        diagnosis: SAMPLE_DIAGNOSIS,
                        recommendations: SAMPLE_RECOMMENDATIONS,
                        raw: `DIAGNOSIS: ${SAMPLE_DIAGNOSIS}\n\nRECOMMENDATIONS: ${SAMPLE_RECOMMENDATIONS}`,
                      });
                    }}
                    className="px-2 py-1 text-[11px] rounded"
                    style={{
                      background: 'var(--bg-elevated)',
                      color: 'var(--text-secondary)',
                      border: '1px solid var(--border)',
                      cursor: 'pointer',
                    }}
                    data-testid="ai-recs-demo-btn-inline"
                  >
                    Load demo data instead
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div
            className="grid gap-2"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))' }}
          >
            {parsedRecs.map((rec) => {
              const isApplied = appliedRecIds.includes(rec.id);
              const isApplyingThis = perTileApplying.includes(rec.id);
              const errMsg = perTileError[rec.id];
              return (
                <button
                  key={rec.id}
                  type="button"
                  role="switch"
                  aria-checked={isApplied}
                  aria-busy={isApplyingThis}
                  disabled={!strategy?.id || isApplyingThis}
                  onClick={() => handleToggleRec(rec)}
                  data-testid="ai-recs-toggle-card"
                  data-rec-id={rec.id}
                  data-applied={isApplied ? 'true' : 'false'}
                  title={
                    isApplyingThis
                      ? 'Sending this recommendation to the orchestrator…'
                      : isApplied
                        ? 'Click to roll back this recommendation (local rollback — server-side undo is a follow-up backend ticket).'
                        : 'Click to apply this recommendation to the strategy.'
                  }
                  className="rounded p-2 text-left text-[11px] flex flex-col gap-1.5"
                  style={{
                    background: isApplied
                      ? 'var(--accent-green-muted)'
                      : 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    borderTop: `3px solid ${
                      isApplied
                        ? 'var(--accent-green)'
                        : 'var(--accent-blue)'
                    }`,
                    opacity: !strategy?.id ? 0.5 : 1,
                    cursor:
                      !strategy?.id || isApplyingThis ? 'not-allowed' : 'pointer',
                    transition: 'opacity 120ms ease, border-color 120ms ease',
                  }}
                >
                  <div className="flex items-start justify-between gap-1.5">
                    <p
                      className="font-semibold truncate flex-1"
                      style={{ color: 'var(--text-secondary)' }}
                      title={rec.title}
                    >
                      {rec.title}
                    </p>
                    <span
                      className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
                      style={{
                        background: isApplied
                          ? 'var(--accent-green)'
                          : 'var(--bg-card)',
                        color: isApplied ? 'var(--text-on-positive)' : 'var(--text-faint)',
                        border: `1px solid ${
                          isApplied
                            ? 'var(--accent-green)'
                            : 'var(--border)'
                        }`,
                      }}
                      data-testid="ai-recs-toggle-badge"
                    >
                      {isApplyingThis ? '…' : isApplied ? 'ON' : 'OFF'}
                    </span>
                  </div>

                  {/* AC17: how this rec sets up / adjusts the building block.
                      We surface the rec type + the first few suggested params
                      so the user sees exactly what would change. */}
                  <p
                    className="text-[10px] truncate"
                    style={{ color: 'var(--text-faint)' }}
                    title={`type: ${rec.type}`}
                  >
                    {rec.type}
                  </p>
                  {rec.suggestedParams.length > 0 && (
                    <ul
                      className="flex flex-col gap-0.5"
                      data-testid="ai-recs-toggle-params"
                    >
                      {rec.suggestedParams.slice(0, 4).map((p, idx) => (
                        <li
                          key={`${rec.id}:p:${idx}`}
                          className="font-mono text-[10px] truncate"
                          style={{ color: 'var(--text-secondary)' }}
                          title={`${p.key} = ${p.value}`}
                        >
                          {p.key} = {p.value}
                        </li>
                      ))}
                      {rec.suggestedParams.length > 4 && (
                        <li
                          className="text-[10px]"
                          style={{ color: 'var(--text-faint)' }}
                        >
                          + {rec.suggestedParams.length - 4} more…
                        </li>
                      )}
                    </ul>
                  )}
                  {rec.rationale && (
                    <p
                      className="text-[10px] line-clamp-2"
                      style={{ color: 'var(--text-faint)' }}
                      title={rec.rationale}
                    >
                      {rec.rationale}
                    </p>
                  )}

                  {/* AC20 error surface: per-tile, not a global banner. */}
                  {errMsg && (
                    <p
                      className="text-[10px] mt-0.5"
                      style={{ color: 'var(--accent-red)' }}
                      data-testid="ai-recs-toggle-error"
                      role="alert"
                    >
                      {errMsg}
                    </p>
                  )}

                  {/* B3: before/after parameter diff — visible only when the rec is ON. */}
                  {isApplied && (() => {
                    const snapshot = preApplySnapshots.find(([id]) => id === rec.id);
                    if (!snapshot) return null;
                    const [, preStrategy] = snapshot;
                    const paramSource: Array<{ key: string; value: string }> =
                      rec.suggestedParams.length > 0
                        ? rec.suggestedParams
                        : rec.parameter && rec.suggestedValue
                          ? [{ key: rec.parameter, value: rec.suggestedValue }]
                          : [];
                    const diffs = paramSource
                      .map((p) => ({
                        key: p.key,
                        before: findParamInStrategy(preStrategy, p.key),
                        after: p.value,
                      }))
                      .filter(
                        (d): d is { key: string; before: string; after: string } =>
                          d.before !== undefined && d.before !== d.after,
                      );
                    return (
                      <div
                        className="mt-1 pt-1.5"
                        style={{ borderTop: '1px solid var(--accent-green)' }}
                        data-testid="ai-recs-param-diff"
                      >
                        <p
                          className="text-[9px] font-semibold uppercase tracking-wide mb-1"
                          style={{ color: 'var(--accent-green-on)' }}
                        >
                          Applied changes
                        </p>
                        {diffs.length > 0 ? (
                          <ul className="flex flex-col gap-0.5" data-testid="ai-recs-param-diff-list">
                            {diffs.map((d) => (
                              <li
                                key={d.key}
                                className="text-[10px] font-mono flex gap-1 flex-wrap"
                                data-testid="ai-recs-param-diff-row"
                              >
                                <span style={{ color: 'var(--text-faint)' }}>{d.key}:</span>
                                <span>
                                  <span style={{ color: 'var(--text-muted)' }}>{d.before}</span>
                                  <span style={{ color: 'var(--text-faint)' }}> → </span>
                                  <span style={{ color: 'var(--accent-green-on)' }}>{d.after}</span>
                                </span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p
                            className="text-[10px]"
                            style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}
                            data-testid="ai-recs-param-diff-none"
                          >
                            No numeric parameters changed — check the strategy blocks manually.
                          </p>
                        )}
                      </div>
                    );
                  })()}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Per-tile saves are now the action surface (AC20). No more
          sticky "Apply all" footer — apply is per-card. */}
      </>)}

      {parsedRecs.length > 0 && (
        <ReverseViewBanner pattern={extractReverseViewPattern(reverseViewInputs)} />
      )}

      {rightTab === 'diagnose' && (
        <DiagnosePane
          diagnosis={aiAnalysis?.diagnosis ?? aiAnalysis?.raw ?? ''}
          rows={diagnoseRows}
          stagedSentence={stagedSentence}
          hasResult={!!result}
        />
      )}
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

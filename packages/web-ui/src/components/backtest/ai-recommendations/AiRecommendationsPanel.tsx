'use client';

import { useState, useCallback } from 'react';
import { ChevronDown, ChevronRight, Trash2 } from 'lucide-react';
import { BacktestResult, Strategy, Trade } from '@/lib/strategy-builder/types';
import { useAiSettings } from '@/hooks/useAiSettings';
import { useAiRecsHistory, AiRecsHistoryEntry, AiRecsHistoryStatus } from '@/hooks/useAiRecsHistory';

export interface AiRecommendationsPanelProps {
  result?: BacktestResult | null;
  strategy?: Strategy | null;
  backtestConfig?: Record<string, unknown> | null;
  disabled?: boolean;
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
}: {
  entry: AiRecsHistoryEntry;
  onUpdateStatus: (id: string, status: AiRecsHistoryStatus) => void;
  onUpdateNotes: (id: string, notes: string) => void;
  onRequestDelete: (id: string) => void;
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

      <div className="flex items-center gap-2 justify-end">
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
}: {
  entries: AiRecsHistoryEntry[];
  hydrated: boolean;
  onUpdateStatus: (id: string, status: AiRecsHistoryStatus) => void;
  onUpdateNotes: (id: string, notes: string) => void;
  onRequestDelete: (id: string) => void;
  onRequestClearAll: () => void;
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
              background: 'var(--accent-red, #f87171)',
              color: '#fff',
              border: '1px solid var(--accent-red, #f87171)',
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

function buildRequestPayload(
  result: BacktestResult | null | undefined,
  strategy: Strategy | null | undefined,
  backtestConfig: Record<string, unknown> | null | undefined,
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
}: AiRecommendationsPanelProps = {}) {
  const hasTrades = (result?.trades?.length ?? 0) > 0;
  const { settings, hydrated: aiSettingsHydrated } = useAiSettings();
  const history = useAiRecsHistory();

  const [view, setView] = useState<View>('current');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisDetail, setAnalysisDetail] = useState<string | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<{
    diagnosis: string;
    recommendations: string;
    raw: string;
  } | null>(null);
  const [confirmation, setConfirmation] = useState<{
    type: 'clear-all' | 'delete';
    entryId?: string;
  } | null>(null);

  const handleExport = useCallback(() => {
    const payload = buildRequestPayload(result, strategy, backtestConfig);
    const blob = new Blob([payload], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ai_request_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [result, strategy, backtestConfig]);

  const handleApproveAndSend = useCallback(async () => {
    if (!hasTrades || analyzing) return;
    setAnalyzing(true);
    setAnalysisError(null);
    setAnalysisDetail(null);
    try {
      const payloadJson = buildRequestPayload(result, strategy, backtestConfig);
      const payload = JSON.parse(payloadJson) as unknown;
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
        }),
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
    } catch (err) {
      setAnalysisError(
        err instanceof Error ? err.message : 'The analyze request failed.',
      );
    } finally {
      setAnalyzing(false);
    }
  }, [
    hasTrades,
    analyzing,
    result,
    strategy,
    backtestConfig,
    settings.provider,
    settings.model,
    settings.apiKeys,
    settings.ollamaBaseUrl,
    history,
  ]);

  const canSend = hasTrades && !analyzing && aiSettingsHydrated;

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
        <>
          {/* Strategy Diagnosis */}
      <div className="rounded p-3" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
        <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
          STRATEGY DIAGNOSIS
        </p>
        {aiAnalysis?.diagnosis ? (
          <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
            {aiAnalysis.diagnosis}
          </p>
        ) : aiAnalysis?.raw ? (
          <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
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

      {/* Recommendations */}
      <div className="rounded p-3" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
        <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
          RECOMMENDATIONS
        </p>
        {aiAnalysis?.recommendations ? (
          <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
            {aiAnalysis.recommendations}
          </p>
        ) : (
          <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
            {aiAnalysis
              ? 'No structured recommendations in the response. See Strategy Diagnosis above for the full reply.'
              : result
                ? 'No recommendations yet. Recommendations appear here after AI analysis completes.'
                : 'No results yet. Run a backtest to generate recommendations.'}
          </p>
        )}
      </div>

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
            const payload = buildRequestPayload(result, strategy, backtestConfig);
            const kb = (payload.length / 1024).toFixed(1);
            const tokens = Math.round(payload.length / 4);
            return `Strategy blocks: ${strategy?.blocks?.length ?? 0} | Trades: ${result.totalTrades} | Request size: ${kb} KB (~${tokens} tokens)`;
          })()}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 justify-end mt-1">
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
        <button
          type="button"
          onClick={handleApproveAndSend}
          disabled={!canSend}
          title={
            analyzing
              ? 'Sending the request preview to the configured AI provider…'
              : 'Send the request preview to the configured AI provider and display the diagnosis and recommendations.'
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
          {analyzing ? 'Sending…' : 'Approve & Send to AI'}
        </button>
      </div>
        </>
      ) : (
        <HistoryView
          entries={history.entries}
          hydrated={history.hydrated}
          onUpdateStatus={history.updateStatus}
          onUpdateNotes={history.updateNotes}
          onRequestDelete={requestDelete}
          onRequestClearAll={requestClearAll}
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
    </div>
  );
}

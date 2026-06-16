'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { BacktestResult, Strategy, Trade } from '@/lib/strategy-builder/types';
import { useAiSettings } from '@/hooks/useAiSettings';

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

export function AiRecommendationsPanel({
  result,
  strategy,
  backtestConfig,
}: AiRecommendationsPanelProps = {}) {
  const hasTrades = (result?.trades?.length ?? 0) > 0;
  const { settings, hydrated: aiSettingsHydrated } = useAiSettings();

  const [phase, setPhase] = useState<SendPhase>('idle');
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisDetail, setAnalysisDetail] = useState<string | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<{
    diagnosis: string;
    recommendations: string;
    raw: string;
  } | null>(null);

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

  const handleCancel = useCallback(() => {
    if (!analyzing) return;
    abortRef.current?.abort();
  }, [analyzing]);

  const handleApproveAndSend = useCallback(async () => {
    if (!hasTrades || analyzing) return;
    setAnalysisError(null);
    setAnalysisDetail(null);
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
      const payloadJson = buildRequestPayload(result, strategy, backtestConfig);
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
          prompt:
            'Analyze this trading strategy backtest and return a diagnosis and concrete, actionable recommendations.',
          payload,
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
      setAiAnalysis(parseAnalysisResponse(data.text ?? ''));
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
  ]);

  const canSend = hasTrades && !analyzing && aiSettingsHydrated;
  const showProgress = phase !== 'idle' && phase !== 'error';
  const progressPercent = phase === 'idle' || phase === 'error' ? 0 : PHASE_INFO[phase as Exclude<SendPhase, 'idle' | 'error'>].percent;
  const progressLabel =
    phase === 'idle' || phase === 'error'
      ? ''
      : PHASE_INFO[phase as Exclude<SendPhase, 'idle' | 'error'>].label;

  return (
    <div className="flex flex-col gap-3">
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

      {/* Progress indicator — visible across building-request / sending / awaiting-provider / done */}
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
          {analyzing
            ? 'Sending…'
            : phase === 'done'
              ? 'Send Again'
              : phase === 'error'
                ? 'Retry'
                : 'Approve & Send to AI'}
        </button>
      </div>
    </div>
  );
}

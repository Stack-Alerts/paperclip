'use client';

import { useState, useCallback } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { BacktestResult, Strategy, Trade } from '@/lib/strategy-builder/types';

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

export function AiRecommendationsPanel({
  result,
  strategy,
  backtestConfig,
}: AiRecommendationsPanelProps = {}) {
  const hasTrades = (result?.trades?.length ?? 0) > 0;

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

  return (
    <div className="flex flex-col gap-3">
      {/* Strategy Diagnosis */}
      <div className="rounded p-3" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
        <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
          STRATEGY DIAGNOSIS
        </p>
        <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
          {result
            ? 'Awaiting AI analysis. Use “Approve & Send to AI” below once the request preview is verified.'
            : 'Run a backtest first, then use “Approve & Send to AI” to receive a strategy diagnosis.'}
        </p>
      </div>

      {/* Recommendations */}
      <div className="rounded p-3" style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}>
        <p className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--text-muted)' }}>
          RECOMMENDATIONS
        </p>
        <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
          {result
            ? 'No recommendations yet. Recommendations appear here after AI analysis completes.'
            : 'No results yet. Run a backtest to generate recommendations.'}
        </p>
      </div>

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
          disabled={!hasTrades}
          title="AI backend endpoint not yet connected — export to JSON and use the Python client to send."
          className="px-3 py-1.5 rounded text-xs font-medium"
          style={{
            background: hasTrades ? 'var(--accent-blue, #3b82f6)' : 'var(--bg-card)',
            color: hasTrades ? '#fff' : 'var(--text-faint)',
            border: '1px solid var(--border)',
            opacity: hasTrades ? 1 : 0.5,
            cursor: hasTrades ? 'pointer' : 'not-allowed',
          }}
        >
          Approve &amp; Send to AI
        </button>
      </div>
    </div>
  );
}

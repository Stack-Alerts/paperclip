'use client';

// BTCAAAAA-37774 Sprint A2 — Strategy Impact KPI bar.
//
// Four tiles (Win Rate · Max Drawdown · Net PnL · Trades) showing
// before → after values and a delta strip, plus a far-right "<n> applied"
// chip and a Preview/Confirmed indicator that flips after a 250ms debounced
// re-backtest stub (Sprint B/B4 ships the real endpoint).
//
// Label set aligned to mockup BTCAAAAA-38517: the prior "DD · PF"
// dual-row tile (maxDrawdown + profitFactor) was simplified to a single
// "Max Drawdown" tile to match the board-supplied mockup. "Net Liquidity"
// was renamed "Net PnL" and "Entries" was renamed "Trades" — the
// underlying KpiSet fields are unchanged.

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AppliedRecImpact,
  KpiSet,
  ProjectedDelta,
  applyDelta,
  deltaDirection,
  formatCurrency,
  formatInteger,
  formatPercent,
  rebacktestStub,
  sumDeltas,
} from './strategyImpactKpi';

// B4: function signature for a server-side re-projection call. When provided,
// the bar fires this after the 250ms debounce and flips to "Confirmed" on
// success. Falls back to rebacktestStub (local delta sum) when absent.
export type ReProjectFn = (signal: AbortSignal) => Promise<KpiSet | null>;

const DEBOUNCE_MS = 250;

export type ImpactBarMode = 'live' | 'snapshot';

export interface StrategyImpactKpiBarProps {
  baseline: KpiSet;
  appliedImpacts: AppliedRecImpact[];
  mode?: ImpactBarMode;
  snapshotAfter?: KpiSet;
  // Sprint B/B4: when provided, the bar calls this after the 250ms debounce
  // to get confirmed KPIs from the real backtest pipeline. Omitting it keeps
  // the bar in Preview (local delta sum) indefinitely — safe for all callers
  // that predate Sprint B.
  reProjectFn?: ReProjectFn;
  /** @deprecated Use reProjectFn instead. Kept for backward compat. */
  enableConfirmed?: boolean;
}

interface TileSpec {
  id: 'wr' | 'max-drawdown' | 'net-pnl' | 'trades';
  label: string;
  format: (v: number) => string;
  pick: (k: KpiSet) => number;
  delta: (d: ProjectedDelta) => number;
  formatDelta: (d: number) => string;
  higherIsBetter: boolean;
}

const TILES: TileSpec[] = [
  {
    id: 'wr',
    label: 'Win Rate',
    format: (v) => formatPercent(v),
    pick: (k) => k.winRate,
    delta: (d) => d.winRate ?? 0,
    formatDelta: (d) => `${d >= 0 ? '+' : ''}${(d * 100).toFixed(1)}pp`,
    higherIsBetter: true,
  },
  {
    id: 'max-drawdown',
    label: 'Max Drawdown',
    format: (v) => formatPercent(v, 1),
    pick: (k) => k.maxDrawdown,
    delta: (d) => d.maxDrawdown ?? 0,
    formatDelta: (d) => `${d >= 0 ? '+' : ''}${(d * 100).toFixed(1)}pp`,
    higherIsBetter: false,
  },
  {
    id: 'net-pnl',
    label: 'Net PnL',
    format: (v) => formatCurrency(v),
    pick: (k) => k.netLiquidity,
    delta: (d) => d.netLiquidity ?? 0,
    formatDelta: (d) => `${d >= 0 ? '+' : ''}${formatCurrency(d)}`,
    higherIsBetter: true,
  },
  {
    id: 'trades',
    label: 'Trades',
    format: (v) => formatInteger(v),
    pick: (k) => k.entries,
    delta: (d) => d.entries ?? 0,
    formatDelta: (d) => `${d >= 0 ? '+' : ''}${Math.trunc(d)}`,
    higherIsBetter: true,
  },
];

const INDICATOR_STYLES: Record<
  'idle' | 'preview' | 'pending' | 'confirmed' | 'snapshot',
  { bg: string; fg: string; border: string }
> = {
  idle: { bg: 'var(--bg-elevated)', fg: 'var(--text-faint)', border: 'var(--border)' },
  preview: { bg: 'var(--accent-blue-soft)', fg: 'var(--accent-blue)', border: 'var(--accent-blue)' },
  pending: { bg: 'var(--bg-elevated)', fg: 'var(--text-muted)', border: 'var(--border)' },
  confirmed: { bg: 'var(--accent-green-soft)', fg: 'var(--accent-green-on)', border: 'var(--accent-green-on)' },
  snapshot: { bg: 'var(--bg-elevated)', fg: 'var(--text-muted)', border: 'var(--border)' },
};

const DELTA_PALETTE: Record<'up' | 'down' | 'flat', { bg: string; fg: string; border: string }> = {
  up: {
    bg: 'var(--accent-green-soft)',
    fg: 'var(--accent-green-on)',
    border: 'var(--accent-green-on)',
  },
  down: {
    bg: 'var(--accent-red-soft)',
    fg: 'var(--accent-red-on)',
    border: 'var(--accent-red-on)',
  },
  flat: {
    bg: 'var(--bg-card)',
    fg: 'var(--text-faint)',
    border: 'var(--border)',
  },
};

export function StrategyImpactKpiBar({
  baseline,
  appliedImpacts,
  mode = 'live',
  snapshotAfter,
  reProjectFn,
  enableConfirmed = false,
}: StrategyImpactKpiBarProps) {
  const deltas = useMemo(
    () => appliedImpacts.map((i) => i.delta),
    [appliedImpacts],
  );
  const combinedDelta = useMemo(() => sumDeltas(deltas), [deltas]);

  const previewAfter = useMemo(
    () => (mode === 'snapshot' && snapshotAfter
      ? snapshotAfter
      : applyDelta(baseline, combinedDelta)),
    [mode, snapshotAfter, baseline, combinedDelta],
  );

  // Tag the confirmed-after value with the applied-set key it was computed
  // against. Deriving showConfirmed from the key match means we never have to
  // clear the state in the effect body when appliedImpacts changes — the
  // existing value simply becomes "stale" until a new one lands.
  const [confirmedResult, setConfirmedResult] = useState<{ forKey: string; after: KpiSet } | null>(null);
  const [confirming, setConfirming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const appliedKey = useMemo(
    () => appliedImpacts.map((i) => i.recId).join('|'),
    [appliedImpacts],
  );

  // 250ms debounced re-backtest. Aborts in-flight request and re-arms whenever
  // the applied set changes. Snapshot mode skips this — the pair is final.
  // When reProjectFn is provided (Sprint B/B4), it's called instead of the
  // stub; if the server call returns null (unavailable) we fall back to the
  // local delta sum so the indicator never sticks on "Re-running…".
  useEffect(() => {
    if (mode === 'snapshot') return;
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    if (appliedImpacts.length === 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- abort-resolved path doesn't reach setConfirming; this keeps the indicator from sticking on "Re-running…" when the applied set is cleared mid-flight
      setConfirming(false);
      return;
    }
    debounceRef.current = setTimeout(() => {
      const controller = new AbortController();
      abortRef.current = controller;
      setConfirming(true);
      const resolveFn: Promise<KpiSet> = reProjectFn
        ? reProjectFn(controller.signal).then(
            (serverResult) =>
              serverResult ?? rebacktestStub(baseline, deltas, controller.signal),
          )
        : rebacktestStub(baseline, deltas, controller.signal);
      resolveFn
        .then((result) => {
          if (controller.signal.aborted) return;
          setConfirmedResult({ forKey: appliedKey, after: result });
          setConfirming(false);
        })
        .catch(() => {
          if (controller.signal.aborted) return;
          setConfirming(false);
        });
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
    };
  }, [appliedImpacts, baseline, deltas, mode, appliedKey, reProjectFn]);

  const showConfirmed =
    mode === 'live' &&
    (enableConfirmed || reProjectFn != null) &&
    confirmedResult !== null &&
    confirmedResult.forKey === appliedKey;
  const after = showConfirmed && confirmedResult ? confirmedResult.after : previewAfter;
  const appliedCount = appliedImpacts.length;

  const indicator = useMemo(() => {
    if (mode === 'snapshot') return { label: 'Snapshot', tone: 'snapshot' as const };
    if (appliedCount === 0) return { label: 'Baseline', tone: 'idle' as const };
    if (confirming) return { label: 'Re-running…', tone: 'pending' as const };
    if (showConfirmed) return { label: 'Confirmed', tone: 'confirmed' as const };
    return { label: 'Preview', tone: 'preview' as const };
  }, [mode, appliedCount, confirming, showConfirmed]);

  const indicatorStyle = INDICATOR_STYLES[indicator.tone];

  return (
    <div
      className="rounded p-2 flex flex-col gap-2"
      data-testid="strategy-impact-kpi-bar"
      data-mode={mode}
      data-indicator={indicator.tone}
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <p
            className="text-[10px] font-semibold uppercase tracking-wide"
            style={{ color: 'var(--text-muted)' }}
          >
            Strategy Impact
          </p>
          <span
            className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
            data-testid="strategy-impact-indicator"
            style={{
              background: indicatorStyle.bg,
              color: indicatorStyle.fg,
              border: `1px solid ${indicatorStyle.border}`,
            }}
            title={
              indicator.tone === 'preview'
                ? 'Live projected impact from applied recommendations. Confirmed values land after re-backtest (Sprint B).'
                : indicator.tone === 'pending'
                  ? 'Re-running backtest with applied recommendations…'
                  : indicator.tone === 'confirmed'
                    ? 'Confirmed by re-backtest.'
                    : indicator.tone === 'snapshot'
                      ? 'Snapshot from history — values frozen.'
                      : 'No recommendations applied yet — showing the baseline backtest.'
            }
          >
            {indicator.label}
          </span>
        </div>
        <span
          className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded"
          data-testid="strategy-impact-applied-chip"
          style={{
            background: appliedCount > 0 ? 'var(--accent-green-soft)' : 'var(--bg-elevated)',
            color: appliedCount > 0 ? 'var(--accent-green-on)' : 'var(--text-faint)',
            border: `1px solid ${appliedCount > 0 ? 'var(--accent-green-on)' : 'var(--border)'}`,
          }}
        >
          {appliedCount} applied
        </span>
      </div>

      <div
        className="grid gap-2"
        style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}
      >
        {TILES.map((tile) => {
          const before1 = tile.pick(baseline);
          const after1 = tile.pick(after);
          const delta1 = after1 - before1;
          const dir1 = deltaDirection(delta1, tile.higherIsBetter);

          return (
            <div
              key={tile.id}
              className="rounded p-2 flex flex-col gap-1"
              data-testid={`strategy-impact-tile-${tile.id}`}
              style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
              }}
            >
              <p
                className="text-[10px] font-semibold uppercase tracking-wide"
                style={{ color: 'var(--text-faint)' }}
              >
                {tile.label}
              </p>

              <div className="flex items-baseline gap-1 flex-wrap">
                <span
                  className="text-[11px] font-mono"
                  style={{ color: 'var(--text-muted)' }}
                  data-testid={`strategy-impact-${tile.id}-before`}
                >
                  {tile.format(before1)}
                </span>
                <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                  →
                </span>
                <span
                  className="text-sm font-mono font-semibold"
                  style={{ color: 'var(--text-secondary)' }}
                  data-testid={`strategy-impact-${tile.id}-after`}
                >
                  {tile.format(after1)}
                </span>
              </div>

              <DeltaChip
                direction={dir1}
                label={tile.formatDelta(delta1)}
                testId={`strategy-impact-${tile.id}-delta`}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DeltaChip({
  direction,
  label,
  testId,
}: {
  direction: 'up' | 'down' | 'flat';
  label: string;
  testId: string;
}) {
  const palette = DELTA_PALETTE[direction];
  const arrow = direction === 'up' ? '▲' : direction === 'down' ? '▼' : '·';
  const dirWord = direction === 'up' ? 'up' : direction === 'down' ? 'down' : 'no change';
  return (
    <span
      className="self-start text-[10px] font-mono px-1.5 py-0.5 rounded"
      data-testid={testId}
      data-direction={direction}
      aria-label={`${dirWord}: ${label}`}
      style={{
        background: palette.bg,
        color: palette.fg,
        border: `1px solid ${palette.border}`,
      }}
    >
      <span aria-hidden="true">{arrow}</span>{' '}{label}
    </span>
  );
}

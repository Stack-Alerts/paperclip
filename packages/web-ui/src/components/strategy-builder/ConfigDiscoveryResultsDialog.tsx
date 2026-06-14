'use client';

import React, { useState, useMemo, useCallback, useRef } from 'react';
import { RichTooltip, type TooltipContent } from './RichTooltip';

export interface DiscoveryScenario {
  rank: number;
  badge: 'gold' | 'silver' | 'bronze' | 'baseline' | '';
  scenario: string;
  trades: number;
  winRate: number;
  totalPnl: number;
  avgPnl: number;
  sharpe: number;
  tp1: number;
  tp2: number;
  tp3: number;
  sl: number;
  time: number;
  avgBars: number;
  maxDd: number;
  type: 'baseline' | 'discovery';
  // BTCAAAAA-36309: full configuration of this run as label/value pairs, shown
  // on row hover so each result exposes the exact config that produced it.
  configDetail?: Array<[string, string]>;
}

export interface DiscoveryProgressState {
  current: number;
  total: number;
  message: string;
}

export interface ConfigDiscoveryResultsDialogProps {
  open: boolean;
  results: DiscoveryScenario[];
  minTradeCount?: number;
  // BTCAAAAA-36309: the dialog now opens the moment discovery starts and streams
  // completed tests in. `running` + `progress` drive the inline progress bar.
  running?: boolean;
  progress?: DiscoveryProgressState | null;
  // BTCAAAAA-36311: when true the modal shows a yes/no confirmation gate instead
  // of the results table — the sweep is long-running, so it only starts once the
  // user confirms via onConfirm.
  awaitingConfirm?: boolean;
  scenarioCount?: number;
  onConfirm?: () => void;
  onApplyConfig: (scenario: DiscoveryScenario) => void;
  onClose: () => void;
}

// Build the hover tooltip for a result row from its captured config detail.
function configTooltip(row: DiscoveryScenario): TooltipContent {
  const hasDetail = !!row.configDetail && row.configDetail.length > 0;
  return {
    title: row.scenario,
    sections: hasDetail
      ? [{ header: 'Run configuration', items: row.configDetail!.map(([k, v]) => `${k}: ${v}`) }]
      : undefined,
    body: hasDetail ? undefined : 'Configuration details unavailable.',
  };
}

const BADGE_INLINE_STYLES: Record<string, React.CSSProperties> = {
  gold: { background: 'color-mix(in srgb, #eab308 20%, transparent)', color: '#eab308', border: '1px solid #ca8a04' },
  silver: { background: 'color-mix(in srgb, var(--text-secondary) 20%, transparent)', color: 'var(--text-secondary)', border: '1px solid var(--border)' },
  bronze: { background: 'color-mix(in srgb, var(--accent-orange) 20%, transparent)', color: 'var(--accent-orange)', border: '1px solid var(--accent-orange)' },
  baseline: { background: 'color-mix(in srgb, var(--accent-blue) 20%, transparent)', color: 'var(--accent-blue)', border: '1px solid var(--accent-blue-dark)' },
  '': { background: 'var(--bg-card)', color: 'var(--text-secondary)' },
};

// BTCAAAAA-36309: two-tone badge icons. The board flagged the full-colour emoji
// medals as violating the Strategy Builder two-tone template (layered shapes that
// inherit the badge colour via currentColor, with a lighter second tone). Medals
// render a ribbon + disc; baseline renders a marker flag. Empty badge → no icon.
function BadgeIcon({ badge }: { badge: string }) {
  if (badge === '') return null;
  if (badge === 'baseline') {
    return (
      <svg width="12" height="12" viewBox="0 0 16 16" fill="none" className="flex-shrink-0" aria-hidden>
        <line x1="4" y1="2" x2="4" y2="14.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        <path d="M4 2.5 H12.5 L10.5 5.25 L12.5 8 H4 Z" fill="currentColor" fillOpacity="0.25" stroke="currentColor" strokeWidth="1.1" strokeLinejoin="round" />
      </svg>
    );
  }
  // gold / silver / bronze medal — ribbon (two tones) + disc.
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" className="flex-shrink-0" aria-hidden>
      <path d="M5 1.2 L8.2 6 L6 7.4 Z" fill="currentColor" fillOpacity="0.85" />
      <path d="M11 1.2 L7.8 6 L10 7.4 Z" fill="currentColor" fillOpacity="0.5" />
      <circle cx="8" cy="10.6" r="4.2" fill="currentColor" fillOpacity="0.25" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}

type SortKey = keyof DiscoveryScenario;

function ColHeader({
  label,
  sortK,
  sortKey,
  sortAsc,
  onSort,
}: {
  label: string;
  sortK: SortKey;
  sortKey: SortKey;
  sortAsc: boolean;
  onSort: (k: SortKey) => void;
}) {
  return (
    <th
      onClick={() => onSort(sortK)}
      className="px-3 py-2 text-left text-xs font-semibold cursor-pointer select-none whitespace-nowrap"
      style={{ color: 'var(--text-secondary)' }}
      onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
      onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
    >
      {label}
      {sortKey === sortK ? (sortAsc ? ' ▲' : ' ▼') : ''}
    </th>
  );
}

export const ConfigDiscoveryResultsDialog: React.FC<ConfigDiscoveryResultsDialogProps> = ({
  open,
  results,
  minTradeCount = 0,
  running = false,
  progress = null,
  awaitingConfirm = false,
  scenarioCount = 0,
  onConfirm,
  onApplyConfig,
  onClose,
}) => {
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [sortAsc, setSortAsc] = useState(true);
  const [minTrades, setMinTrades] = useState(minTradeCount);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  // BTCAAAAA-36309: anchor the per-row config tooltip to this scroll container so
  // the balloon stays in one consistent place (vertically centred on the table)
  // while its arrow tracks whichever row the mouse is over.
  const tableScrollRef = useRef<HTMLDivElement>(null);

  const handleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortAsc((a) => !a);
      } else {
        setSortKey(key);
        setSortAsc(true);
      }
    },
    [sortKey]
  );

  const filtered = useMemo(() => {
    const f = results.filter((r) => r.trades >= minTrades);
    return [...f].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === 'number' && typeof bv === 'number') {
        return sortAsc ? av - bv : bv - av;
      }
      return sortAsc
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
  }, [results, minTrades, sortKey, sortAsc]);

  if (!open) return null;

  // Confirmation gate (BTCAAAAA-36311): the sweep runs scenarioCount scenarios
  // plus a baseline and takes a while, so require an explicit yes/no first.
  if (awaitingConfirm) {
    const totalRuns = scenarioCount + 1;
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
        <div className="rounded-lg shadow-2xl w-full max-w-md mx-4 border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
          <div className="border-b px-6 py-4" style={{ borderColor: 'var(--border)' }}>
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-secondary)' }}>Start Config Discovery?</h2>
          </div>
          <div className="px-6 py-5 space-y-3">
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Config Discovery will run <strong>{totalRuns}</strong> backtests (1 baseline + {scenarioCount} scenarios), one at a time.
            </p>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              This can take a fair amount of time. Do you want to start now?
            </p>
          </div>
          <div className="flex justify-end gap-2 px-6 py-4 border-t" style={{ borderColor: 'var(--border)' }}>
            <button
              onClick={onClose}
              className="px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
            >
              No, cancel
            </button>
            <button
              onClick={() => onConfirm?.()}
              className="px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
            >
              Yes, start
            </button>
          </div>
        </div>
      </div>
    );
  }

  const selected = selectedIdx !== null ? filtered[selectedIdx] : null;
  const progressPct =
    !running
      ? 100
      : progress && progress.total > 0
        ? Math.min(100, Math.round((progress.current / progress.total) * 100))
        : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg shadow-2xl w-full max-w-[92vw] mx-4 h-[85vh] flex flex-col border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <div className="flex items-center justify-between border-b px-6 py-4 flex-shrink-0" style={{ borderColor: 'var(--border)' }}>
          <div>
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-secondary)' }}>Config Discovery Results</h2>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {running
                ? `${results.length} of ${progress?.total ?? '…'} scenarios completed`
                : `${results.length} scenarios evaluated`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="transition-colors text-xl leading-none"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
          >
            ×
          </button>
        </div>

        {/* Filter + progress controls. Left: Min Trades slider. Right: config
            count + a progress bar that fills the remaining width while discovery
            runs (BTCAAAAA-36309). */}
        <div className="flex items-center gap-4 px-6 py-3 border-b flex-shrink-0" style={{ borderColor: 'var(--bg-card)' }}>
          <label className="text-xs whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>Min Trades:</label>
          <input
            type="range"
            min={0}
            max={Math.max(0, ...results.map((r) => r.trades))}
            value={minTrades}
            onChange={(e) => setMinTrades(Number(e.target.value))}
            className="w-32"
          />
          <span className="text-xs w-8" style={{ color: 'var(--text-secondary)' }}>{minTrades}</span>
          <span className="text-xs whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>{filtered.length} shown</span>

          <span className="text-xs whitespace-nowrap ml-2" style={{ color: 'var(--text-secondary)' }}>
            {running ? progress?.total ?? results.length : results.length} configs
          </span>

          {/* Progress bar — claims the leftover horizontal space. */}
          <div className="flex-1 flex items-center gap-2 min-w-0">
            <div
              className="flex-1 h-2 rounded-full overflow-hidden min-w-0"
              style={{ background: 'var(--bg-card)' }}
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={progress?.total ?? 0}
              aria-valuenow={progress?.current ?? 0}
            >
              <div
                className="h-full rounded-full transition-[width] duration-300"
                style={{
                  width: progressPct + '%',
                  background: running ? 'var(--accent-blue)' : 'var(--accent-green)',
                }}
              />
            </div>
            <span className="text-xs whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
              {running
                ? `${progress?.current ?? 0}/${progress?.total ?? 0}`
                : 'Complete'}
            </span>
          </div>
        </div>

        {/* Results Table */}
        <div ref={tableScrollRef} className="flex-1 overflow-auto">
          <table className="w-full text-sm border-collapse">
            <thead className="sticky top-0 z-10" style={{ background: 'var(--bg-card)' }}>
              <tr>
                <ColHeader label="Rank" sortK="rank" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <th className="px-3 py-2 text-left text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>Badge</th>
                <ColHeader label="Scenario" sortK="scenario" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="Trades" sortK="trades" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="Win%" sortK="winRate" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="Total PnL" sortK="totalPnl" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="Avg PnL" sortK="avgPnl" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="Sharpe" sortK="sharpe" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="TP1" sortK="tp1" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="TP2" sortK="tp2" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="TP3" sortK="tp3" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="SL" sortK="sl" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="MaxDD" sortK="maxDd" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <ColHeader label="Type" sortK="type" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
              </tr>
            </thead>
            <tbody style={{ borderColor: 'var(--bg-card)' }}>
              {filtered.map((row, idx) => (
                <RichTooltip key={idx} content={configTooltip(row)} anchorTo={tableScrollRef}>
                <tr
                  onClick={() => setSelectedIdx(idx === selectedIdx ? null : idx)}
                  className="cursor-pointer transition-colors"
                  style={
                    selectedIdx === idx
                      ? { background: 'color-mix(in srgb, var(--accent-blue) 15%, transparent)' }
                      : row.type === 'baseline'
                      ? { background: 'color-mix(in srgb, var(--bg-card) 40%, transparent)' }
                      : {}
                  }
                  onMouseEnter={e => {
                    if (selectedIdx !== idx) {
                      (e.currentTarget as HTMLTableRowElement).style.background = 'color-mix(in srgb, var(--bg-card) 50%, transparent)';
                    }
                  }}
                  onMouseLeave={e => {
                    if (selectedIdx !== idx) {
                      (e.currentTarget as HTMLTableRowElement).style.background = row.type === 'baseline'
                        ? 'color-mix(in srgb, var(--bg-card) 40%, transparent)'
                        : '';
                    }
                  }}
                >
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-secondary)' }}>{row.rank}</td>
                  <td className="px-3 py-2">
                    <span
                      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium"
                      style={BADGE_INLINE_STYLES[row.badge]}
                    >
                      <BadgeIcon badge={row.badge} /> {row.badge || '—'}
                    </span>
                  </td>
                  <td className="px-3 py-2 max-w-xs truncate" style={{ color: 'var(--text-secondary)' }}>{row.scenario}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-secondary)' }}>{row.trades}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-secondary)' }}>{row.winRate.toFixed(1)}%</td>
                  <td
                    className="px-3 py-2 font-mono font-semibold"
                    style={{ color: row.totalPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}
                  >
                    ${row.totalPnl.toFixed(2)}
                  </td>
                  <td
                    className="px-3 py-2 font-mono"
                    style={{ color: row.avgPnl >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}
                  >
                    ${row.avgPnl.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-secondary)' }}>{row.sharpe.toFixed(2)}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-secondary)' }}>{row.tp1}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-secondary)' }}>{row.tp2}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-secondary)' }}>{row.tp3}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-secondary)' }}>{row.sl}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-secondary)' }}>${row.maxDd.toFixed(0)}</td>
                  <td className="px-3 py-2">
                    <span
                      className="inline-flex px-2 py-0.5 rounded text-xs"
                      style={
                        row.type === 'baseline'
                          ? { background: 'color-mix(in srgb, var(--accent-blue) 20%, transparent)', color: 'var(--accent-blue)' }
                          : { background: 'var(--bg-hover)', color: 'var(--text-secondary)' }
                      }
                    >
                      {row.type}
                    </span>
                  </td>
                </tr>
                </RichTooltip>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={14} className="px-3 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                    {running ? 'Running scenarios… completed tests will appear here.' : 'No scenarios match the current filter'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex justify-between items-center px-6 py-4 border-t flex-shrink-0" style={{ borderColor: 'var(--border)' }}>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {selected ? `Selected: ${selected.scenario}` : 'Click a row to select'}
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
            >
              Close
            </button>
            <button
              disabled={!selected}
              onClick={() => selected && onApplyConfig(selected)}
              className="px-4 py-2 rounded text-sm font-medium disabled:opacity-40 transition-colors"
              style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
            >
              Apply Config
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfigDiscoveryResultsDialog;

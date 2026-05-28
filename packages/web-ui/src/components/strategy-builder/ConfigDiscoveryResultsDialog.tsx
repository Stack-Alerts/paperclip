'use client';

import React, { useState, useMemo, useCallback } from 'react';

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
}

export interface ConfigDiscoveryResultsDialogProps {
  open: boolean;
  results: DiscoveryScenario[];
  minTradeCount?: number;
  onApplyConfig: (scenario: DiscoveryScenario) => void;
  onClose: () => void;
}

const BADGE_INLINE_STYLES: Record<string, React.CSSProperties> = {
  gold: { background: 'color-mix(in srgb, #eab308 20%, transparent)', color: '#eab308', border: '1px solid #ca8a04' },
  silver: { background: 'color-mix(in srgb, var(--text-secondary) 20%, transparent)', color: 'var(--text-primary)', border: '1px solid var(--border)' },
  bronze: { background: 'color-mix(in srgb, var(--accent-orange) 20%, transparent)', color: 'var(--accent-orange)', border: '1px solid var(--accent-orange)' },
  baseline: { background: 'color-mix(in srgb, var(--accent-blue) 20%, transparent)', color: 'var(--accent-blue)', border: '1px solid var(--accent-blue-dark)' },
  '': { background: 'var(--bg-card)', color: 'var(--text-secondary)' },
};

const BADGE_ICONS: Record<string, string> = {
  gold: '🥇',
  silver: '🥈',
  bronze: '🥉',
  baseline: '📌',
  '': '',
};

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
      onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
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
  onApplyConfig,
  onClose,
}) => {
  const [sortKey, setSortKey] = useState<SortKey>('rank');
  const [sortAsc, setSortAsc] = useState(true);
  const [minTrades, setMinTrades] = useState(minTradeCount);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

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

  const selected = selectedIdx !== null ? filtered[selectedIdx] : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg shadow-2xl w-full max-w-6xl mx-4 max-h-[90vh] flex flex-col border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <div className="flex items-center justify-between border-b px-6 py-4 flex-shrink-0" style={{ borderColor: 'var(--border)' }}>
          <div>
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-secondary)' }}>Config Discovery Results</h2>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{results.length} scenarios evaluated</p>
          </div>
          <button
            onClick={onClose}
            className="transition-colors text-xl leading-none"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
          >
            ×
          </button>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-4 px-6 py-3 border-b flex-shrink-0" style={{ borderColor: 'var(--bg-card)' }}>
          <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>Min Trades:</label>
          <input
            type="range"
            min={0}
            max={Math.max(0, ...results.map((r) => r.trades))}
            value={minTrades}
            onChange={(e) => setMinTrades(Number(e.target.value))}
            className="w-32"
          />
          <span className="text-xs w-8" style={{ color: 'var(--text-primary)' }}>{minTrades}</span>
          <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>{filtered.length} shown</span>
        </div>

        {/* Results Table */}
        <div className="flex-1 overflow-auto">
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
                <tr
                  key={idx}
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
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-primary)' }}>{row.rank}</td>
                  <td className="px-3 py-2">
                    <span
                      className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium"
                      style={BADGE_INLINE_STYLES[row.badge]}
                    >
                      {BADGE_ICONS[row.badge]} {row.badge || '—'}
                    </span>
                  </td>
                  <td className="px-3 py-2 max-w-xs truncate" style={{ color: 'var(--text-primary)' }}>{row.scenario}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-primary)' }}>{row.trades}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-primary)' }}>{row.winRate.toFixed(1)}%</td>
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
                  <td className="px-3 py-2 font-mono" style={{ color: 'var(--text-primary)' }}>{row.sharpe.toFixed(2)}</td>
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
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={14} className="px-3 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                    No scenarios match the current filter
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
              style={{ background: 'var(--bg-hover)', color: 'var(--text-primary)' }}
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

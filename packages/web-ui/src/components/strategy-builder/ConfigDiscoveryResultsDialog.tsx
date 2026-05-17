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

const BADGE_STYLES: Record<string, string> = {
  gold: 'bg-yellow-500/20 text-yellow-400 border border-yellow-600',
  silver: 'bg-zinc-400/20 text-zinc-300 border border-zinc-500',
  bronze: 'bg-orange-500/20 text-orange-400 border border-orange-600',
  baseline: 'bg-blue-500/20 text-blue-400 border border-blue-600',
  '': 'bg-zinc-800 text-zinc-400',
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
      className="px-3 py-2 text-left text-xs font-semibold text-zinc-400 cursor-pointer select-none hover:text-zinc-200 whitespace-nowrap"
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
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-6xl mx-4 max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between border-b border-zinc-700 px-6 py-4 flex-shrink-0">
          <div>
            <h2 className="text-base font-semibold text-zinc-100">Config Discovery Results</h2>
            <p className="text-xs text-zinc-400">{results.length} scenarios evaluated</p>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-200 transition-colors text-xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-4 px-6 py-3 border-b border-zinc-800 flex-shrink-0">
          <label className="text-xs text-zinc-400">Min Trades:</label>
          <input
            type="range"
            min={0}
            max={Math.max(0, ...results.map((r) => r.trades))}
            value={minTrades}
            onChange={(e) => setMinTrades(Number(e.target.value))}
            className="w-32"
          />
          <span className="text-xs text-zinc-300 w-8">{minTrades}</span>
          <span className="text-xs text-zinc-500 ml-2">{filtered.length} shown</span>
        </div>

        {/* Results Table */}
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm border-collapse">
            <thead className="bg-zinc-800 sticky top-0 z-10">
              <tr>
                <ColHeader label="Rank" sortK="rank" sortKey={sortKey} sortAsc={sortAsc} onSort={handleSort} />
                <th className="px-3 py-2 text-left text-xs font-semibold text-zinc-400">Badge</th>
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
            <tbody className="divide-y divide-zinc-800">
              {filtered.map((row, idx) => (
                <tr
                  key={idx}
                  onClick={() => setSelectedIdx(idx === selectedIdx ? null : idx)}
                  className={`cursor-pointer transition-colors ${
                    selectedIdx === idx
                      ? 'bg-blue-900/30'
                      : row.type === 'baseline'
                      ? 'bg-zinc-800/40 hover:bg-zinc-800'
                      : 'hover:bg-zinc-800/50'
                  }`}
                >
                  <td className="px-3 py-2 text-zinc-300 font-mono">{row.rank}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                        BADGE_STYLES[row.badge]
                      }`}
                    >
                      {BADGE_ICONS[row.badge]} {row.badge || '—'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-zinc-200 max-w-xs truncate">{row.scenario}</td>
                  <td className="px-3 py-2 text-zinc-300 font-mono">{row.trades}</td>
                  <td className="px-3 py-2 text-zinc-300 font-mono">{row.winRate.toFixed(1)}%</td>
                  <td
                    className={`px-3 py-2 font-mono font-semibold ${
                      row.totalPnl >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    ${row.totalPnl.toFixed(2)}
                  </td>
                  <td
                    className={`px-3 py-2 font-mono ${
                      row.avgPnl >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    ${row.avgPnl.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-zinc-300 font-mono">{row.sharpe.toFixed(2)}</td>
                  <td className="px-3 py-2 text-zinc-400 font-mono">{row.tp1}</td>
                  <td className="px-3 py-2 text-zinc-400 font-mono">{row.tp2}</td>
                  <td className="px-3 py-2 text-zinc-400 font-mono">{row.tp3}</td>
                  <td className="px-3 py-2 text-zinc-400 font-mono">{row.sl}</td>
                  <td className="px-3 py-2 text-zinc-400 font-mono">${row.maxDd.toFixed(0)}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-flex px-2 py-0.5 rounded text-xs ${
                        row.type === 'baseline'
                          ? 'bg-blue-900/40 text-blue-300'
                          : 'bg-zinc-700 text-zinc-400'
                      }`}
                    >
                      {row.type}
                    </span>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={14} className="px-3 py-8 text-center text-zinc-500 text-sm">
                    No scenarios match the current filter
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex justify-between items-center px-6 py-4 border-t border-zinc-700 flex-shrink-0">
          <span className="text-xs text-zinc-500">
            {selected ? `Selected: ${selected.scenario}` : 'Click a row to select'}
          </span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
            >
              Close
            </button>
            <button
              disabled={!selected}
              onClick={() => selected && onApplyConfig(selected)}
              className="px-4 py-2 rounded bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-40 transition-colors"
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

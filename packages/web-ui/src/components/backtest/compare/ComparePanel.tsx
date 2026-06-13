'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Search, X, Plus, GitCompare, ChevronUp, ChevronDown, Minus } from 'lucide-react';
import { loadAllRunRecords, deleteRunRecord } from '@/lib/backtest-history';
import type { BacktestRunRecord, BacktestResult, BacktestConfigFull } from '@/lib/strategy-builder/types';

export interface ComparePanelProps {
  currentResult?: BacktestResult;
  currentStrategyId?: string;
  currentStrategyName?: string;
}

// ── Formatters ────────────────────────────────────────────────────────────────

function fmt(n: number | undefined | null, decimals = 2): string {
  if (n == null || !isFinite(n)) return '—';
  return n.toFixed(decimals);
}
function fmtRet(n: number | undefined | null): string {
  if (n == null || !isFinite(n)) return '—';
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
}
function fmtDate(iso: string | undefined | null): string {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString(); } catch { return iso; }
}
function fmtDateTime(iso: string | undefined | null): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  } catch { return iso; }
}
function fmtUSD(n: number | undefined | null): string {
  if (n == null || !isFinite(n)) return '—';
  return `$${n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}
function colorForReturn(v: number | undefined | null): string {
  if (v == null) return 'var(--text-secondary)';
  return v >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
}

// ── Sparkline ─────────────────────────────────────────────────────────────────
function Sparkline({ values, color, height = 40 }: { values: number[]; color: string; height?: number }) {
  if (values.length < 2) return <div style={{ height }} />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const W = 120, H = 40;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = H - ((v - min) / range) * H;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height, display: 'block' }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function SectionLabel({ title }: { title: string }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-widest mt-4 mb-2 first:mt-0" style={{ color: 'var(--text-muted)' }}>
      {title}
    </p>
  );
}

// ── Diff badge ────────────────────────────────────────────────────────────────
function DiffBadge({ base, compare }: { base: number; compare: number }) {
  const delta = compare - base;
  if (Math.abs(delta) < 0.0001) return null;
  const color = delta > 0 ? 'var(--accent-green)' : 'var(--accent-red)';
  const prefix = delta > 0 ? '+' : '';
  return (
    <span className="ml-1 text-[10px]" style={{ color }}>
      ({prefix}{fmt(delta)})
    </span>
  );
}

// ── Config diff row ───────────────────────────────────────────────────────────
function ConfigDiffRow({ label, values }: {
  label: string;
  values: (string | number | boolean | undefined | null)[];
}) {
  const strVals = values.map(v => v == null ? '—' : String(v));
  const allSame = strVals.every(v => v === strVals[0]);
  return (
    <tr style={{ borderBottom: '1px solid var(--border)' }}>
      <td className="py-1.5 pr-3 text-[11px] whitespace-nowrap" style={{ color: 'var(--text-muted)', minWidth: 140 }}>
        {label}
      </td>
      {strVals.map((v, i) => (
        <td key={i} className="py-1.5 px-2 text-[11px] text-center" style={{
          color: (!allSame && i > 0) ? 'var(--accent-yellow, #f0a500)' : 'var(--text-secondary)',
          background: (!allSame && i > 0) ? 'rgba(240,165,0,0.07)' : 'transparent',
          fontVariantNumeric: 'tabular-nums',
        }}>
          {v}
        </td>
      ))}
    </tr>
  );
}

// ── Metric comparison row ─────────────────────────────────────────────────────
function MetricRow({ label, values, colorFn, suffix = '', prefix = '' }: {
  label: string;
  values: (number | undefined | null)[];
  colorFn?: (v: number | null) => string;
  suffix?: string;
  prefix?: string;
}) {
  const baseVal = values[0] ?? null;
  return (
    <tr style={{ borderBottom: '1px solid var(--border)' }}>
      <td className="py-1.5 pr-3 text-[11px] whitespace-nowrap" style={{ color: 'var(--text-muted)', minWidth: 140 }}>
        {label}
      </td>
      {values.map((v, i) => {
        const str = v == null ? '—' : `${prefix}${fmt(v)}${suffix}`;
        const color = colorFn ? colorFn(v ?? null) : 'var(--text-secondary)';
        return (
          <td key={i} className="py-1.5 px-2 text-[11px] text-center" style={{ color, fontVariantNumeric: 'tabular-nums' }}>
            {str}
            {i > 0 && v != null && baseVal != null && (
              <DiffBadge base={baseVal} compare={v} />
            )}
          </td>
        );
      })}
    </tr>
  );
}

// ── Run card ──────────────────────────────────────────────────────────────────
function RunCard({
  record, selected, onSelect, onRemove, disabled,
}: {
  record: BacktestRunRecord;
  selected: boolean;
  onSelect: () => void;
  onRemove: () => void;
  disabled: boolean;
}) {
  const r = record.result;
  const equityVals = (r.equityCurve ?? []).map(p => p.value);
  const profit = r.finalCapital - r.initialCapital;
  return (
    <div
      className="rounded p-3 cursor-pointer transition-all"
      onClick={disabled && !selected ? undefined : onSelect}
      style={{
        border: `1px solid ${selected ? 'rgba(46,140,255,0.6)' : 'var(--border)'}`,
        background: selected ? 'rgba(46,140,255,0.08)' : 'var(--bg-card)',
        opacity: disabled && !selected ? 0.45 : 1,
        cursor: disabled && !selected ? 'not-allowed' : 'pointer',
      }}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-semibold truncate" style={{ color: 'var(--text-secondary)' }}>
            {record.strategyName}
          </p>
          <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
            {fmtDateTime(record.savedAt)}
          </p>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          {selected && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-[3px]" style={{
              background: 'rgba(46,140,255,0.18)', color: 'var(--accent-blue)', border: '1px solid rgba(46,140,255,0.35)',
            }}>
              Selected
            </span>
          )}
          <button
            onClick={e => { e.stopPropagation(); onRemove(); }}
            className="p-0.5 rounded transition-colors"
            title="Remove from history"
            style={{ color: 'var(--text-faint)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-red)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-faint)')}
          >
            <X size={12} />
          </button>
        </div>
      </div>
      <div className="flex gap-3 items-end">
        <div className="flex-1 min-w-0 space-y-0.5">
          <div className="flex gap-2 flex-wrap">
            <span className="text-[11px] font-semibold" style={{ color: colorForReturn(r.returnPercentage), fontVariantNumeric: 'tabular-nums' }}>
              {fmtRet(r.returnPercentage)}
            </span>
            <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              WR {(r.winRate * 100).toFixed(1)}%
            </span>
            <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              {r.totalTrades} trades
            </span>
          </div>
          <div className="flex gap-2 flex-wrap">
            <span className="text-[10px]" style={{ color: profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontVariantNumeric: 'tabular-nums' }}>
              {profit >= 0 ? '+' : ''}{fmtUSD(profit)}
            </span>
            <span className="text-[10px]" style={{ color: 'var(--accent-orange)' }}>
              DD {(r.maxDrawdown * 100).toFixed(1)}%
            </span>
            <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              PF {r.profitFactor.toFixed(2)}
            </span>
          </div>
          <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
            {fmtDate(record.config?.startDate ?? record.fullConfig?.startDate)} → {fmtDate(record.config?.endDate ?? record.fullConfig?.endDate)}
          </p>
        </div>
        {equityVals.length >= 2 && (
          <div style={{ width: 70, flexShrink: 0 }}>
            <Sparkline values={equityVals} color={profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'} height={36} />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Sort controls ─────────────────────────────────────────────────────────────
type SortKey = 'date' | 'return' | 'winRate' | 'profit' | 'drawdown';

function sortRecords(records: BacktestRunRecord[], key: SortKey, dir: 'asc' | 'desc'): BacktestRunRecord[] {
  return [...records].sort((a, b) => {
    let va = 0, vb = 0;
    if (key === 'date') { va = new Date(a.savedAt).getTime(); vb = new Date(b.savedAt).getTime(); }
    else if (key === 'return') { va = a.result.returnPercentage; vb = b.result.returnPercentage; }
    else if (key === 'winRate') { va = a.result.winRate; vb = b.result.winRate; }
    else if (key === 'profit') { va = a.result.finalCapital - a.result.initialCapital; vb = b.result.finalCapital - b.result.initialCapital; }
    else if (key === 'drawdown') { va = a.result.maxDrawdown; vb = b.result.maxDrawdown; }
    return dir === 'asc' ? va - vb : vb - va;
  });
}

// ── Config rows extractor ─────────────────────────────────────────────────────
function extractConfigRows(records: BacktestRunRecord[]) {
  const g = (r: BacktestRunRecord, field: keyof BacktestConfigFull) =>
    (r.fullConfig as unknown as Record<string, unknown>)?.[field as string] as string | number | boolean | null | undefined;
  return [
    { label: 'Mode', values: records.map(r => g(r, 'mode')) },
    { label: 'TP/SL Mode', values: records.map(r => g(r, 'tpslMode')) },
    { label: 'SL Adjustment', values: records.map(r => g(r, 'slAdjustmentMode')) },
    { label: 'Adaptive SL Preset', values: records.map(r => g(r, 'adaptiveSLPreset')) },
    { label: 'Start Date', values: records.map(r => fmtDate(r.config?.startDate ?? r.fullConfig?.startDate)) },
    { label: 'End Date', values: records.map(r => fmtDate(r.config?.endDate ?? r.fullConfig?.endDate)) },
    { label: 'Initial Capital', values: records.map(r => fmtUSD(r.config?.initialCapital ?? r.fullConfig?.initialCapital)) },
    { label: 'Lookback Days', values: records.map(r => g(r, 'lookbackDays')) },
    { label: 'Training Days', values: records.map(r => g(r, 'trainingDays')) },
    { label: 'Testing Days', values: records.map(r => g(r, 'testingDays')) },
    { label: 'Risk %', values: records.map(r => g(r, 'riskPerTradePct') != null ? `${g(r, 'riskPerTradePct')}%` : '—') },
    { label: 'Min R:R', values: records.map(r => g(r, 'minRiskRewardRatio')) },
    { label: 'Max Bars Held', values: records.map(r => g(r, 'maxBarsHeld')) },
    { label: 'Max Leverage', values: records.map(r => g(r, 'maxLeverage') != null ? `${g(r, 'maxLeverage')}x` : '—') },
    { label: 'Confluence', values: records.map(r => g(r, 'confluenceThreshold') != null ? `${g(r, 'confluenceThreshold')} pts` : '—') },
    { label: 'Timeframe', values: records.map(r => r.config?.timeframe ?? r.fullConfig?.timeframe) },
  ];
}

// ── Full config expandable table ──────────────────────────────────────────────
function FullConfigSection({ configRows, colCount, colLabels }: {
  configRows: ReturnType<typeof extractConfigRows>;
  colCount: number;
  colLabels: string[];
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(e => !e)}
        className="flex items-center gap-1 text-[10px] transition-colors"
        style={{ color: 'var(--text-muted)' }}
        onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
        onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
      >
        {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        {expanded ? 'Hide' : 'Show'} all configuration parameters
      </button>
      {expanded && (
        <table className="w-full mt-2" style={{ borderCollapse: 'collapse' }}>
          <colgroup>
            <col style={{ width: 140 }} />
            {Array.from({ length: colCount }).map((_, i) => <col key={i} />)}
          </colgroup>
          <thead>
            <tr>
              <th className="py-1 text-left text-[10px]" style={{ color: 'var(--text-faint)' }}>Parameter</th>
              {colLabels.map((l, i) => (
                <th key={i} className="py-1 text-center text-[10px]" style={{ color: 'var(--text-faint)' }}>{l}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {configRows.map(row => (
              <ConfigDiffRow key={row.label} label={row.label} values={row.values} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
const MAX_SELECTED = 3;

export function ComparePanel({ currentResult }: ComparePanelProps) {
  const [records, setRecords] = useState<BacktestRunRecord[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('date');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const reload = useCallback(() => setRecords(loadAllRunRecords()), []);

  useEffect(() => { reload(); }, [reload, currentResult]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const base = q
      ? records.filter(r =>
          r.strategyName.toLowerCase().includes(q) ||
          fmtDate(r.savedAt).toLowerCase().includes(q)
        )
      : records;
    return sortRecords(base, sortKey, sortDir);
  }, [records, search, sortKey, sortDir]);

  const selectedRecords = useMemo(
    () => selectedIds.map(id => records.find(r => r.runId === id)).filter(Boolean) as BacktestRunRecord[],
    [selectedIds, records],
  );

  const toggleSelect = useCallback((runId: string) => {
    setSelectedIds(prev => {
      if (prev.includes(runId)) return prev.filter(id => id !== runId);
      if (prev.length >= MAX_SELECTED) return prev;
      return [...prev, runId];
    });
  }, []);

  const handleDelete = useCallback((runId: string) => {
    deleteRunRecord(runId);
    setSelectedIds(prev => prev.filter(id => id !== runId));
    reload();
  }, [reload]);

  const handleSortClick = useCallback((key: SortKey) => {
    setSortKey(prev => {
      if (prev === key) { setSortDir(d => d === 'desc' ? 'asc' : 'desc'); return key; }
      setSortDir('desc');
      return key;
    });
  }, []);

  const SortBtn = ({ k, label }: { k: SortKey; label: string }) => (
    <button
      onClick={() => handleSortClick(k)}
      className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-[3px] transition-colors"
      style={{
        background: sortKey === k ? 'rgba(46,140,255,0.12)' : 'var(--bg-deep)',
        border: `1px solid ${sortKey === k ? 'rgba(46,140,255,0.4)' : 'var(--border)'}`,
        color: sortKey === k ? 'var(--accent-blue)' : 'var(--text-muted)',
      }}
    >
      {label}
      {sortKey === k && (sortDir === 'desc' ? <ChevronDown size={9} /> : <ChevronUp size={9} />)}
    </button>
  );

  if (records.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3" style={{ color: 'var(--text-faint)' }}>
        <GitCompare size={32} strokeWidth={1.5} />
        <p className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>No runs to compare yet.</p>
        <p className="text-xs text-center max-w-[280px]">
          Complete a backtest to populate the history. Up to {MAX_SELECTED} runs can be compared side-by-side.
        </p>
      </div>
    );
  }

  const colCount = selectedRecords.length;
  const colLabels = selectedRecords.map((r, i) =>
    `Run ${i + 1}: ${r.strategyName.length > 18 ? r.strategyName.slice(0, 16) + '…' : r.strategyName}`
  );
  const configRows = colCount >= 1 ? extractConfigRows(selectedRecords) : [];
  const diffConfigRows = configRows.filter(row => {
    const strs = row.values.map(v => v == null ? '—' : String(v));
    return strs.some(v => v !== strs[0]);
  });

  return (
    <div className="flex flex-col gap-0">
      {/* Search + sort bar */}
      <div className="flex items-center gap-2 mb-3 flex-shrink-0">
        <div
          className="flex items-center gap-1.5 flex-1 rounded px-2 py-1.5"
          style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)' }}
        >
          <Search size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <input
            type="text"
            placeholder="Search runs by name or date…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 bg-transparent text-[11px] focus:outline-none"
            style={{ color: 'var(--text-secondary)' }}
          />
          {search && (
            <button onClick={() => setSearch('')}>
              <X size={11} style={{ color: 'var(--text-muted)' }} />
            </button>
          )}
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Sort:</span>
          <SortBtn k="date" label="Date" />
          <SortBtn k="return" label="Return" />
          <SortBtn k="winRate" label="Win%" />
          <SortBtn k="profit" label="Profit" />
          <SortBtn k="drawdown" label="DD" />
        </div>
      </div>

      {/* Selection status */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
          Select up to {MAX_SELECTED} runs to compare
        </span>
        {selectedIds.length > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-[3px]" style={{
            background: 'rgba(46,140,255,0.1)', color: 'var(--accent-blue)', border: '1px solid rgba(46,140,255,0.25)',
          }}>
            {selectedIds.length}/{MAX_SELECTED} selected
          </span>
        )}
        {selectedIds.length > 0 && (
          <button
            onClick={() => setSelectedIds([])}
            className="text-[10px] px-1.5 py-0.5 rounded-[3px]"
            style={{ color: 'var(--text-muted)', border: '1px solid var(--border)' }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Run cards */}
      <div className="grid gap-2 flex-shrink-0" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
        {filtered.map(record => (
          <RunCard
            key={record.runId}
            record={record}
            selected={selectedIds.includes(record.runId)}
            onSelect={() => toggleSelect(record.runId)}
            onRemove={() => handleDelete(record.runId)}
            disabled={selectedIds.length >= MAX_SELECTED && !selectedIds.includes(record.runId)}
          />
        ))}
        {filtered.length === 0 && (
          <p className="text-[11px] col-span-full py-4 text-center" style={{ color: 'var(--text-muted)' }}>
            No runs match &ldquo;{search}&rdquo;
          </p>
        )}
      </div>

      {/* Prompt to select more */}
      {colCount === 1 && (
        <div className="mt-4 p-3 rounded flex items-center gap-2" style={{ border: '1px dashed var(--border)', background: 'var(--bg-card)' }}>
          <Plus size={13} style={{ color: 'var(--text-muted)' }} />
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            Select {MAX_SELECTED - 1} more run{MAX_SELECTED - 1 > 1 ? 's' : ''} above to start comparing.
          </p>
        </div>
      )}

      {/* Comparison dashboard */}
      {colCount >= 2 && (
        <div className="mt-4">
          <div className="rounded" style={{ border: '1px solid var(--border)', background: 'var(--bg-card)', overflow: 'hidden' }}>
            {/* Equity sparkline headers */}
            <div className="grid px-3 pt-3 pb-2 gap-2" style={{ gridTemplateColumns: `140px repeat(${colCount}, 1fr)` }}>
              <div />
              {selectedRecords.map((r, i) => {
                const equityVals = (r.result.equityCurve ?? []).map(p => p.value);
                const profit = r.result.finalCapital - r.result.initialCapital;
                return (
                  <div key={r.runId} className="rounded p-2" style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)' }}>
                    <p className="text-[10px] font-semibold mb-0.5 truncate" style={{ color: 'var(--accent-blue)' }}>
                      {colLabels[i]}
                    </p>
                    <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                      {fmtDateTime(r.savedAt)}
                    </p>
                    {equityVals.length >= 2
                      ? <Sparkline values={equityVals} color={profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'} height={44} />
                      : <div style={{ height: 44 }} />
                    }
                    <p className="text-[12px] font-bold mt-0.5" style={{ color: colorForReturn(r.result.returnPercentage), fontVariantNumeric: 'tabular-nums' }}>
                      {fmtRet(r.result.returnPercentage)}
                    </p>
                  </div>
                );
              })}
            </div>

            <div className="px-3 pb-3 overflow-x-auto">
              {/* Returns & Capital */}
              <SectionLabel title="Returns & Capital" />
              <table className="w-full" style={{ borderCollapse: 'collapse' }}>
                <colgroup><col style={{ width: 140 }} />{selectedRecords.map((_, i) => <col key={i} />)}</colgroup>
                <tbody>
                  <MetricRow label="Total Return %" values={selectedRecords.map(r => r.result.returnPercentage)} colorFn={colorForReturn} suffix="%" />
                  <MetricRow label="Net Profit" values={selectedRecords.map(r => r.result.finalCapital - r.result.initialCapital)} colorFn={v => v != null && v >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'} prefix="$" />
                  <MetricRow label="Initial Capital" values={selectedRecords.map(r => r.result.initialCapital)} prefix="$" />
                  <MetricRow label="Final Capital" values={selectedRecords.map(r => r.result.finalCapital)} prefix="$" />
                </tbody>
              </table>

              {/* Risk */}
              <SectionLabel title="Risk Metrics" />
              <table className="w-full" style={{ borderCollapse: 'collapse' }}>
                <colgroup><col style={{ width: 140 }} />{selectedRecords.map((_, i) => <col key={i} />)}</colgroup>
                <tbody>
                  <MetricRow label="Max Drawdown" values={selectedRecords.map(r => r.result.maxDrawdown * 100)} colorFn={() => 'var(--accent-orange)'} suffix="%" />
                  <MetricRow label="Sharpe Ratio" values={selectedRecords.map(r => r.result.sharpeRatio)} />
                  <MetricRow label="Sortino Ratio" values={selectedRecords.map(r => r.result.sortino_ratio)} />
                  <MetricRow label="Calmar Ratio" values={selectedRecords.map(r => r.result.calmar_ratio ?? null)} />
                  <MetricRow label="Profit Factor" values={selectedRecords.map(r => r.result.profitFactor)} />
                </tbody>
              </table>

              {/* Trade stats */}
              <SectionLabel title="Trade Statistics" />
              <table className="w-full" style={{ borderCollapse: 'collapse' }}>
                <colgroup><col style={{ width: 140 }} />{selectedRecords.map((_, i) => <col key={i} />)}</colgroup>
                <tbody>
                  <MetricRow label="Total Trades" values={selectedRecords.map(r => r.result.totalTrades)} />
                  <MetricRow label="Win Rate" values={selectedRecords.map(r => r.result.winRate * 100)} colorFn={v => v != null && v >= 50 ? 'var(--accent-green)' : 'var(--accent-red)'} suffix="%" />
                  <MetricRow label="Winning Trades" values={selectedRecords.map(r => r.result.winningTrades)} colorFn={() => 'var(--accent-green)'} />
                  <MetricRow label="Losing Trades" values={selectedRecords.map(r => r.result.losingTrades)} colorFn={() => 'var(--accent-red)'} />
                  <MetricRow label="Avg Win" values={selectedRecords.map(r => r.result.averageWin)} colorFn={() => 'var(--accent-green)'} prefix="$" />
                  <MetricRow label="Avg Loss" values={selectedRecords.map(r => Math.abs(r.result.averageLoss))} colorFn={() => 'var(--accent-red)'} prefix="-$" />
                </tbody>
              </table>

              {/* Config diffs */}
              <SectionLabel title="Configuration Differences" />
              {diffConfigRows.length === 0 ? (
                <p className="text-[11px] py-2 flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                  <Minus size={12} />
                  All selected runs share identical configuration parameters.
                </p>
              ) : (
                <table className="w-full" style={{ borderCollapse: 'collapse' }}>
                  <colgroup><col style={{ width: 140 }} />{selectedRecords.map((_, i) => <col key={i} />)}</colgroup>
                  <thead>
                    <tr>
                      <th className="py-1 text-left text-[10px]" style={{ color: 'var(--text-faint)' }}>Parameter</th>
                      {colLabels.map((l, i) => (
                        <th key={i} className="py-1 text-center text-[10px]" style={{ color: 'var(--text-faint)' }}>{l}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {diffConfigRows.map(row => (
                      <ConfigDiffRow key={row.label} label={row.label} values={row.values} />
                    ))}
                  </tbody>
                </table>
              )}

              <FullConfigSection configRows={configRows} colCount={colCount} colLabels={colLabels} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

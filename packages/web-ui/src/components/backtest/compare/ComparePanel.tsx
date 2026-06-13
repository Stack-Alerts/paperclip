'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Search, X, Plus, GitCompare, ChevronUp, ChevronDown, Minus, CheckCircle2 } from 'lucide-react';
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
function fmtPct(n: number | undefined | null, decimals = 2): string {
  if (n == null || !isFinite(n)) return '—';
  return `${n >= 0 ? '+' : ''}${n.toFixed(decimals)}%`;
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
function fmtUSD(n: number | undefined | null, showSign = false): string {
  if (n == null || !isFinite(n)) return '—';
  const abs = Math.abs(n);
  const sign = showSign ? (n >= 0 ? '+' : '-') : n < 0 ? '-' : '';
  return `${sign}$${abs.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}
function colorReturn(v: number | undefined | null): string {
  if (v == null) return 'var(--text-secondary)';
  return v >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
}

// ── Per-slot accent colors — blue / violet / amber ────────────────────────────
const RUN_COLORS = [
  'var(--accent-blue)',
  '#a78bfa',
  '#f59e0b',
] as const;

// ── Sparkline ─────────────────────────────────────────────────────────────────
function Sparkline({ values, color, height = 40 }: { values: number[]; color: string; height?: number }) {
  if (values.length < 2) return <div style={{ height }} />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const W = 120, H = height;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = H - ((v - min) / range) * H * 0.85 - H * 0.075;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height, display: 'block' }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

// ── Section header — matches MetricsPanel pattern ─────────────────────────────
function SectionHeader({ title }: { title: string }) {
  return (
    <p className="text-xs font-medium uppercase tracking-wide mt-5 mb-2 first:mt-0" style={{ color: 'var(--text-muted)' }}>
      {title}
    </p>
  );
}

// ── Delta badge ───────────────────────────────────────────────────────────────
function DeltaBadge({ base, compare, higherIsBetter = true }: { base: number; compare: number; higherIsBetter?: boolean }) {
  const delta = compare - base;
  if (Math.abs(delta) < 0.001) return null;
  const positive = higherIsBetter ? delta > 0 : delta < 0;
  const color = positive ? 'var(--accent-green)' : 'var(--accent-red)';
  return (
    <span className="ml-1 text-[10px] tabular-nums" style={{ color }}>
      ({delta > 0 ? '+' : ''}{fmt(delta, Math.abs(delta) < 1 ? 3 : 1)})
    </span>
  );
}

// ── Metric table row ──────────────────────────────────────────────────────────
function MetricRow({
  label, values, fmtFn, colorFn, higherIsBetter = true, isEven = false,
}: {
  label: string;
  values: (number | undefined | null)[];
  fmtFn?: (v: number) => string;
  colorFn?: (v: number | null) => string;
  higherIsBetter?: boolean;
  isEven?: boolean;
}) {
  const baseVal = values[0] ?? null;
  const format = fmtFn ?? ((v: number) => fmt(v));
  return (
    <tr style={{ background: isEven ? 'var(--bg-deep)' : 'transparent' }}>
      <td className="py-2 pl-3 pr-4 text-xs" style={{ color: 'var(--text-muted)', width: 160 }}>
        {label}
      </td>
      {values.map((v, i) => {
        const color = colorFn ? colorFn(v ?? null) : 'var(--text-secondary)';
        return (
          <td key={i} className="py-2 px-3 text-xs text-center tabular-nums" style={{ color }}>
            {v == null ? <span style={{ color: 'var(--text-faint)' }}>—</span> : format(v)}
            {i > 0 && v != null && baseVal != null && (
              <DeltaBadge base={baseVal} compare={v} higherIsBetter={higherIsBetter} />
            )}
          </td>
        );
      })}
    </tr>
  );
}

// ── Config diff row ───────────────────────────────────────────────────────────
function ConfigRow({
  label, values, isEven = false,
}: {
  label: string;
  values: (string | number | boolean | undefined | null)[];
  isEven?: boolean;
}) {
  const strs = values.map(v => (v == null || v === '') ? '—' : String(v));
  const allSame = strs.every(v => v === strs[0]);
  return (
    <tr style={{ background: isEven ? 'var(--bg-deep)' : 'transparent' }}>
      <td className="py-2 pl-3 pr-4 text-xs" style={{ color: 'var(--text-muted)', width: 160 }}>
        {label}
      </td>
      {strs.map((v, i) => (
        <td
          key={i}
          className="py-2 px-3 text-xs text-center tabular-nums"
          style={{
            color: !allSame && i > 0 ? 'var(--accent-yellow, #f59e0b)' : 'var(--text-secondary)',
            fontWeight: !allSame && i > 0 ? 500 : 400,
          }}
        >
          {v}
        </td>
      ))}
    </tr>
  );
}

// ── Table wrapper with per-run column headers ──────────────────────────────────
function CompareTable({
  colLabels, colColors, children,
}: {
  colLabels: string[];
  colColors: string[];
  children: React.ReactNode;
}) {
  return (
    <table className="w-full" style={{ borderCollapse: 'collapse' }}>
      <colgroup>
        <col style={{ width: 160 }} />
        {colLabels.map((_, i) => <col key={i} />)}
      </colgroup>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--border)' }}>
          <th className="pb-1.5 pl-3" />
          {colLabels.map((l, i) => (
            <th key={i} className="pb-1.5 px-3 text-xs font-semibold text-center" style={{ color: colColors[i] }}>
              {l}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  );
}

// ── Run card ──────────────────────────────────────────────────────────────────
function RunCard({
  record, selected, onSelect, onRemove, disabled, slotColor,
}: {
  record: BacktestRunRecord;
  selected: boolean;
  onSelect: () => void;
  onRemove: () => void;
  disabled: boolean;
  slotColor?: string;
}) {
  const r = record.result;
  const equityVals = (r.equityCurve ?? []).map((p: { value: number }) => p.value);
  const profit = r.finalCapital - r.initialCapital;
  const accentColor = slotColor ?? (profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)');

  return (
    <div
      onClick={disabled && !selected ? undefined : onSelect}
      style={{
        position: 'relative',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 6,
        padding: '10px 12px',
        opacity: disabled && !selected ? 0.4 : 1,
        cursor: disabled && !selected ? 'not-allowed' : 'pointer',
        transition: 'opacity 0.15s',
      }}
    >
      {selected && (
        <div style={{
          position: 'absolute', top: 0, left: 0, bottom: 0, width: 3,
          background: accentColor, borderRadius: '6px 0 0 6px',
        }} />
      )}
      <div style={{ paddingLeft: selected ? 6 : 0 }}>
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold truncate" style={{ color: 'var(--text-secondary)' }}>
              {record.strategyName}
            </p>
            <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-faint)' }}>
              {fmtDateTime(record.savedAt)}
            </p>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {selected && <CheckCircle2 size={13} style={{ color: accentColor }} />}
            <button
              onClick={e => { e.stopPropagation(); onRemove(); }}
              className="p-0.5 rounded"
              title="Remove from history"
              style={{ color: 'var(--text-faint)' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-red)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-faint)')}
            >
              <X size={12} />
            </button>
          </div>
        </div>
        {/* Metrics + sparkline */}
        <div className="flex items-end gap-3">
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-baseline gap-2.5">
              <span className="text-sm font-bold tabular-nums" style={{ color: colorReturn(r.returnPercentage) }}>
                {fmtPct(r.returnPercentage)}
              </span>
              <span className="text-xs tabular-nums" style={{ color: colorReturn(profit) }}>
                {fmtUSD(profit, true)}
              </span>
            </div>
            <div className="flex gap-3">
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                WR <span style={{ color: r.winRate >= 0.5 ? 'var(--accent-green)' : 'var(--text-secondary)' }}>
                  {(r.winRate * 100).toFixed(1)}%
                </span>
              </span>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{r.totalTrades} trades</span>
              <span className="text-xs tabular-nums" style={{ color: 'var(--accent-orange, #f97316)' }}>
                DD {(r.maxDrawdown * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex gap-3">
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                PF <span style={{ color: 'var(--text-secondary)' }}>{r.profitFactor.toFixed(2)}</span>
              </span>
              <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                {fmtDate(record.config?.startDate ?? record.fullConfig?.startDate)}–{fmtDate(record.config?.endDate ?? record.fullConfig?.endDate)}
              </span>
            </div>
          </div>
          {equityVals.length >= 2 && (
            <div style={{ width: 68, flexShrink: 0 }}>
              <Sparkline values={equityVals} color={accentColor} height={38} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sort helpers ──────────────────────────────────────────────────────────────
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

// ── Config rows ───────────────────────────────────────────────────────────────
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

// ── Expandable full config ────────────────────────────────────────────────────
function FullConfigSection({
  configRows, colLabels, colColors,
}: {
  configRows: ReturnType<typeof extractConfigRows>;
  colLabels: string[];
  colColors: string[];
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(e => !e)}
        className="flex items-center gap-1.5 text-xs"
        style={{ color: 'var(--text-muted)' }}
        onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
        onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
      >
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        {expanded ? 'Hide' : 'Show'} all configuration parameters
      </button>
      {expanded && (
        <div className="mt-2 rounded overflow-hidden" style={{ border: '1px solid var(--border)' }}>
          <CompareTable colLabels={colLabels} colColors={colColors}>
            {configRows.map((row, idx) => (
              <ConfigRow key={row.label} label={row.label} values={row.values} isEven={idx % 2 === 1} />
            ))}
          </CompareTable>
        </div>
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

  const SortBtn = ({ k, label }: { k: SortKey; label: string }) => {
    const active = sortKey === k;
    return (
      <button
        onClick={() => handleSortClick(k)}
        className="flex items-center gap-0.5 text-xs px-2 py-1 rounded"
        style={{
          background: active ? 'rgba(46,140,255,0.1)' : 'transparent',
          border: `1px solid ${active ? 'rgba(46,140,255,0.35)' : 'var(--border)'}`,
          color: active ? 'var(--accent-blue)' : 'var(--text-muted)',
        }}
      >
        {label}
        {active && (sortDir === 'desc' ? <ChevronDown size={10} /> : <ChevronUp size={10} />)}
      </button>
    );
  };

  // ── Empty state ──────────────────────────────────────────────────────────────
  if (records.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <GitCompare size={32} strokeWidth={1.5} style={{ color: 'var(--text-faint)' }} />
        <p className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>No runs to compare yet.</p>
        <p className="text-xs text-center max-w-xs" style={{ color: 'var(--text-faint)' }}>
          Complete a backtest to populate the history. Up to {MAX_SELECTED} runs can be compared side-by-side.
        </p>
      </div>
    );
  }

  const colCount = selectedRecords.length;
  const colLabels = selectedRecords.map((r, i) => {
    const name = r.strategyName.length > 16 ? r.strategyName.slice(0, 14) + '…' : r.strategyName;
    return `Run ${i + 1} · ${name}`;
  });
  const colColors = selectedRecords.map((_, i) => RUN_COLORS[i] as string);
  const configRows = colCount >= 1 ? extractConfigRows(selectedRecords) : [];
  const diffConfigRows = configRows.filter(row => {
    const strs = row.values.map(v => (v == null || v === '') ? '—' : String(v));
    return strs.some(v => v !== strs[0]);
  });

  return (
    <div className="flex flex-col gap-0">

      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 mb-3 flex-shrink-0">
        <div
          className="flex items-center gap-1.5 flex-1 rounded px-2.5 py-1.5"
          style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)' }}
        >
          <Search size={12} style={{ color: 'var(--text-faint)', flexShrink: 0 }} />
          <input
            type="text"
            placeholder="Search by strategy name or date…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 bg-transparent text-xs focus:outline-none"
            style={{ color: 'var(--text-secondary)' }}
          />
          {search && (
            <button onClick={() => setSearch('')} style={{ color: 'var(--text-faint)' }}>
              <X size={11} />
            </button>
          )}
        </div>
        <div className="flex items-center gap-1">
          <SortBtn k="date" label="Date" />
          <SortBtn k="return" label="Return" />
          <SortBtn k="winRate" label="Win%" />
          <SortBtn k="profit" label="Profit" />
          <SortBtn k="drawdown" label="DD" />
        </div>
      </div>

      {/* ── Selection status ── */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Select up to <strong style={{ color: 'var(--text-secondary)' }}>{MAX_SELECTED}</strong> runs to compare
        </span>
        {selectedIds.length > 0 && (
          <>
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{ background: 'rgba(46,140,255,0.1)', color: 'var(--accent-blue)', border: '1px solid rgba(46,140,255,0.25)' }}
            >
              {selectedIds.length}/{MAX_SELECTED} selected
            </span>
            <button
              onClick={() => setSelectedIds([])}
              className="text-xs px-2 py-0.5 rounded"
              style={{ color: 'var(--text-muted)', border: '1px solid var(--border)' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              Clear all
            </button>
          </>
        )}
      </div>

      {/* ── Run cards ── */}
      <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))' }}>
        {filtered.map(record => {
          const slotIdx = selectedIds.indexOf(record.runId);
          return (
            <RunCard
              key={record.runId}
              record={record}
              selected={slotIdx >= 0}
              slotColor={slotIdx >= 0 ? RUN_COLORS[slotIdx] as string : undefined}
              onSelect={() => toggleSelect(record.runId)}
              onRemove={() => handleDelete(record.runId)}
              disabled={selectedIds.length >= MAX_SELECTED && !selectedIds.includes(record.runId)}
            />
          );
        })}
        {filtered.length === 0 && (
          <p className="text-xs col-span-full py-6 text-center" style={{ color: 'var(--text-muted)' }}>
            No runs match &ldquo;{search}&rdquo;
          </p>
        )}
      </div>

      {/* ── Prompt: select one more ── */}
      {colCount === 1 && (
        <div
          className="mt-4 p-3 rounded flex items-center gap-2"
          style={{ border: '1px dashed var(--border)', background: 'var(--bg-card)' }}
        >
          <Plus size={14} style={{ color: 'var(--text-muted)' }} />
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Select at least one more run above to start comparing.
          </p>
        </div>
      )}

      {/* ── Comparison dashboard ── */}
      {colCount >= 2 && (
        <div className="mt-4 rounded" style={{ border: '1px solid var(--border)', background: 'var(--bg-card)', overflow: 'hidden' }}>

          {/* Run header cards — top border tinted per slot color */}
          <div
            className="grid gap-2 p-3"
            style={{
              gridTemplateColumns: `repeat(${colCount}, 1fr)`,
              background: 'var(--bg-elevated, var(--bg-deep))',
              borderBottom: '1px solid var(--border)',
            }}
          >
            {selectedRecords.map((r, i) => {
              const equityVals = (r.result.equityCurve ?? []).map((p: { value: number }) => p.value);
              return (
                <div
                  key={r.runId}
                  className="rounded px-3 py-2 flex items-center gap-3"
                  style={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderLeft: `3px solid ${colColors[i]}`,
                  }}
                >
                  {/* Left: badge + name + dates */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span
                        className="text-[10px] font-bold px-1.5 py-0.5 rounded flex-shrink-0"
                        style={{ background: `${colColors[i]}20`, color: colColors[i] }}
                      >
                        Run {i + 1}
                      </span>
                      {i === 0 && (
                        <span className="text-[10px] flex-shrink-0" style={{ color: 'var(--text-faint)' }}>baseline</span>
                      )}
                      <p className="text-xs font-semibold truncate" style={{ color: 'var(--text-secondary)' }}>
                        {r.strategyName}
                      </p>
                    </div>
                    <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                      {fmtDate(r.result.startDate ?? r.config?.startDate ?? r.fullConfig?.startDate)}
                      {' → '}
                      {fmtDate(r.result.endDate ?? r.config?.endDate ?? r.fullConfig?.endDate)}
                    </p>
                  </div>
                  {/* Right: sparkline + return% + profit */}
                  <div className="flex items-center gap-3 flex-shrink-0">
                    {equityVals.length >= 2 && (
                      <div style={{ width: 64 }}>
                        <Sparkline values={equityVals} color={colColors[i]} height={32} />
                      </div>
                    )}
                    <div className="text-right">
                      <p className="text-sm font-bold tabular-nums leading-tight" style={{ color: colorReturn(r.result.returnPercentage) }}>
                        {fmtPct(r.result.returnPercentage)}
                      </p>
                      <p className="text-xs tabular-nums leading-tight" style={{ color: colorReturn(r.result.returnPercentage) }}>
                        {fmtUSD(r.result.finalCapital - r.result.initialCapital, true)}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Metric sections */}
          <div className="p-3 overflow-x-auto">

            <SectionHeader title="Returns & Capital" />
            <div className="rounded overflow-hidden" style={{ border: '1px solid var(--border)' }}>
              <CompareTable colLabels={colLabels} colColors={colColors}>
                <MetricRow isEven={false} label="Total Return" values={selectedRecords.map(r => r.result.returnPercentage)} fmtFn={v => fmtPct(v)} colorFn={colorReturn} />
                <MetricRow isEven={true} label="Net Profit" values={selectedRecords.map(r => r.result.finalCapital - r.result.initialCapital)} fmtFn={v => fmtUSD(v, true)} colorFn={v => v != null && v >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'} />
                <MetricRow isEven={false} label="Initial Capital" values={selectedRecords.map(r => r.result.initialCapital)} fmtFn={fmtUSD} colorFn={() => 'var(--text-secondary)'} />
                <MetricRow isEven={true} label="Final Capital" values={selectedRecords.map(r => r.result.finalCapital)} fmtFn={fmtUSD} colorFn={() => 'var(--text-secondary)'} />
              </CompareTable>
            </div>

            <SectionHeader title="Risk Metrics" />
            <div className="rounded overflow-hidden" style={{ border: '1px solid var(--border)' }}>
              <CompareTable colLabels={colLabels} colColors={colColors}>
                <MetricRow isEven={false} label="Max Drawdown" values={selectedRecords.map(r => r.result.maxDrawdown * 100)} fmtFn={v => `${fmt(v)}%`} colorFn={() => 'var(--accent-orange, #f97316)'} higherIsBetter={false} />
                <MetricRow isEven={true} label="Sharpe Ratio" values={selectedRecords.map(r => r.result.sharpeRatio)} colorFn={v => v != null && v >= 1 ? 'var(--accent-green)' : 'var(--text-secondary)'} />
                <MetricRow isEven={false} label="Sortino Ratio" values={selectedRecords.map(r => r.result.sortino_ratio)} colorFn={v => v != null && v >= 1 ? 'var(--accent-green)' : 'var(--text-secondary)'} />
                <MetricRow isEven={true} label="Calmar Ratio" values={selectedRecords.map(r => r.result.calmar_ratio ?? null)} colorFn={() => 'var(--text-secondary)'} />
                <MetricRow isEven={false} label="Profit Factor" values={selectedRecords.map(r => r.result.profitFactor)} colorFn={v => v != null && v >= 1.5 ? 'var(--accent-green)' : v != null && v >= 1 ? 'var(--text-secondary)' : 'var(--accent-red)'} />
              </CompareTable>
            </div>

            <SectionHeader title="Trade Statistics" />
            <div className="rounded overflow-hidden" style={{ border: '1px solid var(--border)' }}>
              <CompareTable colLabels={colLabels} colColors={colColors}>
                <MetricRow isEven={false} label="Total Trades" values={selectedRecords.map(r => r.result.totalTrades)} fmtFn={v => String(Math.round(v))} colorFn={() => 'var(--text-secondary)'} />
                <MetricRow isEven={true} label="Win Rate" values={selectedRecords.map(r => r.result.winRate * 100)} fmtFn={v => `${fmt(v, 1)}%`} colorFn={v => v != null && v >= 50 ? 'var(--accent-green)' : 'var(--accent-red)'} />
                <MetricRow isEven={false} label="Winning Trades" values={selectedRecords.map(r => r.result.winningTrades)} fmtFn={v => String(Math.round(v))} colorFn={() => 'var(--accent-green)'} />
                <MetricRow isEven={true} label="Losing Trades" values={selectedRecords.map(r => r.result.losingTrades)} fmtFn={v => String(Math.round(v))} colorFn={() => 'var(--accent-red)'} higherIsBetter={false} />
                <MetricRow isEven={false} label="Avg Win" values={selectedRecords.map(r => r.result.averageWin)} fmtFn={fmtUSD} colorFn={() => 'var(--accent-green)'} />
                <MetricRow isEven={true} label="Avg Loss" values={selectedRecords.map(r => Math.abs(r.result.averageLoss))} fmtFn={v => `-${fmtUSD(v)}`} colorFn={() => 'var(--accent-red)'} higherIsBetter={false} />
              </CompareTable>
            </div>

            <SectionHeader title="Configuration Differences" />
            {diffConfigRows.length === 0 ? (
              <div
                className="flex items-center gap-2 py-3 px-3 rounded"
                style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)' }}
              >
                <Minus size={13} style={{ color: 'var(--text-faint)' }} />
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  All selected runs share identical configuration.
                </p>
              </div>
            ) : (
              <div className="rounded overflow-hidden" style={{ border: '1px solid var(--border)' }}>
                <CompareTable colLabels={colLabels} colColors={colColors}>
                  {diffConfigRows.map((row, idx) => (
                    <ConfigRow key={row.label} label={row.label} values={row.values} isEven={idx % 2 === 1} />
                  ))}
                </CompareTable>
              </div>
            )}

            <FullConfigSection configRows={configRows} colLabels={colLabels} colColors={colColors} />
          </div>
        </div>
      )}
    </div>
  );
}

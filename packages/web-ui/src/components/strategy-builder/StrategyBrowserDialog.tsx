'use client';

import { useState, useCallback, useMemo, useRef, useEffect, useLayoutEffect, type CSSProperties } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Strategy, StrategyStatus, StrategyVersion, Block, BlockType } from '@/lib/strategy-builder/types';
import {
  deleteStrategyScoped, duplicateStrategyScoped,
  createStrategy, listStrategies, getStrategyVersions, loadStrategyVersion,
} from '@/lib/strategy-builder/api';
import { DeleteStrategyModal, DeleteScope } from './DeleteStrategyModal';
import { DuplicateStrategyModal, DuplicateScope } from './DuplicateStrategyModal';
import {
  Info, Settings, TrendingUp, Calendar, RefreshCw, CheckCircle, GitBranch, Save,
  Trash2, Copy, Download, Upload, FolderOpen,
} from 'lucide-react';
import { AppBrand } from '@/components/shared/AppBrand';

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<StrategyStatus, CSSProperties> = {
  draft:      { color: 'var(--text-muted)',   background: 'var(--bg-card)',           borderColor: 'var(--border)' },
  valid:      { color: 'var(--accent-green)', background: 'var(--accent-green-dark)',  borderColor: 'var(--accent-green-mid)' },
  invalid:    { color: 'var(--accent-red)',   background: 'var(--accent-red-deeper)',  borderColor: 'var(--accent-red-dark)' },
  backtested: { color: 'var(--accent-blue)',  background: 'var(--accent-blue-dark)',   borderColor: 'var(--accent-blue-mid)' },
  active:     { color: 'var(--accent-teal)',  background: 'var(--accent-teal-dark)',   borderColor: 'var(--accent-teal-mid)' },
};

// Splitter persistence: 5-row default + localStorage restore (BTCAAAAA-29359).
const SPLIT_STORAGE_KEY = 'strategyBrowser.splitPct.v1';
const SPLIT_MIN_PCT = 25;
const SPLIT_MAX_PCT = 85;
const SPLIT_FALLBACK_PCT = 60;

function readStoredSplitPct(): number | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(SPLIT_STORAGE_KEY);
    if (raw == null) return null;
    const n = parseFloat(raw);
    if (Number.isFinite(n) && n >= SPLIT_MIN_PCT && n <= SPLIT_MAX_PCT) return n;
  } catch { /* ignore */ }
  return null;
}

const STATUS_PILL_BASE: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  minWidth: 76,
  height: 20,
  lineHeight: 1,
  padding: '0 8px',
  borderRadius: 4,
  borderWidth: 1,
  borderStyle: 'solid',
  fontSize: 12,
  whiteSpace: 'nowrap',
};

const BLOCK_TYPE_LABELS: Record<BlockType, string> = {
  [BlockType.ENTRY_CONDITION]:  'Entry',
  [BlockType.EXIT_CONDITION]:   'Exit',
  [BlockType.RISK_MANAGEMENT]:  'Risk',
  [BlockType.TIME_CONSTRAINT]:  'Time',
  [BlockType.FILTER]:           'Filter',
  [BlockType.INDICATOR]:        'Indicator',
  [BlockType.POSITION_SIZING]:  'Position',
};

type SortKey = 'name' | 'blocks' | 'updated' | 'status' | 'created' | 'version';
type SortDir = 'asc' | 'desc';
type TypeFilter = 'all' | 'bullish' | 'bearish';

// ── Quality score helper ───────────────────────────────────────────────────────

function computeQualityScore(result: NonNullable<Strategy['backtestResults']>[number]) {
  let pts = 0;
  const wr = result.winRate * 100;
  if (wr >= 60) pts += 2; else if (wr >= 45) pts += 1;
  if (result.profitFactor >= 1.5) pts += 2; else if (result.profitFactor >= 1.0) pts += 1;
  if (result.sharpeRatio >= 0.15) pts += 2; else if (result.sharpeRatio >= 0.05) pts += 1;
  if (result.totalTrades >= 20) pts += 1;
  return pts;
}

function getQualityLabel(pts: number) {
  if (pts >= 6) return { label: 'Excellent', dot: '#7cc27a', color: 'var(--accent-green)' };
  if (pts >= 4) return { label: 'Good',      dot: '#60A5FA', color: 'var(--accent-blue)' };
  if (pts >= 2) return { label: 'Fair',      dot: '#f97316', color: 'var(--accent-orange)' };
  return               { label: 'Poor',      dot: '#c35252', color: 'var(--accent-red)' };
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SortHeader({
  label, col, active, dir, onClick, className,
}: { label: string; col: SortKey; active: SortKey; dir: SortDir; onClick: (c: SortKey) => void; className?: string }) {
  const isActive = col === active;
  return (
    <th
      onClick={() => onClick(col)}
      className={className || "px-3 py-2 text-left text-xs font-medium uppercase tracking-wide cursor-pointer whitespace-nowrap select-none"}
      style={{ color: 'var(--text-secondary)' }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)'; }}
    >
      {label}
      {isActive && <span className="ml-1" style={{ color: 'var(--text-muted)' }}>{dir === 'asc' ? '▴' : '▾'}</span>}
    </th>
  );
}

function prettySignalName(s: string): string {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function fmtN(v: number | null | undefined, decimals: number, suffix = ''): string {
  return v != null ? v.toFixed(decimals) + suffix : '—';
}

function StrategyNameCell({ strategy }: { strategy: Strategy }) {
  // API-returned blocks have { name, signals[] } directly; local store blocks use { data.signals }
  const blocks = strategy.blocks as unknown as Array<{ name: string; signals?: Array<{ name: string }> }>;
  const MAX_BLOCKS = 3;
  const shown = blocks.slice(0, MAX_BLOCKS);
  const extra = blocks.length - MAX_BLOCKS;

  return (
    <div className="flex items-baseline flex-wrap gap-x-1 min-w-0" style={{ fontSize: '12px', lineHeight: '1.4' }}>
      <span className="font-medium font-sans shrink-0" style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
        {strategy.name}
      </span>
      {blocks.length > 0 && (
        <>
          <span style={{ color: '#666666' }}>–</span>
          {shown.map((b, i) => {
            const sigs = (b.signals ?? []).map(s => prettySignalName(s.name));
            return (
              <span key={i} className="flex items-baseline gap-x-0.5">
                <span style={{ color: '#00BCD4' }}>{b.name}</span>
                {sigs.length > 0 && (
                  <>
                    <span style={{ color: '#666666' }}>[</span>
                    <span style={{ color: '#81C784' }}>{sigs.join(', ')}</span>
                    <span style={{ color: '#666666' }}>]</span>
                  </>
                )}
                {(i < shown.length - 1 || extra > 0) && (
                  <span style={{ color: '#666666' }}>&nbsp;|</span>
                )}
              </span>
            );
          })}
          {extra > 0 && (
            <span style={{ color: '#666666' }}>+ {extra} more</span>
          )}
        </>
      )}
    </div>
  );
}

// DB blocks: { name, logic, signals: [...], exit_conditions: [...] }
// Store blocks: { id, type, data: { signals, timingConstraint, exits, recheckConfigs } }
interface DBRecheckConfig { enabled?: boolean; bar_delay?: number; validation_mode?: string; }
interface DBExitCondition { signal_name: string; percentage?: number; exit_mode?: string; binding_level?: string; recheck_config?: DBRecheckConfig; }
interface DBSignal {
  name: string; logic?: string;
  timing_constraint?: { reference?: string; max_candles?: number } | null;
  recheck_config?: DBRecheckConfig | null;
  recheck_chain?: DBRecheckConfig[] | null;
  exit_conditions?: DBExitCondition[];
}
type AnyBlock = Block | { name: string; logic?: string; signals?: DBSignal[]; exit_conditions?: DBExitCondition[] };

function exitModeLabel(mode?: string): string {
  return mode === 'ABSOLUTE' ? 'immediate exit' : 'TP-aware exit';
}

function recheckLabel(rc: DBRecheckConfig): string {
  if (rc.validation_mode === 'RECHECK') return `RECHECK of RECHECK (WITHIN ${rc.bar_delay} bars)`;
  if (rc.validation_mode === 'SIGNAL') return `RECHECK of Signal (WITHIN ${rc.bar_delay} bars)`;
  return `RECHECK (WITHIN ${rc.bar_delay} bars)`;
}

function BlockHierarchyTree({ blocks }: { blocks: AnyBlock[] }) {
  if (blocks.length === 0) {
    return <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>No blocks configured</p>;
  }
  return (
    <div className="space-y-2 font-mono text-xs">
      {blocks.map((block, i) => {
        const b = block as Record<string, unknown>;
        const rawSignals = (b.signals ?? (b.data as Record<string, unknown> | undefined)?.signals ?? []) as DBSignal[];
        const blockExits = (b.exit_conditions ?? []) as DBExitCondition[];
        const label = (b.name as string | undefined) ?? BLOCK_TYPE_LABELS[(b.type as BlockType)] ?? String(b.type ?? '');
        return (
          <div key={i} className="space-y-0.5">
            <div>
              <span className="font-bold" style={{ color: '#00BCD4' }}>#{i + 1}</span>{' '}
              <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
            </div>
            {rawSignals.map((sig, si) => (
              <div key={si}>
                <div className="ml-4" style={{ color: 'var(--text-secondary)' }}>
                  └── <span style={{ color: sig.logic === 'OR' ? 'var(--accent-blue)' : '#66BB6A' }}>
                    {si + 1}. {sig.name} [{sig.logic ?? 'AND'}]
                  </span>
                </div>
                {sig.timing_constraint && (
                  <div className="ml-8" style={{ color: '#FFA500' }}>
                    └── TIME CONSTRAINT
                    <div className="ml-4" style={{ color: 'var(--text-muted)' }}>
                      └── Within {sig.timing_constraint.max_candles} candles of previous signal
                    </div>
                  </div>
                )}
                {sig.recheck_config?.enabled && (
                  <div className="ml-8" style={{ color: '#4ADE80' }}>
                    └── RECHECK (WITHIN {sig.recheck_config.bar_delay} bars)
                  </div>
                )}
                {(sig.recheck_chain ?? []).filter(rc => rc.enabled).map((rc, ri) => (
                  <div key={ri} className="ml-8" style={{ color: '#60A5FA' }}>
                    └── {recheckLabel(rc)}
                  </div>
                ))}
                {(sig.exit_conditions ?? []).map((ec, ei) => (
                  <div key={ei}>
                    <div className="ml-8" style={{ color: 'var(--accent-red)' }}>
                      └── EXIT: {ec.signal_name} - {ec.percentage != null ? Math.round(ec.percentage * 100) : 0}% {exitModeLabel(ec.exit_mode)} <span style={{ color: 'var(--text-muted)' }}>[SIGNAL]</span>
                    </div>
                    {ec.recheck_config?.enabled && (
                      <div className="ml-12" style={{ color: '#4ADE80' }}>
                        └── RECHECK (WITHIN {ec.recheck_config.bar_delay} bars)
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ))}
            {blockExits.length > 0 && (
              <div className="mt-1">
                <div className="ml-4 font-semibold" style={{ color: '#81C784' }}>
                  Block-Level Exit Conditions: ({label})
                </div>
                {blockExits.map((ec, ei) => (
                  <div key={ei} className="ml-8" style={{ color: 'var(--accent-red)' }}>
                    └── EXIT: {ec.signal_name} - {ec.percentage != null ? Math.round(ec.percentage * 100) : 0}% {exitModeLabel(ec.exit_mode)} <span style={{ color: 'var(--text-muted)' }}>[BLOCK]</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function DetailsPanel({ strategy }: { strategy: Strategy }) {
  const result = strategy.backtestResults?.[strategy.backtestResults.length - 1];
  const entryBlocks = strategy.blocks.filter((b) => b.type === BlockType.ENTRY_CONDITION);
  const exitBlocks  = strategy.blocks.filter((b) => b.type === BlockType.EXIT_CONDITION);

  const qScore = result ? computeQualityScore(result) : null;
  const quality = qScore != null ? getQualityLabel(qScore) : null;

  const sType = strategy.strategyType ??
    (strategy.settings as { strategyType?: string }).strategyType;

  // Parse description into block components with signal lists
  const parseDescription = (desc: string) => {
    const blocks = desc.split(/\s\+\s|\n/).filter(Boolean);
    return blocks.map((line) => {
      const trimmed = line.trim();
      const match = trimmed.match(/^([^\(]+)\s*\((REQUIRED|OPTIONAL)\):\s*(.*)$/);
      if (match) {
        return {
          name: match[1].trim(),
          required: match[2] === 'REQUIRED',
          signals: match[3].split(',').map((s) => s.trim()).filter(Boolean),
        };
      }
      return { name: trimmed, required: false, signals: [] };
    });
  };

  const descriptionBlocks = strategy.description ? parseDescription(strategy.description) : [];

  return (
    <div className="grid grid-cols-3 gap-4 p-4 min-h-full" style={{ borderTop: '1px solid var(--border)', background: 'var(--bg-deep)' }}>
      {/* Column 1: Strategy Info */}
      <div className="space-y-4 p-4 rounded border" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
          <Info size={12} strokeWidth={1.5} />
          Strategy Info
        </div>

        {/* Identity */}
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold leading-tight" style={{ color: 'var(--text-secondary)' }}>{strategy.name}</p>
            {sType && (
              <span className="text-xs font-medium" style={{
                color: sType.toLowerCase() === 'bullish' ? 'var(--accent-green)' : 'var(--accent-red)',
              }}>
                {sType.toLowerCase() === 'bullish' ? '▲' : '▼'} {sType.charAt(0).toUpperCase() + sType.slice(1).toLowerCase()}
              </span>
            )}
          </div>
          {strategy.versionNumber != null && (
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              v{strategy.versionNumber}
              {strategy.versionId && (
                <span className="ml-1.5" style={{ color: 'var(--text-faintest)' }}>{strategy.versionId.slice(0, 8)}</span>
              )}
            </p>
          )}
        </div>

        {/* Blocks — numbered list, signals as sub-text */}
        {descriptionBlocks.length > 0 && (
          <div className="space-y-2" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
            <p className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
              Blocks ({descriptionBlocks.length})
            </p>
            <div className="space-y-2">
              {descriptionBlocks.map((block, i) => (
                <div key={i} className="space-y-0.5">
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-xs shrink-0 tabular-nums" style={{ color: 'var(--text-faintest)' }}>#{i + 1}</span>
                    <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{block.name}</span>
                    <span className="text-xs ml-auto shrink-0" style={{
                      color: block.required ? 'var(--accent-green)' : 'var(--text-muted)',
                    }}>
                      {block.required ? 'REQ' : 'opt'}
                    </span>
                  </div>
                  {block.signals.length > 0 && (
                    <p className="text-xs pl-5 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                      {block.signals.join(', ')}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Metadata — icon + label rows, no emoji */}
        <div className="space-y-1 text-xs" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem', color: 'var(--text-muted)' }}>
          <div className="flex items-center gap-1.5">
            <Calendar size={11} strokeWidth={1.5} style={{ flexShrink: 0 }} />
            <span>Created {new Date(strategy.createdAt).toLocaleDateString()}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <RefreshCw size={11} strokeWidth={1.5} style={{ flexShrink: 0 }} />
            <span>Updated {new Date(strategy.updatedAt).toLocaleDateString()}</span>
          </div>
          {strategy.testCount != null && (
            <div className="flex items-center gap-1.5">
              <CheckCircle size={11} strokeWidth={1.5} style={{ flexShrink: 0 }} />
              <span>{strategy.testCount} test{strategy.testCount !== 1 ? 's' : ''}</span>
            </div>
          )}
        </div>

        {/* Tags */}
        {strategy.tags && strategy.tags.length > 0 && (
          <div className="flex flex-wrap gap-1" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
            {strategy.tags.map((tag) => (
              <span key={tag} className="px-2 py-0.5 rounded text-xs" style={{
                background: 'var(--bg-card)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border)',
              }}>{tag}</span>
            ))}
          </div>
        )}
      </div>

      {/* Column 2: Configuration Hierarchy */}
      <div className="space-y-2 overflow-y-auto p-4 rounded border" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
          <Settings size={12} strokeWidth={1.5} />
          Configuration
        </div>
        <BlockHierarchyTree blocks={strategy.blocks as AnyBlock[]} />
        <p className="text-xs mt-2" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem', color: 'var(--text-muted)' }}>
          {strategy.blocks.length} block{strategy.blocks.length !== 1 ? 's' : ''}
          {entryBlocks.length > 0 || exitBlocks.length > 0
            ? ` · ${entryBlocks.length} entry · ${exitBlocks.length} exit`
            : ''}
        </p>
      </div>

      {/* Column 3: Performance */}
      <div className="space-y-3 p-4 rounded border" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)', paddingBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
          <TrendingUp size={12} strokeWidth={1.5} />
          Performance
        </div>
        {!result ? (
          <div className="space-y-1">
            <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>
              Run backtest to see: Sharpe Ratio, Win Rate, Trade Stats
            </p>
          </div>
        ) : (
          <div className="space-y-1.5 text-xs">
            {/* Quality Score Badge */}
            {quality && (
              <div className="px-2.5 py-1.5 rounded border flex items-center gap-2" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem', marginTop: '1rem',
                background: quality.color === 'var(--accent-green)' ? 'rgba(124, 194, 122, 0.15)' :
                           quality.color === 'var(--accent-blue)' ? 'rgba(96, 165, 250, 0.15)' :
                           quality.color === 'var(--accent-orange)' ? 'rgba(249, 115, 22, 0.15)' :
                           'rgba(195, 82, 82, 0.15)',
                borderColor: quality.color === 'var(--accent-green)' ? 'rgba(124, 194, 122, 0.3)' :
                            quality.color === 'var(--accent-blue)' ? 'rgba(96, 165, 250, 0.3)' :
                            quality.color === 'var(--accent-orange)' ? 'rgba(249, 115, 22, 0.3)' :
                            'rgba(195, 82, 82, 0.3)'
              }}>
                <span style={{ color: quality.dot, fontSize: '12px' }}>●</span>
                <span className="font-semibold" style={{ color: quality.color }}>{quality.label}</span>
                <span style={{ color: 'var(--text-muted)' }}>{qScore}/7</span>
                {strategy.testCount != null && <span style={{ color: 'var(--text-muted)', marginLeft: 'auto' }}>{strategy.testCount} test{strategy.testCount !== 1 ? 's' : ''}</span>}
              </div>
            )}

            {/* Trade Stats Section */}
            <div className="px-2.5 py-1.5 rounded border" style={{ borderTop: '1px solid var(--border)', borderColor: 'var(--border)', background: 'rgba(0,0,0,0.1)', paddingTop: '1rem', marginTop: '1rem' }}>
              <p className="uppercase tracking-wide font-semibold mb-1 text-xs" style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Trade Stats</p>
              <div className="space-y-0.5">
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--text-muted)' }}>Win Rate</span>
                  <span style={{ color: (result.winRate ?? 0) >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 500 }}>
                    {result.winRate != null ? (result.winRate * 100).toFixed(1) + '%' : '—'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--text-muted)' }}>Trades</span>
                  <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{result.totalTrades} ({result.winningTrades}W/{result.losingTrades}L)</span>
                </div>
              </div>
            </div>

            {/* Returns Section */}
            <div className="px-2.5 py-1.5 rounded border" style={{ borderTop: '1px solid var(--border)', borderColor: 'var(--border)', background: 'rgba(0,0,0,0.1)', paddingTop: '1rem', marginTop: '1rem' }}>
              <p className="uppercase tracking-wide font-semibold mb-1 text-xs" style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Returns</p>
              <div className="space-y-0.5">
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--text-muted)' }}>Return</span>
                  <span style={{ color: (result.returnPercentage ?? 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 500 }}>
                    {result.returnPercentage != null
                      ? (result.returnPercentage >= 0 ? '+' : '') + result.returnPercentage.toFixed(2) + '%'
                      : '—'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--text-muted)' }}>Prof. Factor</span>
                  <span style={{
                    color: (result.profitFactor ?? 0) >= 1.5 ? 'var(--accent-green)' :
                           (result.profitFactor ?? 0) >= 1.0 ? 'var(--accent-orange)' : 'var(--accent-red)',
                    fontWeight: 500
                  }}>
                    {fmtN(result.profitFactor, 2)}
                  </span>
                </div>
              </div>
            </div>

            {/* Risk Metrics Section */}
            <div className="px-2.5 py-1.5 rounded border" style={{ borderTop: '1px solid var(--border)', borderColor: 'var(--border)', background: 'rgba(0,0,0,0.1)', paddingTop: '1rem', marginTop: '1rem' }}>
              <p className="uppercase tracking-wide font-semibold mb-1 text-xs" style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>Risk Metrics</p>
              <div className="space-y-0.5">
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--text-muted)' }}>Sharpe</span>
                  <span style={{ color: (result.sharpeRatio ?? 0) >= 1.0 ? 'var(--accent-green)' : (result.sharpeRatio ?? 0) >= 0.5 ? 'var(--accent-orange)' : 'var(--accent-red)', fontWeight: 500 }}>
                    {fmtN(result.sharpeRatio, 2)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--text-muted)' }}>Sortino</span>
                  <span style={{ color: (result.sortino_ratio ?? 0) >= 1.0 ? 'var(--accent-green)' : (result.sortino_ratio ?? 0) >= 0.5 ? 'var(--accent-orange)' : 'var(--accent-red)', fontWeight: 500 }}>
                    {fmtN(result.sortino_ratio, 2)}
                  </span>
                </div>
                {result.calmar_ratio != null && (
                  <div className="flex items-center justify-between">
                    <span style={{ color: 'var(--text-muted)' }}>Calmar</span>
                    <span style={{ color: result.calmar_ratio >= 1.0 ? 'var(--accent-green)' : result.calmar_ratio >= 0.5 ? 'var(--accent-orange)' : 'var(--accent-red)', fontWeight: 500 }}>
                      {result.calmar_ratio.toFixed(2)}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--text-muted)' }}>Max DD</span>
                  <span style={{ color: 'var(--accent-red)', fontWeight: 500 }}>{fmtN(result.maxDrawdown, 2, '%')}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main dialog ───────────────────────────────────────────────────────────────

export interface StrategySelectOptions {
  // True when the picked version is older than the listed latest — the caller
  // needs this to validate against the in-memory blocks rather than the
  // backend's latest-only validator (BTCAAAAA-33738 Bug 2).
  historicalVersion?: boolean;
}

export interface StrategyBrowserDialogProps {
  open: boolean;
  onSelect: (strategy: Strategy, opts?: StrategySelectOptions) => void;
  onClose: () => void;
  mode?: 'open' | 'save_as';
  standalone?: boolean;
  // Initial visible-state seed used when the standalone window inherits state
  // from the inline view at Pop Out time (BTCAAAAA-29371). All optional; the
  // inline dialog leaves them undefined and uses its normal defaults.
  initialSelectedId?: string | null;
  initialSearchText?: string;
  initialTypeFilter?: TypeFilter;
  initialSortKey?: SortKey;
  initialSortDir?: SortDir;
}

export function StrategyBrowserDialog({
  open, onSelect, onClose, mode = 'open', standalone = false,
  initialSelectedId, initialSearchText, initialTypeFilter, initialSortKey, initialSortDir,
}: StrategyBrowserDialogProps) {
  const { strategyList } = useStrategyStore();
  const [searchText, setSearchText]   = useState<string>(initialSearchText ?? '');
  const [typeFilter, setTypeFilter]   = useState<TypeFilter>(initialTypeFilter ?? 'all');
  const [sortKey, setSortKey]         = useState<SortKey>(initialSortKey ?? 'updated');
  const [sortDir, setSortDir]         = useState<SortDir>(initialSortDir ?? 'desc');
  const [selectedId, setSelectedId]   = useState<string | null>(initialSelectedId ?? null);
  const [controlling, setControlling] = useState(false);
  const [controlMsg, setControlMsg]   = useState<string | null>(null);
  const [localList, setLocalList]     = useState<typeof strategyList | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showDupModal, setShowDupModal]       = useState(false);
  const [versions, setVersions]               = useState<StrategyVersion[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [detailOverride, setDetailOverride]    = useState<Strategy | null>(null);
  const [loadingVersionId, setLoadingVersionId] = useState<string | null>(null);
  // Monotonic counter to discard stale loadStrategyVersion responses when the
  // user clicks faster than the network. Only the most-recent request's
  // result becomes the override (BTCAAAAA-33738).
  const versionLoadSeqRef = useRef(0);
  const importRef = useRef<HTMLInputElement>(null);

  // Splitter state: table flex-basis percentage. Stored value (if any) is
  // loaded in a mount-time effect since useState's lazy initializer runs
  // during SSR where localStorage is unavailable. Without a stored value, a
  // 5-row measured default is applied once the table renders (BTCAAAAA-29359).
  const [splitPct, setSplitPct] = useState<number>(SPLIT_FALLBACK_PCT);
  const splitterRef = useRef<HTMLDivElement>(null);
  const tableTheadRef = useRef<HTMLTableSectionElement>(null);
  const tableFirstRowRef = useRef<HTMLTableRowElement>(null);
  const dragging = useRef(false);
  const fiveRowDefaultApplied = useRef<boolean>(false);
  const hasLoadedOnce = useRef(false);

  const displayList = localList ?? strategyList;

  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError]     = useState<string | null>(null);

  const refreshList = useCallback(async () => {
    setListLoading(true);
    setListError(null);
    try {
      const updated = await listStrategies();
      setLocalList(updated as typeof strategyList);
    } catch (e) {
      setListError(e instanceof Error ? e.message : 'Failed to load strategies');
      setLocalList(null);
    } finally {
      setListLoading(false);
      hasLoadedOnce.current = true;
    }
  }, []);

  // Fetch from DB every time the dialog opens (not just on user-triggered refresh)
  useEffect(() => {
    if (!open) return;
    refreshList();
  }, [open, refreshList]);

  const selectedStrategy = useMemo(
    () => displayList.find((s) => s.id === selectedId) ?? null,
    [displayList, selectedId],
  );
  // DetailsPanel shows the version-overridden data when a different version is selected
  const detailsStrategy = detailOverride ?? selectedStrategy;

  // Re-fetch the version dropdown for a given strategy. Used by the selection
  // effect AND by mutation handlers (duplicate as new version) so the dropdown
  // reflects newly-created rows without requiring the user to deselect and
  // re-pick the strategy (BTCAAAAA-33886).
  const reloadVersions = useCallback(async (strategyId: string) => {
    try {
      const v = await getStrategyVersions(strategyId);
      setVersions((v as StrategyVersion[]) ?? []);
      return (v as StrategyVersion[]) ?? [];
    } catch {
      setVersions([]);
      return [];
    }
  }, []);

  // Load versions when selection changes; reset version override
  useEffect(() => {
    if (!selectedId) { setVersions([]); setSelectedVersionId(null); setDetailOverride(null); return; }
    const currentVersionId = displayList.find(s => s.id === selectedId)?.versionId ?? null;
    setSelectedVersionId(currentVersionId);
    setDetailOverride(null);
    reloadVersions(selectedId);
  }, [selectedId, reloadVersions]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleVersionChange = useCallback(async (strategyId: string, versionId: string) => {
    setSelectedVersionId(versionId);
    setLoadingVersionId(versionId);
    const seq = ++versionLoadSeqRef.current;
    try {
      const data = await loadStrategyVersion(strategyId, versionId);
      // Discard if a newer pick has superseded this load (rapid dropdown clicks).
      if (seq !== versionLoadSeqRef.current) return;
      setDetailOverride(data as Strategy);
    } catch {
      if (seq === versionLoadSeqRef.current) setDetailOverride(null);
    } finally {
      if (seq === versionLoadSeqRef.current) setLoadingVersionId(null);
    }
  }, []);

  // Drag-to-resize splitter. Final position is persisted to localStorage on
  // mouse-up so it survives reloads (BTCAAAAA-29359).
  const onSplitterMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    const container = splitterRef.current?.parentElement;
    if (!container) return;
    const startY = e.clientY;
    const startPct = splitPct;
    const totalH = container.getBoundingClientRect().height;
    let latestPct = startPct;
    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const delta = ev.clientY - startY;
      const newPct = Math.min(SPLIT_MAX_PCT, Math.max(SPLIT_MIN_PCT, startPct + (delta / totalH) * 100));
      latestPct = newPct;
      setSplitPct(newPct);
    };
    const onUp = () => {
      dragging.current = false;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      try {
        window.localStorage.setItem(SPLIT_STORAGE_KEY, String(latestPct));
      } catch { /* ignore */ }
      fiveRowDefaultApplied.current = true;
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [splitPct]);

  // Restore persisted splitter position from localStorage on mount. Runs only
  // on the client, so it bypasses the SSR-unavailable-window issue.
  useEffect(() => {
    const stored = readStoredSplitPct();
    if (stored != null) {
      setSplitPct(stored);
      fiveRowDefaultApplied.current = true;
    }
  }, []);

  // On first open with no stored preference, size the top panel so exactly ~5
  // strategy rows + the table header are visible. Skipped once a stored value
  // is in effect or the user has dragged.
  useLayoutEffect(() => {
    if (!open) return;
    if (fiveRowDefaultApplied.current) return;
    if (!hasLoadedOnce.current || listLoading) return;
    const firstRow = tableFirstRowRef.current;
    if (displayList.length > 0 && !firstRow) return;
    const container = splitterRef.current?.parentElement;
    if (!container) return;
    const containerH = container.getBoundingClientRect().height;
    if (containerH <= 0) return;
    if (displayList.length === 0) {
      fiveRowDefaultApplied.current = true;
      return;
    }
    const headH = tableTheadRef.current?.getBoundingClientRect().height ?? 28;
    const rowH = firstRow!.getBoundingClientRect().height;
    const desiredTopPx = headH + 5 * rowH;
    const pct = (desiredTopPx / containerH) * 100;
    const clamped = Math.min(SPLIT_MAX_PCT, Math.max(SPLIT_MIN_PCT, pct));
    setSplitPct(clamped);
    fiveRowDefaultApplied.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, listLoading, displayList.length]);

  const handleSort = useCallback((col: SortKey) => {
    if (col === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(col);
      setSortDir('asc');
    }
  }, [sortKey]);

  const filtered = useMemo(() => {
    let result = [...displayList];
    if (searchText) {
      const q = searchText.toLowerCase();
      result = result.filter((s) => {
        const sType = s.strategyType ?? (s.settings as { strategyType?: string }).strategyType ?? '';
        const dateStr = new Date(s.updatedAt).toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' });
        return (
          s.name.toLowerCase().includes(q) ||
          (s.description?.toLowerCase().includes(q) ?? false) ||
          sType.toLowerCase().includes(q) ||
          dateStr.includes(q) ||
          s.blocks.some((b) => BLOCK_TYPE_LABELS[b.type]?.toLowerCase().includes(q))
        );
      });
    }
    if (typeFilter !== 'all') {
      result = result.filter((s) => {
        const t = s.strategyType ?? (s.settings as { strategyType?: string }).strategyType;
        return t?.toLowerCase() === typeFilter;
      });
    }
    result.sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'name')    cmp = a.name.localeCompare(b.name);
      if (sortKey === 'blocks')  cmp = a.blocks.length - b.blocks.length;
      if (sortKey === 'updated') cmp = new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
      if (sortKey === 'created') cmp = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
      if (sortKey === 'status')  cmp = a.status.localeCompare(b.status);
      if (sortKey === 'version') cmp = (a.versionNumber ?? 0) - (b.versionNumber ?? 0);
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return result;
  }, [displayList, searchText, typeFilter, sortKey, sortDir]);

  const handleDeleteConfirm = useCallback(async (scope: DeleteScope, versionIds?: string[]) => {
    if (!selectedId) return;
    setShowDeleteModal(false);
    setControlling(true); setControlMsg(null);
    try {
      await deleteStrategyScoped(selectedId, scope, versionIds);
      setSelectedId(null);
      setControlMsg(scope === 'entire' ? 'Strategy deleted' : `Version${(versionIds?.length ?? 0) > 1 ? 's' : ''} deleted`);
      await refreshList();
    }
    catch { setControlMsg('Delete failed'); }
    finally { setControlling(false); }
  }, [selectedId, refreshList]);

  const handleDuplicateConfirm = useCallback(async (scope: DuplicateScope, newName?: string) => {
    if (!selectedId) return;
    setShowDupModal(false);
    setControlling(true); setControlMsg(null);
    try {
      // Pass selectedVersionId so the backend clones the version the user is
      // actually viewing — without it the backend always sources from latest
      // (BTCAAAAA-33886).
      const result = await duplicateStrategyScoped(
        selectedId,
        scope,
        newName,
        scope === 'version' ? selectedVersionId : null,
      ) as { versionId?: string } | null;
      setControlMsg(scope === 'version' ? 'New version created' : 'Strategy duplicated');
      await refreshList();
      // For scope='version' the selected strategy is unchanged, so the
      // selection-keyed useEffect won't re-fetch versions. Refresh the
      // dropdown explicitly and point selection at the newly-created row
      // so the user sees the new version immediately (BTCAAAAA-33886).
      if (scope === 'version') {
        await reloadVersions(selectedId);
        const newVersionId = result?.versionId ?? null;
        if (newVersionId) {
          setSelectedVersionId(newVersionId);
          setDetailOverride(null);
        }
      }
    }
    catch { setControlMsg('Duplicate failed'); }
    finally { setControlling(false); }
  }, [selectedId, selectedVersionId, refreshList, reloadVersions]);

  const handleExportJson = useCallback(() => {
    if (!selectedStrategy) return;
    const json = JSON.stringify(selectedStrategy, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedStrategy.name.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setControlMsg('Exported to JSON');
  }, [selectedStrategy]);

  const handleImportJson = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const data = JSON.parse(text) as Partial<Strategy>;
      if (!data.name) { setControlMsg('Invalid JSON: missing name'); return; }
      await createStrategy({ name: data.name, description: data.description ?? '' });
      setControlMsg('Imported from JSON');
      await refreshList();
    } catch {
      setControlMsg('Import failed');
    }
    if (importRef.current) importRef.current.value = '';
  }, [refreshList]);

  const handleSelect = useCallback(async () => {
    if (!selectedStrategy) return;
    // Resolve the version the user actually picked. Race guard: if the version
    // pick is still in flight (handleVersionChange not yet resolved), or the
    // dropdown value disagrees with the cached detailOverride, fetch the
    // selected version inline so we never fall back to the latest-row data
    // (BTCAAAAA-33738 Bug 1: clicking Open before loadStrategyVersion resolved
    // would pass selectedStrategy — i.e. the latest row — to the builder).
    const latestVersionId = selectedStrategy.versionId ?? null;
    const overrideVersionId = (detailOverride as { versionId?: string } | null)?.versionId ?? null;
    const needsExplicitLoad =
      selectedVersionId != null &&
      selectedVersionId !== latestVersionId &&
      selectedVersionId !== overrideVersionId;

    let target: Strategy = detailOverride ?? selectedStrategy;
    if (needsExplicitLoad) {
      try {
        const data = await loadStrategyVersion(selectedStrategy.id, selectedVersionId!);
        target = data as Strategy;
        setDetailOverride(target);
      } catch {
        // Fall back to whatever we have rather than silently load latest;
        // surface a status so the user knows the version load failed.
        setControlMsg('Failed to load the selected version');
        return;
      }
    }
    const targetVersionId = (target as { versionId?: string }).versionId ?? null;
    const isHistorical = targetVersionId != null && targetVersionId !== latestVersionId;
    onSelect(target, { historicalVersion: isHistorical });
    onClose();
  }, [detailOverride, selectedStrategy, selectedVersionId, onSelect, onClose]);

  const handleRowDoubleClick = useCallback((s: Strategy) => {
    // Double-click bypasses the version dropdown by definition (the row is
    // the latest version), so pass it through unchanged.
    onSelect(s, { historicalVersion: false }); onClose();
  }, [onSelect, onClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Enter' && selectedId) handleSelect().catch(console.error);
    },
    [selectedId, onClose, handleSelect],
  );

  const handlePopOut = useCallback(() => {
    // Carry the inline view's current selection + search/filter/sort into the
    // popped-out window so it opens already showing the same state, then
    // close the inline view so only one Strategy Browser is visible at a time
    // (BTCAAAAA-29371).
    const params = new URLSearchParams();
    if (selectedId) params.set('selectedId', selectedId);
    if (searchText) params.set('q', searchText);
    if (typeFilter !== 'all') params.set('type', typeFilter);
    if (sortKey !== 'updated') params.set('sort', sortKey);
    if (sortDir !== 'desc') params.set('dir', sortDir);
    const qs = params.toString();
    const url = qs ? `/strategy-browser?${qs}` : '/strategy-browser';
    const win = window.open(url, '_blank', 'width=1280,height=800,menubar=no,toolbar=no,location=no,status=no');
    if (win) onClose();
  }, [selectedId, searchText, typeFilter, sortKey, sortDir, onClose]);

  const handlePopIn = useCallback(() => {
    // Standalone-only: hand current state back to the opener and close this
    // window. The opener listens for `strategy-browser:popin` postMessages
    // and re-opens the inline dialog seeded with this state (BTCAAAAA-29371).
    if (typeof window === 'undefined' || !window.opener) return;
    window.opener.postMessage(
      {
        type: 'strategy-browser:popin',
        state: { selectedId, searchText, typeFilter, sortKey, sortDir },
      },
      window.location.origin,
    );
    window.close();
  }, [selectedId, searchText, typeFilter, sortKey, sortDir]);

  // Only show Pop In when this standalone window was opened via Pop Out
  // (i.e., has an opener). Direct URL visits get no Pop In target.
  const [canPopIn, setCanPopIn] = useState(false);
  useEffect(() => {
    if (typeof window !== 'undefined' && standalone && window.opener) {
      setCanPopIn(true);
    }
  }, [standalone]);

  if (!open) return null;

  const isSaveAs = mode === 'save_as';
  const TitleIcon = isSaveAs ? Save : GitBranch;
  const titleText = isSaveAs ? 'Save Strategy As' : 'Strategy Browser';
  const confirmLabel = isSaveAs ? 'Save Here' : 'Open';

  const contentBox = (
    <div
      className="relative w-full flex flex-col"
      style={{
        maxWidth: standalone ? '100%' : '2560px',
        width: '100%',
        height: '100%',
        borderRadius: 0,
        border: '1px solid var(--border)',
        background: 'var(--bg-panel)',
        boxShadow: standalone ? 'none' : '0 25px 50px -12px rgba(0,0,0,0.5)',
      }}
    >

      {/* Header */}
      <div
        className="flex items-center justify-between px-6 py-3 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <h2
          id="strategy-browser-title"
          className="text-sm font-semibold flex items-center gap-3"
          style={{ color: 'var(--text-secondary)' }}
        >
          {/* AppBrand prefix shows in both inline and standalone modes so the
              popout header matches the board reference: BTC brand + title at
              top-left of the dialog (BTCAAAAA-29978). */}
          <AppBrand size={24} />
          <span className="flex items-center gap-2">
            <TitleIcon style={{ width: 16, height: 16, flexShrink: 0 }} />
            <span>{titleText}</span>
          </span>
        </h2>
        <div className="flex items-center gap-2">
          {!standalone && (
            <button
              onClick={handlePopOut}
              title="Open this browser in a separate window that can be moved to another monitor"
              className="px-2.5 py-1 rounded text-xs font-medium transition-colors"
              style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
            >
              ↗ Pop Out
            </button>
          )}
          {canPopIn && (
            <button
              onClick={handlePopIn}
              title="Return this browser to the main app window with the current selection and search state"
              className="px-2.5 py-1 rounded text-xs font-medium transition-colors"
              style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
            >
              ↙ Pop In
            </button>
          )}
          <button
            onClick={onClose}
            className="text-lg transition-colors"
            aria-label="Close dialog"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)'; }}
          >✕</button>
        </div>
      </div>

      {/* Filters */}
      <div
        className="px-3 py-3 flex items-center gap-3 flex-shrink-0 flex-wrap"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <input
          type="text"
          placeholder="Search strategies, blocks…"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className="flex-1 min-w-48 px-3 py-1.5 rounded text-sm focus:outline-none"
          style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--input-text)' }}
          title="Filter strategies by name — updates results as you type"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as TypeFilter)}
          className="px-2 py-1.5 rounded text-sm focus:outline-none"
          style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--text-secondary)' }}
          title="Filter strategies by market direction — Bullish (long) or Bearish (short)"
        >
          <option value="all">All Types</option>
          <option value="bullish">🟢 Bullish</option>
          <option value="bearish">🔴 Bearish</option>
        </select>

        <span className="text-xs whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
          {filtered.length} strateg{filtered.length !== 1 ? 'ies' : 'y'}
        </span>
      </div>

      {/* Resizable table + details area */}
      <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
        {/* Table */}
        <div className="overflow-y-auto" style={{ flex: `0 0 ${splitPct}%` }}>
          <table className="w-full text-sm border-collapse">
            <thead ref={tableTheadRef} className="sticky top-0 z-10" style={{ background: 'var(--bg-panel)', borderBottom: '1px solid var(--border)' }}>
              <tr>
                <SortHeader label="Strategy Name" col="name"    active={sortKey} dir={sortDir} onClick={handleSort} className="pl-6 pr-3 py-2 text-left text-xs font-medium uppercase tracking-wide cursor-pointer whitespace-nowrap select-none" />
                <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>Type</th>
                <SortHeader label="Version"        col="version" active={sortKey} dir={sortDir} onClick={handleSort} />
                <SortHeader label="Last Modified"  col="updated" active={sortKey} dir={sortDir} onClick={handleSort} />
                <SortHeader label="Validation"     col="status"  active={sortKey} dir={sortDir} onClick={handleSort} />
                <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>Published</th>
              </tr>
            </thead>
            <tbody>
              {listLoading ? (
                <tr>
                  <td colSpan={6} className="pl-6 pr-3 py-8 text-center text-sm italic" style={{ color: 'var(--text-muted)' }}>
                    Loading strategies…
                  </td>
                </tr>
              ) : listError ? (
                <tr>
                  <td colSpan={6} className="pl-6 pr-3 py-8 text-center text-sm" style={{ color: 'var(--accent-red)' }}>
                    {listError}
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="pl-6 pr-3 py-8 text-center text-sm italic" style={{ color: 'var(--text-muted)' }}>
                    {displayList.length === 0 ? 'No strategies yet' : 'No matching strategies'}
                  </td>
                </tr>
              ) : (
                filtered.map((strategy, idx) => {
                  const isSelected = strategy.id === selectedId;
                  const sType = strategy.strategyType ?? (strategy.settings as { strategyType?: string }).strategyType;
                  const valStatus = strategy.validationStatus ??
                    (strategy.status === StrategyStatus.VALID ? 'Pass' :
                     strategy.status === StrategyStatus.INVALID ? 'Fail' : 'Un-Validated');
                  return (
                    <tr
                      key={strategy.id}
                      ref={idx === 0 ? tableFirstRowRef : undefined}
                      onClick={() => setSelectedId(strategy.id)}
                      onDoubleClick={() => handleRowDoubleClick(strategy)}
                      className={`border-b cursor-pointer transition-colors ${isSelected ? 'border-l-2' : ''}`}
                      style={{
                        borderBottomColor: 'var(--border)',
                        borderLeftColor: isSelected ? 'var(--accent-blue)' : 'var(--border)',
                        background: isSelected
                          ? 'var(--accent-blue-mid)'
                          : idx % 2 === 0 ? 'var(--bg-panel)' : 'var(--bg-card)',
                      }}
                      onMouseEnter={!isSelected ? e => { (e.currentTarget as HTMLTableRowElement).style.boxShadow = 'inset 0 0 0 1px rgba(46, 140, 255, 0.35)'; } : undefined}
                      onMouseLeave={!isSelected ? e => { (e.currentTarget as HTMLTableRowElement).style.boxShadow = ''; } : undefined}
                    >
                      <td className="pl-6 pr-3 py-2">
                        <StrategyNameCell strategy={strategy} />
                      </td>
                      <td className="px-3 py-2 text-xs text-center">
                        {sType?.toLowerCase() === 'bullish'
                          ? <span><span style={{ color: '#7cc27a' }}>●</span><span style={{ color: '#9CA3AF' }}> Bullish</span></span>
                          : sType?.toLowerCase() === 'bearish'
                          ? <span><span style={{ color: '#c35252' }}>●</span><span style={{ color: '#9CA3AF' }}> Bearish</span></span>
                          : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                      </td>
                      <td className="px-3 py-2 text-xs text-center" style={{ color: 'var(--text-secondary)' }}>
                        {isSelected && versions.length > 1 ? (
                          <select
                            value={selectedVersionId ?? strategy.versionId ?? ''}
                            onChange={e => handleVersionChange(strategy.id, e.target.value)}
                            onClick={e => e.stopPropagation()}
                            className="rounded text-xs px-1 py-0.5 focus:outline-none"
                            style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                          >
                            {versions.map(v => (
                              <option key={v.id} value={v.id}>v{v.versionNumber}{v.isLatest ? ' (latest)' : ''}</option>
                            ))}
                          </select>
                        ) : (
                          strategy.versionNumber != null ? `v${strategy.versionNumber}` : '—'
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>
                        {new Date(strategy.updatedAt).toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' })}
                        {' '}
                        {new Date(strategy.updatedAt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          style={{ ...STATUS_PILL_BASE, ...(STATUS_STYLES[strategy.status] ?? { color: 'var(--text-muted)' }) }}
                        >
                          {valStatus}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        {strategy.published ? (
                          <span style={{ ...STATUS_PILL_BASE, ...STATUS_STYLES.valid }}>Published</span>
                        ) : (
                          <span style={{ ...STATUS_PILL_BASE, ...STATUS_STYLES.draft }}>Draft</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Splitter handle */}
        <div
          ref={splitterRef}
          onMouseDown={onSplitterMouseDown}
          className="flex-shrink-0 flex items-center justify-center h-2 cursor-row-resize select-none transition-colors"
          style={{ background: 'var(--bg-card)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}
          onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = 'var(--bg-hover)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = 'var(--bg-card)'; }}
          title="Drag to resize"
        >
          <span className="text-xs tracking-widest select-none" style={{ color: 'var(--text-muted)' }}>⋯</span>
        </div>

        {/* Details panel */}
        <div className="overflow-y-auto" style={{ flex: `0 0 ${100 - splitPct}%`, background: 'var(--bg-deep)' }}>
          {detailsStrategy ? (
            <DetailsPanel strategy={detailsStrategy} />
          ) : (
            <div className="flex items-center justify-center h-full text-xs italic py-8" style={{ color: 'var(--text-muted)' }}>
              Select a strategy to view details
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div
        className="flex items-center justify-between gap-3 px-6 py-3 flex-shrink-0"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        {/* Left: action buttons (selection-dependent except Import) */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowDeleteModal(true)}
            disabled={!selectedStrategy || controlling}
            title="Permanently delete the selected strategy and all its versions from the database"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
            style={{ background: 'var(--accent-red-deeper)', color: 'var(--accent-red)', border: '1px solid var(--accent-red-dark)' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--accent-red-dark)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--accent-red-deeper)'; }}
          >
            <Trash2 size={13} strokeWidth={1.5} aria-hidden="true" />
            Delete
          </button>
          <button
            onClick={() => setShowDupModal(true)}
            disabled={!selectedStrategy || controlling}
            title="Create a copy of the selected strategy as a new entry"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
            style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
          >
            <Copy size={13} strokeWidth={1.5} aria-hidden="true" />
            Duplicate
          </button>
          <button
            onClick={handleExportJson}
            disabled={!selectedStrategy}
            title="Export the selected strategy's configuration to a JSON file"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
            style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
          >
            <Download size={13} strokeWidth={1.5} aria-hidden="true" />
            Export JSON
          </button>
          <label
            title="Import a strategy configuration from a previously exported JSON file"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium cursor-pointer transition-colors"
            style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
            onMouseEnter={e => { (e.currentTarget as HTMLLabelElement).style.background = 'var(--bg-hover)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLLabelElement).style.background = 'var(--bg-card)'; }}
          >
            <Upload size={13} strokeWidth={1.5} aria-hidden="true" />
            Import JSON
            <input ref={importRef} type="file" accept=".json" className="hidden" onChange={handleImportJson} />
          </label>
          {controlMsg && (
            <span className="text-xs ml-1" style={{ color: 'var(--text-secondary)' }}>{controlMsg}</span>
          )}
        </div>

        {/* Right: Cancel + Open/Save */}
        <div className="flex gap-2 flex-shrink-0">
          <button
            onClick={onClose}
            title="Close the browser without opening or saving a strategy"
            className="px-4 py-1.5 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
          >
            Cancel
          </button>
          <button
            onClick={() => { handleSelect().catch(console.error); }}
            disabled={!selectedId || loadingVersionId != null}
            title={
              loadingVersionId != null
                ? 'Loading the selected version…'
                : isSaveAs
                  ? 'Save the strategy to the selected location'
                  : 'Open the selected strategy in the Strategy Builder'
            }
            className="flex items-center gap-1.5 px-4 py-1.5 rounded text-sm font-medium transition-all border select-none disabled:opacity-40"
            style={{
              background: 'rgba(255,255,255,0.04)',
              borderColor: 'rgba(255,255,255,0.08)',
              color: 'var(--text-secondary)',
            }}
            onMouseEnter={e => {
              if ((e.currentTarget as HTMLButtonElement).disabled) return;
              const t = e.currentTarget as HTMLButtonElement;
              t.style.background = 'rgba(255,255,255,0.08)';
              t.style.borderColor = 'rgba(255,255,255,0.15)';
              t.style.color = 'var(--text-secondary)';
            }}
            onMouseLeave={e => {
              const t = e.currentTarget as HTMLButtonElement;
              t.style.background = 'rgba(255,255,255,0.04)';
              t.style.borderColor = 'rgba(255,255,255,0.08)';
              t.style.color = 'var(--text-secondary)';
            }}
          >
            {isSaveAs
              ? <Save size={14} strokeWidth={1.5} aria-hidden="true" />
              : <FolderOpen size={14} strokeWidth={1.5} aria-hidden="true" />}
            {loadingVersionId != null ? 'Loading…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );

  const modals = (
    <>
      {showDeleteModal && selectedStrategy && (
        <DeleteStrategyModal
          strategy={selectedStrategy}
          versions={versions}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setShowDeleteModal(false)}
        />
      )}
      {showDupModal && selectedStrategy && (
        <DuplicateStrategyModal
          strategy={selectedStrategy}
          onConfirm={handleDuplicateConfirm}
          onCancel={() => setShowDupModal(false)}
        />
      )}
    </>
  );

  if (standalone) {
    return <>{contentBox}{modals}</>;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="strategy-browser-title"
      className="fixed inset-y-0 right-0 z-50 flex items-stretch"
      style={{ left: 'var(--sidebar-width, 0px)' }}
      onKeyDown={handleKeyDown}
    >
      <div className="absolute inset-0 bg-black/70 cursor-pointer" onClick={onClose} />
      {contentBox}
      {modals}
    </div>
  );
}

'use client';

import { useState, useCallback, useMemo, useRef, useEffect, type CSSProperties } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Strategy, StrategyStatus, StrategyVersion, Block, BlockType } from '@/lib/strategy-builder/types';
import {
  enableStrategy, disableStrategy, deleteStrategyScoped, duplicateStrategyScoped,
  createStrategy, listStrategies, getStrategyVersions,
} from '@/lib/strategy-builder/api';
import { DeleteStrategyModal, DeleteScope } from './DeleteStrategyModal';
import { DuplicateStrategyModal, DuplicateScope } from './DuplicateStrategyModal';

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<StrategyStatus, CSSProperties> = {
  draft:      { color: 'var(--text-muted)',   background: 'var(--bg-card)',           borderColor: 'var(--border)' },
  valid:      { color: 'var(--accent-green)', background: 'var(--accent-green-dark)',  borderColor: 'var(--accent-green-mid)' },
  invalid:    { color: 'var(--accent-red)',   background: 'var(--accent-red-deeper)',  borderColor: 'var(--accent-red-dark)' },
  backtested: { color: 'var(--accent-blue)',  background: 'var(--accent-blue-dark)',   borderColor: 'var(--accent-blue-mid)' },
  active:     { color: 'var(--accent-teal)',  background: 'var(--accent-teal-dark)',   borderColor: 'var(--accent-teal-mid)' },
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
  if (pts >= 6) return { label: 'Excellent', color: 'var(--accent-green)' };
  if (pts >= 4) return { label: 'Good',      color: 'var(--accent-blue)' };
  if (pts >= 2) return { label: 'Fair',      color: 'var(--accent-orange)' };
  return               { label: 'Poor',      color: 'var(--accent-red)' };
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SortHeader({
  label, col, active, dir, onClick,
}: { label: string; col: SortKey; active: SortKey; dir: SortDir; onClick: (c: SortKey) => void }) {
  const isActive = col === active;
  return (
    <th
      onClick={() => onClick(col)}
      className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide cursor-pointer whitespace-nowrap select-none"
      style={{ color: 'var(--text-secondary)' }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)'; }}
    >
      {label}
      {isActive && <span className="ml-1" style={{ color: 'var(--text-muted)' }}>{dir === 'asc' ? '▴' : '▾'}</span>}
    </th>
  );
}

function BlockHierarchyTree({ blocks }: { blocks: Block[] }) {
  if (blocks.length === 0) {
    return <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>No blocks configured</p>;
  }
  return (
    <div className="space-y-2 font-mono text-xs">
      {blocks.map((block, i) => {
        const signals = (block.data?.signals as Array<{ name: string; logic?: string }> | undefined) ?? [];
        const timing = block.data?.timingConstraint as { enabled?: boolean; maxCandles?: number } | undefined;
        const exits = (block.data?.exits as Array<{ signalName: string; percentage?: number }> | undefined) ?? [];
        return (
          <div key={block.id} className="space-y-0.5">
            <div style={{ color: 'var(--text-secondary)' }}>
              <span className="font-bold" style={{ color: 'var(--accent-blue)' }}>#{i + 1}</span>{' '}
              <span style={{ color: 'var(--text-primary)' }}>{BLOCK_TYPE_LABELS[block.type] ?? block.type}</span>
              {timing?.enabled && (
                <span className="ml-2" style={{ color: 'var(--accent-orange)' }}>⏱ {timing.maxCandles}c</span>
              )}
            </div>
            {signals.map((sig, si) => (
              <div key={si} className="ml-4" style={{ color: 'var(--text-secondary)' }}>
                └── <span style={{ color: sig.logic === 'OR' ? 'var(--accent-blue)' : 'var(--accent-green)' }}>
                  {sig.logic ?? 'AND'}
                </span>{' '}
                {sig.name}
              </div>
            ))}
            {exits.map((exit, ei) => (
              <div key={ei} className="ml-4" style={{ color: 'var(--accent-red)' }}>
                └── 🔴 {exit.signalName}{exit.percentage != null ? ` (${exit.percentage}%)` : ''}
              </div>
            ))}
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

  return (
    <div className="grid grid-cols-3 gap-4 p-4" style={{ borderTop: '1px solid var(--border)', background: 'var(--bg-deep)' }}>
      {/* Column 1: Strategy Info */}
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>📊 Strategy Info</p>
        <div className="space-y-1.5">
          <div>
            <p className="text-sm font-semibold leading-tight" style={{ color: 'var(--text-primary)' }}>{strategy.name}</p>
            {strategy.versionNumber != null && (
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                v{strategy.versionNumber}
                {strategy.versionId && (
                  <span className="ml-1 font-mono" style={{ color: 'var(--text-faintest)' }}>{strategy.versionId.slice(0, 8)}</span>
                )}
              </p>
            )}
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {strategy.blocks.length} block{strategy.blocks.length !== 1 ? 's' : ''} · {entryBlocks.length} entry · {exitBlocks.length} exit
            </p>
            {strategy.testCount != null && (
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Tests run: {strategy.testCount}</p>
            )}
          </div>
          {sType && (
            <p className="text-xs">
              {sType === 'bullish' ? <span style={{ color: 'var(--accent-green)' }}>🟢 Bullish</span> :
               sType === 'bearish' ? <span style={{ color: 'var(--accent-red)' }}>🔴 Bearish</span> :
               <span style={{ color: 'var(--text-muted)' }}>{sType}</span>}
            </p>
          )}
          {strategy.description && (
            <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{strategy.description}</p>
          )}
          <div className="text-xs space-y-0.5" style={{ color: 'var(--text-muted)' }}>
            <p>Created: {new Date(strategy.createdAt).toLocaleDateString()}</p>
            <p>Updated: {new Date(strategy.updatedAt).toLocaleDateString()}</p>
          </div>
          {strategy.tags && strategy.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {strategy.tags.map((tag) => (
                <span key={tag} className="px-1.5 py-0.5 rounded text-xs" style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>{tag}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Column 2: Configuration Hierarchy */}
      <div className="space-y-2 overflow-y-auto max-h-48">
        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>⚙️ Configuration</p>
        <BlockHierarchyTree blocks={strategy.blocks} />
      </div>

      {/* Column 3: Performance */}
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>📈 Performance</p>
        {!result ? (
          <p className="text-xs italic" style={{ color: 'var(--text-muted)' }}>No backtest results</p>
        ) : (
          <div className="space-y-2 text-xs">
            {quality && (
              <p className="font-semibold" style={{ color: quality.color }}>
                {quality.label} ({qScore}/7)
              </p>
            )}

            <div className="space-y-1">
              <p className="uppercase tracking-wide font-medium" style={{ color: 'var(--text-muted)' }}>Trade Stats</p>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5" style={{ color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Win Rate</span>
                <span style={{ color: result.winRate >= 0.5 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                  {(result.winRate * 100).toFixed(1)}%
                </span>
                <span style={{ color: 'var(--text-muted)' }}>Trades</span>
                <span>{result.totalTrades} ({result.winningTrades}W/{result.losingTrades}L)</span>
              </div>
            </div>

            <div className="space-y-1">
              <p className="uppercase tracking-wide font-medium" style={{ color: 'var(--text-muted)' }}>Returns</p>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5" style={{ color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Return</span>
                <span style={{ color: result.returnPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                  {result.returnPercentage >= 0 ? '+' : ''}{result.returnPercentage.toFixed(2)}%
                </span>
                <span style={{ color: 'var(--text-muted)' }}>Prof. Factor</span>
                <span style={{ color: result.profitFactor >= 1 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                  {result.profitFactor.toFixed(2)}
                </span>
              </div>
            </div>

            <div className="space-y-1">
              <p className="uppercase tracking-wide font-medium" style={{ color: 'var(--text-muted)' }}>Risk Metrics</p>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5" style={{ color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Sharpe</span>
                <span style={{ color: result.sharpeRatio >= 0.1 ? 'var(--accent-green)' : 'var(--accent-orange)' }}>
                  {result.sharpeRatio.toFixed(2)}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>Sortino</span>
                <span style={{ color: result.sortino_ratio >= 0.1 ? 'var(--accent-green)' : 'var(--accent-orange)' }}>
                  {result.sortino_ratio.toFixed(2)}
                </span>
                {result.calmar_ratio != null && (
                  <>
                    <span style={{ color: 'var(--text-muted)' }}>Calmar</span>
                    <span style={{ color: result.calmar_ratio >= 0.1 ? 'var(--accent-green)' : 'var(--accent-orange)' }}>
                      {result.calmar_ratio.toFixed(2)}
                    </span>
                  </>
                )}
                <span style={{ color: 'var(--text-muted)' }}>Max DD</span>
                <span style={{ color: 'var(--accent-orange)' }}>{result.maxDrawdown.toFixed(2)}%</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main dialog ───────────────────────────────────────────────────────────────

export interface StrategyBrowserDialogProps {
  open: boolean;
  onSelect: (strategy: Strategy) => void;
  onClose: () => void;
  mode?: 'open' | 'save_as';
}

export function StrategyBrowserDialog({ open, onSelect, onClose, mode = 'open' }: StrategyBrowserDialogProps) {
  const { strategyList } = useStrategyStore();
  const [searchText, setSearchText]   = useState('');
  const [typeFilter, setTypeFilter]   = useState<TypeFilter>('all');
  const [sortKey, setSortKey]         = useState<SortKey>('updated');
  const [sortDir, setSortDir]         = useState<SortDir>('desc');
  const [selectedId, setSelectedId]   = useState<string | null>(null);
  const [controlling, setControlling] = useState(false);
  const [controlMsg, setControlMsg]   = useState<string | null>(null);
  const [localList, setLocalList]     = useState<typeof strategyList | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showDupModal, setShowDupModal]       = useState(false);
  const [versions, setVersions]               = useState<StrategyVersion[]>([]);
  const importRef = useRef<HTMLInputElement>(null);

  // Splitter state: table flex-basis percentage
  const [splitPct, setSplitPct] = useState(60);
  const splitterRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const displayList = localList ?? strategyList;

  const refreshList = useCallback(async () => {
    try {
      const updated = await listStrategies();
      setLocalList(updated as typeof strategyList);
    } catch {
      setLocalList(null);
    }
  }, []);

  const selectedStrategy = useMemo(
    () => displayList.find((s) => s.id === selectedId) ?? null,
    [displayList, selectedId],
  );

  // Load versions when selection changes
  useEffect(() => {
    if (!selectedId) { setVersions([]); return; }
    getStrategyVersions(selectedId)
      .then((v) => setVersions((v as StrategyVersion[]) ?? []))
      .catch(() => setVersions([]));
  }, [selectedId]);

  // Drag-to-resize splitter
  const onSplitterMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    const container = splitterRef.current?.parentElement;
    if (!container) return;
    const startY = e.clientY;
    const startPct = splitPct;
    const totalH = container.getBoundingClientRect().height;
    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const delta = ev.clientY - startY;
      const newPct = Math.min(85, Math.max(25, startPct + (delta / totalH) * 100));
      setSplitPct(newPct);
    };
    const onUp = () => {
      dragging.current = false;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [splitPct]);

  const handleSort = useCallback((col: SortKey) => {
    setSortKey((prev) => {
      if (prev === col) setSortDir((d) => d === 'asc' ? 'desc' : 'asc');
      else setSortDir('asc');
      return col;
    });
  }, []);

  const filtered = useMemo(() => {
    let result = [...displayList];
    if (searchText) {
      const q = searchText.toLowerCase();
      result = result.filter((s) =>
        s.name.toLowerCase().includes(q) ||
        (s.description?.toLowerCase().includes(q) ?? false) ||
        s.blocks.some((b) => BLOCK_TYPE_LABELS[b.type]?.toLowerCase().includes(q)),
      );
    }
    if (typeFilter !== 'all') {
      result = result.filter((s) => {
        const t = s.strategyType ?? (s.settings as { strategyType?: string }).strategyType;
        return t === typeFilter;
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

  const handleEnable = useCallback(async () => {
    if (!selectedId) return;
    setControlling(true); setControlMsg(null);
    try { await enableStrategy(selectedId); setControlMsg('Strategy enabled'); await refreshList(); }
    catch { setControlMsg('Enable failed'); }
    finally { setControlling(false); }
  }, [selectedId, refreshList]);

  const handleDisable = useCallback(async () => {
    if (!selectedId) return;
    setControlling(true); setControlMsg(null);
    try { await disableStrategy(selectedId); setControlMsg('Strategy disabled'); await refreshList(); }
    catch { setControlMsg('Disable failed'); }
    finally { setControlling(false); }
  }, [selectedId, refreshList]);

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
      await duplicateStrategyScoped(selectedId, scope, newName);
      setControlMsg(scope === 'version' ? 'New version created' : 'Strategy duplicated');
      await refreshList();
    }
    catch { setControlMsg('Duplicate failed'); }
    finally { setControlling(false); }
  }, [selectedId, refreshList]);

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

  const handleSelect = useCallback(() => {
    if (selectedStrategy) { onSelect(selectedStrategy); onClose(); }
  }, [selectedStrategy, onSelect, onClose]);

  const handleRowDoubleClick = useCallback((s: Strategy) => {
    onSelect(s); onClose();
  }, [onSelect, onClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Enter' && selectedId) handleSelect();
    },
    [selectedId, onClose, handleSelect],
  );

  if (!open) return null;

  const isSaveAs = mode === 'save_as';
  const title = isSaveAs ? '💾 Save Strategy As' : '📚 Strategy Browser';
  const confirmLabel = isSaveAs ? 'Save Here' : 'Load Strategy';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="strategy-browser-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
      onKeyDown={handleKeyDown}
    >
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />

      <div
        className="relative w-full max-w-5xl rounded-lg shadow-2xl mx-4 flex flex-col max-h-[88vh]"
        style={{ border: '1px solid var(--border)', background: 'var(--bg-panel)' }}
      >

        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-3 flex-shrink-0"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          <h2 id="strategy-browser-title" className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            {title}
          </h2>
          <button
            onClick={onClose}
            className="text-lg transition-colors"
            aria-label="Close dialog"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)'; }}
          >✕</button>
        </div>

        {/* Filters + toolbar */}
        <div
          className="px-6 py-3 flex items-center gap-3 flex-shrink-0 flex-wrap"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          <input
            type="text"
            placeholder="Search strategies, blocks…"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="flex-1 min-w-48 px-3 py-1.5 rounded text-sm focus:outline-none"
            style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--input-text)' }}
          />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as TypeFilter)}
            className="px-2 py-1.5 rounded text-sm focus:outline-none"
            style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--input-text)' }}
          >
            <option value="all">All Types</option>
            <option value="bullish">🟢 Bullish</option>
            <option value="bearish">🔴 Bearish</option>
          </select>

          <span className="text-xs whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
            {filtered.length} strateg{filtered.length !== 1 ? 'ies' : 'y'}
          </span>

          {/* Import/Export — only in open mode */}
          {!isSaveAs && (
            <div className="flex items-center gap-1.5 ml-auto">
              <button
                onClick={handleExportJson}
                disabled={!selectedStrategy}
                title="Export selected strategy to JSON"
                className="px-2.5 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
                style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
              >
                📥 Export JSON
              </button>
              <label
                title="Import strategy from JSON file"
                className="px-2.5 py-1.5 rounded text-xs font-medium cursor-pointer transition-colors"
                style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLLabelElement).style.background = 'var(--bg-hover)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLLabelElement).style.background = 'var(--bg-card)'; }}
              >
                📤 Import JSON
                <input ref={importRef} type="file" accept=".json" className="hidden" onChange={handleImportJson} />
              </label>
            </div>
          )}
        </div>

        {/* Resizable table + details area */}
        <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
          {/* Table */}
          <div className="overflow-y-auto" style={{ flex: `0 0 ${splitPct}%` }}>
            <table className="w-full text-sm border-collapse">
              <thead className="sticky top-0 z-10" style={{ background: 'var(--bg-panel)', borderBottom: '1px solid var(--border)' }}>
                <tr>
                  <SortHeader label="Strategy Name" col="name"    active={sortKey} dir={sortDir} onClick={handleSort} />
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>Type</th>
                  <SortHeader label="Version"        col="version" active={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label="Last Modified"  col="updated" active={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label="Validation"     col="status"  active={sortKey} dir={sortDir} onClick={handleSort} />
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>Published</th>
                  {!isSaveAs && <th className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={isSaveAs ? 6 : 7} className="px-3 py-8 text-center text-sm italic" style={{ color: 'var(--text-muted)' }}>
                      {displayList.length === 0 ? 'No strategies yet' : 'No matching strategies'}
                    </td>
                  </tr>
                ) : (
                  filtered.map((strategy) => {
                    const isSelected = strategy.id === selectedId;
                    const sType = strategy.strategyType ?? (strategy.settings as { strategyType?: string }).strategyType;
                    const valStatus = strategy.validationStatus ??
                      (strategy.status === StrategyStatus.VALID ? 'Pass' :
                       strategy.status === StrategyStatus.INVALID ? 'Fail' : 'Un-Validated');
                    return (
                      <tr
                        key={strategy.id}
                        onClick={() => setSelectedId(strategy.id)}
                        onDoubleClick={() => handleRowDoubleClick(strategy)}
                        className={`border-b cursor-pointer transition-colors ${isSelected ? 'border-l-2' : ''}`}
                        style={{
                          borderColor: 'var(--border)',
                          ...(isSelected
                            ? { background: 'var(--accent-blue-dark)', borderLeftColor: 'var(--accent-blue)' }
                            : {}),
                        }}
                        onMouseEnter={!isSelected ? e => { (e.currentTarget as HTMLTableRowElement).style.background = 'var(--bg-hover)'; } : undefined}
                        onMouseLeave={!isSelected ? e => { (e.currentTarget as HTMLTableRowElement).style.background = ''; } : undefined}
                      >
                        <td className="px-3 py-2">
                          <span className="font-medium truncate block max-w-xs" style={{ color: 'var(--text-primary)' }} title={strategy.name}>
                            {strategy.name}
                          </span>
                          {strategy.description && (
                            <span className="text-xs block truncate max-w-xs" style={{ color: 'var(--text-muted)' }}>{strategy.description}</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-xs text-center">
                          {sType === 'bullish' ? <span style={{ color: 'var(--accent-green)' }}>🟢 Bullish</span> :
                           sType === 'bearish' ? <span style={{ color: 'var(--accent-red)' }}>🔴 Bearish</span> :
                           <span style={{ color: 'var(--text-muted)' }}>—</span>}
                        </td>
                        <td className="px-3 py-2 text-xs text-center" style={{ color: 'var(--text-secondary)' }}>
                          {strategy.versionNumber != null ? `v${strategy.versionNumber}` : '—'}
                        </td>
                        <td className="px-3 py-2 text-xs whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>
                          {new Date(strategy.updatedAt).toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' })}
                          {' '}
                          {new Date(strategy.updatedAt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="px-3 py-2">
                          <span className="text-xs px-2 py-0.5 rounded border" style={STATUS_STYLES[strategy.status] ?? { color: 'var(--text-muted)' }}>
                            {valStatus}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          {strategy.published ? (
                            <span className="text-xs px-2 py-0.5 rounded border" style={STATUS_STYLES.valid}>Published</span>
                          ) : (
                            <span className="text-xs px-2 py-0.5 rounded border" style={STATUS_STYLES.draft}>Draft</span>
                          )}
                        </td>
                        {!isSaveAs && (
                          <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => { setSelectedId(strategy.id); setShowDupModal(true); }}
                                disabled={controlling}
                                title="Duplicate"
                                className="px-2 py-1 rounded text-xs disabled:opacity-40 transition-colors"
                                style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
                                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
                              >
                                ⧉
                              </button>
                              <button
                                onClick={() => { setSelectedId(strategy.id); setShowDeleteModal(true); }}
                                disabled={controlling}
                                title="Delete"
                                className="px-2 py-1 rounded text-xs disabled:opacity-40 transition-colors"
                                style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
                                onMouseEnter={e => {
                                  const el = e.currentTarget as HTMLButtonElement;
                                  el.style.background = 'var(--accent-red-deeper)';
                                  el.style.color = 'var(--accent-red)';
                                  el.style.borderColor = 'var(--accent-red-dark)';
                                }}
                                onMouseLeave={e => {
                                  const el = e.currentTarget as HTMLButtonElement;
                                  el.style.background = 'var(--bg-card)';
                                  el.style.color = 'var(--text-secondary)';
                                  el.style.borderColor = 'var(--border)';
                                }}
                              >
                                🗑
                              </button>
                            </div>
                          </td>
                        )}
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
          <div className="overflow-y-auto" style={{ flex: `0 0 ${100 - splitPct}%` }}>
            {selectedStrategy ? (
              <DetailsPanel strategy={selectedStrategy} />
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
          <div className="flex items-center gap-2 flex-wrap">
            {!isSaveAs && selectedStrategy?.status === StrategyStatus.ACTIVE ? (
              <button
                onClick={handleDisable}
                disabled={controlling}
                className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-50 transition-colors"
                style={{ background: 'var(--accent-orange)', color: 'var(--btn-primary-text)', border: '1px solid var(--accent-orange)' }}
              >
                {controlling ? 'Working…' : 'Disable Strategy'}
              </button>
            ) : !isSaveAs && selectedStrategy && [StrategyStatus.VALID, StrategyStatus.BACKTESTED].includes(selectedStrategy.status) ? (
              <button
                onClick={handleEnable}
                disabled={controlling}
                className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-50 transition-colors"
                style={{ background: 'var(--accent-green)', color: 'var(--btn-primary-text)', border: '1px solid var(--accent-green)' }}
              >
                {controlling ? 'Working…' : 'Enable Strategy'}
              </button>
            ) : null}
            {controlMsg && <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{controlMsg}</span>}
          </div>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded text-sm font-medium transition-colors"
              style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-hover)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-card)'; }}
            >
              Cancel
            </button>
            <button
              onClick={handleSelect}
              disabled={!selectedId}
              className="px-4 py-1.5 rounded text-sm font-medium disabled:opacity-50 transition-colors"
              style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)', border: '1px solid var(--accent-blue)' }}
            >
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>

      {/* Delete modal */}
      {showDeleteModal && selectedStrategy && (
        <DeleteStrategyModal
          strategy={selectedStrategy}
          versions={versions}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setShowDeleteModal(false)}
        />
      )}

      {/* Duplicate modal */}
      {showDupModal && selectedStrategy && (
        <DuplicateStrategyModal
          strategy={selectedStrategy}
          onConfirm={handleDuplicateConfirm}
          onCancel={() => setShowDupModal(false)}
        />
      )}
    </div>
  );
}

'use client';

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Strategy, StrategyStatus, StrategyVersion, Block, BlockType } from '@/lib/strategy-builder/types';
import {
  enableStrategy, disableStrategy, deleteStrategyScoped, duplicateStrategyScoped,
  createStrategy, listStrategies, getStrategyVersions,
} from '@/lib/strategy-builder/api';
import { DeleteStrategyModal, DeleteScope } from './DeleteStrategyModal';
import { DuplicateStrategyModal, DuplicateScope } from './DuplicateStrategyModal';

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<StrategyStatus, string> = {
  draft:      'text-gray-400 bg-gray-800/50 border-gray-700',
  valid:      'text-emerald-400 bg-emerald-900/30 border-emerald-700',
  invalid:    'text-red-400 bg-red-900/30 border-red-700',
  backtested: 'text-blue-400 bg-blue-900/30 border-blue-700',
  active:     'text-purple-400 bg-purple-900/30 border-purple-700',
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
  if (pts >= 6) return { label: 'Excellent', color: 'text-emerald-400' };
  if (pts >= 4) return { label: 'Good', color: 'text-blue-400' };
  if (pts >= 2) return { label: 'Fair', color: 'text-amber-400' };
  return { label: 'Poor', color: 'text-red-400' };
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SortHeader({
  label, col, active, dir, onClick,
}: { label: string; col: SortKey; active: SortKey; dir: SortDir; onClick: (c: SortKey) => void }) {
  const isActive = col === active;
  return (
    <th
      onClick={() => onClick(col)}
      className="px-3 py-2 text-left text-xs font-medium text-zinc-400 uppercase tracking-wide cursor-pointer hover:text-zinc-200 whitespace-nowrap select-none"
    >
      {label}
      {isActive && <span className="ml-1 text-zinc-500">{dir === 'asc' ? '▴' : '▾'}</span>}
    </th>
  );
}

function BlockHierarchyTree({ blocks }: { blocks: Block[] }) {
  if (blocks.length === 0) {
    return <p className="text-xs text-zinc-600 italic">No blocks configured</p>;
  }
  return (
    <div className="space-y-2 font-mono text-xs">
      {blocks.map((block, i) => {
        const signals = (block.data?.signals as Array<{ name: string; logic?: string }> | undefined) ?? [];
        const timing = block.data?.timingConstraint as { enabled?: boolean; maxCandles?: number } | undefined;
        const exits = (block.data?.exits as Array<{ signalName: string; percentage?: number }> | undefined) ?? [];
        return (
          <div key={block.id} className="space-y-0.5">
            <div className="text-zinc-300">
              <span className="text-blue-400 font-bold">#{i + 1}</span>{' '}
              <span className="text-zinc-200">{BLOCK_TYPE_LABELS[block.type] ?? block.type}</span>
              {timing?.enabled && (
                <span className="text-amber-400 ml-2">⏱ {timing.maxCandles}c</span>
              )}
            </div>
            {signals.map((sig, si) => (
              <div key={si} className="ml-4 text-zinc-400">
                └── <span className={sig.logic === 'OR' ? 'text-blue-400' : 'text-emerald-400'}>
                  {sig.logic ?? 'AND'}
                </span>{' '}
                {sig.name}
              </div>
            ))}
            {exits.map((exit, ei) => (
              <div key={ei} className="ml-4 text-red-400">
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
    <div className="grid grid-cols-3 gap-4 p-4 border-t border-zinc-800 bg-zinc-950/60">
      {/* Column 1: Strategy Info */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">📊 Strategy Info</p>
        <div className="space-y-1.5">
          <div>
            <p className="text-sm font-semibold text-zinc-100 leading-tight">{strategy.name}</p>
            {strategy.versionNumber != null && (
              <p className="text-xs text-zinc-500 mt-0.5">
                v{strategy.versionNumber}
                {strategy.versionId && (
                  <span className="ml-1 font-mono text-zinc-700">{strategy.versionId.slice(0, 8)}</span>
                )}
              </p>
            )}
            <p className="text-xs text-zinc-500 mt-0.5">
              {strategy.blocks.length} block{strategy.blocks.length !== 1 ? 's' : ''} · {entryBlocks.length} entry · {exitBlocks.length} exit
            </p>
            {strategy.testCount != null && (
              <p className="text-xs text-zinc-600 mt-0.5">Tests run: {strategy.testCount}</p>
            )}
          </div>
          {sType && (
            <p className="text-xs">
              {sType === 'bullish' ? <span className="text-emerald-400">🟢 Bullish</span> :
               sType === 'bearish' ? <span className="text-red-400">🔴 Bearish</span> :
               <span className="text-zinc-500">{sType}</span>}
            </p>
          )}
          {strategy.description && (
            <p className="text-xs text-zinc-400 leading-relaxed">{strategy.description}</p>
          )}
          <div className="text-xs text-zinc-600 space-y-0.5">
            <p>Created: {new Date(strategy.createdAt).toLocaleDateString()}</p>
            <p>Updated: {new Date(strategy.updatedAt).toLocaleDateString()}</p>
          </div>
          {strategy.tags && strategy.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {strategy.tags.map((tag) => (
                <span key={tag} className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 text-xs border border-zinc-700">{tag}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Column 2: Configuration Hierarchy */}
      <div className="space-y-2 overflow-y-auto max-h-48">
        <p className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">⚙️ Configuration</p>
        <BlockHierarchyTree blocks={strategy.blocks} />
      </div>

      {/* Column 3: Performance */}
      <div className="space-y-2">
        <p className="text-xs font-semibold text-zinc-300 uppercase tracking-wide">📈 Performance</p>
        {!result ? (
          <p className="text-xs text-zinc-600 italic">No backtest results</p>
        ) : (
          <div className="space-y-2 text-xs">
            {quality && (
              <p className={`font-semibold ${quality.color}`}>
                {quality.label} ({qScore}/7)
              </p>
            )}

            <div className="space-y-1">
              <p className="text-zinc-500 uppercase tracking-wide font-medium">Trade Stats</p>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-zinc-300">
                <span className="text-zinc-500">Win Rate</span>
                <span className={result.winRate >= 0.5 ? 'text-emerald-400' : 'text-red-400'}>
                  {(result.winRate * 100).toFixed(1)}%
                </span>
                <span className="text-zinc-500">Trades</span>
                <span>{result.totalTrades} ({result.winningTrades}W/{result.losingTrades}L)</span>
              </div>
            </div>

            <div className="space-y-1">
              <p className="text-zinc-500 uppercase tracking-wide font-medium">Returns</p>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-zinc-300">
                <span className="text-zinc-500">Return</span>
                <span className={result.returnPercentage >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                  {result.returnPercentage >= 0 ? '+' : ''}{result.returnPercentage.toFixed(2)}%
                </span>
                <span className="text-zinc-500">Prof. Factor</span>
                <span className={result.profitFactor >= 1 ? 'text-emerald-400' : 'text-red-400'}>
                  {result.profitFactor.toFixed(2)}
                </span>
              </div>
            </div>

            <div className="space-y-1">
              <p className="text-zinc-500 uppercase tracking-wide font-medium">Risk Metrics</p>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-zinc-300">
                <span className="text-zinc-500">Sharpe</span>
                <span className={result.sharpeRatio >= 0.1 ? 'text-emerald-400' : 'text-amber-400'}>
                  {result.sharpeRatio.toFixed(2)}
                </span>
                <span className="text-zinc-500">Sortino</span>
                <span className={result.sortino_ratio >= 0.1 ? 'text-emerald-400' : 'text-amber-400'}>
                  {result.sortino_ratio.toFixed(2)}
                </span>
                {result.calmar_ratio != null && (
                  <>
                    <span className="text-zinc-500">Calmar</span>
                    <span className={result.calmar_ratio >= 0.1 ? 'text-emerald-400' : 'text-amber-400'}>
                      {result.calmar_ratio.toFixed(2)}
                    </span>
                  </>
                )}
                <span className="text-zinc-500">Max DD</span>
                <span className="text-amber-400">{result.maxDrawdown.toFixed(2)}%</span>
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

      <div className="relative w-full max-w-5xl rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl mx-4 flex flex-col max-h-[88vh]">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-zinc-800 flex-shrink-0">
          <h2 id="strategy-browser-title" className="text-sm font-semibold text-zinc-50">
            {title}
          </h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-lg" aria-label="Close dialog">✕</button>
        </div>

        {/* Filters + toolbar */}
        <div className="px-6 py-3 border-b border-zinc-800 flex items-center gap-3 flex-shrink-0 flex-wrap">
          <input
            type="text"
            placeholder="Search strategies, blocks…"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="flex-1 min-w-48 px-3 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
          />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as TypeFilter)}
            className="px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-300 focus:outline-none"
          >
            <option value="all">All Types</option>
            <option value="bullish">🟢 Bullish</option>
            <option value="bearish">🔴 Bearish</option>
          </select>

          <span className="text-xs text-zinc-500 whitespace-nowrap">
            {filtered.length} strateg{filtered.length !== 1 ? 'ies' : 'y'}
          </span>

          {/* Import/Export — only in open mode */}
          {!isSaveAs && (
            <div className="flex items-center gap-1.5 ml-auto">
              <button
                onClick={handleExportJson}
                disabled={!selectedStrategy}
                title="Export selected strategy to JSON"
                className="px-2.5 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 text-xs font-medium disabled:opacity-40 transition-colors"
              >
                📥 Export JSON
              </button>
              <label
                title="Import strategy from JSON file"
                className="px-2.5 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 text-xs font-medium cursor-pointer transition-colors"
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
              <thead className="sticky top-0 bg-zinc-900 border-b border-zinc-800 z-10">
                <tr>
                  <SortHeader label="Strategy Name" col="name"    active={sortKey} dir={sortDir} onClick={handleSort} />
                  <th className="px-3 py-2 text-left text-xs font-medium text-zinc-400 uppercase tracking-wide whitespace-nowrap">Type</th>
                  <SortHeader label="Version"        col="version" active={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label="Last Modified"  col="updated" active={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label="Validation"     col="status"  active={sortKey} dir={sortDir} onClick={handleSort} />
                  <th className="px-3 py-2 text-left text-xs font-medium text-zinc-400 uppercase tracking-wide whitespace-nowrap">Published</th>
                  {!isSaveAs && <th className="px-3 py-2 text-left text-xs font-medium text-zinc-400 uppercase tracking-wide">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={isSaveAs ? 6 : 7} className="px-3 py-8 text-center text-sm text-zinc-500 italic">
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
                        className={`border-b border-zinc-800/60 cursor-pointer transition-colors ${
                          isSelected ? 'bg-blue-500/10 border-l-2 border-l-blue-500' : 'hover:bg-zinc-800/50'
                        }`}
                      >
                        <td className="px-3 py-2">
                          <span className="font-medium text-zinc-100 truncate block max-w-xs" title={strategy.name}>
                            {strategy.name}
                          </span>
                          {strategy.description && (
                            <span className="text-xs text-zinc-500 block truncate max-w-xs">{strategy.description}</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-xs text-center">
                          {sType === 'bullish' ? <span className="text-emerald-400">🟢 Bullish</span> :
                           sType === 'bearish' ? <span className="text-red-400">🔴 Bearish</span> :
                           <span className="text-zinc-600">—</span>}
                        </td>
                        <td className="px-3 py-2 text-xs text-zinc-400 text-center">
                          {strategy.versionNumber != null ? `v${strategy.versionNumber}` : '—'}
                        </td>
                        <td className="px-3 py-2 text-xs text-zinc-400 whitespace-nowrap">
                          {new Date(strategy.updatedAt).toLocaleDateString('en-US', { year: 'numeric', month: '2-digit', day: '2-digit' })}
                          {' '}
                          {new Date(strategy.updatedAt).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="px-3 py-2">
                          <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_COLORS[strategy.status] ?? 'text-zinc-400'}`}>
                            {valStatus}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          {strategy.published ? (
                            <span className="text-xs px-2 py-0.5 rounded border text-emerald-400 bg-emerald-900/30 border-emerald-700">Published</span>
                          ) : (
                            <span className="text-xs px-2 py-0.5 rounded border text-gray-400 bg-gray-800/50 border-gray-700">Draft</span>
                          )}
                        </td>
                        {!isSaveAs && (
                          <td className="px-3 py-2" onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => { setSelectedId(strategy.id); setShowDupModal(true); }}
                                disabled={controlling}
                                title="Duplicate"
                                className="px-2 py-1 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-300 text-xs disabled:opacity-40 transition-colors"
                              >
                                ⧉
                              </button>
                              <button
                                onClick={() => { setSelectedId(strategy.id); setShowDeleteModal(true); }}
                                disabled={controlling}
                                title="Delete"
                                className="px-2 py-1 rounded bg-zinc-700 hover:bg-red-900 text-zinc-400 hover:text-red-300 text-xs disabled:opacity-40 transition-colors"
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
            className="flex-shrink-0 flex items-center justify-center h-2 bg-zinc-800 hover:bg-zinc-700 cursor-row-resize select-none border-y border-zinc-700/50 transition-colors"
            title="Drag to resize"
          >
            <span className="text-zinc-600 text-xs tracking-widest select-none">⋯</span>
          </div>

          {/* Details panel */}
          <div className="overflow-y-auto" style={{ flex: `0 0 ${100 - splitPct}%` }}>
            {selectedStrategy ? (
              <DetailsPanel strategy={selectedStrategy} />
            ) : (
              <div className="flex items-center justify-center h-full text-xs text-zinc-600 italic py-8">
                Select a strategy to view details
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-3 px-6 py-3 border-t border-zinc-800 flex-shrink-0">
          <div className="flex items-center gap-2 flex-wrap">
            {!isSaveAs && selectedStrategy?.status === StrategyStatus.ACTIVE ? (
              <button
                onClick={handleDisable}
                disabled={controlling}
                className="px-3 py-1.5 rounded bg-amber-700 hover:bg-amber-600 text-white text-xs font-medium disabled:opacity-50 transition-colors"
              >
                {controlling ? 'Working…' : 'Disable Strategy'}
              </button>
            ) : !isSaveAs && selectedStrategy && [StrategyStatus.VALID, StrategyStatus.BACKTESTED].includes(selectedStrategy.status) ? (
              <button
                onClick={handleEnable}
                disabled={controlling}
                className="px-3 py-1.5 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-medium disabled:opacity-50 transition-colors"
              >
                {controlling ? 'Working…' : 'Enable Strategy'}
              </button>
            ) : null}
            {controlMsg && <span className="text-xs text-zinc-400">{controlMsg}</span>}
          </div>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-sm font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSelect}
              disabled={!selectedId}
              className="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium disabled:opacity-50 transition-colors"
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

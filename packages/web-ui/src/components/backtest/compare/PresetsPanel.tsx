'use client';

import { useState, useCallback } from 'react';
import { ChevronDown, ChevronUp, Search, Trash2, Download, X, Tag, FolderOpen } from 'lucide-react';
import type { BacktestRunRecord } from '@/lib/strategy-builder/types';
import { loadPresets, deletePreset, updatePreset, listGroups, listTags, type ConfigPreset } from '@/lib/config-presets';

interface PresetsPanelProps {
  onLoadPreset: (record: BacktestRunRecord) => void;
}

function presetToRunRecord(preset: ConfigPreset): BacktestRunRecord {
  const fc = preset.fullConfig;
  const m = preset.metrics;
  return {
    runId: preset.id,
    strategyId: '',
    strategyName: preset.strategyName ?? '',
    savedAt: preset.savedAt,
    config: {
      startDate: fc.startDate,
      endDate: fc.endDate,
      initialCapital: fc.initialCapital,
      commissionPercentage: fc.commissionPercentage,
      slippagePercentage: fc.slippagePercentage,
      maxConcurrentPositions: fc.maxConcurrentPositions,
      timeframe: fc.timeframe,
    },
    fullConfig: fc,
    result: {
      id: preset.id,
      strategyId: '',
      runId: preset.id,
      status: 'completed',
      startDate: fc.startDate,
      endDate: fc.endDate,
      initialCapital: m.initialCapital,
      finalCapital: m.finalCapital,
      totalTrades: m.totalTrades,
      winningTrades: Math.round(m.totalTrades * m.winRate),
      losingTrades: Math.round(m.totalTrades * (1 - m.winRate)),
      winRate: m.winRate,
      totalReturn: m.finalCapital - m.initialCapital,
      returnPercentage: m.returnPercentage,
      maxDrawdown: m.maxDrawdown,
      sharpeRatio: m.sharpeRatio,
      sortino_ratio: 0,
      profitFactor: m.profitFactor,
      averageWin: 0,
      averageLoss: 0,
      createdAt: preset.savedAt,
    },
  };
}

function fmtPct(n: number) {
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`;
}

interface PresetCardProps {
  preset: ConfigPreset;
  onLoad: () => void;
  onDelete: () => void;
  onRename: (name: string, group: string) => void;
}

function PresetCard({ preset, onLoad, onDelete, onRename }: PresetCardProps) {
  const [editing, setEditing] = useState(false);
  const [nameVal, setNameVal] = useState(preset.name);
  const [groupVal, setGroupVal] = useState(preset.group);

  function commitEdit() {
    onRename(nameVal, groupVal);
    setEditing(false);
  }

  const m = preset.metrics;
  const returnColor = m.returnPercentage >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';

  return (
    <div
      className="rounded px-3 py-2 flex flex-col gap-1.5"
      style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
    >
      {/* Name row */}
      <div className="flex items-center gap-2 min-w-0">
        {editing ? (
          <div className="flex-1 flex flex-col gap-1 min-w-0">
            <input
              autoFocus
              value={nameVal}
              onChange={e => setNameVal(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditing(false); }}
              className="w-full rounded px-1.5 py-0.5 text-xs focus:outline-none"
              style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              placeholder="Preset name"
            />
            <div className="flex items-center gap-1">
              <FolderOpen size={10} style={{ color: 'var(--text-faint)', flexShrink: 0 }} />
              <input
                value={groupVal}
                onChange={e => setGroupVal(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') commitEdit(); if (e.key === 'Escape') setEditing(false); }}
                className="flex-1 rounded px-1.5 py-0.5 text-xs focus:outline-none"
                style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                placeholder="Group (optional)"
              />
              <button
                onClick={commitEdit}
                className="text-[10px] px-1.5 py-0.5 rounded"
                style={{ background: 'var(--accent-blue)', color: '#fff', border: 'none' }}
              >
                Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="text-[10px] px-1 py-0.5 rounded"
                style={{ color: 'var(--text-muted)', border: '1px solid var(--border)' }}
              >
                <X size={10} />
              </button>
            </div>
          </div>
        ) : (
          <>
            <button
              onClick={() => setEditing(true)}
              className="flex-1 text-left min-w-0"
              title="Click to rename"
            >
              <span className="text-xs font-semibold truncate block" style={{ color: 'var(--text-secondary)' }}>
                {preset.name}
              </span>
              {preset.group && (
                <span className="text-[10px] truncate block" style={{ color: 'var(--text-faint)' }}>
                  {preset.group}
                </span>
              )}
            </button>
            <button
              onClick={onLoad}
              className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded flex-shrink-0"
              title="Load this preset into Config"
              style={{ color: 'var(--accent-blue)', border: '1px solid rgba(46,140,255,0.35)', background: 'rgba(46,140,255,0.08)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(46,140,255,0.18)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'rgba(46,140,255,0.08)')}
            >
              <Download size={9} />Load
            </button>
            <button
              onClick={onDelete}
              className="p-0.5 rounded flex-shrink-0"
              title="Delete preset"
              style={{ color: 'var(--text-faint)' }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent-red)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-faint)')}
            >
              <Trash2 size={11} />
            </button>
          </>
        )}
      </div>

      {/* Metrics row */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs font-bold tabular-nums" style={{ color: returnColor }}>
          {fmtPct(m.returnPercentage)}
        </span>
        <span className="text-[10px] tabular-nums" style={{ color: 'var(--text-muted)' }}>
          WR {(m.winRate * 100).toFixed(1)}%
        </span>
        <span className="text-[10px] tabular-nums" style={{ color: 'var(--text-muted)' }}>
          {m.totalTrades} trades
        </span>
        <span className="text-[10px] tabular-nums" style={{ color: 'var(--accent-orange, #f97316)' }}>
          DD {(m.maxDrawdown * 100).toFixed(1)}%
        </span>
      </div>

      {/* Tags */}
      {preset.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {preset.tags.map(t => (
            <span
              key={t}
              className="flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full"
              style={{ background: 'rgba(46,140,255,0.08)', color: 'var(--accent-blue)', border: '1px solid rgba(46,140,255,0.2)' }}
            >
              <Tag size={8} />{t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function PresetsPanel({ onLoadPreset }: PresetsPanelProps) {
  const [expanded, setExpanded] = useState(true);
  const [search, setSearch] = useState('');
  const [groupFilter, setGroupFilter] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [, forceUpdate] = useState(0);

  const refresh = useCallback(() => forceUpdate(n => n + 1), []);

  const presets = loadPresets();
  if (presets.length === 0) return null;

  const groups = listGroups(presets);
  const tags = listTags(presets);

  const filtered = presets.filter(p => {
    if (search && !p.name.toLowerCase().includes(search.toLowerCase()) && !p.group.toLowerCase().includes(search.toLowerCase())) return false;
    if (groupFilter && p.group !== groupFilter) return false;
    if (tagFilter && !p.tags.includes(tagFilter)) return false;
    return true;
  });

  const grouped = new Map<string, ConfigPreset[]>();
  for (const p of filtered) {
    const key = p.group || '';
    const arr = grouped.get(key) ?? [];
    arr.push(p);
    grouped.set(key, arr);
  }

  const sortedGroupKeys = Array.from(grouped.keys()).sort((a, b) => {
    if (a === '') return 1;
    if (b === '') return -1;
    return a.localeCompare(b);
  });

  return (
    <div className="mb-2 flex-shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
      {/* Header */}
      <button
        className="w-full flex items-center justify-between px-2 py-1.5"
        onClick={() => setExpanded(v => !v)}
        style={{ color: 'var(--text-muted)' }}
      >
        <span className="text-xs font-semibold" style={{ color: 'var(--text-secondary)' }}>
          Saved presets <span style={{ color: 'var(--text-faint)', fontWeight: 400 }}>({presets.length})</span>
        </span>
        {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {expanded && (
        <div className="px-2 pb-2 space-y-2">
          {/* Filters */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative flex-1 min-w-[120px]">
              <Search size={11} className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-faint)' }} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full rounded pl-6 pr-2 py-1 text-xs focus:outline-none"
                style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
                placeholder="Search presets…"
              />
            </div>
            {groups.length > 0 && (
              <select
                value={groupFilter}
                onChange={e => setGroupFilter(e.target.value)}
                className="rounded px-1.5 py-1 text-xs focus:outline-none"
                style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              >
                <option value="">All groups</option>
                {groups.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            )}
            {tags.length > 0 && (
              <select
                value={tagFilter}
                onChange={e => setTagFilter(e.target.value)}
                className="rounded px-1.5 py-1 text-xs focus:outline-none"
                style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
              >
                <option value="">All tags</option>
                {tags.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            )}
          </div>

          {/* Preset cards grouped */}
          {filtered.length === 0 ? (
            <p className="text-xs py-2 text-center" style={{ color: 'var(--text-faint)' }}>
              No presets match the filter
            </p>
          ) : (
            <div className="space-y-3 max-h-64 overflow-y-auto pr-0.5">
              {sortedGroupKeys.map(groupKey => (
                <div key={groupKey || '__ungrouped__'}>
                  {groupKey && (
                    <div className="flex items-center gap-1 mb-1 px-0.5">
                      <FolderOpen size={10} style={{ color: 'var(--text-faint)' }} />
                      <span className="text-[10px] font-medium uppercase tracking-wide" style={{ color: 'var(--text-faint)' }}>
                        {groupKey}
                      </span>
                    </div>
                  )}
                  <div className="grid gap-1.5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
                    {(grouped.get(groupKey) ?? []).map(preset => (
                      <PresetCard
                        key={preset.id}
                        preset={preset}
                        onLoad={() => onLoadPreset(presetToRunRecord(preset))}
                        onDelete={() => { deletePreset(preset.id); refresh(); }}
                        onRename={(name, group) => { updatePreset(preset.id, { name, group }); refresh(); }}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

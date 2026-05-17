'use client';

import { useState, useCallback, useMemo } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Strategy, StrategyStatus } from '@/lib/strategy-builder/types';
import { InfoTooltip } from './InfoTooltip';
import { enableStrategy, disableStrategy } from '@/lib/strategy-builder/api';

const STATUS_COLORS: Record<StrategyStatus, string> = {
  draft: 'text-gray-400',
  valid: 'text-emerald-400',
  invalid: 'text-red-400',
  backtested: 'text-blue-400',
  active: 'text-purple-400',
};

export interface StrategyBrowserDialogProps {
  open: boolean;
  onSelect: (strategy: Strategy) => void;
  onClose: () => void;
}

export function StrategyBrowserDialog({ open, onSelect, onClose }: StrategyBrowserDialogProps) {
  const { strategyList } = useStrategyStore();
  const [searchText, setSearchText] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'updated' | 'status'>('updated');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [controlling, setControlling] = useState(false);
  const [controlMsg, setControlMsg] = useState<string | null>(null);

  const selectedStrategy = useMemo(
    () => strategyList.find((s) => s.id === selectedId) ?? null,
    [strategyList, selectedId],
  );

  const handleEnable = useCallback(async () => {
    if (!selectedId) return;
    setControlling(true);
    setControlMsg(null);
    try {
      await enableStrategy(selectedId);
      setControlMsg('Strategy enabled');
    } catch {
      setControlMsg('Enable failed');
    } finally {
      setControlling(false);
    }
  }, [selectedId]);

  const handleDisable = useCallback(async () => {
    if (!selectedId) return;
    setControlling(true);
    setControlMsg(null);
    try {
      await disableStrategy(selectedId);
      setControlMsg('Strategy disabled');
    } catch {
      setControlMsg('Disable failed');
    } finally {
      setControlling(false);
    }
  }, [selectedId]);

  const filtered = useMemo(() => {
    let result = [...strategyList];

    if (searchText) {
      const q = searchText.toLowerCase();
      result = result.filter((s) =>
        s.name.toLowerCase().includes(q) ||
        (s.description?.toLowerCase().includes(q) ?? false),
      );
    }

    if (sortBy === 'name') result.sort((a, b) => a.name.localeCompare(b.name));
    else if (sortBy === 'updated') result.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
    else if (sortBy === 'status') result.sort((a, b) => a.status.localeCompare(b.status));

    return result;
  }, [strategyList, searchText, sortBy]);

  const handleSelect = useCallback(() => {
    const selected = strategyList.find((s) => s.id === selectedId);
    if (selected) {
      onSelect(selected);
      onClose();
    }
  }, [selectedId, strategyList, onSelect, onClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Enter' && selectedId) handleSelect();
    },
    [selectedId, onClose, handleSelect],
  );

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="strategy-browser-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
      onKeyDown={handleKeyDown}
    >
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative w-full max-w-2xl rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl mx-4 flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 flex-shrink-0">
          <h2 id="strategy-browser-title" className="text-base font-semibold text-zinc-50">
            📚 Strategy Library
          </h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-lg" aria-label="Close dialog">
            ✕
          </button>
        </div>

        {/* Filters */}
        <div className="px-6 py-3 border-b border-zinc-800 space-y-2 flex-shrink-0">
          <InfoTooltip id="strategy-search-input">
            <input
              type="text"
              placeholder="Search strategies…"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="w-full px-3 py-2 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500"
            />
          </InfoTooltip>

          <InfoTooltip id="strategy-sort-select">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'name' | 'updated' | 'status')}
              className="w-full px-3 py-2 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-300 focus:outline-none"
            >
              <option value="updated">Sort by: Recently Updated</option>
              <option value="name">Sort by: Name</option>
              <option value="status">Sort by: Status</option>
            </select>
          </InfoTooltip>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          {filtered.length === 0 ? (
            <div className="text-center py-8 text-zinc-500">
              {strategyList.length === 0 ? 'No strategies yet' : 'No matching strategies'}
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map((strategy) => (
                <button
                  key={strategy.id}
                  onClick={() => setSelectedId(strategy.id)}
                  className={`w-full text-left px-4 py-3 rounded border transition-colors ${
                    selectedId === strategy.id
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-zinc-700 hover:border-zinc-600 bg-zinc-800/50'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-zinc-100 truncate">{strategy.name}</h3>
                      {strategy.description && (
                        <p className="text-xs text-zinc-400 mt-0.5 line-clamp-2">{strategy.description}</p>
                      )}
                      <div className="text-xs text-zinc-500 mt-2 flex gap-3">
                        <span>{strategy.blocks.length} block{strategy.blocks.length !== 1 ? 's' : ''}</span>
                        <span>•</span>
                        <span>{new Date(strategy.updatedAt).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <span className={`text-xs font-medium whitespace-nowrap ${STATUS_COLORS[strategy.status]}`}>
                      {strategy.status.charAt(0).toUpperCase() + strategy.status.slice(1)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between gap-2 px-6 py-4 border-t border-zinc-800 flex-shrink-0">
          <div className="flex items-center gap-2">
            {selectedStrategy?.status === StrategyStatus.ACTIVE ? (
              <InfoTooltip id="strategy-browser-disable-btn">
                <button
                  onClick={handleDisable}
                  disabled={controlling}
                  className="px-4 py-2 rounded bg-amber-700 hover:bg-amber-600 text-white text-sm font-medium disabled:opacity-50 transition-colors"
                >
                  {controlling ? 'Working…' : 'Disable Strategy'}
                </button>
              </InfoTooltip>
            ) : selectedStrategy && [StrategyStatus.VALID, StrategyStatus.BACKTESTED].includes(selectedStrategy.status) ? (
              <InfoTooltip id="strategy-browser-enable-btn">
                <button
                  onClick={handleEnable}
                  disabled={controlling}
                  className="px-4 py-2 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-medium disabled:opacity-50 transition-colors"
                >
                  {controlling ? 'Working…' : 'Enable Strategy'}
                </button>
              </InfoTooltip>
            ) : null}
            {controlMsg && (
              <span className="text-xs text-zinc-400">{controlMsg}</span>
            )}
          </div>

          <div className="flex gap-2">
            <InfoTooltip id="strategy-browser-cancel-btn">
              <button
                onClick={onClose}
                className="px-4 py-2 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </InfoTooltip>
            <InfoTooltip id="strategy-browser-select-btn">
              <button
                onClick={handleSelect}
                disabled={!selectedId}
                className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium disabled:opacity-50 transition-colors"
              >
                Load Strategy
              </button>
            </InfoTooltip>
          </div>
        </div>
      </div>
    </div>
  );
}

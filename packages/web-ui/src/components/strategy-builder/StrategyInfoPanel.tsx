'use client';

import { useCallback, useMemo, useState } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block } from '@/lib/strategy-builder/types';

const STRATEGY_TYPES = ['Bullish', 'Bearish', 'Required', 'Optional', 'Rethemed'] as const;
type StrategyType = typeof STRATEGY_TYPES[number];

const TYPE_STYLES: Record<StrategyType, string> = {
  Bullish:  'bg-emerald-900 text-emerald-300 border-emerald-700',
  Bearish:  'bg-red-900 text-red-300 border-red-700',
  Required: 'bg-amber-900 text-amber-300 border-amber-700',
  Optional: 'bg-blue-900 text-blue-300 border-blue-700',
  Rethemed: 'bg-purple-900 text-purple-300 border-purple-700',
};

const TYPE_INACTIVE = 'bg-zinc-800 text-zinc-500 border-zinc-700 hover:border-zinc-500 hover:text-zinc-300';

interface SignalSummary {
  required: number;
  optional: number;
  exits: number;
  rechecked: number;
}

function computeSignalSummary(blocks: Block[]): SignalSummary {
  let required = 0, optional = 0, exits = 0, rechecked = 0;
  for (const block of blocks) {
    const logic = (block.data.logic as string | undefined) ?? 'AND';
    const signals = (block.data.signals as Array<Record<string, unknown>> | undefined) ?? [];
    if (block.type === 'exit_condition') {
      exits += signals.length || 1;
    } else if (logic === 'OR') {
      optional += signals.length || 1;
    } else {
      required += signals.length || 1;
    }
    for (const sig of signals) {
      const rc = sig.recheck_config as Record<string, unknown> | undefined;
      if (rc?.enabled) rechecked++;
    }
  }
  return { required, optional, exits, rechecked };
}

function stripVersionSuffix(name: string): string {
  return name.replace(/\s*\(v\d+\)\s*$/, '').trim();
}

export interface StrategyInfoPanelProps {
  compact?: boolean;
}

export function StrategyInfoPanel({ compact = false }: StrategyInfoPanelProps) {
  const { currentStrategy, setCurrentStrategy, saveStrategy } = useStrategyStore();
  const [descOpen, setDescOpen] = useState(!compact);

  const handleNameChange = useCallback(
    (name: string) => {
      if (!currentStrategy || name === currentStrategy.name) return;
      const clean = stripVersionSuffix(name);
      setCurrentStrategy({ ...currentStrategy, name: clean });
      saveStrategy().catch(console.error);
    },
    [currentStrategy, setCurrentStrategy, saveStrategy]
  );

  const handleDescChange = useCallback(
    (description: string) => {
      if (!currentStrategy) return;
      setCurrentStrategy({ ...currentStrategy, description });
    },
    [currentStrategy, setCurrentStrategy]
  );

  const handleTypeChange = useCallback(
    (type: StrategyType) => {
      if (!currentStrategy) return;
      setCurrentStrategy({ ...currentStrategy, strategyType: type });
      saveStrategy().catch(console.error);
    },
    [currentStrategy, setCurrentStrategy, saveStrategy]
  );

  const summary = useMemo(
    () => (currentStrategy ? computeSignalSummary(currentStrategy.blocks) : null),
    [currentStrategy]
  );

  if (!currentStrategy) {
    return (
      <div className="px-4 py-3 text-xs text-zinc-500">
        No strategy loaded
      </div>
    );
  }

  const currentType = (currentStrategy.strategyType as StrategyType | undefined) ?? 'Bullish';

  const summaryText = summary
    ? [
        summary.required > 0 && `${summary.required} required`,
        summary.optional > 0 && `${summary.optional} optional`,
        summary.exits > 0 && `${summary.exits} exit`,
        summary.rechecked > 0 && `${summary.rechecked} rechecked`,
      ]
        .filter(Boolean)
        .join(', ') || 'No signals configured'
    : '';

  if (compact) {
    return (
      <div className="bg-zinc-900 px-4 py-3 space-y-3">
        {/* Title row */}
        <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Strategy Information
        </div>

        {/* Name */}
        <div className="space-y-1">
          <label className="text-xs text-zinc-500">Strategy Name</label>
          <input
            type="text"
            key={currentStrategy.name}
            defaultValue={currentStrategy.name}
            onBlur={e => handleNameChange(e.target.value)}
            maxLength={100}
            className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
            placeholder="Strategy name…"
          />
        </div>

        {/* Description (collapsible in compact mode) */}
        <div className="space-y-1">
          <button
            className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300"
            onClick={() => setDescOpen(v => !v)}
          >
            <span>{descOpen ? '▾' : '▸'}</span>
            <span>Description</span>
          </button>
          {descOpen && (
            <textarea
              rows={3}
              value={currentStrategy.description ?? ''}
              onChange={e => handleDescChange(e.target.value)}
              onBlur={() => saveStrategy().catch(console.error)}
              placeholder="Strategy description…"
              className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 resize-none focus:outline-none focus:border-zinc-500 leading-relaxed"
            />
          )}
        </div>

        {/* Strategy Type */}
        <div className="space-y-1.5">
          <label className="text-xs text-zinc-500">Strategy Type</label>
          <div className="flex flex-wrap gap-1.5">
            {STRATEGY_TYPES.map(type => (
              <button
                key={type}
                onClick={() => handleTypeChange(type)}
                className={`px-2 py-0.5 rounded text-xs font-medium border transition-colors ${
                  currentType === type ? TYPE_STYLES[type] : TYPE_INACTIVE
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        {/* Signal summary */}
        {summary && (
          <div className="text-xs text-zinc-500 italic border-t border-zinc-800 pt-2">
            {summaryText || 'No signals configured'}
          </div>
        )}
      </div>
    );
  }

  // Full (non-compact) version for standalone use
  return (
    <div className="flex flex-col h-full bg-zinc-900 border-l border-zinc-800">
      <div className="px-4 py-3 border-b border-zinc-800 flex-shrink-0">
        <h2 className="text-sm font-semibold text-zinc-50">Strategy Information</h2>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        <div className="space-y-1">
          <label className="text-xs text-zinc-500">Strategy Name</label>
          <input
            type="text"
            key={currentStrategy.name}
            defaultValue={currentStrategy.name}
            onBlur={e => handleNameChange(e.target.value)}
            maxLength={100}
            className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs text-zinc-500">Description</label>
          <textarea
            rows={4}
            value={currentStrategy.description ?? ''}
            onChange={e => handleDescChange(e.target.value)}
            onBlur={() => saveStrategy().catch(console.error)}
            placeholder="Strategy description…"
            className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 resize-none focus:outline-none focus:border-zinc-500 leading-relaxed"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs text-zinc-500">Strategy Type</label>
          <div className="flex flex-wrap gap-1.5">
            {STRATEGY_TYPES.map(type => (
              <button
                key={type}
                onClick={() => handleTypeChange(type)}
                className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
                  currentType === type ? TYPE_STYLES[type] : TYPE_INACTIVE
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        {summary && (
          <div className="space-y-1">
            <label className="text-xs text-zinc-500">Signal Summary</label>
            <p className="text-xs text-zinc-400 leading-relaxed">
              {summaryText || 'No signals configured'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

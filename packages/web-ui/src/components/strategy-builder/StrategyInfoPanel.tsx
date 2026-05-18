'use client';

import { useCallback, useMemo } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block, BlockType } from '@/lib/strategy-builder/types';

interface BlockStats {
  required: number;
  optional: number;
  exits: number;
  rechecked: number;
  timeConstrained: number;
  reqSignals: number;
  optSignals: number;
}

function computeStats(blocks: Block[]): BlockStats {
  let required = 0, optional = 0, exits = 0, rechecked = 0, timeConstrained = 0;
  let reqSignals = 0, optSignals = 0;
  for (const block of blocks) {
    const logic = (block.data.logic as string | undefined) ?? 'AND';
    const signals = (block.data.signals as Array<Record<string, unknown>> | undefined) ?? [];
    if (block.type === BlockType.EXIT_CONDITION || logic === 'EXIT') {
      exits++;
    } else if (logic === 'OR') {
      optional++;
      optSignals += signals.length || 1;
    } else {
      required++;
      reqSignals += signals.length || 1;
    }
    for (const sig of signals) {
      const rc = sig.recheck_config as Record<string, unknown> | undefined;
      if (sig.recheckEnabled || rc?.enabled) rechecked++;
      if (sig.timing_constraint) timeConstrained++;
    }
  }
  return { required, optional, exits, rechecked, timeConstrained, reqSignals, optSignals };
}

function generateDescription(blocks: Block[]): string {
  if (blocks.length === 0) {
    return 'Description will be auto-generated when you add building blocks...\n\nExample:\nMoving Average crossover with momentum confirmation. Entry on golden cross with volume confirmation within 5 candles...';
  }
  const required = blocks.filter(b => (b.data.logic as string) !== 'OR' && b.type !== BlockType.EXIT_CONDITION);
  const optional = blocks.filter(b => (b.data.logic as string) === 'OR');
  const exits = blocks.filter(b => b.type === BlockType.EXIT_CONDITION);
  const parts: string[] = [];
  if (required.length > 0) {
    const names = required.map(b => (b.data.name as string) || b.type).slice(0, 3).join(', ');
    parts.push(`Entry requires: ${names}${required.length > 3 ? ` +${required.length - 3} more` : ''}`);
  }
  if (optional.length > 0) {
    const names = optional.map(b => (b.data.name as string) || b.type).slice(0, 2).join(', ');
    parts.push(`Optional boosters: ${names}${optional.length > 2 ? ` +${optional.length - 2} more` : ''}`);
  }
  if (exits.length > 0) {
    parts.push(`${exits.length} exit condition(s) configured`);
  }
  return parts.join('.\n') + '.';
}

export interface StrategyInfoPanelProps {
  compact?: boolean;
}

export function StrategyInfoPanel({ compact: _compact = false }: StrategyInfoPanelProps) {
  const { currentStrategy, setCurrentStrategy, saveStrategy } = useStrategyStore();

  const stats = useMemo(
    () => (currentStrategy ? computeStats(currentStrategy.blocks) : null),
    [currentStrategy]
  );

  const autoDescription = useMemo(
    () => (currentStrategy ? generateDescription(currentStrategy.blocks) : ''),
    [currentStrategy]
  );

  const descLabel = useMemo(() => {
    if (!stats || !currentStrategy) return '';
    const blockCount = currentStrategy.blocks.length;
    const totalSigs = stats.reqSignals + stats.optSignals;
    return `${blockCount} block(s) (${stats.required} required, ${stats.optional} optional), ${totalSigs} signal(s) (${stats.reqSignals} required, ${stats.optSignals} optional)`;
  }, [stats, currentStrategy]);

  const handleNameChange = useCallback(
    (name: string) => {
      if (!currentStrategy || name === currentStrategy.name) return;
      const clean = name.replace(/\s*\(v\d+\)\s*$/, '').trim();
      if (!clean) return;
      setCurrentStrategy({ ...currentStrategy, name: clean });
      saveStrategy().catch(console.error);
    },
    [currentStrategy, setCurrentStrategy, saveStrategy]
  );

  const handleTypeChange = useCallback(
    (type: 'Bullish' | 'Bearish') => {
      if (!currentStrategy) return;
      setCurrentStrategy({ ...currentStrategy, strategyType: type });
      saveStrategy().catch(console.error);
    },
    [currentStrategy, setCurrentStrategy, saveStrategy]
  );

  if (!currentStrategy) {
    return (
      <div className="bg-zinc-900 px-4 py-3 space-y-2">
        <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          💡 Strategy Information
        </div>
        <div className="text-xs text-zinc-600 italic">No strategy loaded</div>
      </div>
    );
  }

  const currentType = (currentStrategy.strategyType as string | undefined) ?? 'Bullish';

  return (
    <div className="bg-zinc-900 px-4 py-3 space-y-2.5">
      {/* Section header */}
      <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
        💡 Strategy Information
      </div>

      {/* Strategy Name */}
      <div className="space-y-1">
        <label className="text-xs text-zinc-500">Strategy Name:</label>
        <input
          type="text"
          key={currentStrategy.id}
          defaultValue={currentStrategy.name}
          onBlur={e => handleNameChange(e.target.value)}
          placeholder="e.g., Example_MA_Crossover"
          maxLength={100}
          className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
        />
      </div>

      {/* Description (auto-generated, read-only) */}
      <div className="space-y-1">
        <label className="text-xs text-zinc-500">
          Description:
          {descLabel && <span className="ml-1 text-zinc-600 font-normal">{descLabel}.</span>}
        </label>
        <textarea
          rows={5}
          value={autoDescription}
          readOnly
          className="w-full px-2 py-1.5 rounded bg-zinc-800/40 border border-zinc-700/60 text-xs text-zinc-500 resize-none focus:outline-none leading-relaxed cursor-default select-none"
          style={{ scrollbarWidth: 'thin' as const, scrollbarColor: '#52525b #18181b' }}
        />
      </div>

      {/* Strategy Type + Meta stats — all inline */}
      <div className="flex items-center gap-2 flex-wrap text-xs">
        <span className="text-zinc-500 flex-shrink-0">Strategy Type:</span>
        {(['Bullish', 'Bearish'] as const).map(type => (
          <button
            key={type}
            onClick={() => handleTypeChange(type)}
            className={`px-3 py-0.5 rounded text-xs font-medium border transition-colors ${
              currentType === type
                ? type === 'Bullish'
                  ? 'bg-emerald-900 text-emerald-300 border-emerald-700'
                  : 'bg-red-900 text-red-300 border-red-700'
                : 'bg-zinc-800 text-zinc-500 border-zinc-700 hover:border-zinc-500 hover:text-zinc-300'
            }`}
          >
            {type}
          </button>
        ))}
        {stats && (
          <>
            <span className="text-zinc-600 mx-0.5">|</span>
            <span className="text-zinc-500">Required:</span>
            <span className={`font-bold ${stats.required > 0 ? 'text-emerald-400' : 'text-zinc-400'}`}>{stats.required}</span>
            <span className="text-zinc-600">|</span>
            <span className="text-zinc-500">Optional:</span>
            <span className={`font-bold ${stats.optional > 0 ? 'text-blue-400' : 'text-zinc-400'}`}>{stats.optional}</span>
            <span className="text-zinc-600">|</span>
            <span className="text-zinc-500">Rechecked:</span>
            <span className={`font-bold ${stats.rechecked > 0 ? 'text-amber-400' : 'text-zinc-400'}`}>{stats.rechecked}</span>
            <span className="text-zinc-600">|</span>
            <span className="text-zinc-500">Exit Conditions:</span>
            <span className={`font-bold ${stats.exits > 0 ? 'text-red-400' : 'text-zinc-400'}`}>{stats.exits}</span>
            <span className="text-zinc-600">|</span>
            <span className="text-zinc-500">Time Constraint:</span>
            <span className={`font-bold ${stats.timeConstrained > 0 ? 'text-emerald-400' : 'text-zinc-400'}`}>
              {stats.timeConstrained > 0 ? 'Yes' : 'No'}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

'use client';

import { useCallback, useMemo } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block, BlockType } from '@/lib/strategy-builder/types';
import { RichTooltip, TooltipContent } from './RichTooltip';

const TT_STRATEGY_NAME: TooltipContent = {
  title: 'Strategy Name',
  body: 'The unique identifier for this strategy used in backtest results, reports, and version history.',
  sections: [
    { header: 'Behaviour:', items: [
      'Auto-saved when you click away (on blur)',
      'Version suffixes like "(v2)" are automatically stripped to avoid accidental duplicates',
      'Names must be non-empty after stripping whitespace',
    ]},
    { header: 'Best practice:', items: ['Use descriptive names that reflect the core logic, e.g. "EMA_Crossover_RSI_Confirm"'] },
  ],
};
const TT_DESCRIPTION: TooltipContent = {
  title: 'Auto-Generated Description',
  body: 'A read-only summary of the strategy\'s current building blocks, logic roles, and exit conditions.',
  sections: [
    { header: 'Updates automatically:', items: [
      'Rebuilds every time blocks are added, removed, or reordered',
      'Shows required blocks, optional boosters, and exit count',
    ]},
    { header: 'Note:', items: ['This field cannot be edited directly — it reflects the live strategy state'] },
  ],
};
const TT_BULLISH: TooltipContent = {
  title: 'Bullish Strategy Direction',
  body: 'Sets the directional bias to LONG — the strategy only enters buy positions.',
  sections: [
    { header: 'In backtesting:', items: [
      'Only upward price movements are analysed for entry triggers',
      'Entry signals fire when bullish conditions are met from the building blocks',
    ]},
    { header: 'Use for:', items: ['Trend-following long strategies, breakout longs, accumulation setups'] },
  ],
};
const TT_BEARISH: TooltipContent = {
  title: 'Bearish Strategy Direction',
  body: 'Sets the directional bias to SHORT — the strategy only enters sell/short positions.',
  sections: [
    { header: 'In backtesting:', items: [
      'Only downward price movements are analysed for entry triggers',
      'Entry signals fire when bearish conditions are met from the building blocks',
    ]},
    { header: 'Use for:', items: ['Short-selling strategies, distribution setups, counter-trend fades'] },
  ],
};
const TT_STAT_REQUIRED: TooltipContent = {
  title: 'Required Blocks (AND)',
  body: 'Count of AND-logic blocks that must all confirm simultaneously for an entry signal to fire.',
  sections: [
    { header: 'How AND works:', items: [
      'Every required block must pass before the strategy generates an entry',
      'Evaluated in order — a failed required block short-circuits the rest',
      'Higher required count = stricter confirmation = fewer but higher-quality entries',
    ]},
  ],
};
const TT_STAT_OPTIONAL: TooltipContent = {
  title: 'Optional Blocks (OR)',
  body: 'Count of OR-logic blocks where at least one must confirm (in addition to all required blocks).',
  sections: [
    { header: 'How OR works:', items: [
      'Only one OR block needs to fire for the optional condition to be satisfied',
      'Used for supporting confluence that strengthens the entry without being mandatory',
      'Zero optional blocks means the strategy uses required blocks only',
    ]},
  ],
};
const TT_STAT_RECHECKED: TooltipContent = {
  title: 'RECHECK-Validated Signals',
  body: 'Number of individual signals with RECHECK validation enabled across all blocks.',
  sections: [
    { header: 'What RECHECK does:', items: [
      'Requires the signal to reoccur within N bars of its initial fire',
      'Filters out single-bar noise and stale signals',
      'WITHIN mode: reoccurs anywhere in N bars; AT mode: reoccurs at exactly bar N',
    ]},
  ],
};
const TT_STAT_EXITS: TooltipContent = {
  title: 'Exit Conditions Count',
  body: 'Total number of exit condition blocks across all binding levels (Strategy, Block, Signal).',
  sections: [
    { header: 'Binding levels:', items: [
      'Strategy — applies to all positions regardless of which block triggered entry',
      'Block — applies only to positions where this block provided the entry signal',
      'Signal — applies only to positions triggered by one specific signal output',
    ]},
    { header: 'Tip:', items: ['Use multiple binding levels to create tiered exit strategies'] },
  ],
};
const TT_STAT_TIMING: TooltipContent = {
  title: 'Timing-Constrained Signals',
  body: 'Whether any signals have timing constraints linking them to prior block signals.',
  sections: [
    { header: 'What timing constraints do:', items: [
      'Require a reference signal from a prior block to have fired within N candles',
      'Enforce sequential confirmation — e.g. pattern must appear within 5 bars of a BOS break',
      'Prevents entry when required sequential conditions occur too far apart',
    ]},
    { header: 'Configure via:', items: ['The ⚙ Config button on each block card'] },
  ],
};

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

function blockLabel(b: Block): string {
  const name = (b.data.name as string) || b.type;
  const signals = (b.data.signals as Array<Record<string, unknown>> | undefined) ?? [];
  return signals.length > 0 ? `${name} (${signals.length} signal${signals.length > 1 ? 's' : ''})` : name;
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
    const labels = required.map(blockLabel).slice(0, 4);
    const overflow = required.length > 4 ? ` +${required.length - 4} more` : '';
    parts.push(`Entry fires when ALL confirm (AND): ${labels.join(', ')}${overflow}`);
  }

  if (optional.length > 0) {
    const labels = optional.map(blockLabel).slice(0, 3);
    const overflow = optional.length > 3 ? ` +${optional.length - 3} more` : '';
    parts.push(`Optional boosters (any 1 of): ${labels.join(', ')}${overflow}`);
  }

  if (exits.length > 0) {
    parts.push(`${exits.length} exit condition${exits.length > 1 ? 's' : ''} protecting open positions`);
  } else {
    parts.push('No exit conditions configured — manual exits only');
  }

  // Recheck / timing extras
  let recheckCount = 0, timingCount = 0;
  for (const block of [...required, ...optional]) {
    const signals = (block.data.signals as Array<Record<string, unknown>> | undefined) ?? [];
    for (const sig of signals) {
      const rc = sig.recheck_config as Record<string, unknown> | undefined;
      if (sig.recheckEnabled || rc?.enabled) recheckCount++;
      if (sig.timing_constraint) timingCount++;
    }
  }
  const extras: string[] = [];
  if (recheckCount > 0) extras.push(`${recheckCount} RECHECK-validated signal${recheckCount > 1 ? 's' : ''}`);
  if (timingCount > 0) extras.push(`${timingCount} timing-constrained signal${timingCount > 1 ? 's' : ''}`);
  if (extras.length > 0) parts.push(extras.join(', '));

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
    const entryBlocks = stats.required + stats.optional;
    const totalSigs = stats.reqSignals + stats.optSignals;
    const exitPart = stats.exits > 0 ? `, ${stats.exits} exit condition(s)` : '';
    return `${entryBlocks} entry block(s) (${stats.required} required, ${stats.optional} optional)${exitPart}, ${totalSigs} signal(s)`;
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
      <div className="px-4 py-3 space-y-2" style={{ background: '#1E2128' }}>
        <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#9AA0A6' }}>
          💡 Strategy Information
        </div>
        <div className="text-xs italic" style={{ color: '#6B7280' }}>No strategy loaded</div>
      </div>
    );
  }

  const currentType = (currentStrategy.strategyType as string | undefined) ?? 'Bullish';

  return (
    <div className="px-4 py-3 space-y-2.5" style={{ background: '#1E2128' }}>
      {/* Section header */}
      <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#9AA0A6' }}>
        💡 Strategy Information
      </div>

      {/* Strategy Name */}
      <div className="space-y-1">
        <label className="text-xs" style={{ color: '#9AA0A6' }}>Strategy Name:</label>
        <RichTooltip content={TT_STRATEGY_NAME}>
          <input
            type="text"
            key={currentStrategy.id}
            defaultValue={currentStrategy.name}
            onBlur={e => handleNameChange(e.target.value)}
            placeholder="e.g., Example_MA_Crossover"
            maxLength={100}
            className="w-full px-2 py-1.5 rounded border text-sm focus:outline-none"
            style={{ background: '#2A2F3A', borderColor: '#3C4149', color: '#E8EAED' }}
          />
        </RichTooltip>
      </div>

      {/* Description (auto-generated, read-only) */}
      <div className="space-y-1">
        <label className="text-xs" style={{ color: '#9AA0A6' }}>
          Description:
          {descLabel && <span className="ml-1 font-normal" style={{ color: '#6B7280' }}>{descLabel}.</span>}
        </label>
        <RichTooltip content={TT_DESCRIPTION}>
          <textarea
            rows={5}
            value={autoDescription}
            readOnly
            className="w-full px-2 py-1.5 rounded border text-xs resize-none focus:outline-none leading-relaxed cursor-default select-none"
            style={{
              background: 'rgba(42,47,58,0.4)',
              borderColor: 'rgba(60,65,73,0.6)',
              color: '#9AA0A6',
              scrollbarWidth: 'thin' as const,
              scrollbarColor: '#3C4149 #1E2128',
            }}
          />
        </RichTooltip>
      </div>

      {/* Strategy Type + Meta stats — all inline */}
      <div className="flex items-center gap-2 flex-wrap text-xs">
        <span className="flex-shrink-0" style={{ color: '#9AA0A6' }}>Strategy Type:</span>
        {(['Bullish', 'Bearish'] as const).map(type => (
          <RichTooltip key={type} content={type === 'Bullish' ? TT_BULLISH : TT_BEARISH}>
            <button
              onClick={() => handleTypeChange(type)}
              className={`px-3 py-0.5 rounded text-xs font-medium border transition-colors ${
                currentType === type
                  ? type === 'Bullish'
                    ? 'bg-emerald-900 text-emerald-300 border-emerald-700'
                    : 'bg-red-900 text-red-300 border-red-700'
                  : 'border-[#3C4149] hover:border-[#9AA0A6] hover:text-[#A0AEC0]'
              }`}
              style={currentType !== type ? { background: '#2A2F3A', color: '#9AA0A6' } : undefined}
            >
              {type}
            </button>
          </RichTooltip>
        ))}
        {stats && (
          <>
            <span className="mx-0.5" style={{ color: '#9AA0A6' }}>|</span>
            <RichTooltip content={TT_STAT_REQUIRED}>
              <span style={{ color: '#A0AEC0', cursor: 'default' }}>Required: <span className="font-bold" style={{ color: '#10B981' }}>{stats.required}</span></span>
            </RichTooltip>
            <span style={{ color: '#9AA0A6' }}>|</span>
            <RichTooltip content={TT_STAT_OPTIONAL}>
              <span style={{ color: '#A0AEC0', cursor: 'default' }}>Optional: <span className="font-bold" style={{ color: '#2070FF' }}>{stats.optional}</span></span>
            </RichTooltip>
            <span style={{ color: '#9AA0A6' }}>|</span>
            <RichTooltip content={TT_STAT_RECHECKED}>
              <span style={{ color: '#A0AEC0', cursor: 'default' }}>Rechecked: <span className="font-bold" style={{ color: '#FFA500' }}>{stats.rechecked}</span></span>
            </RichTooltip>
            <span style={{ color: '#9AA0A6' }}>|</span>
            <RichTooltip content={TT_STAT_EXITS}>
              <span style={{ color: '#A0AEC0', cursor: 'default' }}>Exit Conditions: <span className="font-bold" style={{ color: '#C35252' }}>{stats.exits}</span></span>
            </RichTooltip>
            <span style={{ color: '#9AA0A6' }}>|</span>
            <RichTooltip content={TT_STAT_TIMING}>
              <span style={{ color: '#A0AEC0', cursor: 'default' }}>Time Constraint: <span className="font-bold" style={{ color: '#E8EAED' }}>{stats.timeConstrained > 0 ? 'Yes' : 'No'}</span></span>
            </RichTooltip>
          </>
        )}
      </div>
    </div>
  );
}

'use client';

import { useCallback, useMemo } from 'react';
import { Info } from 'lucide-react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block, BlockType } from '@/lib/strategy-builder/types';
import { RichTooltip, TooltipContent } from './RichTooltip';

// Stable id so File > New Strategy (BTCAAAAA-30520) can focus the Name input
// after clearing the form, regardless of compact vs full panel rendering.
export const STRATEGY_NAME_INPUT_ID = 'strategy-name-input';

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

export function StrategyInfoPanel({ compact = false }: StrategyInfoPanelProps) {
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
    return `${entryBlocks} block(s) (${stats.required} required, ${stats.optional} optional)${exitPart}, ${totalSigs} signal(s) (${stats.reqSignals} required, ${stats.optSignals} optional)`;
  }, [stats, currentStrategy]);

  const handleNameChange = useCallback(
    (name: string) => {
      if (!currentStrategy || name === currentStrategy.name) return;
      const clean = name.replace(/\s*\(v\d+\)\s*$/, '').trim();
      if (!clean) return;
      setCurrentStrategy({ ...currentStrategy, name: clean });
      // Auto-save renames for local-only drafts (id is a Date.now() string).
      // For backend-loaded strategies (id starts with "strategy_") the
      // rename is staged only — Save in the toolbar then surfaces the
      // "Rename existing vs Save as new strategy" modal so the user picks
      // the destination explicitly (BTCAAAAA-30023 board feedback).
      const id = currentStrategy.id as unknown as string;
      if (typeof id !== 'string' || !id.startsWith('strategy_')) {
        saveStrategy().catch(console.error);
      }
    },
    [currentStrategy, setCurrentStrategy, saveStrategy]
  );

  const handleTypeChange = useCallback(
    (type: 'Bullish' | 'Bearish') => {
      if (!currentStrategy) return;
      setCurrentStrategy({ ...currentStrategy, strategyType: type });
      // Local-draft autosave only; backend strategies wait for explicit Save
      // so the rename-disambiguation modal can fire on the bundled change.
      const id = currentStrategy.id as unknown as string;
      if (typeof id !== 'string' || !id.startsWith('strategy_')) {
        saveStrategy().catch(console.error);
      }
    },
    [currentStrategy, setCurrentStrategy, saveStrategy]
  );

  const currentType = (currentStrategy?.strategyType as string | undefined) ?? 'Bullish';

  const statsRow = stats && (
    <>
      <span style={{ color: 'var(--text-muted)' }}>|</span>
      <RichTooltip content={TT_STAT_REQUIRED}>
        <span style={{ color: 'var(--text-dim)', cursor: 'default' }}>Required: <span className="font-bold" style={{ color: 'var(--accent-green)' }}>{stats.required}</span></span>
      </RichTooltip>
      <span style={{ color: 'var(--text-muted)' }}>|</span>
      <RichTooltip content={TT_STAT_OPTIONAL}>
        <span style={{ color: 'var(--text-dim)', cursor: 'default' }}>Optional: <span className="font-bold" style={{ color: 'var(--accent-blue-alt)' }}>{stats.optional}</span></span>
      </RichTooltip>
      <span style={{ color: 'var(--text-muted)' }}>|</span>
      <RichTooltip content={TT_STAT_RECHECKED}>
        <span style={{ color: 'var(--text-dim)', cursor: 'default' }}>Rechecked: <span className="font-bold" style={{ color: 'var(--accent-orange)' }}>{stats.rechecked}</span></span>
      </RichTooltip>
      <span style={{ color: 'var(--text-muted)' }}>|</span>
      <RichTooltip content={TT_STAT_EXITS}>
        <span style={{ color: 'var(--text-dim)', cursor: 'default' }}>Exit Conditions: <span className="font-bold" style={{ color: 'var(--accent-red)' }}>{stats.exits}</span></span>
      </RichTooltip>
      <span style={{ color: 'var(--text-muted)' }}>|</span>
      <RichTooltip content={TT_STAT_TIMING}>
        <span style={{ color: 'var(--text-dim)', cursor: 'default' }}>Time Constraint: <span className="font-bold" style={{ color: 'var(--text-primary)' }}>{stats.timeConstrained > 0 ? 'Yes' : 'No'}</span></span>
      </RichTooltip>
    </>
  );

  if (!currentStrategy) {
    return (
      <div className="px-4 py-3 space-y-2" style={{ background: 'var(--bg-panel)' }}>
        <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
          Strategy Information
        </div>
        <div className="text-xs italic" style={{ color: 'var(--text-muted)' }}>No strategy loaded</div>
      </div>
    );
  }

  /* ── Compact mode: used when embedded in toolbar strip ────────────────── */
  if (compact) {
    return (
      <div className="px-3 py-1.5 space-y-1" style={{ background: 'var(--bg-deep)' }}>
        {/* Row 1: header label + name input side-by-side */}
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-widest flex-shrink-0" style={{ color: 'var(--text-muted)' }}>
            <Info size={10} />
            Strategy Information
          </span>
          <RichTooltip content={TT_STRATEGY_NAME}>
            <input
              type="text"
              id={STRATEGY_NAME_INPUT_ID}
              key={currentStrategy.id}
              defaultValue={currentStrategy.name}
              onBlur={e => handleNameChange(e.target.value)}
              placeholder="Untitled"
              maxLength={100}
              className="px-1.5 py-0.5 rounded border text-xs focus:outline-none min-w-0 flex-1"
              style={{
                background: 'rgba(255,255,255,0.04)',
                borderColor: 'rgba(255,255,255,0.08)',
                color: 'var(--text-secondary)',
              }}
            />
          </RichTooltip>
        </div>

        {/* Row 2: description stats label */}
        <RichTooltip content={TT_DESCRIPTION}>
          <p className="text-[10px] leading-tight cursor-default" style={{ color: 'var(--text-muted)' }}>
            {`Description: ${descLabel ? `${descLabel}.` : autoDescription.split('\n')[0]}`}
          </p>
        </RichTooltip>

        {/* Row 2b: full auto-description in bordered box */}
        <div
          className="rounded text-[10px] px-2 py-1.5 leading-relaxed whitespace-pre-line"
          style={{ color: 'var(--text-muted)', border: '1px solid var(--border)', background: 'rgba(255,255,255,0.02)' }}
        >
          {autoDescription}
        </div>

        {/* Row 3: type buttons + stats */}
        <div className="flex items-center gap-1.5 text-[10px] overflow-hidden flex-nowrap">
          <span className="flex-shrink-0" style={{ color: 'var(--text-secondary)' }}>Strategy Type:</span>
          {(['Bullish', 'Bearish'] as const).map(type => (
            <RichTooltip key={type} content={type === 'Bullish' ? TT_BULLISH : TT_BEARISH}>
              <button
                onClick={() => handleTypeChange(type)}
                className="px-2 py-0 rounded text-[10px] font-medium border transition-colors leading-[18px]"
                style={currentType === type
                  ? type === 'Bullish'
                    ? { background: 'var(--accent-green-dark)', color: 'var(--accent-green)', borderColor: 'var(--accent-green-mid)' }
                    : { background: 'var(--accent-red-deeper)', color: 'var(--accent-red)', borderColor: 'var(--accent-red-dark)' }
                  : { background: 'rgba(255,255,255,0.04)', color: 'var(--text-secondary)', borderColor: 'rgba(255,255,255,0.08)' }
                }
              >
                {type}
              </button>
            </RichTooltip>
          ))}
          {statsRow}
        </div>
      </div>
    );
  }

  /* ── Full mode ────────────────────────────────────────────────────────── */
  return (
    <div className="px-4 py-3 space-y-2.5" style={{ background: 'var(--bg-panel)' }}>
      {/* Section header */}
      <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
        <Info size={12} />
        Strategy Information
      </div>

      {/* Strategy Name */}
      <div className="space-y-1">
        <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>Strategy Name:</label>
        <RichTooltip content={TT_STRATEGY_NAME}>
          <input
            type="text"
            id={STRATEGY_NAME_INPUT_ID}
            key={currentStrategy.id}
            defaultValue={currentStrategy.name}
            onBlur={e => handleNameChange(e.target.value)}
            placeholder="e.g., Example_MA_Crossover"
            maxLength={100}
            className="w-full px-2 py-1.5 rounded border text-sm focus:outline-none"
            style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
          />
        </RichTooltip>
      </div>

      {/* Description (auto-generated, read-only) */}
      <div className="space-y-1">
        <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>Description:</label>
        <RichTooltip content={TT_DESCRIPTION}>
          <p
            className="text-xs leading-relaxed whitespace-pre-line cursor-default"
            style={{ color: 'var(--text-muted)' }}
          >
            {autoDescription}
          </p>
        </RichTooltip>
      </div>

      {/* Strategy Type + Meta stats — no-wrap; clips rather than wraps when panel is narrow */}
      <div className="flex items-center gap-2 text-xs overflow-hidden" style={{ flexWrap: 'nowrap' }}>
        <span className="flex-shrink-0" style={{ color: 'var(--text-secondary)' }}>Strategy Type:</span>
        {(['Bullish', 'Bearish'] as const).map(type => (
          <RichTooltip key={type} content={type === 'Bullish' ? TT_BULLISH : TT_BEARISH}>
            <button
              onClick={() => handleTypeChange(type)}
              className="px-3 py-0.5 rounded text-xs font-medium border transition-colors"
              style={currentType === type
                ? type === 'Bullish'
                  ? { background: 'var(--accent-green-dark)', color: 'var(--accent-green)', borderColor: 'var(--accent-green-mid)' }
                  : { background: 'var(--accent-red-deeper)', color: 'var(--accent-red)', borderColor: 'var(--accent-red-dark)' }
                : { background: 'var(--bg-card)', color: 'var(--text-secondary)', borderColor: 'var(--border)' }
              }
            >
              {type}
            </button>
          </RichTooltip>
        ))}
        {stats && (
          <>
            <span className="mx-0.5" style={{ color: 'var(--text-secondary)' }}>|</span>
            <RichTooltip content={TT_STAT_REQUIRED}>
              <span style={{ color: 'var(--text-dim)', cursor: 'default' }}>Required: <span className="font-bold" style={{ color: 'var(--accent-green)' }}>{stats.required}</span></span>
            </RichTooltip>
            <span style={{ color: 'var(--text-secondary)' }}>|</span>
            <RichTooltip content={TT_STAT_OPTIONAL}>
              <span style={{ color: 'var(--text-dim)', cursor: 'default' }}>Optional: <span className="font-bold" style={{ color: 'var(--accent-blue-alt)' }}>{stats.optional}</span></span>
            </RichTooltip>
            <span style={{ color: 'var(--text-secondary)' }}>|</span>
            <RichTooltip content={TT_STAT_RECHECKED}>
              <span style={{ color: 'var(--text-dim)', cursor: 'default' }}>Rechecked: <span className="font-bold" style={{ color: 'var(--accent-orange)' }}>{stats.rechecked}</span></span>
            </RichTooltip>
            <span style={{ color: 'var(--text-secondary)' }}>|</span>
            <RichTooltip content={TT_STAT_EXITS}>
              <span style={{ color: 'var(--text-dim)', cursor: 'default' }}>Exit Conditions: <span className="font-bold" style={{ color: 'var(--accent-red)' }}>{stats.exits}</span></span>
            </RichTooltip>
            <span style={{ color: 'var(--text-secondary)' }}>|</span>
            <RichTooltip content={TT_STAT_TIMING}>
              <span style={{ color: 'var(--text-dim)', cursor: 'default' }}>Time Constraint: <span className="font-bold" style={{ color: 'var(--text-primary)' }}>{stats.timeConstrained > 0 ? 'Yes' : 'No'}</span></span>
            </RichTooltip>
          </>
        )}
      </div>
    </div>
  );
}

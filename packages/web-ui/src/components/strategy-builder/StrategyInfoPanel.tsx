'use client';

import { useCallback, useMemo } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { Block, StrategyStatus } from '@/lib/strategy-builder/types';
import { InfoTooltip } from './InfoTooltip';

const STATUS_BADGE: Record<StrategyStatus, { label: string; classes: string }> = {
  [StrategyStatus.DRAFT]:      { label: 'Draft',      classes: 'bg-zinc-800 text-zinc-400 border-zinc-700' },
  [StrategyStatus.VALID]:      { label: 'Valid',       classes: 'bg-emerald-950 text-emerald-400 border-emerald-800' },
  [StrategyStatus.INVALID]:    { label: 'Invalid',     classes: 'bg-red-950 text-red-400 border-red-800' },
  [StrategyStatus.BACKTESTED]: { label: 'Backtested',  classes: 'bg-blue-950 text-blue-400 border-blue-800' },
  [StrategyStatus.ACTIVE]:     { label: 'Active',      classes: 'bg-purple-950 text-purple-400 border-purple-800' },
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs text-zinc-500 font-medium uppercase tracking-wide">{label}</dt>
      <dd className="text-sm text-zinc-100">{children}</dd>
    </div>
  );
}

interface SignalCounts {
  required: number;
  optional: number;
  rechecked: number;
  exits: number;
}

function computeSignalCounts(blocks: Block[]): SignalCounts {
  let required = 0;
  let optional = 0;
  let rechecked = 0;
  let exits = 0;

  for (const block of blocks) {
    const logic = (block.data.logic as string | undefined) ?? 'AND';
    const signals = (block.data.signals as unknown[] | undefined) ?? [];
    const blockExits = (block.data.exit_conditions as unknown[] | undefined) ?? [];

    if (logic === 'OR') {
      optional += signals.length;
    } else {
      required += signals.length;
    }

    exits += blockExits.length;

    for (const sig of signals) {
      const s = sig as Record<string, unknown>;
      const recheckCfg = s.recheck_config as Record<string, unknown> | undefined;
      if (recheckCfg && recheckCfg.enabled) {
        rechecked += 1;
      }
      const sigExits = (s.exit_conditions as unknown[] | undefined) ?? [];
      exits += sigExits.length;
    }

    const strategyExits = (block.data.strategy_exit_conditions as unknown[] | undefined) ?? [];
    exits += strategyExits.length;
  }

  return { required, optional, rechecked, exits };
}

const TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'];

const STRATEGY_TYPES = ['Bullish', 'Bearish', 'Both'] as const;
type StrategyType = (typeof STRATEGY_TYPES)[number];

function stripVersionSuffix(name: string): string {
  return name.replace(/\s*\(v\d+\)\s*$/, '').trim();
}

function generateDescriptionFromBlocks(blocks: Block[]): string {
  if (blocks.length === 0) {
    return 'No description available. Add building blocks to generate a strategy description.';
  }

  const entryBlocks = blocks.filter((b) => b.type === 'entry_condition');
  const exitBlocks = blocks.filter((b) => b.type === 'exit_condition');

  const parts: string[] = [];

  if (entryBlocks.length > 0) {
    const entryNames = entryBlocks.map((b) => (b.data.name as string) || 'Entry Condition').join(', ');
    parts.push(`Entry signals: ${entryNames}`);
  }

  if (exitBlocks.length > 0) {
    const exitNames = exitBlocks.map((b) => (b.data.name as string) || 'Exit Condition').join(', ');
    parts.push(`Exit conditions: ${exitNames}`);
  }

  return parts.length > 0
    ? parts.join('. ') + '.'
    : 'Strategy with custom blocks configured.';
}

export function StrategyInfoPanel() {
  const { currentStrategy, updateStrategySettings, saveStrategy, setCurrentStrategy } = useStrategyStore();

  const handleNameChange = useCallback(
    (name: string) => {
      if (!currentStrategy || name === currentStrategy.name) return;
      const cleanName = stripVersionSuffix(name);
      setCurrentStrategy({ ...currentStrategy, name: cleanName });
      saveStrategy().catch(console.error);
    },
    [currentStrategy, saveStrategy, setCurrentStrategy],
  );

  const handleTimeframeChange = useCallback(
    (timeframe: string) => {
      updateStrategySettings({ timeframe });
    },
    [updateStrategySettings],
  );

  const handleStrategyTypeChange = useCallback(
    (strategyType: StrategyType) => {
      if (!currentStrategy) return;
      setCurrentStrategy({ ...currentStrategy, strategyType });
      saveStrategy().catch(console.error);
    },
    [currentStrategy, setCurrentStrategy, saveStrategy],
  );

  const createStrategyInOrchestrator = useCallback(async (): Promise<boolean> => {
    if (!currentStrategy) return false;
    const cleanName = stripVersionSuffix(currentStrategy.name);
    if (!cleanName) return false;

    try {
      await saveStrategy();
      return true;
    } catch {
      return false;
    }
  }, [currentStrategy, saveStrategy]);

  const signalCounts = useMemo(
    () => (currentStrategy ? computeSignalCounts(currentStrategy.blocks) : null),
    [currentStrategy],
  );

  const generatedDescription = useMemo(
    () => (currentStrategy ? generateDescriptionFromBlocks(currentStrategy.blocks) : ''),
    [currentStrategy],
  );

  if (!currentStrategy) {
    return (
      <div className="flex flex-col border-b border-zinc-800 bg-zinc-900 p-6">
        <p className="text-xs text-zinc-500">No strategy loaded</p>
      </div>
    );
  }

  const { name, status, blocks, settings, description, createdAt, updatedAt, strategyType, validationStatus } =
    currentStrategy;
  const badge = STATUS_BADGE[status] ?? STATUS_BADGE[StrategyStatus.DRAFT];

  const entryBlocks = blocks.filter((b) => b.type === 'entry_condition').length;
  const exitBlocks = blocks.filter((b) => b.type === 'exit_condition').length;
  const totalBlocks = blocks.length;

  const fmt = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });

  const fmtFull = (iso: string) => {
    const d = new Date(iso);
    return `${d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })} ${d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}`;
  };

  const currentType: StrategyType =
    strategyType === 'Bearish' ? 'Bearish' : strategyType === 'Both' ? 'Both' : 'Bullish';

  const validationBadge = (() => {
    if (validationStatus === 'Pass') return 'bg-emerald-950 text-emerald-400 border-emerald-800';
    if (validationStatus === 'Fail') return 'bg-red-950 text-red-400 border-red-800';
    return 'bg-zinc-800 text-zinc-500 border-zinc-700';
  })();

  return (
    <div className="flex flex-col bg-zinc-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-50">Strategy Information</h2>
        <div className="flex items-center gap-2">
          {validationStatus && (
            <span className={`text-xs px-1.5 py-0.5 rounded border font-mono ${validationBadge}`}>
              {validationStatus}
            </span>
          )}
          <span className={`text-xs px-1.5 py-0.5 rounded border font-mono ${badge.classes}`}>
            {badge.label}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="px-4 py-4">
        <dl className="space-y-5">
          {/* Name */}
          <Field label="Name">
            <InfoTooltip id="strategy-name-input">
              <input
                type="text"
                key={name}
                defaultValue={name || ''}
                onBlur={(e) => handleNameChange(e.target.value)}
                maxLength={100}
                className="w-full px-2 py-1 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
              />
            </InfoTooltip>
          </Field>

          {/* Strategy Type */}
          <Field label="Strategy Type">
            <div className="flex gap-2 mt-0.5">
              {STRATEGY_TYPES.map((type) => (
                <button
                  key={type}
                  onClick={() => handleStrategyTypeChange(type)}
                  className={`px-3 py-1 rounded text-xs font-medium border transition-colors ${
                    currentType === type
                      ? type === 'Bullish'
                        ? 'bg-emerald-900 text-emerald-300 border-emerald-700'
                        : type === 'Bearish'
                        ? 'bg-red-900 text-red-300 border-red-700'
                        : 'bg-blue-900 text-blue-300 border-blue-700'
                      : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:border-zinc-500'
                  }`}
                >
                  {type === 'Bullish' ? '▲ Bullish' : type === 'Bearish' ? '▼ Bearish' : '↕ Both'}
                </button>
              ))}
            </div>
          </Field>

          {/* Description */}
          <Field label="Description">
            <textarea
              readOnly
              value={(generatedDescription || description) ?? ''}
              placeholder="No description available. Add blocks to generate a description."
              rows={4}
              className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-xs text-zinc-300 leading-relaxed resize-none focus:outline-none"
              style={{ maxHeight: 190 }}
            />
          </Field>

          {/* Timeframe */}
          <Field label="Timeframe">
            <InfoTooltip id="strategy-timeframe-select">
              <select
                value={settings.timeframe}
                onChange={(e) => handleTimeframeChange(e.target.value)}
                className="w-full px-2 py-1 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none"
              >
                {TIMEFRAMES.map((tf) => (
                  <option key={tf} value={tf}>{tf}</option>
                ))}
              </select>
            </InfoTooltip>
          </Field>

          {/* Signal counters */}
          {signalCounts && (
            <Field label="Signal Counts">
              <div className="grid grid-cols-2 gap-2 mt-1">
                <div className="rounded bg-zinc-800 px-2 py-1.5 border border-zinc-700 text-center">
                  <div className="text-base font-bold text-emerald-400">{signalCounts.required}</div>
                  <div className="text-xs text-zinc-500">Required (AND)</div>
                </div>
                <div className="rounded bg-zinc-800 px-2 py-1.5 border border-zinc-700 text-center">
                  <div className="text-base font-bold text-blue-400">{signalCounts.optional}</div>
                  <div className="text-xs text-zinc-500">Optional (OR)</div>
                </div>
                <div className="rounded bg-zinc-800 px-2 py-1.5 border border-zinc-700 text-center">
                  <div className="text-base font-bold text-orange-400">{signalCounts.rechecked}</div>
                  <div className="text-xs text-zinc-500">Rechecked</div>
                </div>
                <div className="rounded bg-zinc-800 px-2 py-1.5 border border-zinc-700 text-center">
                  <div className="text-base font-bold text-red-400">{signalCounts.exits}</div>
                  <div className="text-xs text-zinc-500">Exit Conds</div>
                </div>
              </div>
            </Field>
          )}

          {/* Block counts */}
          <Field label="Blocks">
            <div className="grid grid-cols-3 gap-2 mt-1">
              {[
                { label: 'Total', value: totalBlocks, color: 'text-zinc-100' },
                { label: 'Entry', value: entryBlocks, color: 'text-emerald-400' },
                { label: 'Exit',  value: exitBlocks,  color: 'text-red-400' },
              ].map(({ label, value, color }) => (
                <div key={label} className="rounded bg-zinc-800 px-2 py-1.5 text-center border border-zinc-700">
                  <div className={`text-base font-bold ${color}`}>{value}</div>
                  <div className="text-xs text-zinc-500">{label}</div>
                </div>
              ))}
            </div>
          </Field>

          {/* Target market */}
          {settings.targetMarket && (
            <Field label="Target Market">
              <span className="font-mono text-zinc-200">{settings.targetMarket}</span>
            </Field>
          )}

          {/* Risk parameters */}
          {settings.riskParameters && (
            <Field label="Risk Parameters">
              <div className="space-y-1 text-xs text-zinc-300">
                {settings.riskParameters.maxLossPerTrade != null && (
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Max loss/trade</span>
                    <span>{settings.riskParameters.maxLossPerTrade}%</span>
                  </div>
                )}
                {settings.riskParameters.maxDrawdown != null && (
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Max drawdown</span>
                    <span>{settings.riskParameters.maxDrawdown}%</span>
                  </div>
                )}
                {settings.riskParameters.maxAllocation != null && (
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Max allocation</span>
                    <span>{settings.riskParameters.maxAllocation}%</span>
                  </div>
                )}
              </div>
            </Field>
          )}

          {/* Last validated */}
          {updatedAt && (
            <Field label="Last Validated">
              <span className="text-zinc-400 text-xs font-mono">{fmtFull(updatedAt)}</span>
            </Field>
          )}

          {/* Dates */}
          <Field label="Created">{fmt(createdAt)}</Field>
          <Field label="Updated">{fmt(updatedAt)}</Field>
        </dl>
      </div>
    </div>
  );
}

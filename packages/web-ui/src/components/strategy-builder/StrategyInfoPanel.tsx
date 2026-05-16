'use client';

import { useCallback } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { StrategyStatus } from '@/lib/strategy-builder/types';
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

export function StrategyInfoPanel() {
  const { currentStrategy, updateStrategySettings, saveStrategy } = useStrategyStore();

  const handleNameChange = useCallback(
    async (name: string) => {
      if (!currentStrategy || name === currentStrategy.name) return;
      // Optimistic local update via settings path; full rename would need a separate API call
      // For now, schedule save after debounce is handled externally
      await saveStrategy().catch(console.error);
      void name; // consumed by caller
    },
    [currentStrategy, saveStrategy],
  );

  const handleTimeframeChange = useCallback(
    (timeframe: string) => {
      updateStrategySettings({ timeframe });
    },
    [updateStrategySettings],
  );

  if (!currentStrategy) {
    return (
      <div className="flex flex-col h-full border-l border-zinc-800 bg-zinc-900 p-6">
        <p className="text-xs text-zinc-500">No strategy loaded</p>
      </div>
    );
  }

  const { name, status, blocks, settings, description, createdAt, updatedAt } = currentStrategy;
  const badge = STATUS_BADGE[status] ?? STATUS_BADGE[StrategyStatus.DRAFT];

  const entryBlocks = blocks.filter((b) => b.type === 'entry_condition').length;
  const exitBlocks = blocks.filter((b) => b.type === 'exit_condition').length;
  const totalBlocks = blocks.length;

  const fmt = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });

  const TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'];

  return (
    <div className="flex flex-col h-full border-l border-zinc-800 bg-zinc-900">
      {/* Header */}
      <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between flex-shrink-0">
        <h2 className="text-sm font-semibold text-zinc-50">Strategy Info</h2>
        <span className={`text-xs px-1.5 py-0.5 rounded border font-mono ${badge.classes}`}>
          {badge.label}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <dl className="space-y-5">
          {/* Name */}
          <Field label="Name">
            <InfoTooltip id="strategy-name-input">
              <input
                type="text"
                defaultValue={name}
                onBlur={(e) => handleNameChange(e.target.value)}
                maxLength={100}
                className="w-full px-2 py-1 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
              />
            </InfoTooltip>
          </Field>

          {/* Description */}
          {description && (
            <Field label="Description">
              <p className="text-zinc-300 text-xs leading-relaxed">{description}</p>
            </Field>
          )}

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

          {/* Dates */}
          <Field label="Created">{fmt(createdAt)}</Field>
          <Field label="Updated">{fmt(updatedAt)}</Field>
        </dl>
      </div>
    </div>
  );
}

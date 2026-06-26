'use client';

import { useState } from 'react';

// ── Optimization goal (AC7) ──────────────────────────────────────────────

export type OptimizationGoalId =
  | 'reduce-losses'
  | 'maximize-returns'
  | 'reduce-drawdown'
  | 'improve-win-rate'
  | 'custom';

export interface OptimizationGoalOption {
  id: OptimizationGoalId;
  label: string;
  description: string;
  /** Pre-canned value sent in the payload when this option is chosen. */
  defaultValue: string;
}

export const GOAL_OPTIONS: OptimizationGoalOption[] = [
  {
    id: 'reduce-losses',
    label: 'Reduce losses',
    description: 'Prioritize cutting losing trades and trimming risk per position.',
    defaultValue: 'reduce losses',
  },
  {
    id: 'maximize-returns',
    label: 'Maximize returns',
    description: 'Push for higher total return, even at the cost of more trades.',
    defaultValue: 'maximize returns',
  },
  {
    id: 'reduce-drawdown',
    label: 'Reduce drawdown',
    description: 'Cap the worst peak-to-trough equity drop.',
    defaultValue: 'reduce drawdown',
  },
  {
    id: 'improve-win-rate',
    label: 'Improve win rate',
    description: 'Filter for higher-confidence setups that win more often.',
    defaultValue: 'improve win rate',
  },
  {
    id: 'custom',
    label: 'Custom goal',
    description: 'Describe your own optimization target in your own words.',
    defaultValue: '',
  },
];

export function OptimizationGoalModal({
  onCancel,
  onConfirm,
}: {
  onCancel: () => void;
  onConfirm: (goal: string) => void;
}) {
  const [selected, setSelected] = useState<OptimizationGoalId>('reduce-losses');
  const [customText, setCustomText] = useState('');
  const customOption = GOAL_OPTIONS.find((g) => g.id === 'custom');
  const selectedOption = GOAL_OPTIONS.find((g) => g.id === selected) ?? GOAL_OPTIONS[0];

  const resolved = selected === 'custom' ? customText.trim() : selectedOption.defaultValue;
  const canConfirm = resolved.length > 0;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="opt-goal-modal-title"
      data-testid="opt-goal-modal"
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'var(--overlay-scrim)' }}
      onClick={onCancel}
    >
      <div
        className="rounded p-4 max-w-md w-full mx-4"
        style={{
          background: 'var(--bg-card)',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <p
          id="opt-goal-modal-title"
          className="text-sm font-semibold mb-1"
          style={{ color: 'var(--text-secondary)' }}
        >
          Choose an optimization goal
        </p>
        <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
          The AI provider will be told to prioritize this goal when shaping recommendations.
          Pick a preset or describe a custom target.
        </p>

        <div role="radiogroup" aria-label="Optimization goal" className="flex flex-col gap-2 mb-3">
          {GOAL_OPTIONS.map((opt) => {
            const isSelected = selected === opt.id;
            return (
              <label
                key={opt.id}
                className="flex items-start gap-2 rounded p-2 cursor-pointer"
                style={{
                  background: isSelected ? 'var(--bg-elevated)' : 'transparent',
                  border: `1px solid ${isSelected ? 'var(--accent-blue)' : 'var(--border)'}`,
                }}
              >
                <input
                  type="radio"
                  name="optimization-goal"
                  value={opt.id}
                  checked={isSelected}
                  onChange={() => setSelected(opt.id)}
                  data-testid={`opt-goal-${opt.id}`}
                  className="mt-1"
                  style={{ accentColor: 'var(--accent-blue)' }}
                />
                <span className="flex flex-col gap-0.5">
                  <span
                    className="text-xs font-semibold"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    {opt.label}
                  </span>
                  <span className="text-[11px]" style={{ color: 'var(--text-faint)' }}>
                    {opt.description}
                  </span>
                </span>
              </label>
            );
          })}
        </div>

        {selected === 'custom' && (
          <div className="mb-3">
            <label
              className="text-[10px] font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-muted)' }}
              htmlFor="opt-goal-custom-text"
            >
              {customOption?.label ?? 'Custom goal'}
            </label>
            <textarea
              id="opt-goal-custom-text"
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              data-testid="opt-goal-custom-text"
              rows={3}
              placeholder="e.g. Reduce overnight exposure while keeping at least 80% of the current total return."
              className="w-full mt-1 rounded p-2 text-xs"
              style={{
                background: 'var(--bg-elevated)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border)',
                fontFamily: 'var(--font-mono, monospace)',
                resize: 'vertical',
              }}
            />
          </div>
        )}

        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            data-testid="opt-goal-cancel"
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: 'var(--bg-elevated)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onConfirm(resolved)}
            disabled={!canConfirm}
            data-testid="opt-goal-confirm"
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: canConfirm ? 'var(--accent-blue)' : 'var(--bg-elevated)',
              color: canConfirm ? 'var(--text-on-accent)' : 'var(--text-faint)',
              border: '1px solid var(--border)',
              opacity: canConfirm ? 1 : 0.5,
              cursor: canConfirm ? 'pointer' : 'not-allowed',
            }}
          >
            Send with this goal
          </button>
        </div>
      </div>
    </div>
  );
}

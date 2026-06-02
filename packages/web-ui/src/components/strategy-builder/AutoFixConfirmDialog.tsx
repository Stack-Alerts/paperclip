'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { Wrench, BarChart3, Settings } from 'lucide-react';
import Structural005FixDialog from './Structural005FixDialog';
import MissingTimeframeFixDialog from './MissingTimeframeFixDialog';
import MissingTargetMarketFixDialog from './MissingTargetMarketFixDialog';
import { RichTooltip } from './RichTooltip';

export interface AutoFixOption {
  key: string;
  label: string;
  /** Whether the option is checked by default */
  defaultChecked?: boolean;
  tooltip?: string;
}

export interface Structural005Data {
  blockName: string;
  signalName: string;
  duplicateIndices: number[];
  signalDetails: Array<{ index: number; name: string; weight: number; exitCount: number }>;
}

export interface AutoFixConfirmDialogProps {
  open: boolean;
  fixType: string;
  fixDescription: string;
  beforeState: Record<string, unknown>;
  afterState: Record<string, unknown>;
  impactAnalysis: string;
  options?: AutoFixOption[];
  ruleId?: string;
  structural005Data?: Structural005Data;
  onConfirm: (userOptions: Record<string, boolean> | { mode: string; targetIndex: number; newName?: string } | { value: string }) => void;
  onCancel: () => void;
}

// ─── State formatter (mirrors PyQt5 _format_state) ───────────────────────────

function toTitleCase(snake: string): string {
  return snake
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatStateValue(value: unknown): string {
  if (Array.isArray(value)) {
    if (value.length > 3) return `[${value.length} items]`;
    return JSON.stringify(value);
  }
  if (value !== null && typeof value === 'object') {
    const keys = Object.keys(value as object).length;
    return `{...} (${keys} field${keys !== 1 ? 's' : ''})`;
  }
  return String(value);
}

function formatState(state: Record<string, unknown>): string {
  return Object.entries(state)
    .map(([k, v]) => `${toTitleCase(k)}: ${formatStateValue(v)}`)
    .join('\n');
}

// ─── Dialog ──────────────────────────────────────────────────────────────────

export const AutoFixConfirmDialog: React.FC<AutoFixConfirmDialogProps> = ({
  open,
  fixType,
  fixDescription,
  beforeState,
  afterState,
  impactAnalysis,
  ruleId,
  structural005Data,
  options = [],
  onConfirm,
  onCancel,
}) => {
  const [userOptions, setUserOptions] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(options.map((o) => [o.key, o.defaultChecked ?? false]))
  );
  const isStructural005 = ruleId === 'STRUCTURAL_005' && structural005Data;
  const isMissingTimeframe = ruleId === 'missing_timeframe';
  const isMissingTargetMarket = ruleId === 'missing_target_market';

  // Reset state when the dialog opens. The previous form of this effect
  // depended on `options` directly; callers pass it as an inline array (or
  // omit it so it defaults to a new `[]` on every render) which made the
  // dependency change identity on every render and triggered an infinite
  // setState loop the moment the dialog opened (BTCAAAAA-32954 board comment
  // 9b5949ca: "applied the 2 fixes ... nothing changed"). Key off a stable
  // serialization so re-init only fires when the option keys/defaults
  // actually change.
  const optionsKey = options
    .map((o) => `${o.key}:${o.defaultChecked ? 1 : 0}`)
    .join('|');
  useEffect(() => {
    if (open) {
      setUserOptions(
        Object.fromEntries(options.map((o) => [o.key, o.defaultChecked ?? false]))
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, optionsKey]);

  const handleOptionChange = useCallback((key: string, checked: boolean) => {
    setUserOptions((prev) => ({ ...prev, [key]: checked }));
  }, []);

  const handleConfirm = useCallback(() => {
    onConfirm(userOptions);
  }, [userOptions, onConfirm]);

  if (!open) return null;

  const beforeFormatted = formatState(beforeState);
  const afterFormatted = formatState(afterState);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg shadow-2xl w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>

        {/* ── Sticky header ── */}
        <div className="flex items-center gap-3 border-b px-6 py-4 sticky top-0 z-10" style={{ borderColor: 'var(--border)', background: 'var(--bg-panel)' }}>
          <Wrench size={18} strokeWidth={1.75} style={{ color: 'var(--text-secondary)' }} />
          <div>
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-secondary)' }}>
              Auto-Fix: {fixType}
            </h2>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Review proposed changes before applying</p>
          </div>
        </div>

        <div className="px-6 py-5 space-y-5">

          {/* Description */}
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{fixDescription}</p>

          {/* ── Before / Arrow / After (skip for local auto-fixes) ── */}
          {!isMissingTimeframe && !isMissingTargetMarket && (
          <div className="flex items-start gap-3">
            {/* Before */}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5" style={{ color: 'var(--accent-red)' }}>
                <span aria-hidden="true">✕</span> Current State (Has Issues)
              </p>
              <pre className="rounded p-3 text-xs overflow-auto max-h-48 font-mono whitespace-pre-wrap break-words border" style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                {beforeFormatted}
              </pre>
            </div>

            {/* Arrow */}
            <div className="flex items-center justify-center pt-7 flex-shrink-0">
              <span className="text-2xl font-bold select-none" style={{ color: 'var(--accent-blue)' }}>→</span>
            </div>

            {/* After */}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5" style={{ color: 'var(--accent-green)' }}>
                <span aria-hidden="true">✓</span> After Fix (Corrected)
              </p>
              <pre className="rounded p-3 text-xs overflow-auto max-h-48 font-mono whitespace-pre-wrap break-words border" style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                {afterFormatted}
              </pre>
            </div>
          </div>
          )}

          {/* ── Impact Analysis (skip for local auto-fixes) ── */}
          {!isMissingTimeframe && !isMissingTargetMarket && (
          <div className="rounded-r px-4 py-3" style={{ borderLeft: '4px solid var(--accent-blue)', background: 'color-mix(in srgb, var(--bg-deep) 60%, transparent)' }}>
            <p className="text-xs font-semibold uppercase tracking-wider mb-1.5 flex items-center gap-1.5" style={{ color: 'var(--accent-blue)' }}>
              <BarChart3 size={12} strokeWidth={1.75} /> Impact Analysis
            </p>
            <p className="text-sm whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>{impactAnalysis}</p>
          </div>
          )}

          {/* ── Rule-specific Controls ── */}
          {isStructural005 && structural005Data && (
            <Structural005FixDialog
              strategyId=""
              blockName={structural005Data.blockName}
              signalName={structural005Data.signalName}
              duplicateIndices={structural005Data.duplicateIndices}
              signalDetails={structural005Data.signalDetails}
              onConfirm={(mode, targetIndex, newName) => {
                onConfirm({ mode, targetIndex, newName });
              }}
              onCancel={onCancel}
            />
          )}

          {isMissingTimeframe && (
            <MissingTimeframeFixDialog
              onConfirm={(value) => {
                onConfirm({ value });
              }}
              onCancel={onCancel}
            />
          )}

          {isMissingTargetMarket && (
            <MissingTargetMarketFixDialog
              onConfirm={(value) => {
                onConfirm({ value });
              }}
              onCancel={onCancel}
            />
          )}

          {/* ── Checkbox Options ── */}
          {!isStructural005 && options.length > 0 && (
            <div className="rounded-lg px-5 py-4 space-y-3 border" style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--bg-card) 30%, transparent)' }}>
              <p className="text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                <Settings size={12} strokeWidth={1.75} /> Options
              </p>
              {options.map((opt) => {
                const optionRow = (
                  <label
                    key={opt.key}
                    className="flex items-start gap-3 cursor-pointer group"
                  >
                    <input
                      type="checkbox"
                      checked={userOptions[opt.key] ?? false}
                      onChange={(e) => handleOptionChange(opt.key, e.target.checked)}
                      className="mt-0.5 w-4 h-4 rounded cursor-pointer flex-shrink-0"
                      style={{ borderColor: 'var(--border)', background: 'var(--bg-card)', accentColor: 'var(--accent-blue)' }}
                    />
                    <span className="text-sm transition-colors" style={{ color: 'var(--text-secondary)' }}>
                      {opt.label}
                    </span>
                  </label>
                );
                return opt.tooltip ? (
                  <RichTooltip key={opt.key} content={{ title: opt.label, body: opt.tooltip }}>
                    {optionRow}
                  </RichTooltip>
                ) : optionRow;
              })}
            </div>
          )}
        </div>

        {/* ── Sticky footer (hidden for rule types with their own buttons) ── */}
        {!isStructural005 && !isMissingTimeframe && !isMissingTargetMarket && (
          <div className="flex justify-end gap-2 px-6 py-4 border-t sticky bottom-0 z-10" style={{ borderColor: 'var(--border)', background: 'var(--bg-panel)' }}>
            <button
              onClick={onCancel}
              className="px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              className="px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
            >
              Apply Fix
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default AutoFixConfirmDialog;

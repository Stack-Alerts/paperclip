'use client';

import React, { useState, useCallback, useEffect } from 'react';

export interface AutoFixOption {
  key: string;
  label: string;
  /** Whether the option is checked by default */
  defaultChecked?: boolean;
  tooltip?: string;
}

export interface AutoFixConfirmDialogProps {
  open: boolean;
  fixType: string;
  fixDescription: string;
  beforeState: Record<string, unknown>;
  afterState: Record<string, unknown>;
  impactAnalysis: string;
  options?: AutoFixOption[];
  onConfirm: (userOptions: Record<string, boolean>) => void;
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
  options = [],
  onConfirm,
  onCancel,
}) => {
  const [userOptions, setUserOptions] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(options.map((o) => [o.key, o.defaultChecked ?? false]))
  );

  // Reset state when options change or dialog opens (matches PyQt5 behavior of re-instantiation)
  useEffect(() => {
    if (open) {
      setUserOptions(
        Object.fromEntries(options.map((o) => [o.key, o.defaultChecked ?? false]))
      );
    }
  }, [open, options]);

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
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto">

        {/* ── Sticky header ── */}
        <div className="flex items-center gap-3 border-b border-zinc-700 px-6 py-4 sticky top-0 bg-zinc-900 z-10">
          <span className="text-xl">🔧</span>
          <div>
            <h2 className="text-base font-semibold text-zinc-100">
              Auto-Fix: {fixType}
            </h2>
            <p className="text-xs text-zinc-400">Review proposed changes before applying</p>
          </div>
        </div>

        <div className="px-6 py-5 space-y-5">

          {/* Description */}
          <p className="text-sm text-zinc-200">{fixDescription}</p>

          {/* ── Before / Arrow / After ── */}
          <div className="flex items-start gap-3">
            {/* Before */}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
                ❌ Current State (Has Issues)
              </p>
              <pre className="bg-zinc-950 border border-zinc-700 rounded p-3 text-xs text-zinc-300 overflow-auto max-h-48 font-mono whitespace-pre-wrap break-words">
                {beforeFormatted}
              </pre>
            </div>

            {/* Arrow */}
            <div className="flex items-center justify-center pt-7 flex-shrink-0">
              <span className="text-2xl font-bold text-blue-400 select-none">→</span>
            </div>

            {/* After */}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-2">
                ✅ After Fix (Corrected)
              </p>
              <pre className="bg-zinc-950 border border-zinc-700 rounded p-3 text-xs text-zinc-300 overflow-auto max-h-48 font-mono whitespace-pre-wrap break-words">
                {afterFormatted}
              </pre>
            </div>
          </div>

          {/* ── Impact Analysis ── */}
          <div className="border-l-4 border-blue-500 bg-zinc-950/60 rounded-r px-4 py-3">
            <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-1.5">
              📊 Impact Analysis
            </p>
            <p className="text-sm text-zinc-300 whitespace-pre-wrap">{impactAnalysis}</p>
          </div>

          {/* ── Checkbox Options ── */}
          {options.length > 0 && (
            <div className="border border-zinc-700 rounded-lg px-5 py-4 space-y-3 bg-zinc-800/30">
              <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                ⚙️ Options
              </p>
              {options.map((opt) => (
                <label
                  key={opt.key}
                  className="flex items-start gap-3 cursor-pointer group"
                  title={opt.tooltip}
                >
                  <input
                    type="checkbox"
                    checked={userOptions[opt.key] ?? false}
                    onChange={(e) => handleOptionChange(opt.key, e.target.checked)}
                    className="mt-0.5 w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-blue-500 focus:ring-blue-500 cursor-pointer flex-shrink-0"
                  />
                  <span className="text-sm text-zinc-300 group-hover:text-zinc-100 transition-colors">
                    {opt.label}
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* ── Sticky footer ── */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-zinc-700 sticky bottom-0 bg-zinc-900 z-10">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="px-4 py-2 rounded bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors"
          >
            ✅ Apply Fix
          </button>
        </div>
      </div>
    </div>
  );
};

export default AutoFixConfirmDialog;

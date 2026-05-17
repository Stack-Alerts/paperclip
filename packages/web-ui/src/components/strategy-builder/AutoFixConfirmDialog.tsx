'use client';

import React, { useState, useCallback } from 'react';

export interface AutoFixOption {
  key: string;
  label: string;
  choices: string[];
  defaultChoice: string;
}

export interface AutoFixConfirmDialogProps {
  open: boolean;
  fixType: string;
  fixDescription: string;
  beforeState: Record<string, unknown>;
  afterState: Record<string, unknown>;
  impactAnalysis: string;
  options?: AutoFixOption[];
  onConfirm: (userOptions: Record<string, string>) => void;
  onCancel: () => void;
}

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
  const [userOptions, setUserOptions] = useState<Record<string, string>>(() =>
    Object.fromEntries(options.map((o) => [o.key, o.defaultChoice]))
  );

  const handleOptionChange = useCallback((key: string, value: string) => {
    setUserOptions((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleConfirm = useCallback(() => {
    onConfirm(userOptions);
  }, [userOptions, onConfirm]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center gap-3 border-b border-zinc-700 px-6 py-4 sticky top-0 bg-zinc-900">
          <span className="text-xl">🔧</span>
          <div>
            <h2 className="text-base font-semibold text-zinc-100">Confirm Auto-Fix</h2>
            <p className="text-xs text-zinc-400">{fixType}</p>
          </div>
        </div>

        <div className="px-6 py-5 space-y-5">
          <div>
            <p className="text-sm font-medium text-zinc-200">{fixDescription}</p>
          </div>

          {/* Before / After Comparison */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">Before</p>
              <pre className="bg-zinc-950 border border-zinc-700 rounded p-3 text-xs text-zinc-300 overflow-auto max-h-48 font-mono">
                {JSON.stringify(beforeState, null, 2)}
              </pre>
            </div>
            <div>
              <p className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-2">After</p>
              <pre className="bg-zinc-950 border border-zinc-700 rounded p-3 text-xs text-zinc-300 overflow-auto max-h-48 font-mono">
                {JSON.stringify(afterState, null, 2)}
              </pre>
            </div>
          </div>

          {/* Impact Analysis */}
          <div>
            <p className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-2">
              Impact Analysis
            </p>
            <div className="bg-zinc-950 border border-zinc-700 rounded p-3 text-sm text-zinc-300 whitespace-pre-wrap">
              {impactAnalysis}
            </div>
          </div>

          {/* User Options */}
          {options.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">Options</p>
              {options.map((opt) => (
                <div key={opt.key} className="space-y-1">
                  <label className="text-sm text-zinc-300">{opt.label}</label>
                  <div className="flex gap-2">
                    {opt.choices.map((choice) => (
                      <button
                        key={choice}
                        onClick={() => handleOptionChange(opt.key, choice)}
                        className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                          userOptions[opt.key] === choice
                            ? 'bg-blue-600 text-white'
                            : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
                        }`}
                      >
                        {choice}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 px-6 py-4 border-t border-zinc-700 sticky bottom-0 bg-zinc-900">
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

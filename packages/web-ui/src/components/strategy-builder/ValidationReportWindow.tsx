'use client';

import { useMemo } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { ValidationLevel, ValidationMessage } from '@/lib/strategy-builder/types';

const LEVEL_COLORS: Record<ValidationLevel, string> = {
  error: 'text-red-400 bg-red-950',
  warning: 'text-amber-400 bg-amber-950',
  info: 'text-blue-400 bg-blue-950',
};

export interface ValidationReportWindowProps {
  open: boolean;
  onClose: () => void;
}

export function ValidationReportWindow({ open, onClose }: ValidationReportWindowProps) {
  const { validationMessages, isValidating, validateStrategy } = useStrategyStore();

  const grouped = useMemo(() => {
    const errors = validationMessages.filter((m) => m.level === ValidationLevel.ERROR);
    const warnings = validationMessages.filter((m) => m.level === ValidationLevel.WARNING);
    const infos = validationMessages.filter((m) => m.level === ValidationLevel.INFO);
    return { errors, warnings, infos };
  }, [validationMessages]);

  const total = validationMessages.length;
  const critical = grouped.errors.length > 0;

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative w-full max-w-4xl rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl mx-4 flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 flex-shrink-0">
          <div>
            <h2 className="text-base font-semibold text-zinc-50">📋 Validation Report</h2>
            <p className="text-xs text-zinc-500 mt-1">
              {total === 0 ? 'No validation results' : `${total} message${total !== 1 ? 's' : ''}`}
            </p>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-lg" aria-label="Close dialog">
            ✕
          </button>
        </div>

        {/* Summary bar */}
        <div className="px-6 py-3 border-b border-zinc-800 flex gap-4 bg-zinc-800/30 flex-shrink-0">
          <div className="text-xs">
            <span className="text-red-400 font-medium">{grouped.errors.length} error{grouped.errors.length !== 1 ? 's' : ''}</span>
          </div>
          <div className="text-xs">
            <span className="text-amber-400 font-medium">{grouped.warnings.length} warning{grouped.warnings.length !== 1 ? 's' : ''}</span>
          </div>
          <div className="text-xs">
            <span className="text-blue-400">{grouped.infos.length} info</span>
          </div>
          <div className="flex-1" />
          <button
            onClick={() => validateStrategy().catch(console.error)}
            disabled={isValidating}
            className="px-3 py-1 rounded bg-green-700 hover:bg-green-600 text-white text-xs font-medium disabled:opacity-50"
          >
            {isValidating ? 'Validating…' : 'Re-validate'}
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {total === 0 ? (
            <div className="text-center py-12">
              <p className="text-zinc-400 text-sm">No validation messages. Click Re-validate to run checks.</p>
            </div>
          ) : (
            <>
              {grouped.errors.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-red-400 uppercase mb-2">Errors</h3>
                  <div className="space-y-2">
                    {grouped.errors.map((msg) => (
                      <div key={msg.id} className={`rounded border border-red-800 p-2.5 ${LEVEL_COLORS.error}`}>
                        <p className="text-sm leading-relaxed">{msg.text}</p>
                        {msg.blockIndex != null && <p className="text-xs text-red-300 mt-1">Block #{msg.blockIndex + 1}</p>}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {grouped.warnings.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-amber-400 uppercase mb-2">Warnings</h3>
                  <div className="space-y-2">
                    {grouped.warnings.map((msg) => (
                      <div key={msg.id} className={`rounded border border-amber-800 p-2.5 ${LEVEL_COLORS.warning}`}>
                        <p className="text-sm leading-relaxed">{msg.text}</p>
                        {msg.blockIndex != null && <p className="text-xs text-amber-300 mt-1">Block #{msg.blockIndex + 1}</p>}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {grouped.infos.length > 0 && (
                <section>
                  <h3 className="text-xs font-semibold text-blue-400 uppercase mb-2">Information</h3>
                  <div className="space-y-2">
                    {grouped.infos.map((msg) => (
                      <div key={msg.id} className={`rounded border border-blue-800 p-2.5 ${LEVEL_COLORS.info}`}>
                        <p className="text-sm leading-relaxed">{msg.text}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-zinc-800 flex-shrink-0">
          <button
            onClick={onClose}
            className={`px-4 py-2 rounded text-white text-sm font-medium transition-colors ${
              critical
                ? 'bg-red-600 hover:bg-red-500'
                : total === 0
                  ? 'bg-emerald-600 hover:bg-emerald-500'
                  : 'bg-zinc-700 hover:bg-zinc-600'
            }`}
          >
            {critical ? '⚠ Close' : total === 0 ? '✓ All Clear' : 'Done'}
          </button>
        </div>
      </div>
    </div>
  );
}

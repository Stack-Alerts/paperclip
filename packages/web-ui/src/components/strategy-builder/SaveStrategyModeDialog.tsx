'use client';

// Disambiguates Save after a rename for backend-loaded strategies. Board
// feedback on BTCAAAAA-30023 (2026-05-27): clicking Save with a different
// name needs to ask "rename the existing strategy or create a new
// strategy v1?" so the user does not silently lose the original or fork
// a strategy they meant to rename.
//
// "Rename existing" → bumps the version on the same strategy_id with the
// new name (current PUT path).
// "Save as new strategy v1" → POST .../duplicate?scope=strategy with the
// new name, producing a brand-new strategy_id starting at version 1.

import { useEffect, useRef } from 'react';

export interface SaveStrategyModeDialogProps {
  open: boolean;
  originalName: string;
  newName: string;
  busy?: boolean;
  onRenameExisting: () => void;
  onSaveAsNew: () => void;
  onCancel: () => void;
}

export function SaveStrategyModeDialog({
  open,
  originalName,
  newName,
  busy = false,
  onRenameExisting,
  onSaveAsNew,
  onCancel,
}: SaveStrategyModeDialogProps) {
  const renameRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) renameRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-mode-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onKeyDown={(e) => {
        if (e.key === 'Escape' && !busy) onCancel();
      }}
    >
      <div
        className="rounded-lg shadow-2xl w-[480px] max-w-[92vw] p-6 border"
        style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}
      >
        <h2
          id="save-mode-dialog-title"
          className="text-base font-semibold mb-2"
          style={{ color: 'var(--text-primary)' }}
        >
          Save renamed strategy
        </h2>
        <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
          The strategy name changed from{' '}
          <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
            “{originalName}”
          </span>{' '}
          to{' '}
          <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
            “{newName}”
          </span>
          . How should it be saved?
        </p>

        <div className="space-y-3 mb-5 text-xs" style={{ color: 'var(--text-muted)' }}>
          <div>
            <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>
              Rename existing strategy
            </span>{' '}
            — keeps the same strategy and adds a new version under the renamed name. The
            previous name is replaced everywhere.
          </div>
          <div>
            <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>
              Save as new strategy v1
            </span>{' '}
            — leaves “{originalName}” untouched and creates a brand-new strategy named “{newName}”
            starting at version 1, copied from the latest saved state of the original.
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <button
            ref={renameRef}
            type="button"
            disabled={busy}
            onClick={onRenameExisting}
            className="px-4 py-2 text-sm transition-colors disabled:opacity-50"
            style={{
              background: 'var(--accent-blue-dark)',
              color: 'var(--accent-blue)',
              fontWeight: 600,
              border: '1px solid var(--border)',
              borderRadius: 4,
            }}
          >
            Rename existing strategy
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onSaveAsNew}
            className="px-4 py-2 text-sm transition-colors disabled:opacity-50"
            style={{
              background: 'var(--bg-card)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border)',
              borderRadius: 4,
            }}
          >
            Save as new strategy v1
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onCancel}
            className="px-4 py-2 text-sm transition-colors disabled:opacity-50 mt-1"
            style={{
              background: 'transparent',
              color: 'var(--text-muted)',
              border: '1px solid transparent',
              borderRadius: 4,
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

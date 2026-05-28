'use client';

import { useState } from 'react';
import { Strategy } from '@/lib/strategy-builder/types';

export type DuplicateScope = 'version' | 'strategy';

interface DuplicateStrategyModalProps {
  strategy: Strategy;
  onConfirm: (scope: DuplicateScope, newName?: string) => void;
  onCancel: () => void;
}

export function DuplicateStrategyModal({ strategy, onConfirm, onCancel }: DuplicateStrategyModalProps) {
  const [scope, setScope] = useState<DuplicateScope>('version');
  const [newName, setNewName] = useState(`${strategy.name} (copy)`);
  const [cancelHover, setCancelHover] = useState(false);
  const [confirmHover, setConfirmHover] = useState(false);

  const canConfirm = scope === 'version' || newName.trim().length > 0;

  return (
    <div className="absolute inset-0 flex items-center justify-center z-60">
      <div
        className="rounded-lg p-6 shadow-2xl max-w-sm w-full mx-4 space-y-4"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Duplicate Strategy</h3>
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Choose how to duplicate <strong style={{ color: 'var(--text-secondary)' }}>{strategy.name}</strong>:
        </p>

        <div className="space-y-2">
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="radio"
              name="dupScope"
              value="version"
              checked={scope === 'version'}
              onChange={() => setScope('version')}
              className="mt-0.5 accent-blue-500"
            />
            <div>
              <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>Duplicate as new version of existing strategy</span>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Creates a new version under the same strategy ID.</p>
            </div>
          </label>

          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="radio"
              name="dupScope"
              value="strategy"
              checked={scope === 'strategy'}
              onChange={() => setScope('strategy')}
              className="mt-0.5 accent-blue-500"
            />
            <div>
              <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>Duplicate as new strategy</span>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Creates a completely separate strategy with its own ID.</p>
            </div>
          </label>
        </div>

        {scope === 'strategy' && (
          <div className="space-y-1.5">
            <label className="text-xs" style={{ color: 'var(--text-secondary)' }}>New strategy name</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full px-3 py-1.5 rounded text-sm focus:outline-none"
              style={{
                background: 'var(--input-bg)',
                border: '1px solid var(--input-border)',
                color: 'var(--input-text)',
              }}
              autoFocus
            />
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            onMouseEnter={() => setCancelHover(true)}
            onMouseLeave={() => setCancelHover(false)}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
            style={{
              background: cancelHover ? 'var(--bg-hover)' : 'var(--bg-panel)',
              color: 'var(--text-primary)',
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(scope, scope === 'strategy' ? newName.trim() : undefined)}
            disabled={!canConfirm}
            onMouseEnter={() => setConfirmHover(true)}
            onMouseLeave={() => setConfirmHover(false)}
            className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-50 transition-colors"
            style={{
              background: confirmHover ? 'var(--accent-blue-dark)' : 'var(--accent-blue)',
              color: 'var(--btn-primary-text)',
            }}
          >
            {scope === 'version' ? 'Create New Version' : 'Create New Strategy'}
          </button>
        </div>
      </div>
    </div>
  );
}

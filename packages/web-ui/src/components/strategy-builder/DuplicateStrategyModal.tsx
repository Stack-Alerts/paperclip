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

  const canConfirm = scope === 'version' || newName.trim().length > 0;

  return (
    <div className="absolute inset-0 flex items-center justify-center z-60">
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6 shadow-2xl max-w-sm w-full mx-4 space-y-4">
        <h3 className="text-sm font-semibold text-zinc-50">Duplicate Strategy</h3>
        <p className="text-xs text-zinc-400">
          Choose how to duplicate <strong className="text-zinc-200">{strategy.name}</strong>:
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
              <span className="text-xs font-medium text-zinc-200">Duplicate as new version of existing strategy</span>
              <p className="text-xs text-zinc-500 mt-0.5">Creates a new version under the same strategy ID.</p>
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
              <span className="text-xs font-medium text-zinc-200">Duplicate as new strategy</span>
              <p className="text-xs text-zinc-500 mt-0.5">Creates a completely separate strategy with its own ID.</p>
            </div>
          </label>
        </div>

        {scope === 'strategy' && (
          <div className="space-y-1.5">
            <label className="text-xs text-zinc-400">New strategy name</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full px-3 py-1.5 rounded bg-zinc-700 border border-zinc-600 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
              autoFocus
            />
          </div>
        )}

        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-xs font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(scope, scope === 'strategy' ? newName.trim() : undefined)}
            disabled={!canConfirm}
            className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium disabled:opacity-50 transition-colors"
          >
            {scope === 'version' ? 'Create New Version' : 'Create New Strategy'}
          </button>
        </div>
      </div>
    </div>
  );
}

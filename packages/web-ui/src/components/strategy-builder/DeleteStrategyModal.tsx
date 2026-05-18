'use client';

import { useState } from 'react';
import { Strategy, StrategyVersion } from '@/lib/strategy-builder/types';

export type DeleteScope = 'entire' | 'version';

interface DeleteStrategyModalProps {
  strategy: Strategy;
  versions: StrategyVersion[];
  onConfirm: (scope: DeleteScope, versionIds?: string[]) => void;
  onCancel: () => void;
}

export function DeleteStrategyModal({ strategy, versions, onConfirm, onCancel }: DeleteStrategyModalProps) {
  const [scope, setScope] = useState<DeleteScope>(versions.length === 1 ? 'entire' : 'version');
  const [selectedVersionIds, setSelectedVersionIds] = useState<Set<string>>(
    versions.length > 0 ? new Set([versions[versions.length - 1].id]) : new Set(),
  );

  const toggleVersion = (id: string) => {
    setSelectedVersionIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const canConfirm = scope === 'entire' || selectedVersionIds.size > 0;

  return (
    <div className="absolute inset-0 flex items-center justify-center z-60">
      <div className="bg-zinc-800 border border-zinc-700 rounded-lg p-6 shadow-2xl max-w-sm w-full mx-4 space-y-4">
        <h3 className="text-sm font-semibold text-zinc-50">Delete Strategy</h3>
        <p className="text-xs text-zinc-400">
          Choose what to delete for <strong className="text-zinc-200">{strategy.name}</strong>:
        </p>

        <div className="space-y-2">
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="radio"
              name="deleteScope"
              value="entire"
              checked={scope === 'entire'}
              onChange={() => setScope('entire')}
              className="mt-0.5 accent-red-500"
            />
            <div>
              <span className="text-xs font-medium text-zinc-200">
                Delete entire strategy — All {versions.length} version{versions.length !== 1 ? 's' : ''}
              </span>
              <p className="text-xs text-zinc-500 mt-0.5">Permanently removes all versions. Cannot be undone.</p>
            </div>
          </label>

          <label className={`flex items-start gap-2 ${versions.length <= 1 ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}>
            <input
              type="radio"
              name="deleteScope"
              value="version"
              checked={scope === 'version'}
              onChange={() => setScope('version')}
              disabled={versions.length <= 1}
              className="mt-0.5 accent-red-500"
            />
            <div>
              <span className="text-xs font-medium text-zinc-200">Delete specific version only</span>
              {versions.length <= 1 && (
                <p className="text-xs text-zinc-500 mt-0.5">Only one version — delete entire strategy to remove.</p>
              )}
            </div>
          </label>
        </div>

        {scope === 'version' && versions.length > 1 && (
          <div className="space-y-1.5">
            <p className="text-xs text-zinc-400">Select version(s) to delete:</p>
            <div className="max-h-36 overflow-y-auto rounded border border-zinc-700 bg-zinc-900/50">
              {versions.map((v) => (
                <label
                  key={v.id}
                  className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-zinc-700/50 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedVersionIds.has(v.id)}
                    onChange={() => toggleVersion(v.id)}
                    className="accent-red-500"
                  />
                  <span className="text-xs text-zinc-200">v{v.versionNumber}</span>
                  {v.isLatest && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-blue-900/40 border border-blue-700 text-blue-400">latest</span>
                  )}
                  <span className="text-xs text-zinc-500 ml-auto">
                    {new Date(v.createdAt).toLocaleDateString()}
                  </span>
                </label>
              ))}
            </div>
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
            onClick={() => onConfirm(scope, scope === 'version' ? Array.from(selectedVersionIds) : undefined)}
            disabled={!canConfirm}
            className="px-3 py-1.5 rounded bg-red-700 hover:bg-red-600 text-white text-xs font-medium disabled:opacity-50 transition-colors"
          >
            {scope === 'entire' ? 'Delete Strategy' : `Delete ${selectedVersionIds.size} Version${selectedVersionIds.size !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}

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
  const [cancelHover, setCancelHover] = useState(false);
  const [confirmHover, setConfirmHover] = useState(false);

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
      <div
        className="rounded-lg p-6 shadow-2xl max-w-sm w-full mx-4 space-y-4"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Delete Strategy</h3>
        <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Choose what to delete for <strong style={{ color: 'var(--text-secondary)' }}>{strategy.name}</strong>:
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
              <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                Delete entire strategy — All {versions.length} version{versions.length !== 1 ? 's' : ''}
              </span>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Permanently removes all versions. Cannot be undone.</p>
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
              <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Delete specific version only</span>
              {versions.length <= 1 && (
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Only one version — delete entire strategy to remove.</p>
              )}
            </div>
          </label>
        </div>

        {scope === 'version' && versions.length > 1 && (
          <div className="space-y-1.5">
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>Select version(s) to delete:</p>
            <div
              className="max-h-36 overflow-y-auto rounded"
              style={{ border: '1px solid var(--border)', background: 'var(--bg-deep)' }}
            >
              {versions.map((v) => (
                <label
                  key={v.id}
                  className="flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors"
                  style={{ background: 'transparent' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <input
                    type="checkbox"
                    checked={selectedVersionIds.has(v.id)}
                    onChange={() => toggleVersion(v.id)}
                    className="accent-red-500"
                  />
                  <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>v{v.versionNumber}</span>
                  {v.isLatest && (
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{
                        background: 'var(--accent-blue-dark)',
                        border: '1px solid var(--accent-blue-mid)',
                        color: 'var(--accent-blue)',
                      }}
                    >latest</span>
                  )}
                  <span className="text-xs ml-auto" style={{ color: 'var(--text-muted)' }}>
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
            onMouseEnter={() => setCancelHover(true)}
            onMouseLeave={() => setCancelHover(false)}
            className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
            style={{
              background: cancelHover ? 'var(--bg-hover)' : 'var(--bg-panel)',
              color: 'var(--text-secondary)',
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(scope, scope === 'version' ? Array.from(selectedVersionIds) : undefined)}
            disabled={!canConfirm}
            onMouseEnter={() => setConfirmHover(true)}
            onMouseLeave={() => setConfirmHover(false)}
            className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-50 transition-colors"
            style={{
              background: confirmHover ? 'var(--accent-red-dark)' : 'var(--accent-red)',
              color: 'var(--btn-primary-text)',
            }}
          >
            {scope === 'entire' ? 'Delete Strategy' : `Delete ${selectedVersionIds.size} Version${selectedVersionIds.size !== 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  );
}

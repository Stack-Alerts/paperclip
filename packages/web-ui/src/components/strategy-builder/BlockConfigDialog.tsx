'use client';

import { useState, useEffect } from 'react';
import { Block, BlockType } from '@/lib/strategy-builder/types';

interface BlockSignalEntry {
  name: string;
  logic?: 'AND' | 'OR';
  recheck?: {
    mode?: 'WITHIN' | 'AT';
    barDelay?: number;
  };
}

interface BlockConfigDialogProps {
  open: boolean;
  block: Block | null;
  blockIndex: number;
  onSave: (index: number, data: Record<string, unknown>) => void;
  onClose: () => void;
}

export function BlockConfigDialog({ open, block, blockIndex, onSave, onClose }: BlockConfigDialogProps) {
  const [name, setName] = useState('');
  const [logic, setLogic] = useState<'AND' | 'OR'>('AND');
  const [signals, setSignals] = useState<BlockSignalEntry[]>([]);

  useEffect(() => {
    if (!block) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setName((block.data?.name as string) ?? '');
    setLogic(((block.data?.logic as string) === 'OR' ? 'OR' : 'AND') as 'AND' | 'OR');
    setSignals(((block.data?.signals as BlockSignalEntry[]) ?? []).map((s) => ({ ...s })));
  }, [block, open]);

  if (!open || !block) return null;

  const isExit = block.type === BlockType.EXIT_CONDITION;

  const handleSignalLogicChange = (idx: number, val: 'AND' | 'OR') => {
    setSignals((prev) => prev.map((s, i) => (i === idx ? { ...s, logic: val } : s)));
  };

  const handleRecheckModeChange = (idx: number, mode: 'WITHIN' | 'AT' | '') => {
    setSignals((prev) =>
      prev.map((s, i) =>
        i === idx
          ? { ...s, recheck: mode ? { ...(s.recheck ?? {}), mode } : undefined }
          : s,
      ),
    );
  };

  const handleRecheckDelayChange = (idx: number, barDelay: number) => {
    setSignals((prev) =>
      prev.map((s, i) =>
        i === idx ? { ...s, recheck: { ...(s.recheck ?? {}), barDelay } } : s,
      ),
    );
  };

  const handleSave = () => {
    onSave(blockIndex, { name, logic, signals });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="rounded-lg shadow-2xl w-[500px] max-h-[80vh] flex flex-col" style={{ background: 'var(--bg-panel)', border: '1px solid var(--border)' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
          <h2 className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Configure Block #{blockIndex + 1}</h2>
          <button onClick={onClose} className="text-lg leading-none transition-colors" style={{ color: 'var(--text-muted)' }}>✕</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {/* Block name */}
          <div className="space-y-1">
            <label className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Block Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-2 py-1.5 rounded text-sm focus:outline-none"
              style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--input-text)' }}
            />
          </div>

          {/* Block logic */}
          {!isExit && (
            <div className="space-y-1">
              <label className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Block Logic</label>
              <div className="flex gap-2">
                {(['AND', 'OR'] as const).map((l) => (
                  <button
                    key={l}
                    onClick={() => setLogic(l)}
                    className="px-4 py-1.5 rounded text-xs font-semibold border transition-colors"
                    style={logic === l
                      ? l === 'AND'
                        ? { background: 'var(--accent-green-mid)', color: 'var(--btn-primary-text)', borderColor: 'var(--accent-green-dark)' }
                        : { background: 'var(--accent-blue-mid)', color: 'var(--btn-primary-text)', borderColor: 'var(--accent-blue-dark)' }
                      : { background: 'var(--bg-card)', color: 'var(--text-secondary)', borderColor: 'var(--border)' }
                    }
                  >
                    {l === 'AND' ? 'REQUIRED (AND)' : 'OPTIONAL (OR)'}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Signals */}
          {signals.length > 0 && (
            <div className="space-y-2">
              <label className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>Signals</label>
              {signals.map((sig, idx) => (
                <div key={idx} className="rounded p-3 space-y-2" style={{ border: '1px solid var(--border)', background: 'var(--bg-card)' }}>
                  <div className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{sig.name}</div>

                  {/* Signal logic */}
                  {!isExit && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs w-16" style={{ color: 'var(--text-muted)' }}>Logic:</span>
                      {(['AND', 'OR'] as const).map((l) => (
                        <button
                          key={l}
                          onClick={() => handleSignalLogicChange(idx, l)}
                          className="px-2 py-0.5 rounded text-xs border transition-colors"
                          style={(sig.logic ?? 'AND') === l
                            ? l === 'AND'
                              ? { background: 'var(--accent-green-mid)', color: 'var(--btn-primary-text)', borderColor: 'var(--accent-green-dark)' }
                              : { background: 'var(--accent-blue-mid)', color: 'var(--btn-primary-text)', borderColor: 'var(--accent-blue-dark)' }
                            : { background: 'var(--bg-panel)', color: 'var(--text-secondary)', borderColor: 'var(--border)' }
                          }
                        >
                          {l}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Recheck */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs w-16" style={{ color: 'var(--text-muted)' }}>Recheck:</span>
                    <select
                      value={sig.recheck?.mode ?? ''}
                      onChange={(e) => handleRecheckModeChange(idx, e.target.value as 'WITHIN' | 'AT' | '')}
                      className="px-2 py-0.5 rounded text-xs focus:outline-none"
                      style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--input-text)' }}
                    >
                      <option value="">None</option>
                      <option value="WITHIN">WITHIN</option>
                      <option value="AT">AT</option>
                    </select>
                    {sig.recheck?.mode && (
                      <>
                        <input
                          type="number"
                          min={1}
                          max={100}
                          value={sig.recheck?.barDelay ?? 1}
                          onChange={(e) => handleRecheckDelayChange(idx, Number(e.target.value))}
                          className="w-16 px-2 py-0.5 rounded text-xs focus:outline-none"
                          style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--input-text)' }}
                        />
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>bars</span>
                        <button
                          onClick={() => handleRecheckModeChange(idx, '')}
                          className="ml-1 text-xs px-1 rounded transition-colors"
                          style={{ color: 'var(--text-muted)' }}
                          title="Remove recheck"
                        >✕</button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-4 py-3" style={{ borderTop: '1px solid var(--border)' }}>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm rounded transition-colors"
            style={{ background: 'var(--bg-card)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-1.5 text-sm rounded transition-colors"
            style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)', border: '1px solid var(--accent-blue)' }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

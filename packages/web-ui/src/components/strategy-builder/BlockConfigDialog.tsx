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
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-[500px] max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-100">Configure Block #{blockIndex + 1}</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 text-lg leading-none">✕</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {/* Block name */}
          <div className="space-y-1">
            <label className="text-xs text-zinc-500 font-medium uppercase tracking-wide">Block Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-2 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-zinc-500"
            />
          </div>

          {/* Block logic */}
          {!isExit && (
            <div className="space-y-1">
              <label className="text-xs text-zinc-500 font-medium uppercase tracking-wide">Block Logic</label>
              <div className="flex gap-2">
                {(['AND', 'OR'] as const).map((l) => (
                  <button
                    key={l}
                    onClick={() => setLogic(l)}
                    className={`px-4 py-1.5 rounded text-xs font-semibold border transition-colors ${
                      logic === l
                        ? l === 'AND'
                          ? 'bg-emerald-900 text-emerald-300 border-emerald-700'
                          : 'bg-blue-900 text-blue-300 border-blue-700'
                        : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:border-zinc-500'
                    }`}
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
              <label className="text-xs text-zinc-500 font-medium uppercase tracking-wide">Signals</label>
              {signals.map((sig, idx) => (
                <div key={idx} className="rounded border border-zinc-700 bg-zinc-800 p-3 space-y-2">
                  <div className="text-xs font-medium text-zinc-100">{sig.name}</div>

                  {/* Signal logic */}
                  {!isExit && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-zinc-500 w-16">Logic:</span>
                      {(['AND', 'OR'] as const).map((l) => (
                        <button
                          key={l}
                          onClick={() => handleSignalLogicChange(idx, l)}
                          className={`px-2 py-0.5 rounded text-xs border transition-colors ${
                            (sig.logic ?? 'AND') === l
                              ? l === 'AND'
                                ? 'bg-emerald-900 text-emerald-300 border-emerald-700'
                                : 'bg-blue-900 text-blue-300 border-blue-700'
                              : 'bg-zinc-700 text-zinc-400 border-zinc-600 hover:border-zinc-500'
                          }`}
                        >
                          {l}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Recheck */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-zinc-500 w-16">Recheck:</span>
                    <select
                      value={sig.recheck?.mode ?? ''}
                      onChange={(e) => handleRecheckModeChange(idx, e.target.value as 'WITHIN' | 'AT' | '')}
                      className="px-2 py-0.5 rounded bg-zinc-700 border border-zinc-600 text-xs text-zinc-300 focus:outline-none"
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
                          className="w-16 px-2 py-0.5 rounded bg-zinc-700 border border-zinc-600 text-xs text-zinc-300 focus:outline-none"
                        />
                        <span className="text-xs text-zinc-500">bars</span>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-zinc-800">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-1.5 text-sm bg-blue-700 hover:bg-blue-600 text-white rounded transition-colors"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

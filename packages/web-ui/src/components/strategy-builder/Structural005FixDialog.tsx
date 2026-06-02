'use client';

import React, { useState, useMemo } from 'react';
import { Wrench, Trash2, Pencil, Target, FileEdit, AlertTriangle, BarChart3 } from 'lucide-react';

export interface Structural005FixDialogProps {
  strategyId: string;
  blockName: string;
  signalName: string;
  duplicateIndices: number[];
  signalDetails: Array<{ index: number; name: string; weight: number; exitCount: number }>;
  onConfirm: (mode: 'remove' | 'rename', targetIndex: number, newName?: string) => void;
  onCancel: () => void;
}

export const Structural005FixDialog: React.FC<Structural005FixDialogProps> = ({
  blockName,
  signalName,
  duplicateIndices,
  signalDetails,
  onConfirm,
  onCancel,
}) => {
  const [mode, setMode] = useState<'remove' | 'rename'>('remove');
  const [selectedIndex, setSelectedIndex] = useState(duplicateIndices[0] ?? 0);
  const [newName, setNewName] = useState('');
  const [nameError, setNameError] = useState('');

  const selectedSignal = useMemo(
    () => signalDetails.find((s) => s.index === selectedIndex),
    [selectedIndex, signalDetails]
  );

  const validateName = (name: string) => {
    if (mode !== 'rename') return true;
    if (!name.trim()) {
      setNameError('Name is required');
      return false;
    }
    if (!/^[a-zA-Z0-9_]+$/.test(name)) {
      setNameError('Name must be alphanumeric with underscores only');
      return false;
    }
    if (signalDetails.some((s) => s.name === name)) {
      setNameError('Name already exists in this block');
      return false;
    }
    setNameError('');
    return true;
  };

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setNewName(value);
    validateName(value);
  };

  const handleConfirm = () => {
    if (mode === 'rename' && !validateName(newName)) return;
    onConfirm(mode, selectedIndex, mode === 'rename' ? newName : undefined);
  };

  return (
    <div className="space-y-4">
      {/* Mode Selection */}
      <div className="rounded-lg border p-4" style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--bg-card) 30%, transparent)' }}>
        <p className="text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
          <Wrench size={12} strokeWidth={1.75} /> Fix Method
        </p>
        <div className="space-y-2">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="radio"
              name="fix-mode"
              value="remove"
              checked={mode === 'remove'}
              onChange={(e) => {
                setMode(e.target.value as 'remove' | 'rename');
                setNameError('');
              }}
              className="w-4 h-4"
              style={{ accentColor: 'var(--accent-blue)' }}
            />
            <span className="text-sm flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
              <Trash2 size={14} strokeWidth={1.75} /> <strong>Remove</strong> — Delete one duplicate signal
            </span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="radio"
              name="fix-mode"
              value="rename"
              checked={mode === 'rename'}
              onChange={(e) => {
                setMode(e.target.value as 'remove' | 'rename');
                setNameError('');
              }}
              className="w-4 h-4"
              style={{ accentColor: 'var(--accent-blue)' }}
            />
            <span className="text-sm flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
              <Pencil size={14} strokeWidth={1.75} /> <strong>Rename</strong> — Rename one signal to make it unique
            </span>
          </label>
        </div>
      </div>

      {/* Target Selection */}
      <div className="rounded-lg border p-4" style={{ borderColor: 'var(--border)', background: 'color-mix(in srgb, var(--bg-card) 30%, transparent)' }}>
        <p className="text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
          <Target size={12} strokeWidth={1.75} /> Select Target Signal
        </p>
        <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
          Block: <strong>{blockName}</strong> • Duplicates of: <strong>{signalName}</strong>
        </p>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {signalDetails.map((signal) => (
            <label
              key={`signal-${signal.index}`}
              className="flex items-center gap-3 p-2 rounded cursor-pointer transition-colors"
              style={{
                background: selectedIndex === signal.index ? 'color-mix(in srgb, var(--accent-blue) 10%, transparent)' : 'transparent',
                borderLeft: selectedIndex === signal.index ? '3px solid var(--accent-blue)' : '3px solid transparent',
              }}
            >
              <input
                type="radio"
                name="target-signal"
                value={signal.index}
                checked={selectedIndex === signal.index}
                onChange={(e) => setSelectedIndex(parseInt(e.target.value))}
                className="w-4 h-4 flex-shrink-0"
                style={{ accentColor: 'var(--accent-blue)' }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                  Signal #{signal.index + 1}
                </p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Name: {signal.name} • Weight: {signal.weight} • Exits: {signal.exitCount}
                </p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Rename Input (conditional) */}
      {mode === 'rename' && (
        <div className="rounded-lg border p-4" style={{ borderColor: nameError ? 'var(--accent-red)' : 'var(--border)', background: 'color-mix(in srgb, var(--bg-card) 30%, transparent)' }}>
          <label className="block">
            <p className="text-xs font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
              <FileEdit size={12} strokeWidth={1.75} /> New Name
            </p>
            <input
              type="text"
              value={newName}
              onChange={handleNameChange}
              placeholder="e.g., AT_ASIA_50_RENAMED"
              className="w-full px-3 py-2 rounded border text-sm"
              style={{
                borderColor: nameError ? 'var(--accent-red)' : 'var(--border)',
                background: 'var(--bg-deep)',
                color: 'var(--text-secondary)',
              }}
            />
          </label>
          {nameError && (
            <p className="text-xs mt-2 flex items-center gap-1.5" style={{ color: 'var(--accent-red)' }}>
              <AlertTriangle size={12} strokeWidth={1.75} /> {nameError}
            </p>
          )}
        </div>
      )}

      {/* Impact Preview */}
      {selectedSignal && (
        <div
          className="rounded-lg px-4 py-3"
          style={{
            borderLeft: '4px solid var(--accent-blue)',
            background: 'color-mix(in srgb, var(--bg-deep) 60%, transparent)',
          }}
        >
          <p className="text-xs font-semibold uppercase tracking-wider mb-1.5 flex items-center gap-1.5" style={{ color: 'var(--accent-blue)' }}>
            <BarChart3 size={12} strokeWidth={1.75} /> Impact Preview
          </p>
          <div className="text-xs space-y-1" style={{ color: 'var(--text-secondary)' }}>
            <p>
              {mode === 'remove' && (
                <>
                  <strong>Removing Signal #{selectedSignal.index + 1}:</strong> Will reduce block contribution by {selectedSignal.weight} pts
                </>
              )}
              {mode === 'rename' && (
                <>
                  <strong>Renaming Signal #{selectedSignal.index + 1}:</strong> Changing "{selectedSignal.name}" to "{newName || '?'}" will eliminate the duplicate
                </>
              )}
            </p>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end gap-2 pt-2">
        <button
          onClick={onCancel}
          className="px-4 py-2 rounded text-sm font-medium transition-colors"
          style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--border)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
        >
          Cancel
        </button>
        <button
          onClick={handleConfirm}
          disabled={mode === 'rename' && !newName.trim()}
          className="px-4 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50"
          style={{ background: 'var(--btn-confirm-bg)', color: 'var(--btn-primary-text)' }}
        >
          {mode === 'remove' ? 'Remove Signal' : 'Rename Signal'}
        </button>
      </div>
    </div>
  );
};

export default Structural005FixDialog;

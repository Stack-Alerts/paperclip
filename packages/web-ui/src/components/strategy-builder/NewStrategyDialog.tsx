'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useStrategyStore } from '@/hooks/strategy-builder/useStrategyStore';
import { InfoTooltip } from './InfoTooltip';

export interface NewStrategyDialogProps {
  open: boolean;
  onClose: () => void;
}

export function NewStrategyDialog({ open, onClose }: NewStrategyDialogProps) {
  const { createStrategy } = useStrategyStore();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  // Focus name on open
  useEffect(() => {
    if (open) {
      setName('');
      setDescription('');
      setError(null);
      setTimeout(() => nameRef.current?.focus(), 50);
    }
  }, [open]);

  const handleSubmit = useCallback(async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError('Strategy name is required.');
      nameRef.current?.focus();
      return;
    }
    setIsCreating(true);
    setError(null);
    try {
      await createStrategy(trimmed, description.trim() || undefined);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create strategy.');
    } finally {
      setIsCreating(false);
    }
  }, [name, description, createStrategy, onClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) handleSubmit();
      if (e.key === 'Escape') onClose();
    },
    [handleSubmit, onClose],
  );

  if (!open) return null;

  const valid = name.trim().length > 0;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-strategy-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
      onKeyDown={handleKeyDown}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-lg rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
          <h2 id="new-strategy-title" className="text-base font-semibold text-zinc-50">
            📝 Create New Strategy
          </h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 text-lg leading-none"
            aria-label="Close dialog"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {/* Name */}
          <div className="space-y-1.5">
            <label htmlFor="new-strategy-name" className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
              Strategy Name <span className="text-red-400">*</span>
            </label>
            <InfoTooltip id="new-strategy-name-input">
              <input
                ref={nameRef}
                id="new-strategy-name"
                type="text"
                value={name}
                onChange={(e) => { setName(e.target.value); setError(null); }}
                placeholder="e.g., MA_Crossover_RSI"
                maxLength={100}
                className={`w-full px-3 py-2 rounded bg-zinc-800 border text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none ${
                  error ? 'border-red-600 focus:border-red-500' : 'border-zinc-700 focus:border-zinc-500'
                }`}
              />
            </InfoTooltip>
            {error && <p className="text-xs text-red-400">{error}</p>}
            <p className="text-xs text-zinc-500">Unique identifier stored in the database</p>
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label htmlFor="new-strategy-desc" className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
              Description <span className="text-zinc-600">(optional)</span>
            </label>
            <InfoTooltip id="new-strategy-desc-input">
              <textarea
                id="new-strategy-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the market thesis or signal combination…"
                rows={4}
                className="w-full px-3 py-2 rounded bg-zinc-800 border border-zinc-700 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-500 resize-none"
              />
            </InfoTooltip>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-zinc-800">
          <InfoTooltip id="new-strategy-cancel-btn">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-sm font-medium transition-colors"
            >
              Cancel
            </button>
          </InfoTooltip>
          <InfoTooltip id="new-strategy-create-btn">
            <button
              onClick={handleSubmit}
              disabled={!valid || isCreating}
              className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {isCreating ? 'Creating…' : 'Create Strategy'}
            </button>
          </InfoTooltip>
        </div>
      </div>
    </div>
  );
}

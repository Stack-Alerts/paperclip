'use client';

import { useState, useCallback, useRef } from 'react';
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
  const [cancelHover, setCancelHover] = useState(false);
  const [createHover, setCreateHover] = useState(false);

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
      <div
        className="relative w-full max-w-lg rounded-lg shadow-2xl mx-4"
        style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)' }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: '1px solid var(--bg-card)' }}
        >
          <h2 id="new-strategy-title" className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            📝 Create New Strategy
          </h2>
          <button
            onClick={onClose}
            className="text-lg leading-none transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
            aria-label="Close dialog"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {/* Name */}
          <div className="space-y-1.5">
            <label htmlFor="new-strategy-name" className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>
              Strategy Name <span style={{ color: 'var(--accent-red)' }}>*</span>
            </label>
            <InfoTooltip id="new-strategy-name-input">
              <input
                ref={nameRef}
                id="new-strategy-name"
                type="text"
                autoFocus
                value={name}
                onChange={(e) => { setName(e.target.value); setError(null); }}
                placeholder="e.g., MA_Crossover_RSI"
                maxLength={100}
                className="w-full px-3 py-2 rounded text-sm focus:outline-none"
                style={{
                  background: 'var(--input-bg)',
                  border: `1px solid ${error ? 'var(--accent-red)' : 'var(--input-border)'}`,
                  color: 'var(--input-text)',
                }}
              />
            </InfoTooltip>
            {error && <p className="text-xs" style={{ color: 'var(--accent-red)' }}>{error}</p>}
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Unique identifier stored in the database</p>
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label htmlFor="new-strategy-desc" className="text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>
              Description <span style={{ color: 'var(--text-muted)' }}>(optional)</span>
            </label>
            <InfoTooltip id="new-strategy-desc-input">
              <textarea
                id="new-strategy-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe the market thesis or signal combination…"
                rows={4}
                className="w-full px-3 py-2 rounded text-sm focus:outline-none resize-none"
                style={{
                  background: 'var(--input-bg)',
                  border: '1px solid var(--input-border)',
                  color: 'var(--input-text)',
                }}
              />
            </InfoTooltip>
          </div>
        </div>

        {/* Footer */}
        <div
          className="flex justify-end gap-2 px-6 py-4"
          style={{ borderTop: '1px solid var(--bg-card)' }}
        >
          <InfoTooltip id="new-strategy-cancel-btn">
            <button
              onClick={onClose}
              onMouseEnter={() => setCancelHover(true)}
              onMouseLeave={() => setCancelHover(false)}
              className="px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{
                background: cancelHover ? 'var(--bg-hover)' : 'var(--bg-panel)',
                color: 'var(--text-primary)',
              }}
            >
              Cancel
            </button>
          </InfoTooltip>
          <InfoTooltip id="new-strategy-create-btn">
            <button
              onClick={handleSubmit}
              disabled={!valid || isCreating}
              onMouseEnter={() => setCreateHover(true)}
              onMouseLeave={() => setCreateHover(false)}
              className="px-4 py-2 rounded text-sm font-medium disabled:opacity-50 transition-colors"
              style={{
                background: createHover ? 'var(--accent-blue-dark)' : 'var(--accent-blue)',
                color: 'var(--btn-primary-text)',
              }}
            >
              {isCreating ? 'Creating…' : 'Create Strategy'}
            </button>
          </InfoTooltip>
        </div>
      </div>
    </div>
  );
}

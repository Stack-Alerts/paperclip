'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';

export interface AdminPinDialogProps {
  open: boolean;
  /** setup_mode=true: create a new PIN; false: verify existing PIN */
  setupMode?: boolean;
  onSuccess: (pin: string) => void;
  onCancel: () => void;
}

export const AdminPinDialog: React.FC<AdminPinDialogProps> = ({
  open,
  setupMode = false,
  onSuccess,
  onCancel,
}) => {
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [error, setError] = useState('');
  const [prevOpen, setPrevOpen] = useState(open);
  const inputRef = useRef<HTMLInputElement>(null);

  if (prevOpen !== open && open) {
    setPrevOpen(open);
    setPin('');
    setConfirmPin('');
    setError('');
  } else if (prevOpen !== open) {
    setPrevOpen(open);
  }

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (pin.length < 4) {
        setError('PIN must be at least 4 digits.');
        return;
      }
      if (setupMode && pin !== confirmPin) {
        setError('PINs do not match.');
        return;
      }
      onSuccess(pin);
    },
    [pin, confirmPin, setupMode, onSuccess]
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="rounded-lg shadow-2xl w-full max-w-sm mx-4 border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3 border-b px-6 py-4" style={{ borderColor: 'var(--border)' }}>
          <span className="text-xl">🔐</span>
          <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            {setupMode ? 'Set Admin PIN' : 'Admin Authentication'}
          </h2>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            {setupMode
              ? 'Create a PIN to protect admin settings.'
              : 'Enter your admin PIN to access restricted settings.'}
          </p>
          <div className="space-y-2">
            <label className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>PIN</label>
            <input
              ref={inputRef}
              type="password"
              inputMode="numeric"
              pattern="[0-9]*"
              maxLength={8}
              value={pin}
              onChange={(e) => {
                setPin(e.target.value.replace(/\D/g, ''));
                setError('');
              }}
              className="w-full rounded px-3 py-2 text-sm focus:outline-none tracking-widest border"
              style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
              placeholder="••••"
            />
          </div>
          {setupMode && (
            <div className="space-y-2">
              <label className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>Confirm PIN</label>
              <input
                type="password"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={8}
                value={confirmPin}
                onChange={(e) => {
                  setConfirmPin(e.target.value.replace(/\D/g, ''));
                  setError('');
                }}
                className="w-full rounded px-3 py-2 text-sm focus:outline-none tracking-widest border"
                style={{ background: 'var(--input-bg)', borderColor: 'var(--input-border)', color: 'var(--input-text)' }}
                placeholder="••••"
              />
            </div>
          )}
          {error && <p className="text-xs" style={{ color: 'var(--accent-red)' }}>{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{ background: 'var(--bg-hover)', color: 'var(--text-primary)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded text-sm font-medium transition-colors"
              style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
            >
              {setupMode ? 'Set PIN' : 'Unlock'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AdminPinDialog;

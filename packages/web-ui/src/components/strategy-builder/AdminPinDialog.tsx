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
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setPin('');
      setConfirmPin('');
      setError('');
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
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-sm mx-4">
        <div className="flex items-center gap-3 border-b border-zinc-700 px-6 py-4">
          <span className="text-xl">🔐</span>
          <h2 className="text-base font-semibold text-zinc-100">
            {setupMode ? 'Set Admin PIN' : 'Admin Authentication'}
          </h2>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <p className="text-sm text-zinc-400">
            {setupMode
              ? 'Create a PIN to protect admin settings.'
              : 'Enter your admin PIN to access restricted settings.'}
          </p>
          <div className="space-y-2">
            <label className="text-xs font-medium text-zinc-300">PIN</label>
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
              className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:border-blue-500 tracking-widest"
              placeholder="••••"
            />
          </div>
          {setupMode && (
            <div className="space-y-2">
              <label className="text-xs font-medium text-zinc-300">Confirm PIN</label>
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
                className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-zinc-100 text-sm focus:outline-none focus:border-blue-500 tracking-widest"
                placeholder="••••"
              />
            </div>
          )}
          {error && <p className="text-xs text-red-400">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
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

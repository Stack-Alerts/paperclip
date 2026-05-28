'use client';

import React, { useState } from 'react';
import { ValidationPanel } from './ValidationPanel';

export interface ValidationDialogProps {
  open: boolean;
  onClose: () => void;
}

export const ValidationDialog: React.FC<ValidationDialogProps> = ({ open, onClose }) => {
  const [closeHover, setCloseHover] = useState(false);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div
        className="rounded-lg shadow-2xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col"
        style={{ background: 'var(--bg-deep)', border: '1px solid var(--border)' }}
      >
        <div
          className="flex items-center justify-between px-6 py-4 flex-shrink-0"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          <div className="flex items-center gap-3">
            <span className="text-xl">✅</span>
            <h2 className="text-base font-semibold" style={{ color: 'var(--text-secondary)' }}>Strategy Validation</h2>
          </div>
          <button
            onClick={onClose}
            className="transition-colors text-xl leading-none"
            style={{ color: closeHover ? 'var(--text-primary)' : 'var(--text-secondary)' }}
            onMouseEnter={() => setCloseHover(true)}
            onMouseLeave={() => setCloseHover(false)}
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <ValidationPanel />
        </div>

        <div
          className="flex justify-end px-6 py-4 flex-shrink-0"
          style={{ borderTop: '1px solid var(--border)' }}
        >
          <button
            onClick={onClose}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-panel)')}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--bg-panel)', color: 'var(--text-primary)' }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ValidationDialog;

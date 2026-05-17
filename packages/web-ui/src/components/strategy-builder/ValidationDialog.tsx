'use client';

import React from 'react';
import { ValidationPanel } from './ValidationPanel';

export interface ValidationDialogProps {
  open: boolean;
  onClose: () => void;
}

export const ValidationDialog: React.FC<ValidationDialogProps> = ({ open, onClose }) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-4xl mx-4 max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between border-b border-zinc-700 px-6 py-4 flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xl">✅</span>
            <h2 className="text-base font-semibold text-zinc-100">Strategy Validation</h2>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-200 transition-colors text-xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <ValidationPanel />
        </div>

        <div className="flex justify-end px-6 py-4 border-t border-zinc-700 flex-shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ValidationDialog;

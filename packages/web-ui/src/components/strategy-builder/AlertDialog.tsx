'use client';

import React, { useState, useCallback } from 'react';

export type AlertIcon = '⚠️' | '✅' | '❌' | 'ℹ️' | '❓';

export interface AlertDialogProps {
  open: boolean;
  title: string;
  heading: string;
  message: string;
  icon?: AlertIcon;
  onClose: () => void;
}

export const AlertDialog: React.FC<AlertDialogProps> = ({
  open,
  title,
  heading,
  message,
  icon = '⚠️',
  onClose,
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-2xl mx-4">
        <div className="flex items-center gap-3 border-b border-zinc-700 px-6 py-4">
          <span className="text-2xl">{icon}</span>
          <h2 className="text-base font-semibold text-zinc-100 flex-1">{title}</h2>
        </div>
        <div className="px-6 py-5 space-y-3">
          <p className="text-lg font-semibold text-zinc-100">{heading}</p>
          <p
            className="text-sm text-zinc-400 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: message }}
          />
        </div>
        <div className="flex justify-end px-6 py-4 border-t border-zinc-700">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            ✓ OK
          </button>
        </div>
      </div>
    </div>
  );
};

export type QuestionResult = 'yes' | 'no' | 'cancel';

export interface QuestionDialogProps {
  open: boolean;
  title: string;
  heading: string;
  message: string;
  icon?: AlertIcon;
  onResult: (result: QuestionResult) => void;
}

export const QuestionDialog: React.FC<QuestionDialogProps> = ({
  open,
  title,
  heading,
  message,
  icon = '❓',
  onResult,
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl w-full max-w-2xl mx-4">
        <div className="flex items-center gap-3 border-b border-zinc-700 px-6 py-4">
          <span className="text-2xl">{icon}</span>
          <h2 className="text-base font-semibold text-zinc-100 flex-1">{title}</h2>
        </div>
        <div className="px-6 py-5 space-y-3">
          <p className="text-lg font-semibold text-zinc-100">{heading}</p>
          <p
            className="text-sm text-zinc-400 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: message }}
          />
        </div>
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-zinc-700">
          <button
            onClick={() => onResult('cancel')}
            className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
          >
            ❌ Cancel
          </button>
          <button
            onClick={() => onResult('no')}
            className="px-4 py-2 rounded bg-zinc-700 text-zinc-200 text-sm font-medium hover:bg-zinc-600 transition-colors"
          >
            🔴 No
          </button>
          <button
            onClick={() => onResult('yes')}
            className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            ✅ Yes
          </button>
        </div>
      </div>
    </div>
  );
};

export function useAlertDialog() {
  const [state, setState] = useState<Omit<AlertDialogProps, 'onClose'> & { open: boolean }>({
    open: false,
    title: '',
    heading: '',
    message: '',
    icon: '⚠️',
  });

  const showAlert = useCallback(
    (title: string, heading: string, message: string, icon: AlertIcon = '⚠️') => {
      setState({ open: true, title, heading, message, icon });
    },
    []
  );

  const closeAlert = useCallback(() => {
    setState((prev) => ({ ...prev, open: false }));
  }, []);

  return { alertState: state, showAlert, closeAlert };
}

export default AlertDialog;

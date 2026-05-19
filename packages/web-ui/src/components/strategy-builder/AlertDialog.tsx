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
      <div className="rounded-lg shadow-2xl w-full max-w-2xl mx-4 border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3 border-b px-6 py-4" style={{ borderColor: 'var(--border)' }}>
          <span className="text-2xl">{icon}</span>
          <h2 className="text-base font-semibold flex-1" style={{ color: 'var(--text-primary)' }}>{title}</h2>
        </div>
        <div className="px-6 py-5 space-y-3">
          <p className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>{heading}</p>
          <p
            className="text-sm leading-relaxed"
            style={{ color: 'var(--text-secondary)' }}
            dangerouslySetInnerHTML={{ __html: message }}
          />
        </div>
        <div className="flex justify-end px-6 py-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
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
      <div className="rounded-lg shadow-2xl w-full max-w-2xl mx-4 border" style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3 border-b px-6 py-4" style={{ borderColor: 'var(--border)' }}>
          <span className="text-2xl">{icon}</span>
          <h2 className="text-base font-semibold flex-1" style={{ color: 'var(--text-primary)' }}>{title}</h2>
        </div>
        <div className="px-6 py-5 space-y-3">
          <p className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>{heading}</p>
          <p
            className="text-sm leading-relaxed"
            style={{ color: 'var(--text-secondary)' }}
            dangerouslySetInnerHTML={{ __html: message }}
          />
        </div>
        <div className="flex justify-end gap-2 px-6 py-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <button
            onClick={() => onResult('cancel')}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--bg-hover)', color: 'var(--text-primary)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
          >
            ❌ Cancel
          </button>
          <button
            onClick={() => onResult('no')}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--bg-hover)', color: 'var(--text-primary)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--border)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
          >
            🔴 No
          </button>
          <button
            onClick={() => onResult('yes')}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{ background: 'var(--accent-blue)', color: 'var(--btn-primary-text)' }}
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

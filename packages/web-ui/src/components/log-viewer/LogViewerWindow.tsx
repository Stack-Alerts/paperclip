'use client';

import React, { useCallback } from 'react';
import { X, Maximize2 } from 'lucide-react';
import { LogViewerPanel } from './LogViewerPanel';
import type { LogViewerPanelProps } from './LogViewerPanel';

export interface LogViewerWindowProps extends LogViewerPanelProps {
  /** Whether the window is visible */
  open: boolean;
  /** Called when the user closes the window */
  onClose: () => void;
  title?: string;
}

/**
 * LogViewerWindow — React port of PyQt5 LogViewerWindow (QDialog).
 *
 * Wraps LogViewerPanel inside a full-screen modal overlay with a title bar
 * and close button, matching the PyQt5 window semantics.
 */
export const LogViewerWindow: React.FC<LogViewerWindowProps> = ({
  open,
  onClose,
  title = 'Log Viewer',
  ...panelProps
}) => {
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose]
  );

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleBackdropClick}
    >
      <div className="relative flex flex-col bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl w-[90vw] max-w-5xl h-[85vh] mx-4">
        {/* Title bar */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800 flex-shrink-0">
          <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
          <div className="flex items-center gap-2">
            <button
              title="Expand"
              className="p-1 text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <Maximize2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              title="Close"
              className="p-1 text-zinc-500 hover:text-zinc-200 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          <LogViewerPanel {...panelProps} />
        </div>
      </div>
    </div>
  );
};

export default LogViewerWindow;

'use client';
import type { ReactNode } from 'react';
import { useState } from 'react';

interface Props {
  tip: string;
  children: ReactNode;
}

export function Tooltip({ tip, children }: Props) {
  const [visible, setVisible] = useState(false);
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-1.5 -translate-x-1/2 whitespace-pre-wrap rounded-lg px-2.5 py-1.5 text-xs shadow-lg max-w-xs"
          style={{ border: '1px solid var(--tooltip-border)', background: 'var(--tooltip-bg)', color: 'var(--tooltip-text)' }}
        >
          {tip}
        </span>
      )}
    </span>
  );
}

'use client';
import type { ReactNode } from 'react';
import type { WsStatus } from '@/hooks/useWebSocket';
import { WsStatusBadge } from './WsStatusBadge';

interface Props {
  title: string;
  subtitle?: string;
  status: WsStatus;
  children: ReactNode;
  className?: string;
}

export function PanelShell({ title, subtitle, status, children, className = '' }: Props) {
  return (
    <section
      className={`flex flex-col rounded-xl ${className}`}
      style={{ border: '1px solid var(--border)', background: 'var(--surface-panel)' }}
      aria-label={title}
    >
      <header className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <div>
          <h2 className="text-sm font-semibold tracking-wide" style={{ color: 'var(--text-primary)' }}>{title}</h2>
          {subtitle && <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{subtitle}</p>}
        </div>
        <WsStatusBadge status={status} />
      </header>
      <div className="flex-1 overflow-auto p-4">{children}</div>
    </section>
  );
}

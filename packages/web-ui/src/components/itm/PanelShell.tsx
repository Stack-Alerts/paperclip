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
      className={`flex flex-col rounded-xl border border-zinc-800 bg-zinc-900 ${className}`}
      aria-label={title}
    >
      <header className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100 tracking-wide">{title}</h2>
          {subtitle && <p className="text-xs text-zinc-500 mt-0.5">{subtitle}</p>}
        </div>
        <WsStatusBadge status={status} />
      </header>
      <div className="flex-1 overflow-auto p-4">{children}</div>
    </section>
  );
}

'use client';
import type { WsStatus } from '@/hooks/useWebSocket';

const COLOR: Record<WsStatus, string> = {
  connecting: 'bg-yellow-400',
  open: 'bg-emerald-400',
  closed: 'bg-zinc-500',
  error: 'bg-red-500',
};

const LABEL: Record<WsStatus, string> = {
  connecting: 'Connecting…',
  open: 'Live',
  closed: 'Reconnecting…',
  error: 'Error',
};

export function WsStatusBadge({ status }: { status: WsStatus }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium text-white"
      title={`WebSocket status: ${status}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${COLOR[status]}`} />
      <span className={`${COLOR[status]} rounded-full px-1.5 py-0.5`}>
        {LABEL[status]}
      </span>
    </span>
  );
}

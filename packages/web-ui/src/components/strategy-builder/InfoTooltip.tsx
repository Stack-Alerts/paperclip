'use client';

import React, { ReactNode } from 'react';
import { useTooltipRegistry } from './Providers';

interface InfoTooltipProps {
  id: string;
  children: ReactNode;
  className?: string;
}

export function InfoTooltip({ id, children, className = '' }: InfoTooltipProps) {
  const { getTooltip } = useTooltipRegistry();
  const tooltip = getTooltip(id);

  return (
    <div
      className={`relative inline-flex items-center cursor-help ${className}`}
      title={tooltip}
      data-tooltip-id={id}
    >
      {children}
      {tooltip && (
        <span className="ml-1 inline-flex items-center justify-center w-4 h-4 text-xs bg-zinc-700 text-zinc-50 rounded-full">
          ?
        </span>
      )}
    </div>
  );
}

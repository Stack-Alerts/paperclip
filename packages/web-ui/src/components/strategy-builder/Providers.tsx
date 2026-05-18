'use client';

import React, { createContext, useContext, ReactNode } from 'react';

interface TooltipContextType {
  getTooltip: (id: string) => string | undefined;
}

const FALLBACK: TooltipContextType = { getTooltip: () => undefined };

const TooltipContext = createContext<TooltipContextType>(FALLBACK);

export const useTooltipRegistry = () => useContext(TooltipContext);

interface ProvidersProps {
  children: ReactNode;
  tooltips?: Record<string, string>;
}

export function Providers({ children, tooltips = {} }: ProvidersProps) {
  const contextValue: TooltipContextType = {
    getTooltip: (id: string) => tooltips[id],
  };

  return (
    <TooltipContext.Provider value={contextValue}>
      {children}
    </TooltipContext.Provider>
  );
}

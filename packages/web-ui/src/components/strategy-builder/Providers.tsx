'use client';

import React, { createContext, useContext, ReactNode } from 'react';

interface TooltipContextType {
  getTooltip: (id: string) => string | undefined;
}

const TooltipContext = createContext<TooltipContextType | undefined>(undefined);

export const useTooltipRegistry = () => {
  const context = useContext(TooltipContext);
  if (!context) {
    throw new Error('useTooltipRegistry must be used within TooltipProvider');
  }
  return context;
};

interface ProvidersProps {
  children: ReactNode;
  tooltips: Record<string, string>;
}

export function Providers({ children, tooltips }: ProvidersProps) {
  const contextValue: TooltipContextType = {
    getTooltip: (id: string) => tooltips[id],
  };

  return (
    <TooltipContext.Provider value={contextValue}>
      <div className="dark">{children}</div>
    </TooltipContext.Provider>
  );
}

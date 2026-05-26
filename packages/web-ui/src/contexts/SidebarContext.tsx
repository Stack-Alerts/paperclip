'use client';

import React, { createContext, useContext, useState, ReactNode, Suspense } from 'react';

interface SidebarContextType {
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

function SidebarProviderContent({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <SidebarContext.Provider value={{ collapsed, setCollapsed }}>
      {children}
    </SidebarContext.Provider>
  );
}

export function SidebarProvider({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={null}>
      <SidebarProviderContent>{children}</SidebarProviderContent>
    </Suspense>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (!context) {
    return { collapsed: false, setCollapsed: () => {} };
  }
  return context;
}

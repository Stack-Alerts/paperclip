'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export interface SidebarItem {
  label: string;
  href: string;
  icon: string;
}

const NAV_ITEMS: SidebarItem[] = [
  { label: 'Live Trading', href: '/', icon: '📊' },
  { label: 'Strategy Builder', href: '/strategy-builder', icon: '🏗️' },
  { label: 'Backtest', href: '/backtest', icon: '🔬' },
  { label: 'Data Management', href: '/data-management', icon: '🗄️' },
  { label: 'Log Viewer', href: '/log-viewer', icon: '📋' },
  { label: 'Settings', href: '/settings', icon: '⚙️' },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col w-16 bg-zinc-950 border-r border-zinc-800 h-full flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center justify-center h-14 border-b border-zinc-800">
        <span className="text-xl font-bold text-blue-500">₿</span>
      </div>

      {/* Navigation Items */}
      <div className="flex flex-col flex-1 py-2 gap-1">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === '/'
            ? pathname === '/'
            : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              className={`flex flex-col items-center justify-center h-14 gap-0.5 text-center transition-colors group relative ${
                isActive
                  ? 'bg-blue-900/30 text-blue-400 border-r-2 border-blue-500'
                  : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50'
              }`}
            >
              <span className="text-lg leading-none">{item.icon}</span>
              <span className="text-[9px] leading-tight font-medium px-0.5 truncate w-full text-center">
                {item.label.split(' ')[0]}
              </span>

              {/* Tooltip on hover */}
              <div className="absolute left-full ml-2 px-2 py-1 bg-zinc-800 text-zinc-100 text-xs rounded shadow-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                {item.label}
              </div>
            </Link>
          );
        })}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-center h-12 border-t border-zinc-800">
        <span className="text-zinc-700 text-xs">BTE</span>
      </div>
    </nav>
  );
};

export default Sidebar;

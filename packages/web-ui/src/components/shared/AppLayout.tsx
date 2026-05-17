'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  Database,
  TerminalSquare,
  Settings,
  Layers,
  Menu,
  X,
  Activity,
} from 'lucide-react';

const navItems = [
  { href: '/strategy-builder', label: 'Strategy Builder', icon: Layers },
  { href: '/backtest', label: 'Backtest', icon: BarChart3 },
  { href: '/data-management', label: 'Data Management', icon: Database },
  { href: '/log-viewer', label: 'Log Viewer', icon: TerminalSquare },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-gray-50">
      <aside
        className={`bg-gray-900 text-white flex-shrink-0 transition-all duration-200 ${
          collapsed ? 'w-16' : 'w-56'
        } border-r border-gray-800 flex flex-col`}
      >
        <div className="flex items-center justify-between p-3 border-b border-gray-800">
          {!collapsed && (
            <div className="flex items-center gap-2 min-w-0">
              <Activity className="w-4 h-4 text-blue-400 flex-shrink-0" />
              <span className="text-sm font-bold truncate text-gray-100">BTC Trade Engine</span>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 hover:bg-gray-800 rounded transition-colors ml-auto"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <Menu className="w-4 h-4" /> : <X className="w-4 h-4" />}
          </button>
        </div>

        <nav className="flex-1 py-3 space-y-1 px-2">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== '/' && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                title={label}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  active
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {!collapsed && <span className="truncate">{label}</span>}
              </Link>
            );
          })}
        </nav>

        {!collapsed && (
          <div className="p-3 border-t border-gray-800">
            <p className="text-xs text-gray-600">PyQt5 Web Port</p>
          </div>
        )}
      </aside>

      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}

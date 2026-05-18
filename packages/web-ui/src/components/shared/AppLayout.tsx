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
    <div className="flex h-screen" style={{ background: 'var(--app-bg)' }}>
      <aside
        className={`flex-shrink-0 transition-all duration-200 flex flex-col ${
          collapsed ? 'w-16' : 'w-56'
        }`}
        style={{
          background: 'var(--sidebar-bg)',
          borderRight: '1px solid var(--border)',
          color: 'var(--text-primary)',
        }}
      >
        <div
          className="flex items-center justify-between p-3"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          {!collapsed && (
            <div className="flex items-center gap-2 min-w-0">
              <Activity className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--accent-blue)' }} />
              <span
                className="text-xs font-bold truncate"
                style={{
                  color: 'var(--text-secondary)',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                }}
              >
                BTC Trade Engine
              </span>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 rounded transition-colors ml-auto"
            style={{ color: 'var(--text-secondary)' }}
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
                className="flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors"
                style={active
                  ? {
                      background: 'var(--bg-panel)',
                      color: '#FFFFFF',
                      borderLeft: '3px solid var(--accent-blue)',
                      paddingLeft: '9px',
                    }
                  : { color: 'var(--text-secondary)' }}
              >
                <Icon
                  className="w-4 h-4 flex-shrink-0"
                  style={active ? { color: 'var(--accent-blue)' } : {}}
                />
                {!collapsed && <span className="truncate">{label}</span>}
              </Link>
            );
          })}
        </nav>

        {!collapsed && (
          <div className="p-3" style={{ borderTop: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: '#26C46A',
                  display: 'inline-block',
                }}
              />
              <span
                style={{
                  fontSize: 10,
                  color: '#26C46A',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                }}
              >
                CONNECTED
              </span>
            </div>
          </div>
        )}
      </aside>

      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}

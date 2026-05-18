'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import {
  Home,
  BarChart3,
  Database,
  TerminalSquare,
  Settings,
  Layers,
  Menu,
  ChevronLeft,
} from 'lucide-react';

const NAV_ITEMS = [
  { href: '/', label: 'Home', icon: Home },
  { href: '/strategy-builder', label: 'Strategy Builder', icon: Layers },
  { href: '/backtest', label: 'Backtest', icon: BarChart3 },
  { href: '/data-management', label: 'Data Management', icon: Database },
  { href: '/log-viewer', label: 'Log Viewer', icon: TerminalSquare },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={`flex-shrink-0 flex flex-col transition-all duration-300 ${collapsed ? 'w-16' : 'w-56'}`}
      style={{
        background: 'var(--sidebar-bg)',
        borderRight: '1px solid var(--border)',
        color: 'var(--text-primary)',
      }}
    >
      <div
        className="flex items-center justify-between px-3 py-4"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        {!collapsed && (
          <span className="font-bold text-sm truncate" style={{ color: 'var(--text-primary)' }}>
            BTC Trade Engine
          </span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded transition-colors flex-shrink-0"
          style={{ color: 'var(--sidebar-item-default)' }}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--sidebar-item-hover)'; (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-hover)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--sidebar-item-default)'; (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; }}
        >
          {collapsed ? <Menu className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      <nav className="flex-1 py-3 space-y-1 px-2">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active =
            href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-sm"
              style={active
                ? {
                    background: 'var(--sidebar-item-active-bg)',
                    color: 'var(--sidebar-item-hover)',
                    borderLeft: '2px solid var(--sidebar-item-active-border)',
                    paddingLeft: 10,
                  }
                : {
                    color: 'var(--sidebar-item-default)',
                  }}
              onMouseEnter={e => {
                if (!active) {
                  const el = e.currentTarget as HTMLAnchorElement;
                  el.style.background = 'var(--surface-hover)';
                  el.style.color = 'var(--sidebar-item-hover)';
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  const el = e.currentTarget as HTMLAnchorElement;
                  el.style.background = 'transparent';
                  el.style.color = 'var(--sidebar-item-default)';
                }
              }}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 py-3" style={{ borderTop: '1px solid var(--border)' }}>
        {!collapsed && (
          <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
            NautilusTrader v2
          </p>
        )}
      </div>
    </aside>
  );
}

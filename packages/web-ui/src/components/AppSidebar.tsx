'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import {
  LayoutDashboard,
  Layers,
  BarChart3,
  Zap,
  Database,
  FileBarChart,
  FileCode,
  Settings,
  HelpCircle,
  Menu,
  ChevronLeft,
} from 'lucide-react';

const NAV_ITEMS = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/strategy-builder', label: 'Strategies', icon: Layers },
  { href: '/backtest', label: 'Backtesting', icon: BarChart3 },
  { href: '/signals', label: 'Signals', icon: Zap },
  { href: '/data-management', label: 'Market Data', icon: Database },
  { href: '/reports', label: 'Reports', icon: FileBarChart },
  { href: '/templates', label: 'Templates', icon: FileCode },
  { href: '/settings', label: 'Settings', icon: Settings },
  { href: '/help', label: 'Help & Docs', icon: HelpCircle },
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
        <div className="flex items-center gap-2 flex-1">
          <BarChart3 className="w-5 h-5 flex-shrink-0" style={{ color: '#2E8CFF' }} />
          {!collapsed && (
            <span
              className="font-bold text-xs truncate"
              style={{
                color: 'var(--text-secondary)',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              BTC TRADE ENGINE
            </span>
          )}
        </div>
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
                    background: 'var(--bg-panel)',
                    color: '#FFFFFF',
                    borderLeft: '3px solid var(--accent-blue)',
                    paddingLeft: '9px',
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
              <Icon
                className="w-4 h-4 flex-shrink-0"
                style={active ? { color: '#2E8CFF' } : {}}
              />
              {!collapsed && <span className="truncate">{label}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 py-3" style={{ borderTop: '1px solid var(--border)' }}>
        {!collapsed && (
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
        )}
      </div>
    </aside>
  );
}

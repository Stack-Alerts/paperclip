'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutGrid,
  GitBranch,
  BarChart2,
  Activity,
  TrendingUp,
  FileText,
  Copy,
  Settings,
  HelpCircle,
  Menu,
  ChevronLeft,
} from 'lucide-react';
import { BtcWaveformLogo } from './shared/AppBrand';
import { useSidebar } from '@/contexts/SidebarContext';

const NAV_ITEMS = [
  { href: '/', label: 'Dashboard', icon: LayoutGrid },
  { href: '/strategy-builder', label: 'Strategies', icon: GitBranch },
  { href: '/backtest', label: 'Backtesting', icon: BarChart2 },
  { href: '/signals', label: 'Signals', icon: Activity },
  { href: '/data-management', label: 'Market Data', icon: TrendingUp },
  { href: '/reports', label: 'Reports', icon: FileText },
  { href: '/templates', label: 'Templates', icon: Copy },
  { href: '/settings', label: 'Settings', icon: Settings },
  { href: '/help', label: 'Help & Docs', icon: HelpCircle },
];

export function AppSidebar() {
  const pathname = usePathname();
  const { collapsed, setCollapsed } = useSidebar();

  // Popped-out Strategy Browser window (BTCAAAAA-29978) and popped-out
  // Backtest Configuration window (BTCAAAAA-34600): the standalone routes
  // render no sidebar at all so each popout reads as a focused full-screen
  // dialog matching the board reference.
  if (pathname === '/strategy-browser' || pathname === '/strategy-builder/backtest-config') {
    return null;
  }

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
        className={`flex items-center px-3 py-4 ${collapsed ? 'justify-center' : 'justify-between'}`}
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        {!collapsed && (
          <div className="flex items-center gap-2.5 flex-1 min-w-0">
            <BtcWaveformLogo size={28} />
            <div className="flex flex-col leading-none min-w-0">
              <span className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                BTC
              </span>
              <span
                className="truncate"
                style={{
                  color: 'var(--text-muted)',
                  letterSpacing: '0.07em',
                  textTransform: 'uppercase',
                  fontSize: '9px',
                  marginTop: 1,
                }}
              >
                TRADE ENGINE
              </span>
            </div>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 rounded transition-colors flex-shrink-0"
          style={{ color: 'var(--sidebar-item-default)' }}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          onMouseEnter={e => {
            const el = e.currentTarget as HTMLButtonElement;
            el.style.color = 'var(--sidebar-item-hover)';
            el.style.background = 'var(--surface-hover)';
          }}
          onMouseLeave={e => {
            const el = e.currentTarget as HTMLButtonElement;
            el.style.color = 'var(--sidebar-item-default)';
            el.style.background = 'transparent';
          }}
        >
          {collapsed ? <Menu className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      <nav className="flex-1 py-3 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active =
            href === '/' ? pathname === '/' : pathname === href || pathname.startsWith(href + '/');

          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={`flex items-center text-sm transition-colors py-2.5 ${
                collapsed ? 'justify-center' : 'gap-3'
              }`}
              style={
                active
                  ? {
                      paddingLeft: collapsed ? '8px' : '14px',
                      paddingRight: collapsed ? '8px' : '16px',
                      background: 'var(--sidebar-item-active-bg)',
                      color: 'var(--text-primary)',
                      borderLeft: '2px solid var(--sidebar-item-active-border)',
                    }
                  : {
                      paddingLeft: collapsed ? '8px' : '16px',
                      paddingRight: collapsed ? '8px' : '16px',
                      color: 'var(--sidebar-item-default)',
                    }
              }
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
                style={{
                  width: 18,
                  height: 18,
                  flexShrink: 0,
                  color: active ? 'var(--sidebar-item-active-border)' : 'var(--sidebar-item-default)',
                }}
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
                background: 'var(--status-connected)',
                display: 'inline-block',
              }}
            />
            <span
              style={{
                fontSize: 10,
                color: 'var(--status-connected)',
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

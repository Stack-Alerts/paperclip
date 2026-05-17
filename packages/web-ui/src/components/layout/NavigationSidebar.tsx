'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Zap,
  BarChart2,
  Database,
  ScrollText,
  Settings,
} from 'lucide-react';

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { href: '/', label: 'Live Trading', icon: LayoutDashboard },
  { href: '/strategy-builder', label: 'Strategy Builder', icon: Zap },
  { href: '/backtest', label: 'Backtest', icon: BarChart2 },
  { href: '/data-management', label: 'Data', icon: Database },
  { href: '/log-viewer', label: 'Logs', icon: ScrollText },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function NavigationSidebar() {
  const pathname = usePathname();

  return (
    <nav className="w-16 flex-shrink-0 bg-zinc-950 border-r border-zinc-800 flex flex-col items-center py-4 gap-1">
      <div className="mb-4 text-xs font-bold text-zinc-500 tracking-widest">BTC</div>
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || (href !== '/' && pathname.startsWith(href));
        return (
          <Link
            key={href}
            href={href}
            title={label}
            className={[
              'flex flex-col items-center justify-center w-12 h-12 rounded-lg gap-0.5 transition-colors text-xs',
              active
                ? 'bg-blue-600 text-white'
                : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100',
            ].join(' ')}
          >
            <Icon size={18} />
            <span className="text-[9px] leading-none">{label.split(' ')[0]}</span>
          </Link>
        );
      })}
    </nav>
  );
}

'use client';

import { useTheme, ThemeName } from '@/components/ThemeProvider';

const THEMES: { name: ThemeName; label: string }[] = [
  { name: 'dark', label: 'Dark' },
  { name: 'ocean', label: 'Ocean' },
];

export function ThemeSelector() {
  const { theme, setTheme } = useTheme();

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
      <span style={{ fontSize: 10, color: 'var(--toolbar-accent)', marginRight: 2, letterSpacing: '0.05em' }}>
        THEME
      </span>
      {THEMES.map(t => (
        <button
          key={t.name}
          title={`Switch to ${t.label} theme`}
          onClick={() => setTheme(t.name)}
          style={{
            padding: '1px 7px',
            borderRadius: 3,
            border: `1px solid ${theme === t.name ? 'var(--toolbar-accent)' : 'var(--border)'}`,
            background: theme === t.name ? 'var(--bg-card)' : 'transparent',
            color: theme === t.name ? 'var(--text-secondary)' : 'var(--text-faint)',
            cursor: 'pointer',
            fontSize: 10,
            fontWeight: theme === t.name ? 600 : 400,
            transition: 'all 0.1s ease',
          }}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

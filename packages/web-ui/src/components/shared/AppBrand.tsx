'use client';

export function BtcWaveformLogo({ size = 28 }: { size?: number }) {
  const id = 'btcWaveGrad';
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
    >
      <defs>
        <linearGradient id={id} x1="2" y1="14" x2="26" y2="14" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="var(--core-accent-blue)" />
          <stop offset="100%" stopColor="var(--core-accent-cyan)" />
        </linearGradient>
      </defs>
      <polyline
        points="2,20 5,14 8,21 12,8 16,18 20,10 24,15 26,12"
        stroke={`url(#${id})`}
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export interface AppBrandProps {
  size?: number;
  showWordmark?: boolean;
}

export function AppBrand({ size = 28, showWordmark = true }: AppBrandProps) {
  return (
    <div className="flex items-center gap-2.5 min-w-0">
      <BtcWaveformLogo size={size} />
      {showWordmark && (
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
      )}
    </div>
  );
}

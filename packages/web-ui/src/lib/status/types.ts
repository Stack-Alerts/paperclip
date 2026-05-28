export type StatusVariant = 'idle' | 'info' | 'success' | 'warning' | 'error';

export interface StatusEntry {
  id: string;
  text: string;
  variant: StatusVariant;
  createdAt: number;
  expiresAt?: number;
}

export interface StatusEmitOptions {
  variant?: StatusVariant;
  duration?: number;
}

export interface StatusBarSettings {
  tickerMode: boolean;
}

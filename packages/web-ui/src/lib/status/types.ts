export type StatusVariant = 'idle' | 'info' | 'success' | 'warning' | 'error';

export interface StatusEntry {
  id: string;
  text: string;
  variant: StatusVariant;
  createdAt: number;
  expiresAt?: number;
  pinned?: boolean;
  dismissed?: boolean;
}

export interface StatusEmitOptions {
  variant?: StatusVariant;
  duration?: number;
  pinned?: boolean;
}

export interface StatusBarSettings {
  tickerMode: boolean;
  maxVisible: number;
  errorPersist: boolean;
  errorDuration: number;
  successDuration: number;
  warningDuration: number;
}

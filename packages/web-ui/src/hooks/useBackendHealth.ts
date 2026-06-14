'use client';
import { useEffect, useRef, useState } from 'react';
import { get } from '@/lib/strategy-builder/api';

export interface BackendHealth {
  status: 'ok' | 'degraded';
  redis: boolean;
  uptime_seconds: number;
  version: string;
  commit_sha: string | null;
  branch: string | null;
}

export type ConnectionState = 'connected' | 'disconnected' | 'checking';

export interface BackendHealthState {
  connectionState: ConnectionState;
  health: BackendHealth | null;
  lastChecked: Date | null;
  error: string | null;
}

const POLL_INTERVAL_MS = 15_000;

export function useBackendHealth(): BackendHealthState {
  const [state, setState] = useState<BackendHealthState>({
    connectionState: 'checking',
    health: null,
    lastChecked: null,
    error: null,
  });
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmounted = useRef(false);

  const check = async () => {
    if (unmounted.current) return;
    try {
      const data = await get<BackendHealth>('/health');
      if (!unmounted.current) {
        setState({
          connectionState: data.status === 'ok' ? 'connected' : 'disconnected',
          health: data,
          lastChecked: new Date(),
          error: null,
        });
      }
    } catch (err) {
      if (!unmounted.current) {
        setState(prev => ({
          ...prev,
          connectionState: 'disconnected',
          lastChecked: new Date(),
          error: err instanceof Error ? err.message : 'Unreachable',
        }));
      }
    }
    if (!unmounted.current) {
      timerRef.current = setTimeout(check, POLL_INTERVAL_MS);
    }
  };

  useEffect(() => {
    unmounted.current = false;
    check();
    return () => {
      unmounted.current = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return state;
}

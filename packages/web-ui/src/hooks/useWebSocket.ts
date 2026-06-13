'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { status } from '@/lib/status';
import { useStatusSettings } from '@/contexts/StatusContext';

export type WsStatus = 'connecting' | 'open' | 'closed' | 'error';

export function useWebSocket<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [status_ws, setStatus] = useState<WsStatus>('connecting');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmounted = useRef(false);
  const connectRef = useRef<() => void>(() => { /* populated by effect */ });
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _statusTickerId = useRef<string | null>(null);
  const { settings } = useStatusSettings();

  const connect = useCallback(() => {
    if (unmounted.current) return;
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;
      setStatus('connecting');

      ws.onopen = () => {
        if (!unmounted.current) {
          setStatus('open');
          if (settings.tickerMode) {
            status.emit('WebSocket connected', { variant: 'success', duration: 2000 });
          }
        }
      };

      ws.onmessage = (evt) => {
        if (unmounted.current) return;
        try {
          setData(JSON.parse(evt.data) as T);
        } catch {
          // ignore malformed frames
        }
      };

      ws.onerror = () => {
        if (!unmounted.current) {
          setStatus('error');
          if (settings.tickerMode) {
            status.emit('WebSocket error', { variant: 'error', duration: 4000 });
          }
        }
      };

      ws.onclose = () => {
        if (unmounted.current) return;
        setStatus('closed');
        if (settings.tickerMode) {
          status.emit('WebSocket disconnected', { variant: 'warning', duration: 2000 });
        }
        reconnectTimer.current = setTimeout(connectRef.current, 3000);
      };
    } catch {
      setStatus('error');
      if (settings.tickerMode) {
        status.emit('WebSocket connection failed', { variant: 'error', duration: 4000 });
      }
      reconnectTimer.current = setTimeout(connectRef.current, 5000);
    }
  }, [url, settings.tickerMode]);

  useEffect(() => {
    connectRef.current = connect;
    unmounted.current = false;
    const initTimer = setTimeout(connect, 0);
    return () => {
      clearTimeout(initTimer);
      unmounted.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { data, status: status_ws };
}

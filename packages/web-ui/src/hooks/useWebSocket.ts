'use client';
import { useEffect, useRef, useState, useCallback } from 'react';

export type WsStatus = 'connecting' | 'open' | 'closed' | 'error';

export function useWebSocket<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<WsStatus>('connecting');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmounted = useRef(false);
  const connectRef = useRef<() => void>(() => { /* populated by effect */ });

  const connect = useCallback(() => {
    if (unmounted.current) return;
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;
      setStatus('connecting');

      ws.onopen = () => {
        if (!unmounted.current) setStatus('open');
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
        if (!unmounted.current) setStatus('error');
      };

      ws.onclose = () => {
        if (unmounted.current) return;
        setStatus('closed');
        reconnectTimer.current = setTimeout(connectRef.current, 3000);
      };
    } catch {
      setStatus('error');
      reconnectTimer.current = setTimeout(connectRef.current, 5000);
    }
  }, [url]);

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

  return { data, status };
}

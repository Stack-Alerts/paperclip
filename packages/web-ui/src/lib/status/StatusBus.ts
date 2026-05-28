import type { StatusEntry } from './types';

type Listener<T = any> = (event: T) => void;

interface Events {
  emit: StatusEntry;
  update: { id: string; text: string };
  dismiss: { id: string };
  clear: void;
}

class StatusBus {
  private listeners: { [K in keyof Events]?: Set<Listener> } = {};

  on<K extends keyof Events>(event: K, fn: Listener<Events[K]>) {
    if (!this.listeners[event]) this.listeners[event] = new Set();
    this.listeners[event]!.add(fn);
    return () => this.listeners[event]?.delete(fn);
  }

  emit<K extends keyof Events>(event: K, data: Events[K]) {
    this.listeners[event]?.forEach(fn => fn(data));
  }
}

export const statusBus = new StatusBus();

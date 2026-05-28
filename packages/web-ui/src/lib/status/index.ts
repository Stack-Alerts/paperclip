import { statusBus } from './StatusBus';
import type { StatusEmitOptions, StatusEntry, StatusVariant } from './types';

function generateId() {
  return `status-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export const status = {
  emit(text: string, options?: StatusEmitOptions) {
    const id = generateId();
    const variant: StatusVariant = options?.variant ?? 'info';
    const duration = options?.duration ?? 2000;
    const entry: StatusEntry = {
      id,
      text,
      variant,
      createdAt: Date.now(),
      expiresAt: duration > 0 ? Date.now() + duration : undefined,
    };
    statusBus.emit('emit', entry);
    if (duration > 0) {
      setTimeout(() => statusBus.emit('dismiss', { id }), duration);
    }
    return id;
  },

  update(id: string, text: string) {
    statusBus.emit('update', { id, text });
  },

  dismiss(id: string) {
    statusBus.emit('dismiss', { id });
  },

  clear() {
    statusBus.emit('clear', undefined);
  },
};

export { statusBus };
export type { StatusEntry, StatusVariant, StatusEmitOptions, StatusBarSettings } from './types';

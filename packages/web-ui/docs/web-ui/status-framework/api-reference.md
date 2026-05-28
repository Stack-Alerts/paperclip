# Status Framework API Reference

## `status.emit(text, options?)`

Emits a new status entry to the status bar.

**Parameters:**
- `text` (string): The status message to display
- `options` (optional):
  - `variant` ('idle' | 'info' | 'success' | 'warning' | 'error'): Message variant (default: 'info')
  - `duration` (number): Milliseconds until auto-dismiss (default: 2000). Use any non-positive value (e.g., -1, 0) to create a persistent status that does not auto-dismiss

**Returns:** `string` — The unique ID of the emitted status entry

**Example:**
```typescript
import { status } from '@/lib/status';

// Simple message with default 2s duration
status.emit('Strategy saved');

// Error with custom duration
status.emit('Save failed', { variant: 'error', duration: 3000 });

// Persistent message (no auto-dismiss)
const countdownId = status.emit('Checking data…', { duration: -1 });
```

## `status.update(id, text)`

Updates the text of an existing status entry (useful for countdown timers).

**Parameters:**
- `id` (string): The status entry ID (returned from `status.emit()`)
- `text` (string): The new text to display

**Limitations:**
- Only the `text` field can be updated; `variant` cannot be changed after the status is emitted. If you need to change the variant, dismiss the current status and emit a new one.

**Example:**
```typescript
const id = status.emit('Next data check in 15m 0s', { duration: -1 });

// Later, in a timer update:
status.update(id, 'Next data check in 14m 59s');
```

## `status.dismiss(id)`

Immediately removes a status entry from the status bar.

**Parameters:**
- `id` (string): The status entry ID

**Example:**
```typescript
const id = status.emit('Operation in progress…', { duration: -1 });
// ...later...
status.dismiss(id);
```

## `status.clear()`

Clears all status entries from the status bar.

**Example:**
```typescript
status.clear();
```

## `useStatus()`

React hook that returns the current array of status entries. Primarily used internally by `<StatusBar />`.

**Returns:** `StatusEntry[]`

**Example:**
```typescript
import { useStatus } from '@/contexts/StatusContext';

function MyComponent() {
  const entries = useStatus();
  return <div>{entries.length} statuses active</div>;
}
```

## `useStatusSettings()`

React hook that returns status settings and an update function.

**Returns:** `{ settings: StatusBarSettings; update: (settings: Partial<StatusBarSettings>) => void }`

**Example:**
```typescript
import { useStatusSettings } from '@/contexts/StatusContext';

function MyComponent() {
  const { settings, update } = useStatusSettings();
  return (
    <button onClick={() => update({ tickerMode: !settings.tickerMode })}>
      Toggle Ticker
    </button>
  );
}
```

## Types

### StatusVariant
```typescript
type StatusVariant = 'idle' | 'info' | 'success' | 'warning' | 'error';
```

### StatusEntry
```typescript
interface StatusEntry {
  id: string;
  text: string;
  variant: StatusVariant;
  createdAt: number;
  expiresAt?: number;
}
```

### StatusBarSettings
```typescript
interface StatusBarSettings {
  tickerMode: boolean;
}
```

## Implementation Notes

- Status IDs are globally unique and internally generated
- The StatusBar displays only the most recent entry (others are tracked but not visible)
- Expired entries are automatically dismissed
- The `duration: -1` option is used for entries that should persist until explicitly dismissed

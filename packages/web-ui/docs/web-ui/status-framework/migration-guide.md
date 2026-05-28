# Status Framework Migration Guide

This guide helps component authors migrate from the old `setStatusText()` pattern to the new Status Framework.

## Old Pattern

```typescript
const [statusText, setStatusText] = useState('Ready');

return (
  <div>
    {/* ...component content... */}
    <div className="h-6 border-t px-3 flex items-center">
      <span className="text-xs">{statusText}</span>
    </div>
  </div>
);
```

## New Pattern

### Step 1: Import the status API

```typescript
import { status } from '@/lib/status';
```

### Step 2: Replace setStatusText calls

**Old:**
```typescript
setStatusText('Strategy saved');
setTimeout(() => setStatusText('Ready'), 2000);
```

**New:**
```typescript
status.emit('Strategy saved', { duration: 2000 });
```

### Step 3: Remove status bar markup

Delete the status bar `<div>` from your component. The global `<StatusBar />` in the root layout will display messages.

### Step 4: For countdown timers

**Old:**
```typescript
const [statusText, setStatusText] = useState('Ready');

useEffect(() => {
  const timer = setInterval(() => {
    setStatusText(`Next in ${timeRemaining}s`);
  }, 1000);
  return () => clearInterval(timer);
}, []);
```

**New:**
```typescript
const countdownIdRef = useRef<string | null>(null);

useEffect(() => {
  const timer = setInterval(() => {
    const text = `Next in ${timeRemaining}s`;
    if (countdownIdRef.current) {
      status.update(countdownIdRef.current, text);
    } else {
      countdownIdRef.current = status.emit(text, { duration: -1 });
    }
  }, 1000);
  return () => clearInterval(timer);
}, []);
```

## Error Handling

Use the `variant` option to distinguish message types:

```typescript
// Success
status.emit('Operation completed', { variant: 'success', duration: 2000 });

// Error
status.emit('Operation failed', { variant: 'error', duration: 3000 });

// Warning
status.emit('This action may take time', { variant: 'warning', duration: -1 });

// Info (default)
status.emit('Processing…');
```

## Styling

The status bar styling is centralized in `src/components/layout/StatusBar.tsx` and uses CSS variables from the design system. No per-component styling needed.

## Notes

- You must be inside a `<StatusBarProvider>` (parent of your component) to use the `status` API
- The root app layout provides this automatically
- If building a reusable component library, consumers should ensure they wrap their app with `<StatusBarProvider>`

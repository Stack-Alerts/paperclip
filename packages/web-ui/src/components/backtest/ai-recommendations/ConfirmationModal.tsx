'use client';

export function ConfirmationModal({
  confirmation,
  onCancel,
  onConfirmClearAll,
  onConfirmDelete,
}: {
  confirmation: { type: 'clear-all' | 'delete'; entryId?: string };
  onCancel: () => void;
  onConfirmClearAll: () => void;
  onConfirmDelete: () => void;
}) {
  const isClearAll = confirmation.type === 'clear-all';
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'var(--overlay-scrim)' }}
      onClick={onCancel}
    >
      <div
        className="rounded p-4 max-w-sm w-full mx-4"
        style={{
          background: 'var(--bg-card)',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-sm font-semibold mb-2">
          {isClearAll ? 'Clear all history?' : 'Delete this entry?'}
        </p>
        <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
          {isClearAll
            ? 'This will permanently remove all stored AI recommendation analyses from this browser. This action cannot be undone.'
            : 'This will permanently remove the selected analysis from this browser. This action cannot be undone.'}
        </p>
        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: 'var(--bg-elevated)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={isClearAll ? onConfirmClearAll : onConfirmDelete}
            className="px-3 py-1.5 rounded text-xs font-medium"
            style={{
              background: 'var(--accent-red)',
              color: 'var(--text-on-negative)',
              border: '1px solid var(--accent-red)',
              cursor: 'pointer',
            }}
          >
            {isClearAll ? 'Clear all' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

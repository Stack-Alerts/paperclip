'use client';

import React from 'react';

interface WindowBreadcrumbProps {
  page: string;
  item?: string | null;
  itemDirty?: boolean;
}

/**
 * Right-aligned breadcrumb rendered in the top bar of every WebUI window.
 *
 * Format: `BTC Trade Engine — {page} — {item}{itemDirty ? '●' : ''}`
 *
 * The `item` segment is omitted when null/undefined/empty, and the `●`
 * dirty indicator only renders when `itemDirty` is true and an item name
 * is present.
 */
export function WindowBreadcrumb({ page, item, itemDirty = false }: WindowBreadcrumbProps) {
  const hasItem = item != null && item !== '';
  return (
    <span
      className="ml-auto text-xs whitespace-nowrap pr-2"
      style={{ color: 'var(--text-secondary)' }}
    >
      BTC Trade Engine — {page}
      {hasItem && (
        <>
          {' — '}
          <span style={{ color: 'var(--text-secondary)' }}>{item}</span>
        </>
      )}
      {hasItem && itemDirty && (
        <span className="ml-1" style={{ color: 'var(--accent-orange)' }} title="Unsaved changes">
          ●
        </span>
      )}
    </span>
  );
}

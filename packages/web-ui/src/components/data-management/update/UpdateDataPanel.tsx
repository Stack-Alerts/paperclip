'use client';

import { DataManagementPanel } from '@/components/data-management/DataManagementPanel';
import type { DataManagementPanelProps } from '@/components/data-management/DataManagementPanel';

export type UpdateDataPanelProps = DataManagementPanelProps;

export function UpdateDataPanel(props: UpdateDataPanelProps) {
  return <DataManagementPanel {...props} />;
}

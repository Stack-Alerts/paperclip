'use client';

import { DataManagementPanel } from '@/components/data-management/DataManagementPanel';
import type { DataManagementPanelProps } from '@/components/data-management/DataManagementPanel';

export type VerifyDataPanelProps = DataManagementPanelProps;

export function VerifyDataPanel(props: VerifyDataPanelProps) {
  return <DataManagementPanel {...props} />;
}

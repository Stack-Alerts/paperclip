import { DataManagementPanel } from '@/components/data-management/DataManagementPanel';

export default function DataManagementPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
      <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>Data Management</h1>
      <DataManagementPanel />
    </div>
  );
}

import { DataManagementPanel } from '@/components/data-management/DataManagementPanel';

export default function DataManagementPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6 bg-zinc-950">
      <h1 className="text-xl font-semibold text-zinc-100 mb-6">Data Management</h1>
      <DataManagementPanel />
    </div>
  );
}

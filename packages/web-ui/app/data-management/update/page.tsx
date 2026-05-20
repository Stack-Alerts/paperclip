import { UpdateDataPanel } from '@/components/data-management/update';

export default function UpdateDataPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
      <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>
        Update Data
      </h1>
      <UpdateDataPanel />
    </div>
  );
}

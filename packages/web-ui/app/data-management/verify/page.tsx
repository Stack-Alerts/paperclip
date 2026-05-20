import { VerifyDataPanel } from '@/components/data-management/verify';

export default function VerifyDataPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
      <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>
        Verify Data
      </h1>
      <VerifyDataPanel />
    </div>
  );
}

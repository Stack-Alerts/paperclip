import { ITMDashboard } from '@/components/itm/ITMDashboard';
import { WindowBreadcrumb } from '@/components/shared/WindowBreadcrumb';

export default function Home() {
  return (
    <>
      <div
        className="flex items-center border-b px-3 py-1.5 flex-shrink-0"
        style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)' }}
      >
        <WindowBreadcrumb page="Dashboard" />
      </div>
      <div className="flex-1 overflow-y-auto">
        <ITMDashboard />
      </div>
    </>
  );
}

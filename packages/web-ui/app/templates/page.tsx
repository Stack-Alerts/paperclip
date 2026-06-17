import { WindowBreadcrumb } from '@/components/shared/WindowBreadcrumb';

export default function TemplatesPage() {
  return (
    <>
      <div
        className="flex items-center border-b px-3 py-1.5 flex-shrink-0"
        style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)' }}
      >
        <WindowBreadcrumb page="Templates" />
      </div>
      <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
        <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>
          Templates
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Templates window — scaffold only. Owned by WebUI: Templates project.
        </p>
      </div>
    </>
  );
}

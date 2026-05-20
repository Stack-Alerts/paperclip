export default function TemplatesPage() {
  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ background: 'var(--app-bg)' }}>
      <h1 className="text-xl font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>
        Templates
      </h1>
      <p style={{ color: 'var(--text-secondary)' }}>
        Templates window — scaffold only. Owned by WebUI: Templates project.
      </p>
    </div>
  );
}

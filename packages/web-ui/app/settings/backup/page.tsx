'use client';

/**
 * Backup settings page — P5 surface for issue BTCAAAAA-38756.
 *
 * Four cards mirror the P5 /api/backup/* endpoints:
 *   1. ProvidersCard      GET/POST/DELETE /providers, POST /providers/{name}/test
 *   2. ScheduleCard       GET/PUT /config (cron), POST /run-now, GET /runs/{id}, GET /status
 *   3. ScopeCard          GET/PUT /config (scope + retention_days + retention_count)
 *   4. HistoryCard        GET /history
 *
 * Hard gates (from the issue's webui spec):
 *   - only @/lib/strategy-builder/api for HTTP (no direct fetch, no Paperclip)
 *   - provider view never carries path/remote/config_path (only name/type/last_test_*)
 *   - restore endpoint is a P4 follow-up — the button is wired but POSTing it
 *     against the current P5 server will return 404; we surface that gracefully
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { WindowBreadcrumb } from '@/components/shared/WindowBreadcrumb';
import { del, get, post, put } from '@/lib/strategy-builder/api';

// ---------------------------------------------------------------------------
// Types — mirror src/backup/api_router.py Pydantic models
// ---------------------------------------------------------------------------

interface ProviderView {
  name: string;
  type: string;
  last_test_at: string | null;
  last_test_ok: boolean | null;
}

interface BackupConfig {
  providers: ProviderView[];
  schedule_cron: string;
  scope: string;
  retention_days: number;
  retention_count: number;
  last_run_at: string | null;
}

interface ProviderTestResult {
  name: string;
  ok: boolean;
  latency_ms: number;
  tested_at: string;
  free_space_bytes: number | null;
  error: string | null;
}

interface HistoryEntry {
  remote_id: string;
  provider: string;
  size: number;
  uploaded_at: string | null;
  created_at: string | null;
  sha256: string | null;
  source: string | null;
}

interface HistoryResponse {
  count: number;
  entries: HistoryEntry[];
}

interface RunTriggerResponse {
  run_id: string;
  status_url: string;
  status: string;
}

interface RunStateView {
  run_id: string;
  kind: string;
  status: 'pending' | 'running' | 'complete' | 'failed' | 'skipped';
  started_at: string;
  finished_at: string | null;
  error: string | null;
}

interface StatusResponse {
  running: boolean;
  schedule_cron: string;
  last_run_at: string | null;
  next_fire_times: string[];
  scheduler_started: boolean;
}

type CronValidation =
  | { valid: true; fire_times: string[] }
  | { valid: false; error: string };

const TERMINAL_RUN_STATUSES = new Set(['complete', 'failed', 'skipped']);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTimestamp(value: string | null): string {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || Number.isNaN(bytes)) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function truncate(value: string, head = 8, tail = 6): string {
  if (value.length <= head + tail + 3) return value;
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

// ---------------------------------------------------------------------------
// ProvidersCard
// ---------------------------------------------------------------------------

function ProvidersCard({
  providers,
  onChange,
}: {
  providers: ProviderView[];
  onChange: () => void;
}) {
  const [addName, setAddName] = useState('');
  const [addPath, setAddPath] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, ProviderTestResult>>({});

  const handleAdd = useCallback(async () => {
    setError(null);
    if (!addName.trim() || !addPath.trim()) {
      setError('Name and path are required.');
      return;
    }
    setBusy(true);
    try {
      await post<ProviderView>('/api/backup/providers', {
        name: addName.trim(),
        type: 'local',
        path: addPath.trim(),
      });
      setAddName('');
      setAddPath('');
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [addName, addPath, onChange]);

  const handleRemove = useCallback(
    async (name: string) => {
      setError(null);
      setBusy(true);
      try {
        await del<unknown>(`/api/backup/providers/${encodeURIComponent(name)}`);
        setTestResults((prev) => {
          const next = { ...prev };
          delete next[name];
          return next;
        });
        onChange();
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [onChange],
  );

  const handleTest = useCallback(async (name: string) => {
    setError(null);
    try {
      const result = await post<ProviderTestResult>(
        `/api/backup/providers/${encodeURIComponent(name)}/test`,
      );
      setTestResults((prev) => ({ ...prev, [name]: result }));
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [onChange]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Providers</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
          Backup targets. The server only returns <code>name</code>, <code>type</code>, and
          the most recent test result — on-disk paths are never echoed back.
        </p>

        {providers.length === 0 ? (
          <div className="text-sm italic mb-4" style={{ color: 'var(--text-muted)' }}>
            No providers configured yet.
          </div>
        ) : (
          <div className="space-y-2 mb-4">
            {providers.map((p) => {
              const last = testResults[p.name];
              const status = last
                ? last.ok
                  ? `OK · ${last.latency_ms.toFixed(0)}ms`
                  : `Failed: ${last.error ?? 'unknown error'}`
                : p.last_test_ok === true
                ? 'Last test: OK'
                : p.last_test_ok === false
                ? 'Last test: failed'
                : 'Never tested';
              const statusColor = last
                ? last.ok
                  ? 'var(--success, #16a34a)'
                  : 'var(--danger, #dc2626)'
                : p.last_test_ok === true
                ? 'var(--success, #16a34a)'
                : p.last_test_ok === false
                ? 'var(--danger, #dc2626)'
                : 'var(--text-muted)';
              return (
                <div
                  key={p.name}
                  className="flex items-center justify-between rounded px-3 py-2"
                  style={{
                    background: 'var(--bg-app)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div>
                    <div className="font-medium" style={{ color: 'var(--text-primary)' }}>
                      {p.name}
                    </div>
                    <div className="text-xs mt-0.5" style={{ color: statusColor }}>
                      {p.type} · {status}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleTest(p.name)}
                      disabled={busy}
                    >
                      Test
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleRemove(p.name)}
                      disabled={busy}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
          <div>
            <Label htmlFor="provider-name">Name</Label>
            <Input
              id="provider-name"
              value={addName}
              onChange={(e) => setAddName(e.target.value)}
              placeholder="alpha"
              disabled={busy}
            />
          </div>
          <div>
            <Label htmlFor="provider-type">Type</Label>
            <Select
              id="provider-type"
              value="local"
              disabled
            >
              <option value="local">local</option>
            </Select>
          </div>
          <div>
            <Label htmlFor="provider-path">Path</Label>
            <Input
              id="provider-path"
              value={addPath}
              onChange={(e) => setAddPath(e.target.value)}
              placeholder="/var/backups"
              disabled={busy}
            />
          </div>
        </div>
        <div className="flex items-center gap-3 mt-3">
          <Button onClick={handleAdd} disabled={busy}>
            {busy ? 'Adding…' : 'Add provider'}
          </Button>
          {error && (
            <span className="text-sm" style={{ color: 'var(--danger, #dc2626)' }}>
              {error}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// ScheduleCard
// ---------------------------------------------------------------------------

function ScheduleCard({
  config,
  onConfigChange,
}: {
  config: BackupConfig;
  onConfigChange: () => void;
}) {
  const [cron, setCron] = useState(config.schedule_cron);
  const [validation, setValidation] = useState<CronValidation | null>(null);
  const [savingCron, setSavingCron] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [runState, setRunState] = useState<RunStateView | null>(null);
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Sync cron input when the parent re-fetches the config (e.g. after Run now completes).
  useEffect(() => {
    setCron(config.schedule_cron);
  }, [config.schedule_cron]);

  const refreshStatus = useCallback(async () => {
    try {
      const next = await get<StatusResponse>('/api/backup/status');
      setStatus(next);
    } catch {
      // The endpoint may 5xx if the scheduler has not been installed yet;
      // we surface that as a missing-status state below rather than a hard error.
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  // Tear down any active poll loop when the component unmounts.
  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

  const handleValidate = useCallback(async () => {
    try {
      const result = await post<CronValidation>('/api/backup/validate-cron', {
        expression: cron,
      });
      setValidation(result);
    } catch (e) {
      setValidation({
        valid: false,
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }, [cron]);

  const handleSaveCron = useCallback(async () => {
    setSavingCron(true);
    try {
      await put<BackupConfig>('/api/backup/config', { schedule_cron: cron });
      onConfigChange();
    } catch (e) {
      setValidation({
        valid: false,
        error: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setSavingCron(false);
    }
  }, [cron, onConfigChange]);

  const handleRunNow = useCallback(async () => {
    setRunState(null);
    try {
      const trigger = await post<RunTriggerResponse>('/api/backup/run-now', {});
      setRunId(trigger.run_id);
      setRunState({
        run_id: trigger.run_id,
        kind: 'backup',
        status: 'pending',
        started_at: new Date().toISOString(),
        finished_at: null,
        error: null,
      });

      // Poll /runs/{id} every 500ms until terminal.
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const next = await get<RunStateView>(
            `/api/backup/runs/${encodeURIComponent(trigger.run_id)}`,
          );
          setRunState(next);
          if (TERMINAL_RUN_STATUSES.has(next.status)) {
            if (pollRef.current) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
            refreshStatus();
            onConfigChange();
          }
        } catch {
          // Treat poll errors as transient — the loop keeps going.
        }
      }, 500);
    } catch (e) {
      setRunState({
        run_id: '',
        kind: 'backup',
        status: 'failed',
        started_at: new Date().toISOString(),
        finished_at: new Date().toISOString(),
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }, [onConfigChange, refreshStatus]);

  const isRunning =
    runState !== null && !TERMINAL_RUN_STATUSES.has(runState.status);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Schedule</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 items-end">
          <div>
            <Label htmlFor="schedule-cron">Cron expression (UTC)</Label>
            <Input
              id="schedule-cron"
              value={cron}
              onChange={(e) => {
                setCron(e.target.value);
                setValidation(null);
              }}
              placeholder="0 3 * * *"
              disabled={savingCron}
            />
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={handleValidate}
              disabled={savingCron}
            >
              Validate
            </Button>
            <Button
              onClick={handleSaveCron}
              disabled={savingCron || cron === config.schedule_cron}
            >
              {savingCron ? 'Saving…' : 'Save cron'}
            </Button>
          </div>
        </div>

        {validation && (
          <div className="mt-3 text-sm" style={{ color: 'var(--text-muted)' }}>
            {validation.valid ? (
              <>
                <span style={{ color: 'var(--success, #16a34a)' }}>Valid.</span>{' '}
                Next 3 fire times:{' '}
                <code>{validation.fire_times.map(formatTimestamp).join(', ')}</code>
              </>
            ) : (
              <span style={{ color: 'var(--danger, #dc2626)' }}>
                Invalid: {validation.error}
              </span>
            )}
          </div>
        )}

        <div className="mt-6 flex items-center gap-3">
          <Button onClick={handleRunNow} disabled={isRunning}>
            {isRunning ? 'Running…' : 'Run now'}
          </Button>
          {runState && (
            <span
              className="text-sm"
              style={{
                color:
                  runState.status === 'complete'
                    ? 'var(--success, #16a34a)'
                    : runState.status === 'failed'
                    ? 'var(--danger, #dc2626)'
                    : runState.status === 'skipped'
                    ? 'var(--text-muted)'
                    : 'var(--text-primary)',
              }}
            >
              Status: <strong>{runState.status}</strong>
              {runState.error ? ` — ${runState.error}` : ''}
              {runState.finished_at ? ` (finished ${formatTimestamp(runState.finished_at)})` : ''}
            </span>
          )}
        </div>

        {status && (
          <div className="mt-4 text-sm" style={{ color: 'var(--text-muted)' }}>
            <div>
              Scheduler:{' '}
              {status.scheduler_started
                ? status.running
                  ? 'running'
                  : `idle (cron: ${status.schedule_cron})`
                : 'not started'}
            </div>
            {status.next_fire_times.length > 0 && (
              <div>
                Next fires:{' '}
                <code>{status.next_fire_times.map(formatTimestamp).join(', ')}</code>
              </div>
            )}
            <div>Last run: {formatTimestamp(status.last_run_at)}</div>
          </div>
        )}

        {runId && (
          <div className="mt-2 text-xs" style={{ color: 'var(--text-muted)' }}>
            Run id: <code>{truncate(runId, 10, 6)}</code>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// ScopeCard
// ---------------------------------------------------------------------------

function ScopeCard({
  config,
  onConfigChange,
}: {
  config: BackupConfig;
  onConfigChange: () => void;
}) {
  const [scope, setScope] = useState(config.scope);
  const [retentionDays, setRetentionDays] = useState(String(config.retention_days));
  const [retentionCount, setRetentionCount] = useState(String(config.retention_count));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync drafts when the parent re-fetches the config.
  useEffect(() => {
    setScope(config.scope);
    setRetentionDays(String(config.retention_days));
    setRetentionCount(String(config.retention_count));
  }, [config.scope, config.retention_days, config.retention_count]);

  const dirty =
    scope !== config.scope ||
    retentionDays !== String(config.retention_days) ||
    retentionCount !== String(config.retention_count);

  const handleSave = useCallback(async () => {
    setError(null);
    const days = Number.parseInt(retentionDays, 10);
    const count = Number.parseInt(retentionCount, 10);
    if (!Number.isFinite(days) || days < 1) {
      setError('Retention days must be a positive integer.');
      return;
    }
    if (!Number.isFinite(count) || count < 1) {
      setError('Retention count must be a positive integer.');
      return;
    }
    setSaving(true);
    try {
      await put<BackupConfig>('/api/backup/config', {
        scope,
        retention_days: days,
        retention_count: count,
      });
      onConfigChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }, [scope, retentionDays, retentionCount, onConfigChange]);

  const handleReset = useCallback(() => {
    setScope(config.scope);
    setRetentionDays(String(config.retention_days));
    setRetentionCount(String(config.retention_count));
    setError(null);
  }, [config.scope, config.retention_days, config.retention_count]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scope &amp; Retention</CardTitle>
      </CardHeader>
      <CardContent>
        <fieldset className="mb-4">
          <legend
            className="text-sm font-medium mb-2"
            style={{ color: 'var(--text-primary)' }}
          >
            Scope
          </legend>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="scope"
                value="db"
                checked={scope === 'db'}
                onChange={() => setScope('db')}
                disabled={saving}
              />
              Database only
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="scope"
                value="system"
                checked={scope === 'system'}
                onChange={() => setScope('system')}
                disabled={saving}
              />
              System (db + files)
            </label>
          </div>
        </fieldset>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 items-end">
          <div>
            <Label htmlFor="retention-days">Retention (days)</Label>
            <Input
              id="retention-days"
              type="number"
              min={1}
              value={retentionDays}
              onChange={(e) => setRetentionDays(e.target.value)}
              disabled={saving}
            />
          </div>
          <div>
            <Label htmlFor="retention-count">Retention (count)</Label>
            <Input
              id="retention-count"
              type="number"
              min={1}
              value={retentionCount}
              onChange={(e) => setRetentionCount(e.target.value)}
              disabled={saving}
            />
          </div>
        </div>

        <div className="flex items-center gap-3 mt-3">
          <Button onClick={handleSave} disabled={saving || !dirty}>
            {saving ? 'Saving…' : 'Save'}
          </Button>
          <Button variant="secondary" onClick={handleReset} disabled={saving || !dirty}>
            Reset
          </Button>
          {error && (
            <span className="text-sm" style={{ color: 'var(--danger, #dc2626)' }}>
              {error}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// HistoryCard
// ---------------------------------------------------------------------------

function HistoryCard({
  hasProviders,
  onNotify,
}: {
  hasProviders: boolean;
  onNotify: (msg: string, kind: 'info' | 'error') => void;
}) {
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const next = await get<HistoryResponse>('/api/backup/history');
      setHistory(next);
    } catch (e) {
      onNotify(
        e instanceof Error ? e.message : String(e),
        'error',
      );
    } finally {
      setLoading(false);
    }
  }, [onNotify]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleRestore = useCallback(
    async (remoteId: string) => {
      setRestoring(remoteId);
      try {
        // P4 follow-up: the restore endpoint is not part of P5. The button
        // is wired so the UI is correct as soon as P4 lands; until then the
        // server returns 404 and we surface that as an info message.
        await post<unknown>(
          `/api/backup/history/${encodeURIComponent(remoteId)}/restore`,
          {},
        );
        onNotify(`Restore requested for ${truncate(remoteId)}`, 'info');
      } catch (e) {
        onNotify(
          e instanceof Error ? e.message : String(e),
          'error',
        );
      } finally {
        setRestoring(null);
      }
    },
    [onNotify],
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-3 mb-3">
          <Button variant="secondary" onClick={refresh} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </Button>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {hasProviders
              ? 'Showing the 50 most recent backup manifests.'
              : 'Configure a provider to populate history.'}
          </span>
        </div>

        {history === null ? (
          <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Loading…
          </div>
        ) : history.entries.length === 0 ? (
          <div className="text-sm italic" style={{ color: 'var(--text-muted)' }}>
            No backup history yet.
          </div>
        ) : (
          <div
            className="rounded overflow-x-auto"
            style={{ border: '1px solid var(--border-subtle)' }}
          >
            <table className="w-full text-sm">
              <thead>
                <tr style={{ background: 'var(--bg-app)' }}>
                  <th
                    className="text-left px-3 py-2 font-medium"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    Provider
                  </th>
                  <th
                    className="text-left px-3 py-2 font-medium"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    Remote ID
                  </th>
                  <th
                    className="text-right px-3 py-2 font-medium"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    Size
                  </th>
                  <th
                    className="text-left px-3 py-2 font-medium"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    Uploaded
                  </th>
                  <th
                    className="text-left px-3 py-2 font-medium"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    sha256
                  </th>
                  <th
                    className="text-right px-3 py-2 font-medium"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {history.entries.map((e) => (
                  <tr
                    key={e.remote_id}
                    style={{ borderTop: '1px solid var(--border-subtle)' }}
                  >
                    <td className="px-3 py-2" style={{ color: 'var(--text-primary)' }}>
                      {e.provider}
                    </td>
                    <td className="px-3 py-2">
                      <code style={{ color: 'var(--text-muted)' }}>
                        {truncate(e.remote_id)}
                      </code>
                    </td>
                    <td
                      className="px-3 py-2 text-right"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {formatBytes(e.size)}
                    </td>
                    <td className="px-3 py-2" style={{ color: 'var(--text-muted)' }}>
                      {formatTimestamp(e.uploaded_at ?? e.created_at)}
                    </td>
                    <td className="px-3 py-2">
                      <code style={{ color: 'var(--text-muted)' }}>
                        {e.sha256 ? truncate(e.sha256, 10, 6) : '—'}
                      </code>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleRestore(e.remote_id)}
                        disabled={restoring === e.remote_id}
                      >
                        {restoring === e.remote_id ? 'Restoring…' : 'Restore'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function BackupSettingsPage() {
  const [config, setConfig] = useState<BackupConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; kind: 'info' | 'error' } | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await get<BackupConfig>('/api/backup/config');
      setConfig(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Auto-dismiss toasts after 4 seconds.
  useEffect(() => {
    if (!toast) return;
    const handle = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(handle);
  }, [toast]);

  const handleNotify = useCallback((msg: string, kind: 'info' | 'error') => {
    setToast({ msg, kind });
  }, []);

  return (
    <>
      <div
        className="flex items-center border-b px-3 py-1.5 flex-shrink-0"
        style={{ background: 'var(--bg-deep)', borderColor: 'var(--border)' }}
      >
        <WindowBreadcrumb page="Settings" item="Backup" />
      </div>
      <div
        className="flex-1 overflow-y-auto p-6"
        style={{ background: 'var(--app-bg)' }}
      >
        <h1
          className="text-xl font-semibold mb-6"
          style={{ color: 'var(--text-primary)' }}
        >
          Backup
        </h1>

        {toast && (
          <div
            className="mb-4 rounded px-3 py-2 text-sm"
            style={{
              background: 'var(--bg-app)',
              border: '1px solid var(--border-subtle)',
              color:
                toast.kind === 'error'
                  ? 'var(--danger, #dc2626)'
                  : 'var(--text-primary)',
            }}
          >
            {toast.msg}
          </div>
        )}

        {loading && config === null ? (
          <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Loading backup configuration…
          </div>
        ) : error ? (
          <div
            className="rounded px-3 py-2 text-sm"
            style={{
              background: 'var(--bg-app)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--danger, #dc2626)',
            }}
          >
            Failed to load configuration: {error}
          </div>
        ) : config ? (
          <div className="space-y-6">
            <ProvidersCard
              providers={config.providers}
              onChange={refresh}
            />
            <ScheduleCard config={config} onConfigChange={refresh} />
            <ScopeCard config={config} onConfigChange={refresh} />
            <HistoryCard
              hasProviders={config.providers.length > 0}
              onNotify={handleNotify}
            />
          </div>
        ) : null}
      </div>
    </>
  );
}
'use client';

import type { DiagnoseMetricRow } from './diagnoseMetrics';

// ── Minimal markdown renderer for the Diagnose pane ─────────────────────
// BTCAAAAA-37780 / Sprint A6 — light inline support for **bold**, _italic_,
// and `inline code` plus `- `/`* ` bullet lists.

function renderInline(line: string, keyPrefix: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|_[^_]+_|`[^`]+`)/g;
  let last = 0;
  let i = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(line)) !== null) {
    if (m.index > last) out.push(line.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('**')) {
      out.push(<strong key={`${keyPrefix}:b:${i++}`}>{tok.slice(2, -2)}</strong>);
    } else if (tok.startsWith('_')) {
      out.push(<em key={`${keyPrefix}:i:${i++}`}>{tok.slice(1, -1)}</em>);
    } else if (tok.startsWith('`')) {
      out.push(
        <code
          key={`${keyPrefix}:c:${i++}`}
          style={{ fontFamily: 'var(--font-mono, monospace)' }}
        >
          {tok.slice(1, -1)}
        </code>,
      );
    }
    last = m.index + tok.length;
  }
  if (last < line.length) out.push(line.slice(last));
  return out;
}

function DiagnosisMarkdown({ text }: { text: string }) {
  if (!text.trim()) return null;
  const lines = text.split(/\r?\n/);
  const out: React.ReactNode[] = [];
  let bullets: string[] | null = null;
  let blockIdx = 0;

  const flushBullets = () => {
    if (!bullets) return;
    const items = bullets;
    out.push(
      <ul
        key={`ul:${blockIdx++}`}
        className="list-disc pl-5 text-xs"
        style={{ color: 'var(--text-secondary)' }}
      >
        {items.map((b, i) => (
          <li key={i}>{renderInline(b, `ul:${blockIdx}:${i}`)}</li>
        ))}
      </ul>,
    );
    bullets = null;
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    const bulletMatch = line.match(/^\s*[-*]\s+(.*)$/);
    if (bulletMatch) {
      if (!bullets) bullets = [];
      bullets.push(bulletMatch[1]);
      continue;
    }
    flushBullets();
    if (line.trim().length === 0) continue;
    out.push(
      <p
        key={`p:${blockIdx++}`}
        className="text-xs whitespace-pre-wrap"
        style={{ color: 'var(--text-secondary)' }}
      >
        {renderInline(line, `p:${blockIdx}`)}
      </p>,
    );
  }
  flushBullets();
  return <div className="flex flex-col gap-2">{out}</div>;
}

export interface DiagnosePaneProps {
  diagnosis: string;
  rows: DiagnoseMetricRow[];
  stagedSentence: string;
  hasResult: boolean;
}

export function DiagnosePane({ diagnosis, rows, stagedSentence, hasResult }: DiagnosePaneProps) {
  return (
    <div className="flex flex-col gap-3" data-testid="ai-recs-diagnose-pane">
      <div
        className="rounded p-3"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <p
          className="text-xs font-semibold uppercase tracking-wide mb-2"
          style={{ color: 'var(--text-muted)' }}
        >
          DIAGNOSIS
        </p>
        {diagnosis.trim() ? (
          <DiagnosisMarkdown text={diagnosis} />
        ) : (
          <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
            {hasResult
              ? 'Awaiting AI analysis. Use "Approve & Send to AI" once the request preview is verified.'
              : 'Run a backtest first, then use "Approve & Send to AI" to receive a strategy diagnosis.'}
          </p>
        )}
      </div>

      <div
        className="rounded"
        style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
      >
        <p
          className="text-xs font-semibold uppercase tracking-wide px-3 pt-3"
          style={{ color: 'var(--text-muted)' }}
        >
          METRICS — REPORTED vs PER-ENTRY
        </p>
        <table
          data-testid="ai-recs-diagnose-table"
          className="w-full text-xs mt-2"
          style={{ borderCollapse: 'collapse' }}
        >
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              <th
                className="text-left px-3 py-1.5 font-semibold"
                style={{ color: 'var(--text-muted)' }}
              >
                Metric
              </th>
              <th
                className="text-right px-3 py-1.5 font-semibold"
                style={{ color: 'var(--text-muted)' }}
              >
                Reported
              </th>
              <th
                className="text-right px-3 py-1.5 font-semibold"
                style={{ color: 'var(--text-muted)' }}
              >
                Per-entry
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.key}
                data-testid={`ai-recs-diagnose-row-${row.key}`}
                data-divergent={row.divergent ? 'true' : 'false'}
                style={{ borderBottom: '1px solid var(--border)' }}
              >
                <td className="px-3 py-1.5" style={{ color: 'var(--text-secondary)' }}>
                  {row.label}
                </td>
                <td
                  className="px-3 py-1.5 text-right"
                  style={{
                    color: 'var(--text-secondary)',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}
                >
                  {row.reported}
                </td>
                <td
                  className="px-3 py-1.5 text-right"
                  style={{
                    color: row.divergent ? 'var(--accent-orange)' : 'var(--text-secondary)',
                    fontFamily: 'var(--font-mono, monospace)',
                  }}
                >
                  {row.perEntry}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div
        data-testid="ai-recs-staged-sentence"
        className="rounded p-3 text-xs"
        style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderLeft: '3px solid var(--accent-blue)',
          color: 'var(--text-secondary)',
        }}
      >
        {stagedSentence}
      </div>
    </div>
  );
}

// Alias export for external consumers who prefer the "DiagnosisCard" name
export { DiagnosePane as DiagnosisCard };

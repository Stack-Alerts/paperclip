import { useQuery } from "@tanstack/react-query";
import { versionsApi, type VersionEntry, type VersionsResponse } from "@/api/versions";
import { queryKeys } from "@/lib/queryKeys";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/**
 * VersionsBadge — small read-only badge that renders on the right edge of
 * the top breadcrumb bar. Visible on every page; the same data is surfaced
 * to operators everywhere regardless of which company they're inspecting.
 *
 * Format:
 *   BTC-Paperclip v1.0.0.0 (paperclip v2026.707.0) | Backup Plugin v1.0.0.0 | Git Merges v1.0.0.0
 *
 * The badge is intentionally low-contrast (muted-foreground) so it doesn't
 * compete with the breadcrumb itself. A tooltip on hover lists every
 * resolved component with its provenance (`source`) so operators can
 * confirm where each value came from without devtools.
 */
export function VersionsBadge() {
  const versionsQuery = useQuery<VersionsResponse>({
    queryKey: queryKeys.versions,
    queryFn: () => versionsApi.get(),
    // Cheap endpoint, but we don't need to thrash it on every focus change.
    // 60s keeps it useful for new installs without pinning the network.
    refetchInterval: 60_000,
    // Stay visible on transient errors; the badge degrades to a small "?".
    retry: 2,
  });

  return (
    <div
      data-testid="versions-badge"
      className="hidden md:flex shrink-0 items-center gap-1 pl-2 text-[11px] font-medium text-muted-foreground tabular-nums whitespace-nowrap"
    >
      <VersionsLabel label="versions" loading={versionsQuery.isLoading}>
        <VersionsTooltip data={versionsQuery.data} error={versionsQuery.error}>
          <span className="cursor-default truncate">
            <VersionsBody data={versionsQuery.data} error={versionsQuery.error} />
          </span>
        </VersionsTooltip>
      </VersionsLabel>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* helpers                                                                    */
/* -------------------------------------------------------------------------- */

function VersionsLabel({
  label,
  loading,
  children,
}: {
  label: string;
  loading: boolean;
  children: React.ReactNode;
}) {
  return (
    <span
      aria-busy={loading}
      aria-label={label}
      className="inline-flex items-center gap-1"
    >
      {children}
    </span>
  );
}

function VersionsBody({
  data,
  error,
}: {
  data: VersionsResponse | undefined;
  error: unknown;
}) {
  if (error) {
    return <span className="text-muted-foreground/60">versions ?</span>;
  }
  if (!data) {
    return <span className="text-muted-foreground/60">versions …</span>;
  }
  const parts: string[] = [];
  parts.push(
    `BTC-Paperclip v${data.btcPaperclip.version} (paperclip v${data.paperclip.version})`,
  );
  for (const [name, entry] of Object.entries(data.plugins)) {
    parts.push(`${name} v${entry.version}`);
  }
  return (
    <>
      {parts.map((p, i) => (
        <span key={i}>
          {i > 0 ? (
            <span className="mx-1.5 text-muted-foreground/40" aria-hidden>
              |
            </span>
          ) : null}
          {p}
        </span>
      ))}
    </>
  );
}

function VersionsTooltip({
  data,
  error,
  children,
}: {
  data: VersionsResponse | undefined;
  error: unknown;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent
        side="bottom"
        align="end"
        sideOffset={6}
        className="max-w-md whitespace-pre-wrap font-mono text-[11px]"
      >
        {error ? (
          <span>Failed to load versions: {String((error as Error)?.message ?? error)}</span>
        ) : data ? (
          <TooltipBody data={data} />
        ) : (
          <span>Loading…</span>
        )}
      </TooltipContent>
    </Tooltip>
  );
}

function TooltipBody({ data }: { data: VersionsResponse }) {
  const lines: string[] = [];
  lines.push(
    `BTC-Paperclip   v${data.btcPaperclip.version}\n  ${data.btcPaperclip.source}`,
  );
  lines.push(
    `Paperclip       v${data.paperclip.version}\n  ${data.paperclip.source}`,
  );
  for (const [name, entry] of Object.entries(data.plugins)) {
    lines.push(
      `${padRight(name, 16)} v${entry.version}\n  ${entry.source}`,
    );
  }
  lines.push("");
  lines.push(`generatedAt: ${data.generatedAt}`);
  return <span>{lines.join("\n")}</span>;
}

function padRight(s: string, n: number): string {
  if (s.length >= n) return s;
  return s + " ".repeat(n - s.length);
}

/* -------------------------------------------------------------------------- */
/* Type alias re-exports for consumers                                       */
/* -------------------------------------------------------------------------- */

export type { VersionEntry, VersionsResponse };
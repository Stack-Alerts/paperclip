/**
 * /api/versions — BTC version-control surface area.
 *
 * Returned by the server-side `versionsRoutes()` from `server/src/routes/versions.ts`.
 * The endpoint is unauthenticated, read-only, and is cheap to poll.
 */

export type VersionEntry = {
  /** The display version string (no leading "v" — caller can format). */
  version: string;
  /**
   * Where the version was resolved from — surfaced in the tooltip so the
   * badge can be inspected for provenance without devtools spelunking.
   */
  source: string;
};

export type VersionsResponse = {
  /** Our BTC-Paperclip customizations layer (read from VERSION at worktree root). */
  btcPaperclip: VersionEntry;
  /** Upstream Paperclip (read from server/package.json). */
  paperclip: VersionEntry;
  /** Per-plugin versions, keyed by display name (e.g. "Backup Plugin"). */
  plugins: Record<string, VersionEntry>;
  /** ISO 8601 timestamp when the response was assembled. */
  generatedAt: string;
};

export const versionsApi = {
  get: async (): Promise<VersionsResponse> => {
    const res = await fetch("/api/versions", {
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) {
      const payload = (await res.json().catch(() => null)) as
        | { error?: string }
        | null;
      throw new Error(
        payload?.error ?? `Failed to load versions (${res.status})`,
      );
    }
    return (await res.json()) as VersionsResponse;
  },
};
// constants.ts — paperclip-pause plugin constants
//
// All keys for data providers, action handlers, and plugin-state rows
// used by this plugin. Names are deliberately prefixed with
// `paperclip-pause.` so they don't collide with other plugins when
// surfaced in /api/plugins.

export const PLUGIN_ID = "paperclip.pause" as const;
export const PLUGIN_VERSION = "0.1.0" as const;
export const PLUGIN_DISPLAY_NAME = "Pause / Run Agent Control";

export const DATA_KEYS = {
  /** Current global pause state. Returns `{paused, pausedAt, pausedBy, summary}`. */
  state: "state",
} as const;

export const ACTION_KEYS = {
  /** Toggle the system-wide pause flag. Body: `{paused: boolean, reason?: string}`. */
  setPaused: "set-paused",
  /** Re-scan all agents and reflect their actual paused state. */
  refreshSummary: "refresh-summary",
} as const;

export const STATE_KEYS = {
  /** The single source-of-truth pause flag, instance scope. */
  paused: "system-paused",
  /** When paused, the user who triggered it. */
  pausedBy: "system-paused-by",
  /** When paused, ISO timestamp. */
  pausedAt: "system-paused-at",
  /** When paused, free-form reason string. */
  pausedReason: "system-paused-reason",
  /** Cached summary: number of paused agents last time we computed it. */
  summaryAgents: "system-paused-summary-agents",
  /** Cached summary: number of affected companies. */
  summaryCompanies: "system-paused-summary-companies",
  /** When the cached summary was computed. */
  summaryAt: "system-paused-summary-at",
} as const;

export const JOB_KEYS = {
  /** Re-check that paused state is still reflected on every agent. */
  reconcilePausedAgents: "reconcile-paused-agents",
} as const;

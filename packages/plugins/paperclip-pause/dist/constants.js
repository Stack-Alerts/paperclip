// src/constants.ts
var PLUGIN_ID = "paperclip.pause";
var PLUGIN_VERSION = "0.1.0";
var PLUGIN_DISPLAY_NAME = "Pause / Run Agent Control";
var DATA_KEYS = {
  /** Current global pause state. Returns `{paused, pausedAt, pausedBy, summary}`. */
  state: "state"
};
var ACTION_KEYS = {
  /** Toggle the system-wide pause flag. Body: `{paused: boolean, reason?: string}`. */
  setPaused: "set-paused",
  /** Re-scan all agents and reflect their actual paused state. */
  refreshSummary: "refresh-summary"
};
var STATE_KEYS = {
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
  summaryAt: "system-paused-summary-at"
};
var JOB_KEYS = {
  /** Re-check that paused state is still reflected on every agent. */
  reconcilePausedAgents: "reconcile-paused-agents"
};
export {
  ACTION_KEYS,
  DATA_KEYS,
  JOB_KEYS,
  PLUGIN_DISPLAY_NAME,
  PLUGIN_ID,
  PLUGIN_VERSION,
  STATE_KEYS
};

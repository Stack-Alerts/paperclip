export declare const PLUGIN_ID: "paperclip.pause";
export declare const PLUGIN_VERSION: "1.0.0.0";
export declare const PLUGIN_DISPLAY_NAME = "Pause / Run Agent Control";
export declare const DATA_KEYS: {
    /** Current global pause state. Returns `{paused, pausedAt, pausedBy, summary}`. */
    readonly state: "state";
};
export declare const ACTION_KEYS: {
    /** Toggle the system-wide pause flag. Body: `{paused: boolean, reason?: string}`. */
    readonly setPaused: "set-paused";
    /** Re-scan all agents and reflect their actual paused state. */
    readonly refreshSummary: "refresh-summary";
};
export declare const STATE_KEYS: {
    /** The single source-of-truth pause flag, instance scope. */
    readonly paused: "system-paused";
    /** When paused, the user who triggered it. */
    readonly pausedBy: "system-paused-by";
    /** When paused, ISO timestamp. */
    readonly pausedAt: "system-paused-at";
    /** When paused, free-form reason string. */
    readonly pausedReason: "system-paused-reason";
    /** Cached summary: number of paused agents last time we computed it. */
    readonly summaryAgents: "system-paused-summary-agents";
    /** Cached summary: number of affected companies. */
    readonly summaryCompanies: "system-paused-summary-companies";
    /** When the cached summary was computed. */
    readonly summaryAt: "system-paused-summary-at";
};
export declare const JOB_KEYS: {
    /** Re-check that paused state is still reflected on every agent. */
    readonly reconcilePausedAgents: "reconcile-paused-agents";
};
//# sourceMappingURL=constants.d.ts.map
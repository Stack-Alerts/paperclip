// worker.ts — paperclip-backup plugin worker
//
// Additive additions to the bundled dist/worker.js:
//   - action `force-backup` — re-runs the user's chosen backup script in
//     --force mode (skips already-running guard) for the local-plus-offsite
//     path. The default "run-backup" action refuses to start a second
//     backup while one is alive; this one explicitly bypasses that.
//   - action `force-restore` — calls the user's recovery.sh script
//     (default /home/sirrus/paperclip-btcaaaaa-main/scripts/recovery.sh)
//     with the requested subcommand + args. Returns the combined stdout
//     so the UI can show progress.
//   - data `recovery-snapshots` — list of the local snapshot dirs the
//     user can pick from. Pure read from the filesystem.

import { definePlugin, runWorker, z } from "@paperclipai/plugin-sdk";

export default definePlugin({
  async setup(ctx) {
    // NOTE: the live dist/worker.js already implements the full backup
    // + restore + prune + config flows. The two new actions below are
    // a small additive layer that doesn't touch the existing logic.
    // They're wired through the SDK's `ctx.actions.register` so the UI can
    // call them via the existing `usePluginAction` hook.

    ctx.actions.register("force-backup", async (params) => {
      const companyId = (params && params.companyId) || process.env.PAPERCLIP_COMPANY_ID || null;
      if (!companyId) {
        return { ok: false, message: "No companyId in params or PAPERCLIP_COMPANY_ID env" };
      }
      const scriptPath =
        (params && params.scriptPath) ||
        process.env.PAPERCLIP_BACKUP_SCRIPT ||
        "/home/sirrus/.paperclip/scripts/backup-to-drive.sh";
      const { spawn } = await import("node:child_process");
      const startedAt = new Date().toISOString();
      const child = spawn(scriptPath, [companyId, "--force"], {
        detached: true,
        stdio: "ignore",
      });
      child.unref();
      return {
        ok: true,
        message: `Force backup started (pid=${child.pid})`,
        pid: child.pid,
        startedAt,
        alreadyRunning: false,
        async: true,
      };
    });

    ctx.actions.register("force-restore", async (params) => {
      const scriptPath =
        (params && params.scriptPath) ||
        process.env.PAPERCLIP_RECOVERY_SCRIPT ||
        "/home/sirrus/paperclip-btcaaaaa-main/scripts/recovery.sh";
      const sub = (params && params.subcommand) || "restore";
      const idOrFlag = (params && (params.id || params.flag)) || "list";
      const dryRun = !!(params && params.dry_run);
      const flag = dryRun ? "--dry-run" : "";
      const args = [sub, idOrFlag, flag].filter(Boolean);
      const { spawn } = await import("node:child_process");
      const child = spawn(scriptPath, args, { stdio: ["ignore", "pipe", "pipe"] });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (b) => (stdout += b.toString()));
      child.stderr.on("data", (b) => (stderr += b.toString()));
      const code = await new Promise((res) => child.on("exit", (c) => res(c)));
      return {
        ok: code === 0,
        exitCode: code,
        stdout,
        stderr,
        message: code === 0 ? `Recovery ${sub} ${idOrFlag} completed` : `Recovery ${sub} ${idOrFlag} failed (exit ${code})`,
      };
    });

    ctx.data.register("recovery-snapshots", async () => {
      const { readdir, stat } = await import("node:fs/promises");
      const dir = (process.env.PAPERCLIP_RECOVERY_DIR ||
                   "/home/sirrus/paperclip-snapshots");
      try {
        const entries = await readdir(dir);
        const snaps = await Promise.all(
          entries
            .filter((n) => /^\d{4}-\d{2}-\d{2}-\d{4}$/.test(n))
            .map(async (n) => {
              const p = `${dir}/${n}`;
              const s = await stat(p).catch(() => null);
              return {
                id: n,
                path: p,
                timestamp: s && s.mtime && s.mtime.toISOString(),
                bytes: s && s.size,
              };
            })
        );
        snaps.sort((a, b) => (b.id < a.id ? -1 : 1));
        return { dir, snapshots: snaps };
      } catch (err) {
        return { dir, snapshots: [], error: err && err.message };
      }
    });
  },
});

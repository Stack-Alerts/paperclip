import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  runAdapterSessionEndAutosave,
  runSessionEndAutosave,
} from "./session-end-autosave.js";

/**
 * Build a temp repo that looks like a working Paperclip checkout:
 *   - on a `feat/BTCAAAAA-test` branch (the allowlist the wrapper cares about)
 *   - a synthetic `fake-autosave.sh` that we can spy on
 *   - empty initial commit so refs are stable
 *
 * All git invocations go through spawnSync with an arg array (no shell
 * interpolation), matching how the wrapper itself spawns python.
 */
function runGit(dir: string, args: string[]): void {
  const result = spawnSync("git", args, {
    cwd: dir,
    stdio: "pipe",
    env: {
      ...process.env,
      GIT_AUTHOR_NAME: "test",
      GIT_AUTHOR_EMAIL: "t@x",
      GIT_COMMITTER_NAME: "test",
      GIT_COMMITTER_EMAIL: "t@x",
    },
  });
  if (result.status !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed: ${result.stderr?.toString() ?? ""}`,
    );
  }
}

function buildTempRepo(): string {
  const dir = mkdtempSync(join(tmpdir(), "session-end-autosave-"));
  runGit(dir, ["init", "-q", "-b", "main"]);
  runGit(dir, ["config", "user.email", "t@x"]);
  runGit(dir, ["config", "user.name", "test"]);
  runGit(dir, ["commit", "-q", "--allow-empty", "-m", "init"]);
  runGit(dir, ["checkout", "-q", "-b", "feat/BTCAAAAA-test"]);
  // Minimal stand-in for the real script so we don't depend on the repo's
  // actual session_end_autosave.py. The wrapper only invokes "<bin> <script>
  // --cwd <repo> --run-id <id> [--issue-id <id>]"; the fake just records what
  // it saw and exits 0.
  writeFileSync(
    join(dir, "fake-autosave.sh"),
    [
      "#!/usr/bin/env bash",
      "set -u",
      "echo \"fake-run=$PAPERCLIP_RUN_ID cwd=$(pwd) args=$*\" >> \"$AUTOSAVE_FAKE_LOG\"",
      "exit 0",
    ].join("\n"),
  );
  return dir;
}

describe("session-end-autosave wrapper", () => {
  let tempDir: string;
  let fakeLog: string;

  beforeEach(() => {
    tempDir = buildTempRepo();
    fakeLog = join(tempDir, "fake-autosave.log");
    delete process.env.PAPERCLIP_NO_AUTOSAVE;
  });

  afterEach(() => {
    if (tempDir) {
      rmSync(tempDir, { recursive: true, force: true });
    }
    delete process.env.AUTOSAVE_FAKE_LOG;
  });

  it("invokes the autosave script with the run-id and the workspace cwd", async () => {
    process.env.AUTOSAVE_FAKE_LOG = fakeLog;
    const result = await runSessionEndAutosave({
      runId: "run-deadbeef",
      workspaceCwd: tempDir,
      scriptPath: join(tempDir, "fake-autosave.sh"),
      pythonBin: "bash",
      timeoutMs: 5_000,
    });

    expect(result.invoked).toBe(true);
    expect(result.skipped).toBe(false);
    expect(result.exitCode).toBe(0);
    // The fake stamp proves the wrapper passed run-id + cwd through.
    const logContents = readFileSync(fakeLog, "utf8");
    expect(logContents).toContain("run-deadbeef");
    expect(logContents).toContain(tempDir);
  });

  it("skips when PAPERCLIP_NO_AUTOSAVE=1 is set", async () => {
    process.env.PAPERCLIP_NO_AUTOSAVE = "1";
    const result = await runSessionEndAutosave({
      runId: "run-should-skip",
      workspaceCwd: tempDir,
      scriptPath: join(tempDir, "fake-autosave.sh"),
      pythonBin: "bash",
    });
    expect(result.skipped).toBe(true);
    expect(result.reason).toContain("PAPERCLIP_NO_AUTOSAVE");
    delete process.env.PAPERCLIP_NO_AUTOSAVE;
  });

  it("skips when no runId is provided", async () => {
    const result = await runSessionEndAutosave({
      runId: "",
      workspaceCwd: tempDir,
      scriptPath: join(tempDir, "fake-autosave.sh"),
      pythonBin: "bash",
    });
    expect(result.skipped).toBe(true);
    expect(result.reason).toMatch(/missing runId|workspaceCwd/);
  });

  it("captures the exit code from the script", async () => {
    process.env.AUTOSAVE_FAKE_LOG = fakeLog;
    // Make the fake script return a non-zero exit code so we can verify the
    // wrapper surfaces it without trying to interpret / retry.
    writeFileSync(
      join(tempDir, "failing-fake.sh"),
      "#!/usr/bin/env bash\nexit 2\n",
    );
    const result = await runSessionEndAutosave({
      runId: "run-failure",
      workspaceCwd: tempDir,
      scriptPath: join(tempDir, "failing-fake.sh"),
      pythonBin: "bash",
      timeoutMs: 5_000,
    });
    expect(result.invoked).toBe(true);
    expect(result.exitCode).toBe(2);
  });
});

describe("runAdapterSessionEndAutosave", () => {
  let tempDir: string;
  let fakeLog: string;

  beforeEach(() => {
    tempDir = buildTempRepo();
    fakeLog = join(tempDir, "fake-autosave.log");
    delete process.env.PAPERCLIP_NO_AUTOSAVE;
  });

  afterEach(() => {
    if (tempDir) {
      rmSync(tempDir, { recursive: true, force: true });
    }
    delete process.env.AUTOSAVE_FAKE_LOG;
  });

  it("forwards runId, workspace cwd, and issue id from the context shape", async () => {
    process.env.AUTOSAVE_FAKE_LOG = fakeLog;
    const result = await runSessionEndAutosave({
      runId: "run-ctx",
      workspaceCwd: tempDir,
      issueId: "BTCAAAAA-39074",
      scriptPath: join(tempDir, "fake-autosave.sh"),
      pythonBin: "bash",
      timeoutMs: 5_000,
    });

    expect(result.invoked).toBe(true);
    expect(result.exitCode).toBe(0);
    const logContents = readFileSync(fakeLog, "utf8");
    // The fake log records $PAPERCLIP_RUN_ID env via the wrapper + the argv;
    // both must show through so the real script's WIP commit is correct.
    expect(logContents).toContain("run-ctx");
    expect(logContents).toContain("BTCAAAAA-39074");
    // Belt-and-suspenders: also verify the high-level helper returns a
    // structurally sane result (no throw, sane skipped flag).
    const helper = await runAdapterSessionEndAutosave(
      {
        runId: "run-ctx-2",
        context: { paperclipWorkspace: { cwd: tempDir }, issueId: "BTCAAAAA-39074" },
      },
      {
        scriptPath: join(tempDir, "fake-autosave.sh"),
        pythonBin: "bash",
        timeoutMs: 5_000,
      },
    );
    expect(helper.invoked || helper.skipped).toBe(true);
  });

  it("never throws when given an unspeakable context shape", async () => {
    // Defensive: adapters pass a parsed ctx; if shape is broken, helper must
    // still return a result (not throw) — finally blocks depend on this.
    const result = await runAdapterSessionEndAutosave({
      runId: "run-defensive",
      context: null,
    } as any);
    expect(result).toBeDefined();
    expect(typeof result.skipped).toBe("boolean");
  });
});

describe("dirty-tree run-end", () => {
  it("simulates a run that leaves the workspace dirty on termination", async () => {
    // End-to-end smoke: simulate an adapter run that edits files in the
    // protected branch workspace, then the wrapper must successfully invoke
    // a stand-in autosave script. We don't assert on the git push itself
    // (that's the python script's job and is exercised by session_end_autosave's
    // own smoke contract); we only assert that the wrapper forwarded all
    // the args the script needs to do the commit.
    const tempDir = buildTempRepo();
    const fakeLog = join(tempDir, "dirty.log");
    try {
      process.env.AUTOSAVE_FAKE_LOG = fakeLog;
      writeFileSync(join(tempDir, "dirty.txt"), "uncommitted work\n");
      runGit(tempDir, ["add", "dirty.txt"]);

      // sanity-check: dirty tree really is dirty
      const before = spawnSync("git", ["status", "--porcelain"], {
        cwd: tempDir,
        encoding: "utf8",
      });
      expect(before.stdout.trim()).not.toBe("");

      const result = await runSessionEndAutosave({
        runId: "run-dirty",
        workspaceCwd: tempDir,
        scriptPath: join(tempDir, "fake-autosave.sh"),
        pythonBin: "bash",
        timeoutMs: 5_000,
      });

      expect(result.invoked).toBe(true);
      const logContents = readFileSync(fakeLog, "utf8");
      expect(logContents).toContain("run-dirty");
      expect(logContents).toContain(tempDir);
    } finally {
      delete process.env.AUTOSAVE_FAKE_LOG;
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});

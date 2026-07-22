import { describe, expect, it, vi, beforeEach } from "vitest";

const mockFs = vi.hoisted(() => ({
  lstat: vi.fn(),
  stat: vi.fn(),
  mkdir: vi.fn(),
  rm: vi.fn(),
  readdir: vi.fn(),
}));

vi.mock("node:fs/promises", () => ({ default: mockFs }));

const mockExecFile = vi.hoisted(() => vi.fn());

vi.mock("node:child_process", () => ({
  execFile: mockExecFile,
}));

vi.mock("node:util", () => ({
  promisify: (fn: unknown) => fn,
}));

vi.mock("../home-paths.ts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../home-paths.ts")>();
  return { ...actual, resolvePaperclipInstanceRoot: () => "/tmp" };
});

vi.mock("../middleware/logger.js", () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
}));

const { probeWorkspaceCwdHealthy, attemptWorkspaceCwdRepair } = await import(
  "../services/heartbeat.ts"
);

const okStat = () =>
  Promise.resolve({
    isDirectory: () => true,
    isFile: () => false,
  }) as unknown as Promise<import("node:fs").Stats>;

const dirStat = () =>
  Promise.resolve({
    isDirectory: () => true,
    isFile: () => false,
  }) as unknown as Promise<import("node:fs").Stats>;

const fileStat = () =>
  Promise.resolve({
    isDirectory: () => false,
    isFile: () => true,
  }) as unknown as Promise<import("node:fs").Stats>;

describe("probeWorkspaceCwdHealthy", () => {
  beforeEach(() => {
    mockFs.lstat.mockReset();
    mockFs.stat.mockReset();
    mockExecFile.mockReset();
    mockFs.mkdir.mockReset();
    mockFs.rm.mockReset();
    mockFs.readdir.mockReset();
  });

  it("returns false when cwd is null or empty", async () => {
    mockFs.lstat.mockImplementation(() => Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" })));
    await expect(probeWorkspaceCwdHealthy(null)).resolves.toBe(false);
    await expect(probeWorkspaceCwdHealthy(undefined)).resolves.toBe(false);
    await expect(probeWorkspaceCwdHealthy("")).resolves.toBe(false);
    expect(mockFs.lstat).not.toHaveBeenCalled();
  });

  it("returns false when .git metadata is missing", async () => {
    mockFs.lstat.mockImplementation(() =>
      Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" })),
    );
    await expect(probeWorkspaceCwdHealthy("/tmp/missing")).resolves.toBe(false);
    expect(mockFs.lstat).toHaveBeenCalledTimes(1);
    expect(mockFs.stat).not.toHaveBeenCalled();
  });

  it("returns false when .git exists but the cwd stat throws", async () => {
    mockFs.lstat.mockImplementation(() => dirStat());
    mockFs.stat.mockImplementation(() =>
      Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" })),
    );
    await expect(probeWorkspaceCwdHealthy("/tmp/cwd")).resolves.toBe(false);
    expect(mockFs.lstat).toHaveBeenCalledWith("/tmp/cwd/.git");
    expect(mockFs.stat).toHaveBeenCalledWith("/tmp/cwd");
  });

  it("returns true when .git exists and the cwd stat resolves", async () => {
    mockFs.lstat.mockImplementation(() => dirStat());
    mockFs.stat.mockImplementation(() => okStat());
    await expect(probeWorkspaceCwdHealthy("/tmp/cwd")).resolves.toBe(true);
  });

  it("returns true when .git is a file (worktree-style gitdir)", async () => {
    mockFs.lstat.mockImplementation(() => fileStat());
    mockFs.stat.mockImplementation(() => okStat());
    await expect(probeWorkspaceCwdHealthy("/tmp/worktree")).resolves.toBe(true);
  });
});

describe("attemptWorkspaceCwdRepair", () => {
  beforeEach(() => {
    mockFs.lstat.mockReset();
    mockFs.stat.mockReset();
    mockFs.mkdir.mockReset();
    mockFs.rm.mockReset();
    mockFs.readdir.mockReset();
    mockExecFile.mockReset();
  });

  it("returns missing_cwd when no cwd is provided", async () => {
    const result = await attemptWorkspaceCwdRepair({ cwd: null, repoUrl: "git@example.com:repo.git" });
    expect(result).toEqual({ ok: false, reason: "missing_cwd" });
    expect(mockExecFile).not.toHaveBeenCalled();
    expect(mockFs.rm).not.toHaveBeenCalled();
  });

  it("rejects a broken cwd outside the Paperclip instance root", async () => {
    mockFs.lstat.mockImplementation(() =>
      Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" })),
    );
    const result = await attemptWorkspaceCwdRepair({
      cwd: "/etc/paperclip-workspace",
      repoUrl: "https://example.com/repo.git",
    });
    expect(result).toEqual({ ok: false, reason: "unsafe_path" });
    expect(mockExecFile).not.toHaveBeenCalled();
    expect(mockFs.mkdir).not.toHaveBeenCalled();
  });

  it("rejects a healthy cwd outside the Paperclip instance root", async () => {
    mockFs.lstat.mockImplementation(() => dirStat());
    mockFs.stat.mockImplementation(() => okStat());
    const result = await attemptWorkspaceCwdRepair({
      cwd: "/etc/paperclip-workspace",
      repoUrl: "https://example.com/repo.git",
    });
    expect(result).toEqual({ ok: false, reason: "unsafe_path" });
    expect(mockExecFile).not.toHaveBeenCalled();
  });

  it("rejects the Paperclip instance root itself", async () => {
    mockFs.lstat.mockImplementation(() =>
      Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" })),
    );
    const result = await attemptWorkspaceCwdRepair({
      cwd: "/tmp",
      repoUrl: "https://example.com/repo.git",
    });
    expect(result).toEqual({ ok: false, reason: "unsafe_path" });
    expect(mockExecFile).not.toHaveBeenCalled();
  });

  it("refuses to replace an existing unhealthy directory with a symlink", async () => {
    mockFs.stat.mockImplementation((path: string) => {
      if (path === "/tmp/managed" || path === "/tmp/cwd") return okStat();
      return Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" }));
    });
    mockFs.lstat.mockImplementation((path: string) => {
      if (path === "/tmp/managed/.git") return dirStat();
      if (path === "/tmp/cwd") {
        return Promise.resolve({
          isSymbolicLink: () => false,
          isDirectory: () => true,
          isFile: () => false,
        } as unknown as import("node:fs").Stats);
      }
      return Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" }));
    });

    const result = await attemptWorkspaceCwdRepair({
      cwd: "/tmp/cwd",
      repoUrl: "https://example.com/repo.git",
      managedFolder: "/tmp/managed",
    });

    expect(result).toEqual({ ok: false, reason: "unsafe_existing_path" });
    expect(mockExecFile).not.toHaveBeenCalled();
  });

  it("returns noop_existing when the cwd already has .git metadata", async () => {
    mockFs.stat.mockImplementation(() => okStat());
    mockFs.lstat.mockImplementation(() => dirStat());
    const result = await attemptWorkspaceCwdRepair({
      cwd: "/tmp/already-cloned",
      repoUrl: "git@example.com:repo.git",
      managedFolder: "/tmp/managed",
    });
    expect(result).toEqual({ ok: true, cwd: "/tmp/already-cloned", mode: "noop_existing" });
    expect(mockExecFile).not.toHaveBeenCalled();
    expect(mockFs.mkdir).not.toHaveBeenCalled();
    expect(mockFs.rm).not.toHaveBeenCalled();
  });

  it("symlinks cwd to a populated, healthy managed folder via ln -snf", async () => {
    let symlinked = false;
    mockFs.stat.mockImplementation((path: string) => {
      if (path === "/tmp/managed") return okStat();
      if (symlinked && path === "/tmp/cwd") return okStat();
      return Promise.reject(
        Object.assign(new Error("ENOENT"), { code: "ENOENT" }),
      );
    });
    mockFs.lstat.mockImplementation((path: string) => {
      if (symlinked && path === "/tmp/cwd") {
        return Promise.resolve({
          isSymbolicLink: () => true,
          isDirectory: () => false,
        } as unknown as import("node:fs").Stats);
      }
      if (path === "/tmp/managed/.git") return dirStat();
      if (symlinked && path === "/tmp/cwd/.git") return dirStat();
      return Promise.reject(
        Object.assign(new Error("ENOENT"), { code: "ENOENT" }),
      );
    });
    mockFs.readdir.mockImplementation((path: string) =>
      path === "/tmp/managed"
        ? Promise.resolve([".git"] as unknown as string[])
        : Promise.resolve([] as unknown as string[]),
    );
    mockFs.mkdir.mockImplementation(() => Promise.resolve());
    mockExecFile.mockImplementation(() => {
      symlinked = true;
      return Promise.resolve({ stdout: "", stderr: "" });
    });
    const result = await attemptWorkspaceCwdRepair({
      cwd: "/tmp/cwd",
      repoUrl: "git@example.com:repo.git",
      managedFolder: "/tmp/managed",
    });
    expect(result).toEqual({ ok: true, cwd: "/tmp/managed", mode: "symlink" });
    expect(mockFs.rm).not.toHaveBeenCalled();
    expect(mockExecFile).toHaveBeenCalledTimes(1);
    const callArgs = mockExecFile.mock.calls[0];
    expect(callArgs[0]).toBe("ln");
    expect(callArgs[1]).toEqual(["-snf", "/tmp/managed", "/tmp/cwd"]);
  });

  it("falls through to git fetch when .git metadata appears during the repair", async () => {
    let lstatCalls = 0;
    mockFs.stat.mockImplementation(() => okStat());
    mockFs.lstat.mockImplementation(() => {
      lstatCalls += 1;
      if (lstatCalls === 1) {
        return Promise.reject(
          Object.assign(new Error("ENOENT"), { code: "ENOENT" }),
        );
      }
      return dirStat();
    });
    mockExecFile.mockImplementation(() => Promise.resolve({ stdout: "", stderr: "" }));
    const result = await attemptWorkspaceCwdRepair({
      cwd: "/tmp/existing",
      repoUrl: "git@example.com:repo.git",
    });
    expect(result).toEqual({ ok: true, cwd: "/tmp/existing", mode: "git_fetch" });
    expect(mockFs.rm).not.toHaveBeenCalled();
    expect(mockExecFile).toHaveBeenCalledTimes(1);
    const callArgs = mockExecFile.mock.calls[0];
    expect(callArgs[0]).toBe("git");
    expect(callArgs[1]).toEqual(["-C", "/tmp/existing", "fetch"]);
  });

  it("returns no_repo_url when cwd exists but lacks .git and no repoUrl is supplied", async () => {
    mockFs.stat.mockImplementation(() => okStat());
    mockFs.lstat.mockImplementation(() =>
      Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" })),
    );
    const result = await attemptWorkspaceCwdRepair({ cwd: "/tmp/empty", repoUrl: null });
    expect(result).toEqual({ ok: false, reason: "no_repo_url" });
    expect(mockExecFile).not.toHaveBeenCalled();
    expect(mockFs.rm).not.toHaveBeenCalled();
  });

  it("runs git clone without deleting the existing cwd", async () => {
    let lstatCalls = 0;
    mockFs.stat.mockImplementation(() => okStat());
    mockFs.lstat.mockImplementation(() => {
      lstatCalls += 1;
      if (lstatCalls <= 2) {
        return Promise.reject(
          Object.assign(new Error("ENOENT"), { code: "ENOENT" }),
        );
      }
      return dirStat();
    });
    mockExecFile.mockImplementation(() => Promise.resolve({ stdout: "", stderr: "" }));
    const result = await attemptWorkspaceCwdRepair({
      cwd: "/tmp/corrupted",
      repoUrl: "git@example.com:repo.git",
    });
    expect(result).toEqual({ ok: true, cwd: "/tmp/corrupted", mode: "git_clone" });
    expect(mockFs.rm).not.toHaveBeenCalled();
    expect(mockExecFile).toHaveBeenCalledTimes(1);
    const callArgs = mockExecFile.mock.calls[0];
    expect(callArgs[0]).toBe("git");
    expect(callArgs[1]).toEqual(["clone", "--", "git@example.com:repo.git", "/tmp/corrupted"]);
  });

  it("returns git_repair_failed when the git subprocess throws", async () => {
    let lstatCalls = 0;
    mockFs.stat.mockImplementation(() => okStat());
    mockFs.lstat.mockImplementation(() => {
      lstatCalls += 1;
      if (lstatCalls === 1) {
        return Promise.reject(
          Object.assign(new Error("ENOENT"), { code: "ENOENT" }),
        );
      }
      return dirStat();
    });
    mockExecFile.mockImplementation(() =>
      Promise.reject(Object.assign(new Error("fatal: repository not found"), { code: 128 })),
    );
    const result = await attemptWorkspaceCwdRepair({
      cwd: "/tmp/bad-fetch",
      repoUrl: "git@example.com:repo.git",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason.startsWith("git_repair_failed:")).toBe(true);
    }
    expect(mockFs.rm).not.toHaveBeenCalled();
  });

  it("never invokes fs.rm regardless of branch", async () => {
    const scenarios = [
      {
        cwd: "/tmp/rm-check-1",
        repoUrl: "git@example.com:repo.git",
        statImpl: () => okStat(),
        lstatImpl: () => dirStat(),
      },
      {
        cwd: "/tmp/rm-check-2",
        repoUrl: "git@example.com:repo.git",
        statImpl: () => okStat(),
        lstatImpl: () =>
          Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" })),
      },
    ];
    mockExecFile.mockImplementation(() => Promise.resolve({ stdout: "", stderr: "" }));
    for (const scenario of scenarios) {
      mockFs.stat.mockImplementation(scenario.statImpl);
      mockFs.lstat.mockImplementation(scenario.lstatImpl);
      mockFs.rm.mockClear();
      await attemptWorkspaceCwdRepair({
        cwd: scenario.cwd,
        repoUrl: scenario.repoUrl,
      });
      expect(mockFs.rm).not.toHaveBeenCalled();
    }
  });

  it("mkdirs the parent and falls through to git fetch when .git is present", async () => {
    let statCalls = 0;
    mockFs.stat.mockImplementation(() => {
      statCalls += 1;
      if (statCalls === 1) {
        return Promise.reject(Object.assign(new Error("ENOENT"), { code: "ENOENT" }));
      }
      return okStat();
    });
    mockFs.mkdir.mockImplementation(() => Promise.resolve());
    mockFs.lstat.mockImplementation(() => dirStat());
    mockExecFile.mockImplementation(() => Promise.resolve({ stdout: "", stderr: "" }));
    const result = await attemptWorkspaceCwdRepair({
      cwd: "/tmp/clean",
      repoUrl: "git@example.com:repo.git",
    });
    expect(mockFs.mkdir).toHaveBeenCalledWith("/tmp", { recursive: true });
    expect(mockFs.rm).not.toHaveBeenCalled();
    expect(mockExecFile).toHaveBeenCalledTimes(1);
    const callArgs = mockExecFile.mock.calls[0];
    expect(callArgs[0]).toBe("git");
    expect(callArgs[1]).toEqual(["-C", "/tmp/clean", "fetch"]);
    expect(result).toEqual({ ok: true, cwd: "/tmp/clean", mode: "git_fetch" });
  });
});

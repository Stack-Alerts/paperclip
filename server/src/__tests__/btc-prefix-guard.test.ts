import { describe, expect, it } from "vitest";
import express from "express";
import request from "supertest";
import {
  BTC_FULL_PREFIX,
  enforceBtcPrefixTokens,
  extractBtcPrefixTokens,
  pickActorCompanyId,
  respondBtcPrefixGuardFailure,
  suggestedFullForm,
} from "../middleware/btc-prefix-guard.js";

describe("extractBtcPrefixTokens", () => {
  it("extracts a single 4-digit token", () => {
    expect(extractBtcPrefixTokens("see BTC-9999 for context")).toEqual(["BTC-9999"]);
  });

  it("extracts 5- and 6-digit tokens", () => {
    expect(extractBtcPrefixTokens("BTC-12345 and BTC-123456 both qualify")).toEqual([
      "BTC-12345",
      "BTC-123456",
    ]);
  });

  it("matches tokens with fewer than 4 digits (early issue numbers must also be caught)", () => {
    expect(extractBtcPrefixTokens("BTC-12 is an early issue")).toEqual(["BTC-12"]);
    expect(extractBtcPrefixTokens("BTC-1 is the first")).toEqual(["BTC-1"]);
  });

  it("does not match tokens with more than 6 digits", () => {
    expect(extractBtcPrefixTokens("BTC-1234567 has 7 digits")).toEqual([]);
    expect(extractBtcPrefixTokens("BTC-1234567890123 way too long")).toEqual([]);
  });

  it("does not match non-digit suffixes like BTC-EUR", () => {
    expect(extractBtcPrefixTokens("BTC-EUR is a fiat pair")).toEqual([]);
    expect(extractBtcPrefixTokens("BTC-USD")).toEqual([]);
  });

  it("does not match the full prefix form BTCAAAAA-1234", () => {
    expect(extractBtcPrefixTokens("already full BTCAAAAA-1234")).toEqual([]);
  });

  it("requires word boundaries (no match for BTC-1234abc)", () => {
    expect(extractBtcPrefixTokens("see BTC-1234abc trailing")).toEqual([]);
  });

  it("returns [] for empty or non-string input", () => {
    expect(extractBtcPrefixTokens("")).toEqual([]);
    expect(extractBtcPrefixTokens(null)).toEqual([]);
    expect(extractBtcPrefixTokens(undefined)).toEqual([]);
  });

  it("is idempotent across multiple tokens", () => {
    const text = "first BTC-1234 then BTC-5678 finally BTC-1234 again";
    expect(extractBtcPrefixTokens(text)).toEqual(["BTC-1234", "BTC-5678", "BTC-1234"]);
  });

  it("matches lowercase variants (btc-9999 is an issue reference)", () => {
    expect(extractBtcPrefixTokens("see btc-9999 lowercase")).toEqual(["btc-9999"]);
    expect(extractBtcPrefixTokens("mixed Btc-1234 case")).toEqual(["Btc-1234"]);
  });

  it("ignores BTC-N tokens inside inline code blocks", () => {
    expect(extractBtcPrefixTokens("run `BTC-9999` in terminal")).toEqual([]);
  });

  it("ignores BTC-N tokens inside fenced code blocks", () => {
    const text = "See the example:\n```\ncurl /issues/BTC-9999\n```\nFor more context.";
    expect(extractBtcPrefixTokens(text)).toEqual([]);
  });

  it("catches BTC-N tokens outside of code blocks", () => {
    const text = "Reference BTC-1234 but not `BTC-5678`";
    expect(extractBtcPrefixTokens(text)).toEqual(["BTC-1234"]);
  });
});

describe("suggestedFullForm", () => {
  it("normalizes BTC-N to BTCAAAAA-N", () => {
    expect(suggestedFullForm("BTC-9999")).toBe("BTCAAAAA-9999");
  });

  it("uses a custom prefix when supplied", () => {
    expect(suggestedFullForm("BTC-9999", "PAPER")).toBe("PAPER-9999");
  });

  it("returns null for non-conforming tokens", () => {
    expect(suggestedFullForm("BTCAAAAA-1234")).toBeNull();
    expect(suggestedFullForm("BTC-EUR")).toBeNull();
  });

  it("normalizes short-number tokens like BTC-12 (early issues)", () => {
    expect(suggestedFullForm("BTC-12")).toBe("BTCAAAAA-12");
    expect(suggestedFullForm("BTC-1")).toBe("BTCAAAAA-1");
  });

  it("normalizes lowercase variants to full-prefix form", () => {
    expect(suggestedFullForm("btc-9999")).toBe("BTCAAAAA-9999");
    expect(suggestedFullForm("Btc-1234")).toBe("BTCAAAAA-1234");
  });
});

describe("pickActorCompanyId", () => {
  it("prefers the singular companyId field", () => {
    expect(pickActorCompanyId({ type: "agent", companyId: "c1", companyIds: ["c2"] })).toBe("c1");
  });

  it("falls back to the first entry of companyIds", () => {
    expect(pickActorCompanyId({ type: "board", companyIds: ["c2", "c3"] })).toBe("c2");
  });

  it("returns null when the actor has no company context", () => {
    expect(pickActorCompanyId({ type: "agent" })).toBeNull();
    expect(pickActorCompanyId(null)).toBeNull();
    expect(pickActorCompanyId(undefined)).toBeNull();
  });
});

describe("enforceBtcPrefixTokens", () => {
  const companyId = "73419cf3-bd37-4a7c-8782-311ccb47fced";
  const actor = { type: "agent", companyId };

  it("passes when text has no BTC-N tokens", async () => {
    const result = await enforceBtcPrefixTokens({
      text: "hello world",
      actor,
      lookup: async () => ({ exists: true }),
    });
    expect(result.ok).toBe(true);
  });

  it("passes when the candidate resolves in the actor's company", async () => {
    const seen: string[] = [];
    const result = await enforceBtcPrefixTokens({
      text: "see BTC-9999",
      actor,
      lookup: async (candidate, cid) => {
        seen.push(candidate);
        expect(cid).toBe(companyId);
        return { exists: true };
      },
    });
    expect(result).toEqual({ ok: true });
    expect(seen).toEqual(["BTCAAAAA-9999"]);
  });

  it("rejects with 422 fields when the candidate does not resolve", async () => {
    const result = await enforceBtcPrefixTokens({
      text: "see BTC-9999",
      actor,
      lookup: async () => null,
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.offendingToken).toBe("BTC-9999");
      expect(result.suggestedFull).toBe("BTCAAAAA-9999");
      expect(result.actorCompanyId).toBe(companyId);
    }
  });

  it("rejects when lookup returns exists:false", async () => {
    const result = await enforceBtcPrefixTokens({
      text: "look at BTC-12345",
      actor,
      lookup: async () => ({ exists: false }),
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.offendingToken).toBe("BTC-12345");
      expect(result.suggestedFull).toBe("BTCAAAAA-12345");
    }
  });

  it("rejects when the candidate resolves in a different company", async () => {
    const result = await enforceBtcPrefixTokens({
      text: "see BTC-9999",
      actor,
      lookup: async () => ({ exists: false }),
    });
    expect(result.ok).toBe(false);
  });

  it("ignores tokens that don't match the regex (BTC-EUR, BTCAAAAA-1234)", async () => {
    const seen: string[] = [];
    const result = await enforceBtcPrefixTokens({
      text: "trading BTC-EUR vs BTC-USD, see BTCAAAAA-1234",
      actor,
      lookup: async (candidate) => {
        seen.push(candidate);
        return { exists: true };
      },
    });
    expect(result).toEqual({ ok: true });
    expect(seen).toEqual([]);
  });

  it("skips enforcement when the actor has no companyId (no false positives on unknown actors)", async () => {
    let calls = 0;
    const result = await enforceBtcPrefixTokens({
      text: "see BTC-9999",
      actor: { type: "agent" },
      lookup: async () => {
        calls += 1;
        return { exists: true };
      },
    });
    expect(result).toEqual({ ok: true });
    expect(calls).toBe(0);
  });

  it("uses explicit companyId over actor when both are provided", async () => {
    const seen: Array<{ candidate: string; cid: string }> = [];
    const result = await enforceBtcPrefixTokens({
      text: "see BTC-9999",
      companyId: "explicit-company",
      actor: { type: "board", companyIds: ["other-company"] },
      lookup: async (candidate, cid) => {
        seen.push({ candidate, cid });
        return { exists: true };
      },
    });
    expect(result).toEqual({ ok: true });
    expect(seen[0].cid).toBe("explicit-company");
  });

  it("uses explicit companyId without actor (multi-company board user scenario)", async () => {
    const result = await enforceBtcPrefixTokens({
      text: "see BTC-9999",
      companyId: "target-company",
      lookup: async (_candidate, cid) => ({ exists: cid === "target-company" }),
    });
    expect(result).toEqual({ ok: true });
  });

  it("allows token when it resolves in a non-primary actor company (multi-company board user)", async () => {
    // Board actor has two companies; token only exists in the second one.
    const boardActor = { type: "board", companyIds: ["c-primary", "c-secondary"] };
    const result = await enforceBtcPrefixTokens({
      text: "see BTC-9999",
      actor: boardActor,
      lookup: async (_candidate, cid) => ({ exists: cid === "c-secondary" }),
    });
    expect(result).toEqual({ ok: true });
  });

  it("rejects token when it resolves in NONE of the actor companies", async () => {
    const boardActor = { type: "board", companyIds: ["c1", "c2"] };
    const result = await enforceBtcPrefixTokens({
      text: "see BTC-9999",
      actor: boardActor,
      lookup: async () => ({ exists: false }),
    });
    expect(result.ok).toBe(false);
  });

  it("catches lowercase BTC-N tokens (case-insensitive enforcement)", async () => {
    const result = await enforceBtcPrefixTokens({
      text: "see btc-9999 lowercase",
      actor,
      lookup: async () => null,
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.offendingToken).toBe("btc-9999");
      expect(result.suggestedFull).toBe("BTCAAAAA-9999");
    }
  });

  it("does not reject BTC-N tokens inside inline code blocks", async () => {
    const result = await enforceBtcPrefixTokens({
      text: "Run `BTC-9999` in the terminal",
      actor,
      lookup: async () => null,
    });
    expect(result).toEqual({ ok: true });
  });

  it("deduplicates lookups for repeated tokens", async () => {
    let calls = 0;
    const result = await enforceBtcPrefixTokens({
      text: "first BTC-9999 then BTC-9999 again",
      actor,
      lookup: async () => {
        calls += 1;
        return { exists: true };
      },
    });
    expect(result).toEqual({ ok: true });
    expect(calls).toBe(1);
  });

  it("returns the first failing token when multiple are present", async () => {
    const result = await enforceBtcPrefixTokens({
      text: "BTC-1111 ok BTC-2222 bad",
      actor,
      lookup: async (candidate) => {
        if (candidate === "BTCAAAAA-1111") return { exists: true };
        return { exists: false };
      },
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.offendingToken).toBe("BTC-2222");
      expect(result.suggestedFull).toBe("BTCAAAAA-2222");
    }
  });
});

describe("BTC_FULL_PREFIX", () => {
  it("matches the active company's prefix for BTCAAAAA", () => {
    expect(BTC_FULL_PREFIX).toBe("BTCAAAAA");
  });
});

describe("enforceBtcPrefixTokens via express middleware mount", () => {
  function mountGuard(lookup: Parameters<typeof enforceBtcPrefixTokens>[0]["lookup"]) {
    const app = express();
    app.use(express.json());
    app.use((req, _res, next) => {
      req.actor = { type: "agent", companyId: "company-1" };
      next();
    });
    app.post("/comments", async (req, res) => {
      const result = await enforceBtcPrefixTokens({
        text: req.body?.body ?? "",
        actor: req.actor,
        lookup,
      });
      if (!result.ok) {
        res.status(422).json({
          error: "Truncated prefix",
          message: `Comment contains '${result.offendingToken}' which does not resolve to a real identifier in this company. Use the full '${result.suggestedFull}' form.`,
          details: {
            offendingToken: result.offendingToken,
            suggestedFull: result.suggestedFull,
            companyId: result.actorCompanyId,
          },
        });
        return;
      }
      res.status(201).json({ ok: true });
    });
    return app;
  }

  it("returns 422 with the expected payload when a BTC-N token doesn't resolve", async () => {
    const app = mountGuard(async () => null);
    const res = await request(app)
      .post("/comments")
      .send({ body: "see BTC-9999 for context" });
    expect(res.status).toBe(422);
    expect(res.body.error).toBe("Truncated prefix");
    expect(res.body.details.offendingToken).toBe("BTC-9999");
    expect(res.body.details.suggestedFull).toBe("BTCAAAAA-9999");
    expect(res.body.details.companyId).toBe("company-1");
  });

  it("returns 201 for a comment containing a resolving short form", async () => {
    const app = mountGuard(async (candidate) => ({
      exists: candidate === "BTCAAAAA-9999",
    }));
    const res = await request(app).post("/comments").send({ body: "see BTC-9999" });
    expect(res.status).toBe(201);
    expect(res.body).toEqual({ ok: true });
  });

  it("returns 201 for a control comment with the full prefix", async () => {
    const app = mountGuard(async () => {
      throw new Error("lookup should not be called when no BTC-N tokens are present");
    });
    const res = await request(app).post("/comments").send({ body: "see BTCAAAAA-1234" });
    expect(res.status).toBe(201);
  });

  it("returns 201 for a comment with no issue tokens at all", async () => {
    const app = mountGuard(async () => {
      throw new Error("lookup should not be called");
    });
    const res = await request(app).post("/comments").send({ body: "no tokens here" });
    expect(res.status).toBe(201);
  });

  it("returns 201 for a comment containing BTC-EUR (no false positives)", async () => {
    const app = mountGuard(async () => {
      throw new Error("lookup should not be called for BTC-EUR");
    });
    const res = await request(app).post("/comments").send({ body: "trading BTC-EUR" });
    expect(res.status).toBe(201);
  });
});

/**
 * Route-level integration tests that mirror the exact wire-up pattern in
 * server/src/routes/issues.ts for POST /issues/:id/comments and PATCH
 * /issues/:id. The lookup shape matches `svc.getByIdentifierForCompany`
 * (returns truthy when the issue exists in the company, null when missing).
 */
describe("btc-prefix-guard wired into route handlers", () => {
  type IssueRow = { id: string; identifier: string };
  function buildLookup(issues: IssueRow[]) {
    return async (fullIdentifier: string, companyId: string) => {
      const found = issues.find(
        (i) => i.identifier.toLowerCase() === fullIdentifier.toLowerCase(),
      );
      return found ? { exists: true, id: found.id, companyId } : null;
    };
  }

  function buildRouteApp(opts: {
    actor:
      | { type: "agent"; companyId: string }
      | { type: "board"; companyIds: string[] }
      | { type: "none" };
    issue: { id: string; companyId: string };
    lookup: (fullIdentifier: string, companyId: string) => Promise<unknown>;
  }) {
    const app = express();
    app.use(express.json());
    app.use((req, _res, next) => {
      (req as unknown as { actor: typeof opts.actor }).actor = opts.actor;
      next();
    });
    // Mirrors the wire-up in routes/issues.ts POST /issues/:id/comments
    app.post("/issues/:id/comments", async (req, res) => {
      const actor = (req as unknown as { actor: typeof opts.actor }).actor;
      if (actor.type === "agent" && typeof (req.body as { body?: unknown }).body === "string") {
        const result = await enforceBtcPrefixTokens({
          text: (req.body as { body: string }).body,
          companyId: opts.issue.companyId,
          actor,
          lookup: opts.lookup as Parameters<typeof enforceBtcPrefixTokens>[0]["lookup"],
        });
        if (!result.ok) {
          respondBtcPrefixGuardFailure(res, result);
          return;
        }
      }
      res.status(201).json({ ok: true, issueId: opts.issue.id });
    });
    // Mirrors the wire-up in routes/issues.ts PATCH /issues/:id
    app.patch("/issues/:id", async (req, res) => {
      const actor = (req as unknown as { actor: typeof opts.actor }).actor;
      if (actor.type === "agent") {
        const body = req.body as { description?: unknown; comment?: unknown };
        const descriptionText = typeof body.description === "string" ? body.description : null;
        const commentBodyText = typeof body.comment === "string" ? body.comment : null;
        const textToGuard = descriptionText ?? commentBodyText;
        if (textToGuard !== null) {
          const result = await enforceBtcPrefixTokens({
            text: textToGuard,
            companyId: opts.issue.companyId,
            actor,
            lookup: opts.lookup as Parameters<typeof enforceBtcPrefixTokens>[0]["lookup"],
          });
          if (!result.ok) {
            respondBtcPrefixGuardFailure(res, result);
            return;
          }
        }
      }
      res.status(200).json({ ok: true, issueId: opts.issue.id });
    });
    return app;
  }

  const existingIssues: IssueRow[] = [
    { id: "issue-1", identifier: "BTCAAAAA-9999" },
  ];

  it("(a) POST /issues/:id/comments returns 422 for agent actor when BTC-9999 does not resolve", async () => {
    const app = buildRouteApp({
      actor: { type: "agent", companyId: "company-A" },
      issue: { id: "issue-1", companyId: "company-A" },
      lookup: buildLookup([]),
    });
    const res = await request(app)
      .post("/issues/issue-1/comments")
      .send({ body: "see BTC-9999 for context" });
    expect(res.status).toBe(422);
    expect(res.body.error).toBe("Truncated prefix");
    expect(res.body.details.offendingToken).toBe("BTC-9999");
    expect(res.body.details.suggestedFull).toBe("BTCAAAAA-9999");
    expect(res.body.details.companyId).toBe("company-A");
  });

  it("(b) POST /issues/:id/comments returns 201 when BTC-9999 resolves in the actor's company", async () => {
    const app = buildRouteApp({
      actor: { type: "agent", companyId: "company-A" },
      issue: { id: "issue-1", companyId: "company-A" },
      lookup: buildLookup(existingIssues),
    });
    const res = await request(app)
      .post("/issues/issue-1/comments")
      .send({ body: "see BTC-9999 for context" });
    expect(res.status).toBe(201);
    expect(res.body).toEqual({ ok: true, issueId: "issue-1" });
  });

  it("(c) POST /issues/:id/comments returns 201 for system actor (type:'none') — bypasses BTC-EUR crypto context (and any BTC-N)", async () => {
    let lookupCalls = 0;
    const app = buildRouteApp({
      // system / internal actor: this codebase uses actor.type === "none" for
      // unauthenticated/internal callers (see server/src/middleware/auth.ts:35).
      // The route bypasses any actor that isn't "agent", so the guard never runs.
      actor: { type: "none" },
      issue: { id: "issue-1", companyId: "company-A" },
      lookup: async () => {
        lookupCalls += 1;
        return null;
      },
    });
    const res = await request(app)
      .post("/issues/issue-1/comments")
      .send({ body: "trading BTC-EUR pair against BTC-USD, see BTC-9999" });
    expect(res.status).toBe(201);
    expect(res.body).toEqual({ ok: true, issueId: "issue-1" });
    // Route-level bypass means the guard is never invoked; lookup is untouched.
    expect(lookupCalls).toBe(0);
  });

  it("(c-board) POST /issues/:id/comments returns 201 for board actor (bypass) even when BTC-9999 would not resolve", async () => {
    let lookupCalls = 0;
    const app = buildRouteApp({
      actor: { type: "board", companyIds: ["company-A", "company-B"] },
      issue: { id: "issue-1", companyId: "company-A" },
      lookup: async () => {
        lookupCalls += 1;
        return null;
      },
    });
    const res = await request(app)
      .post("/issues/issue-1/comments")
      .send({ body: "trading BTC-EUR pair, see BTC-9999" });
    expect(res.status).toBe(201);
    expect(lookupCalls).toBe(0); // board bypass skips the guard entirely
  });

  it("(d) PATCH /issues/:id returns 422 for agent actor when description contains an unresolvable BTC-9999", async () => {
    const app = buildRouteApp({
      actor: { type: "agent", companyId: "company-A" },
      issue: { id: "issue-1", companyId: "company-A" },
      lookup: buildLookup([]),
    });
    const res = await request(app)
      .patch("/issues/issue-1")
      .send({ description: "follow-up on BTC-9999" });
    expect(res.status).toBe(422);
    expect(res.body.error).toBe("Truncated prefix");
    expect(res.body.details.offendingToken).toBe("BTC-9999");
    expect(res.body.details.suggestedFull).toBe("BTCAAAAA-9999");
  });
});

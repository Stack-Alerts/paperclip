import { describe, expect, it } from "vitest";
import {
  REDACTED_EVENT_VALUE,
  REDACTED_ENV_PLAIN_VALUE,
  redactAdapterConfigEnvForResponse,
  redactEventPayload,
  redactSensitiveText,
  sanitizeRecord,
} from "../redaction.js";

describe("redaction", () => {
  it("redacts sensitive keys and nested secret values", () => {
    const input = {
      apiKey: "abc123",
      nested: {
        AUTH_TOKEN: "token-value",
        safe: "ok",
      },
      env: {
        OPENAI_API_KEY: "sk-openai",
        OPENAI_API_KEY_REF: {
          type: "secret_ref",
          secretId: "11111111-1111-1111-1111-111111111111",
        },
        OPENAI_API_KEY_PLAIN: {
          type: "plain",
          value: "sk-plain",
        },
        PAPERCLIP_API_URL: "http://localhost:3100",
      },
    };

    const result = sanitizeRecord(input);

    expect(result.apiKey).toBe(REDACTED_EVENT_VALUE);
    expect(result.nested).toEqual({
      AUTH_TOKEN: REDACTED_EVENT_VALUE,
      safe: "ok",
    });
    expect(result.env).toEqual({
      OPENAI_API_KEY: REDACTED_EVENT_VALUE,
      OPENAI_API_KEY_REF: {
        type: "secret_ref",
        secretId: "11111111-1111-1111-1111-111111111111",
      },
      OPENAI_API_KEY_PLAIN: {
        type: "plain",
        value: REDACTED_EVENT_VALUE,
      },
      PAPERCLIP_API_URL: "http://localhost:3100",
    });
  });

  it("redacts jwt-looking values even when key name is not sensitive", () => {
    const input = {
      session: "aaa.bbb.ccc",
      normal: "plain",
    };

    const result = sanitizeRecord(input);

    expect(result.session).toBe(REDACTED_EVENT_VALUE);
    expect(result.normal).toBe("plain");
  });

  it("redacts payload objects while preserving null", () => {
    expect(redactEventPayload(null)).toBeNull();
    expect(redactEventPayload({ password: "hunter2", safe: "value" })).toEqual({
      password: REDACTED_EVENT_VALUE,
      safe: "value",
    });
  });

  it("redacts common secret shapes from unstructured text", () => {
    const jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
    const githubToken = "ghp_1234567890abcdefghijklmnopqrstuvwxyz";
    const input = [
      "Authorization: Bearer live-bearer-token-value",
      `payload {"apiKey":"json-secret-value"}`,
      `escaped {\\"apiKey\\":\\"escaped-json-secret\\"}`,
      `GITHUB_TOKEN=${githubToken}`,
      `session=${jwt}`,
    ].join("\n");

    const result = redactSensitiveText(input);

    expect(result).toContain(REDACTED_EVENT_VALUE);
    expect(result).not.toContain("live-bearer-token-value");
    expect(result).not.toContain("json-secret-value");
    expect(result).not.toContain("escaped-json-secret");
    expect(result).not.toContain(githubToken);
    expect(result).not.toContain(jwt);
  });

  it("redacts inline secrets from command metadata without hiding safe command text", () => {
    const input = {
      command: "custom-acp --token ghp_example_secret env OPENAI_API_KEY=sk-live-example custom-acp",
      commandArgs: ["--safe", "ok", "--token", "ghp_arg_secret", "--api-key=sk-inline-example"],
      env: {
        PAPERCLIP_RESOLVED_COMMAND: "env OPENAI_API_KEY=sk-live-example custom-acp --token ghp_example_secret",
        SAFE_VALUE: "visible",
      },
    };

    const result = redactEventPayload(input);

    expect(result?.command).toBe(
      `custom-acp --token ${REDACTED_EVENT_VALUE} env OPENAI_API_KEY=${REDACTED_EVENT_VALUE} custom-acp`,
    );
    expect(result?.commandArgs).toEqual([
      "--safe",
      "ok",
      "--token",
      REDACTED_EVENT_VALUE,
      `--api-key=${REDACTED_EVENT_VALUE}`,
    ]);
    expect(result?.env).toEqual({
      PAPERCLIP_RESOLVED_COMMAND:
        `env OPENAI_API_KEY=${REDACTED_EVENT_VALUE} custom-acp --token ${REDACTED_EVENT_VALUE}`,
      SAFE_VALUE: "visible",
    });
  });

  it("redacts non-string command args after secret flags", () => {
    const result = redactEventPayload({
      commandArgs: ["--api-key", { nested: "secret-value" }, "safe-next"],
    });

    expect(result?.commandArgs).toEqual(["--api-key", REDACTED_EVENT_VALUE, "safe-next"]);
  });

  it("does not treat bare args payloads as command args", () => {
    const result = redactEventPayload({
      args: ["--api-key", "not-a-command-secret"],
      argv: ["--api-key", "command-secret"],
    });

    expect(result?.args).toEqual(["--api-key", "not-a-command-secret"]);
    expect(result?.argv).toEqual(["--api-key", REDACTED_EVENT_VALUE]);
  });

  describe("redactAdapterConfigEnvForResponse", () => {
    it("redacts every plain env value and leaves secret_ref entries opaque", () => {
      const adapterConfig = {
        env: {
          OPENAI_API_KEY: { type: "plain", value: "sk-live" },
          OPENAI_BASE_URL: { type: "plain", value: "https://api.example.com" },
          OPENAI_API_KEY_REF: {
            type: "secret_ref",
            secretId: "11111111-1111-1111-1111-111111111111",
            version: 2,
          },
        },
        model: "gpt-4o",
      };

      const result = redactAdapterConfigEnvForResponse(adapterConfig);

      expect(result.env).toEqual({
        OPENAI_API_KEY: { type: "plain", value: REDACTED_ENV_PLAIN_VALUE },
        OPENAI_BASE_URL: { type: "plain", value: REDACTED_ENV_PLAIN_VALUE },
        OPENAI_API_KEY_REF: {
          type: "secret_ref",
          secretId: "11111111-1111-1111-1111-111111111111",
          version: 2,
        },
      });
      expect(result.redactedPlainKeys.sort()).toEqual(["OPENAI_API_KEY", "OPENAI_BASE_URL"]);
    });

    it("promotes legacy string env entries to a redacted plain binding", () => {
      const adapterConfig = {
        env: {
          LEGACY_TOKEN: "sk-from-binding",
        },
      };

      const result = redactAdapterConfigEnvForResponse(adapterConfig);

      expect(result.env).toEqual({
        LEGACY_TOKEN: { type: "plain", value: REDACTED_ENV_PLAIN_VALUE },
      });
      expect(result.redactedPlainKeys).toEqual(["LEGACY_TOKEN"]);
    });

    it("does not mutate the input object", () => {
      const adapterConfig = {
        env: {
          OPENAI_API_KEY: { type: "plain", value: "sk-live" },
        },
      };
      const envRef = adapterConfig.env as Record<string, unknown>;

      redactAdapterConfigEnvForResponse(adapterConfig);

      expect((envRef.OPENAI_API_KEY as { value: string }).value).toBe("sk-live");
    });

    it("returns an empty result when adapterConfig is missing or not an object", () => {
      expect(redactAdapterConfigEnvForResponse(null)).toEqual({
        env: {},
        redactedPlainKeys: [],
      });
      expect(redactAdapterConfigEnvForResponse(undefined)).toEqual({
        env: {},
        redactedPlainKeys: [],
      });
      expect(redactAdapterConfigEnvForResponse("not-an-object")).toEqual({
        env: {},
        redactedPlainKeys: [],
      });
    });

    it("returns an empty result when env is missing or not an object", () => {
      expect(redactAdapterConfigEnvForResponse({})).toEqual({
        env: {},
        redactedPlainKeys: [],
      });
      expect(redactAdapterConfigEnvForResponse({ env: null })).toEqual({
        env: {},
        redactedPlainKeys: [],
      });
      expect(redactAdapterConfigEnvForResponse({ env: "not-an-object" })).toEqual({
        env: {},
        redactedPlainKeys: [],
      });
    });

    it("ignores entries whose shape is neither plain nor secret_ref", () => {
      const adapterConfig = {
        env: {
          WEIRD: { type: "unknown", value: "skip-me" },
          NULL_VALUE: null,
        },
      };

      const result = redactAdapterConfigEnvForResponse(adapterConfig);

      expect(result.env).toEqual({
        WEIRD: { type: "unknown", value: "skip-me" },
        NULL_VALUE: null,
      });
      expect(result.redactedPlainKeys).toEqual([]);
    });
  });
});

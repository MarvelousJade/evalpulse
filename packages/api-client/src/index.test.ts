import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./index";

afterEach(() => vi.unstubAllGlobals());

describe("typed API client", () => {
  it("sends credentials and idempotency key for runs", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ id: "run-1", status: "queued", evaluators: [], aggregate: {} }),
        { status: 202, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    await api.createRun("project-1", "prompt-1", "dataset-1", "stable-key", [
      { type: "exact_match" },
    ]);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.credentials).toBe("include");
    expect(new Headers(init.headers).get("Idempotency-Key")).toBe("stable-key");
  });

  it("normalizes API errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Invalid dataset", code: "invalid_dataset" }), {
          status: 422,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    await expect(api.projects()).rejects.toEqual(
      expect.objectContaining({ status: 422, code: "invalid_dataset" }),
    );
  });
});

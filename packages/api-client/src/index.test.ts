import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./index";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

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

  it("retries login while the deployed API wakes up", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("<html>no deploy</html>", { status: 502 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "user-1",
            email: "demo@evalpulse.local",
            display_name: "Demo Reviewer",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    const login = api.login("demo@evalpulse.local", "evalpulse-demo");
    await vi.advanceTimersByTimeAsync(1_000);

    await expect(login).resolves.toEqual(
      expect.objectContaining({ id: "user-1", email: "demo@evalpulse.local" }),
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not retry invalid login credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid email or password" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.login("demo@evalpulse.local", "wrong")).rejects.toEqual(
      expect.objectContaining({ status: 401, message: "Invalid email or password" }),
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("reports a useful error when the API remains unavailable", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "API service unavailable" }), {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const assertion = expect(api.login("demo@evalpulse.local", "evalpulse-demo")).rejects.toEqual(
      expect.objectContaining({
        status: 502,
        code: "service_unavailable",
        message: "The API is still waking up. Please wait a moment and try again.",
      }),
    );
    await vi.runAllTimersAsync();

    await assertion;
    expect(fetchMock).toHaveBeenCalledTimes(8);
  });
});

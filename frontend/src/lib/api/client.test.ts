import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { ApiError, request, setAccessTokenProvider, setUnauthorizedHandler } from "./client";

const fetchMock = vi.fn<typeof fetch>();
vi.stubGlobal("fetch", fetchMock);

afterEach(() => {
  fetchMock.mockReset();
  setAccessTokenProvider(() => null);
  setUnauthorizedHandler(null);
});

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...headers } });
}

const unauthorized = () => jsonResponse({ error: { code: "UNAUTHORIZED", message: "La sesión expiró.", request_id: "r", details: { reason: "expired" } } }, 401);

describe("api client", () => {
  it("validates successful responses with the given schema", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ status: "ok" }));
    const data = await request("/health", z.object({ status: z.literal("ok") }));
    expect(data.status).toBe("ok");
    const call = fetchMock.mock.calls[0];
    expect(call).toBeDefined();
    const [url, init] = call ?? [];
    expect(url).toBe("/api/v1/health");
    expect(init?.credentials).toBe("include");
  });

  it("normalizes backend error envelopes into ApiError", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ error: { code: "FORBIDDEN", message: "No tienes permiso.", request_id: "req-1", details: null } }, 403));
    await expect(request("/x", z.unknown())).rejects.toMatchObject({ status: 403, code: "FORBIDDEN", message: "No tienes permiso.", requestId: "req-1" });
  });

  it("falls back to a generic error when the body is not the standard envelope", async () => {
    fetchMock.mockResolvedValueOnce(new Response("boom", { status: 502, headers: { "X-Request-ID": "rid" } }));
    const error = await request("/x", z.unknown()).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("HTTP_ERROR");
    expect((error as ApiError).requestId).toBe("rid");
  });

  it("sends the bearer token when a provider is configured", async () => {
    setAccessTokenProvider(() => "token-123");
    fetchMock.mockResolvedValueOnce(jsonResponse({}));
    await request("/me", z.object({}));
    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Record<string, string> | undefined;
    expect(headers?.Authorization).toBe("Bearer token-123");
  });

  it("renews the session once on 401 and retries with the new token (case 12)", async () => {
    let token = "old";
    setAccessTokenProvider(() => token);
    setUnauthorizedHandler(async () => {
      token = "new";
      return true;
    });
    fetchMock.mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(jsonResponse({ ok: true }));
    const data = await request("/protected", z.object({ ok: z.boolean() }));
    expect(data.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const retryHeaders = fetchMock.mock.calls[1]?.[1]?.headers as Record<string, string> | undefined;
    expect(retryHeaders?.Authorization).toBe("Bearer new");
  });

  it("does not retry when the session cannot be renewed", async () => {
    setAccessTokenProvider(() => "old");
    setUnauthorizedHandler(async () => false);
    fetchMock.mockResolvedValueOnce(unauthorized());
    await expect(request("/protected", z.unknown())).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("rejects responses that do not match the schema", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ status: "weird" }));
    await expect(request("/health", z.object({ status: z.literal("ok") }))).rejects.toThrow();
  });
});

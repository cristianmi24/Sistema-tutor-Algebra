import { request } from "./client";
import { healthSchema, metaSchema, readinessSchema } from "./types";

export { ApiError, request, setAccessTokenProvider } from "./client";
export * from "./types";

export const api = {
  health: (signal?: AbortSignal) => request("/health", healthSchema, signal ? { signal } : {}),
  readiness: (signal?: AbortSignal) => request("/health/ready", readinessSchema, signal ? { signal } : {}),
  meta: (signal?: AbortSignal) => request("/meta", metaSchema, signal ? { signal } : {}),
} as const;

/** Claves de TanStack Query centralizadas para invalidación coherente. */
export const queryKeys = {
  health: ["health"] as const,
  readiness: ["health", "ready"] as const,
  meta: ["meta"] as const,
} as const;

import { ApiError, request } from "./client";
import { healthSchema, metaSchema, readinessSchema } from "./types";

export { ApiError, request, setAccessTokenProvider, setUnauthorizedHandler } from "./client";
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

/** Mensaje legible para el usuario a partir de cualquier error. */
export function errorMessage(error: unknown, fallback = "Ocurrió un error. Inténtalo de nuevo."): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

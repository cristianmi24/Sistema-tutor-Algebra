import type { z } from "zod";

import { config } from "@/lib/config";

import { apiErrorSchema } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, requestId: string | null = null, details: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

/** Proveedor del access token (en memoria). Lo configura el store de sesión (Fase 2). */
let accessTokenProvider: () => string | null = () => null;

export function setAccessTokenProvider(provider: () => string | null): void {
  accessTokenProvider = provider;
}

async function parseError(response: Response): Promise<ApiError> {
  const requestId = response.headers.get("X-Request-ID");
  try {
    const json: unknown = await response.json();
    const parsed = apiErrorSchema.safeParse(json);
    if (parsed.success) {
      const { code, message, request_id, details } = parsed.data.error;
      return new ApiError(response.status, code, message, request_id ?? requestId, details);
    }
  } catch {
    // cuerpo no JSON: se usa el mensaje genérico
  }
  return new ApiError(response.status, "HTTP_ERROR", `Error ${response.status} al comunicarse con el servidor.`, requestId);
}

/**
 * Cliente HTTP tipado: valida la respuesta con un esquema Zod y normaliza los errores en ApiError.
 * `credentials: "include"` permite la cookie HttpOnly del refresh token (Fase 2).
 */
export async function request<TSchema extends z.ZodType>(path: string, schema: TSchema, options: RequestOptions = {}): Promise<z.output<TSchema>> {
  const headers: Record<string, string> = { Accept: "application/json", ...options.headers };
  const token = accessTokenProvider();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: string | undefined;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const response = await fetch(`${config.apiBaseUrl}${path}`, {
    method: options.method ?? "GET",
    headers,
    credentials: "include",
    ...(body !== undefined ? { body } : {}),
    ...(options.signal ? { signal: options.signal } : {}),
  });

  if (!response.ok) {
    throw await parseError(response);
  }
  if (response.status === 204) {
    return schema.parse(undefined);
  }
  const json: unknown = await response.json();
  return schema.parse(json);
}

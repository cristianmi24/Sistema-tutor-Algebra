import { z } from "zod";

/**
 * Configuración pública del frontend. Todo lo que empieza por VITE_ se incluye en el bundle:
 * aquí NUNCA hay secretos. La autorización real siempre ocurre en el backend.
 */
const envSchema = z.object({
  VITE_API_BASE_URL: z
    .string()
    .trim()
    .default("")
    .transform((value) => value.replace(/\/+$/, "")),
  VITE_APP_NAME: z.string().trim().min(1).default("STI-GA"),
});

const parsed = envSchema.safeParse({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_APP_NAME: import.meta.env.VITE_APP_NAME,
});

if (!parsed.success) {
  throw new Error(`Configuración inválida del frontend: ${parsed.error.message}`);
}

export const config = {
  appName: parsed.data.VITE_APP_NAME,
  /** Prefijo de la API. Vacío ⇒ mismo origen (proxy de Vite en desarrollo). */
  apiBaseUrl: `${parsed.data.VITE_API_BASE_URL}/api/v1`,
} as const;

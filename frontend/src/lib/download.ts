import { ApiError } from "@/lib/api";

/**
 * Descarga un archivo autenticado (Bearer) sin exponer el token en la URL.
 */
export async function downloadAuthenticated(url: string, token: string | null, fallbackName: string): Promise<void> {
  const response = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {}, credentials: "include" });
  if (!response.ok) {
    let message = `Error ${response.status} al exportar.`;
    try {
      const body = (await response.json()) as { error?: { message?: string } };
      if (body.error?.message) message = body.error.message;
    } catch {
      // cuerpo no JSON
    }
    throw new ApiError(response.status, "EXPORT_FAILED", message);
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="([^"]+)"/.exec(disposition);
  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = match?.[1] ?? fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

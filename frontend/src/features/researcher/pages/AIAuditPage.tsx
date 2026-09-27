import { useQuery } from "@tanstack/react-query";

import { Alert, Badge, Card, EmptyState, PageHeader, Skeleton } from "@/design-system/components";
import { useSession } from "@/features/auth/session-store";
import { errorMessage } from "@/lib/api";
import { asText } from "@/lib/text";

import { researchApi } from "../api";

/** Trazabilidad de la IA opcional: qué propuso, qué se validó y qué se bloqueó. */
export function AIAuditPage() {
  const { user } = useSession();
  const isAdmin = user?.role === "ADMIN";
  const config = useQuery({ queryKey: ["ai", "config"], queryFn: researchApi.aiConfig, enabled: isAdmin });
  const rows = useQuery({ queryKey: ["ai", "interactions"], queryFn: researchApi.aiInteractions });

  return (
    <>
      <PageHeader
        eyebrow="IA opcional"
        title="Trazabilidad de la IA"
        description="El LLM nunca decide la intervención. Solo propone; cada propuesta pasa por validadores pedagógico, de seguridad y de dominio."
      />
      <div className="ds-stack">
        {isAdmin && config.data && (
          <Card title="Configuración" actions={<Badge tone={config.data.enabled ? "success" : "neutral"}>{config.data.enabled ? "Activa" : "Desactivada"}</Badge>}>
            <p className="text-caption">
              Proveedor {config.data.provider} · modelo {config.data.model ?? "—"} · límite {config.data.max_calls_per_session} llamadas por sesión · clave{" "}
              {config.data.key_configured ? "configurada" : "no configurada"}
            </p>
            <ul>
              {config.data.guarantees.map((g) => (
                <li key={g}>{g}</li>
              ))}
            </ul>
          </Card>
        )}
        <Card title="Llamadas registradas">
          {rows.isPending && <Skeleton height="6rem" />}
          {rows.isError && <Alert tone="error">{errorMessage(rows.error)}</Alert>}
          {rows.data?.length === 0 && <EmptyState title="Sin llamadas" description="La IA está desactivada o aún no se ha usado." />}
          {rows.data && rows.data.length > 0 && (
            <div className="ds-table-wrap">
              <table className="ds-table">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Propósito</th>
                    <th>Resultado</th>
                    <th>Salida del modelo</th>
                    <th>Motivos</th>
                    <th>Latencia</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.data.map((r) => (
                    <tr key={r.id}>
                      <td>{new Date(r.created_at).toLocaleString("es-CO")}</td>
                      <td>{r.purpose}</td>
                      <td>
                        <Badge tone={r.approved ? "success" : "warning"}>{r.approved ? "Aprobada" : "Bloqueada"}</Badge>
                      </td>
                      <td>
                        <code className="text-caption">{r.raw_output ?? "—"}</code>
                      </td>
                      <td className="text-caption">{Array.isArray(r.validation.reasons) ? (r.validation.reasons as unknown[]).map((x) => asText(x)).join("; ") || "—" : "—"}</td>
                      <td className="tabular">{r.latency_ms ?? "—"} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}

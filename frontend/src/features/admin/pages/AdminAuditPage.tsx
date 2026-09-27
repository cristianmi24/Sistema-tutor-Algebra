import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Alert, Badge, Card, Field, PageHeader, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { adminApi, adminQueryKeys } from "../api";

export function AdminAuditPage() {
  const [action, setAction] = useState("");
  const params = { action: action || undefined, page_size: 100 };
  const audit = useQuery({ queryKey: adminQueryKeys.audit(params), queryFn: () => adminApi.audit(params) });

  return (
    <>
      <PageHeader eyebrow="Administración" title="Auditoría" description="Registro inmutable de acciones sensibles: quién, qué, cuándo y sobre qué." />
      <Card
        actions={
          <Field
            label={<span className="visually-hidden">Filtrar por acción</span>}
            placeholder="Filtrar por acción (p. ej. LOGIN_FAILED)"
            value={action}
            onChange={(e) => {
              setAction(e.target.value.toUpperCase());
            }}
          />
        }
        title="Eventos"
      >
        {audit.isPending && <Skeleton height="8rem" />}
        {audit.isError && <Alert tone="error">{errorMessage(audit.error)}</Alert>}
        {audit.data && (
          <div className="ds-table-wrap">
            <table className="ds-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Acción</th>
                  <th>Resultado</th>
                  <th>Actor</th>
                  <th>Recurso</th>
                  <th>Detalles</th>
                </tr>
              </thead>
              <tbody>
                {audit.data.items.map((row) => (
                  <tr key={row.id}>
                    <td className="tabular">{new Date(row.occurred_at).toLocaleString("es-CO")}</td>
                    <td>{row.action}</td>
                    <td>
                      <Badge tone={row.outcome === "SUCCESS" ? "success" : row.outcome === "DENIED" ? "warning" : "error"}>{row.outcome}</Badge>
                    </td>
                    <td className="tabular">{row.actor_role ?? "—"}</td>
                    <td>{row.resource_type ?? "—"}</td>
                    <td>
                      <code className="text-caption">{JSON.stringify(row.details)}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-caption">Total: {audit.data.total}</p>
          </div>
        )}
      </Card>
    </>
  );
}

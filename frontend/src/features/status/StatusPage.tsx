import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleDashed, XCircle } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge, Card, PageHeader, Skeleton } from "@/design-system/components";
import { ApiError, api, queryKeys } from "@/lib/api";

function StatusBadge({ state }: { state: "loading" | "ok" | "error" }) {
  if (state === "loading") return <Badge tone="neutral" icon={<CircleDashed size={14} aria-hidden />}>Comprobando</Badge>;
  if (state === "ok") return <Badge tone="success" icon={<CheckCircle2 size={14} aria-hidden />}>Operativo</Badge>;
  return <Badge tone="error" icon={<XCircle size={14} aria-hidden />}>No disponible</Badge>;
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) return `${error.code}: ${error.message}`;
  if (error instanceof Error) return error.message;
  return "Error desconocido";
}

/** Página pública de salud: no expone datos ni configuración sensible. */
export function StatusPage() {
  const health = useQuery({ queryKey: queryKeys.health, queryFn: ({ signal }) => api.health(signal) });
  const readiness = useQuery({ queryKey: queryKeys.readiness, queryFn: ({ signal }) => api.readiness(signal), retry: false });

  const toState = (q: { isPending: boolean; isError: boolean }) => (q.isPending ? "loading" : q.isError ? "error" : "ok");

  return (
    <div className="centered-page">
      <div style={{ width: "min(100%, 720px)" }}>
        <PageHeader eyebrow="Sistema" title="Estado de la plataforma" description="Comprobación de la API y la base de datos." />
        <div className="status-grid">
          <Card title="API">
            <div className="status-row">
              <span>Servicio</span>
              <StatusBadge state={toState(health)} />
            </div>
            <div className="status-row">
              <span>Versión</span>
              {health.isPending ? <Skeleton width="4rem" /> : <span className="tabular">{health.data?.version ?? "—"}</span>}
            </div>
            <div className="status-row">
              <span>Entorno</span>
              {health.isPending ? <Skeleton width="6rem" /> : <span>{health.data?.environment ?? "—"}</span>}
            </div>
            {health.isError && <p className="text-caption">{describeError(health.error)}</p>}
          </Card>
          <Card title="Base de datos">
            <div className="status-row">
              <span>Conexión</span>
              <StatusBadge state={toState(readiness)} />
            </div>
            {readiness.isError && <p className="text-caption">{describeError(readiness.error)}</p>}
          </Card>
        </div>
        <p className="text-caption" style={{ marginTop: "var(--space-6)" }}>
          <Link to="/login">Ir al inicio de sesión</Link>
        </p>
      </div>
    </div>
  );
}

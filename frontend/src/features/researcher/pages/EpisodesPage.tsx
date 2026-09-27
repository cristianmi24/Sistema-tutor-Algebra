import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { Alert, Badge, Card, EmptyState, PageHeader, Select, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { TRIGGER_LABEL, researchApi, researchQueryKeys } from "../api";

export function EpisodesPage() {
  const [params, setParams] = useSearchParams();
  const base = useLocation().pathname.startsWith("/teacher") ? "/teacher" : "/researcher";
  const filters = {
    ...(params.get("student") ? { student_id: params.get("student") ?? "" } : {}),
    ...(params.get("session") ? { session_id: params.get("session") ?? "" } : {}),
    ...(params.get("trigger") ? { trigger: params.get("trigger") ?? "" } : {}),
  };
  const episodes = useQuery({ queryKey: researchQueryKeys.episodes(filters), queryFn: () => researchApi.episodes(filters) });

  return (
    <>
      <PageHeader
        eyebrow="Investigación"
        title="Episodios"
        description="Trayectorias reconstruidas: dificultad → ayuda → reacción → nueva acción → resultado. El disparador y el resumen son registros automáticos."
        actions={
          <Select
            label={<span className="visually-hidden">Disparador</span>}
            value={params.get("trigger") ?? ""}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              if (e.target.value) next.set("trigger", e.target.value);
              else next.delete("trigger");
              setParams(next);
            }}
          >
            <option value="">Todos los disparadores</option>
            {Object.entries(TRIGGER_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </Select>
        }
      />
      <Card>
        {episodes.isPending && <Skeleton height="8rem" />}
        {episodes.isError && <Alert tone="error">{errorMessage(episodes.error)}</Alert>}
        {episodes.data?.length === 0 && <EmptyState title="Sin episodios" description="Se crean cuando hay ayuda solicitada u ofrecida, o intervención docente." />}
        {episodes.data && episodes.data.length > 0 && (
          <div className="ds-table-wrap">
            <table className="ds-table">
              <thead>
                <tr>
                  <th>Participante</th>
                  <th>Actividad</th>
                  <th>Disparador</th>
                  <th>Eventos</th>
                  <th>Ayudas</th>
                  <th>Cierre</th>
                  <th>Fecha</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {episodes.data.map((e) => {
                  const levels = (e.summary.help_levels_sequence as number[] | undefined) ?? [];
                  return (
                    <tr key={e.id}>
                      <td className="tabular">{e.participant_code}</td>
                      <td>
                        {e.task_title}
                        <span className="text-caption" style={{ display: "block" }}>
                          {e.task_code}
                        </span>
                      </td>
                      <td>
                        <Badge tone={e.trigger === "TEACHER" ? "teacher" : e.trigger === "MANUAL" ? "neutral" : "info"}>{TRIGGER_LABEL[e.trigger] ?? e.trigger}</Badge>
                      </td>
                      <td className="tabular">{e.interaction_count}</td>
                      <td className="tabular">{levels.length ? levels.join(" → ") : "—"}</td>
                      <td>{e.status === "OPEN" ? <Badge tone="success">abierto</Badge> : (e.close_reason ?? "—")}</td>
                      <td>{new Date(e.created_at).toLocaleString("es-CO")}</td>
                      <td>
                        <Link to={`${base}/episodes/${e.id}`}>Abrir</Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}

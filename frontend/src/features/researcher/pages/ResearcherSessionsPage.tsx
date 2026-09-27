import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { Alert, Badge, Card, PageHeader, Skeleton } from "@/design-system/components";
import { Timeline } from "@/features/shared/Timeline";
import { studentApi } from "@/features/student/api";
import { errorMessage, request } from "@/lib/api";

import { z } from "zod";

import { researchApi, researchQueryKeys } from "../api";
import { sessionSummarySchema } from "@/features/student/api";

export function ResearcherSessionsPage() {
  const [params, setParams] = useSearchParams();
  const studentId = params.get("student") ?? undefined;
  const selected = params.get("session");
  const sessions = useQuery({
    queryKey: ["research", "sessions", studentId],
    queryFn: () => (studentId ? request(`/sessions?student_id=${studentId}`, z.array(sessionSummarySchema)) : studentApi.sessions()),
  });
  const timeline = useQuery({
    queryKey: researchQueryKeys.sessionTimeline(selected ?? ""),
    queryFn: () => researchApi.sessionTimeline(selected ?? ""),
    enabled: Boolean(selected),
  });

  return (
    <>
      <PageHeader eyebrow="Investigación" title="Sesiones" description="Fecha, duración, tareas, intervenciones y ayudas. Selecciona una sesión para ver su trayectoria completa." />
      <div className="ds-stack">
        <Card>
          {sessions.isPending && <Skeleton height="6rem" />}
          {sessions.isError && <Alert tone="error">{errorMessage(sessions.error)}</Alert>}
          {sessions.data && (
            <div className="ds-table-wrap">
              <table className="ds-table">
                <thead>
                  <tr>
                    <th>Participante</th>
                    <th>Inicio</th>
                    <th>Duración</th>
                    <th>Tareas</th>
                    <th>Eventos</th>
                    <th>Ayudas del sistema</th>
                    <th>Estado</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {sessions.data.map((s) => {
                    const minutes = s.ended_at ? Math.round((new Date(s.ended_at).getTime() - new Date(s.started_at).getTime()) / 60000) : null;
                    return (
                      <tr key={s.id} aria-selected={selected === s.id}>
                        <td className="tabular">{s.participant_code}</td>
                        <td>{new Date(s.started_at).toLocaleString("es-CO")}</td>
                        <td className="tabular">{minutes !== null ? `${minutes} min` : "en curso"}</td>
                        <td className="tabular">
                          {s.completed_count}/{s.task_count}
                        </td>
                        <td className="tabular">{s.interaction_count}</td>
                        <td className="tabular">{s.help_count}</td>
                        <td>
                          <Badge tone={s.status === "ACTIVE" ? "success" : "neutral"}>{s.status}</Badge>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="ds-button ds-button--ghost ds-button--sm"
                            onClick={() => {
                              const next = new URLSearchParams(params);
                              next.set("session", s.id);
                              setParams(next);
                            }}
                          >
                            Ver trayectoria
                          </button>{" "}
                          <Link to={`/researcher/episodes?session=${s.id}`}>Episodios</Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        {selected && (
          <Card title="Trayectoria de la sesión">
            {timeline.isPending && <Skeleton height="10rem" />}
            {timeline.isError && <Alert tone="error">{errorMessage(timeline.error)}</Alert>}
            {timeline.data && <Timeline steps={timeline.data} />}
          </Card>
        )}
      </div>
    </>
  );
}

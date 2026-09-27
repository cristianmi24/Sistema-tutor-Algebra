import { useQuery } from "@tanstack/react-query";
import { HandHelping, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { Alert, Badge, Card, EmptyState, PageHeader, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { teacherApi, teacherQueryKeys } from "../api";

export function TeacherDashboardPage() {
  const groups = useQuery({ queryKey: teacherQueryKeys.groups, queryFn: teacherApi.groups, refetchInterval: 20_000 });
  return (
    <>
      <PageHeader eyebrow="Docente" title="Acompañamiento" description="Observa sesiones, revisa producciones e interviene cuando aporte." />
      <div className="ds-stack">
        <Alert tone="teacher" title="Tus intervenciones se registran por separado">
          Las intervenciones del docente nunca se mezclan con las del sistema: tienen su propio registro, color e icono. Cuando intervienes, el tutor
          automático hace una pausa.
        </Alert>
        {groups.isPending && <Skeleton height="8rem" />}
        {groups.isError && <Alert tone="error">{errorMessage(groups.error)}</Alert>}
        {groups.data?.length === 0 && (
          <Card>
            <EmptyState icon={<Users size={26} />} title="Sin grupos asignados" description="Pide a la administración que te asigne tus grupos." />
          </Card>
        )}
        {groups.data?.map((group) => (
          <Card key={`${group.grade}-${group.group_code}`} title={`Grupo ${group.grade}.º ${group.group_code}`} description={`${group.students.length} estudiantes`}>
            <div className="ds-table-wrap">
              <table className="ds-table">
                <thead>
                  <tr>
                    <th>Estudiante</th>
                    <th>Actividad actual</th>
                    <th>Estado (sistema)</th>
                    <th>Ayudas del sistema</th>
                    <th>Pidió ayuda</th>
                    <th>Tus intervenciones</th>
                    <th>Último evento</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {group.students.map((s) => (
                    <tr key={s.student_id}>
                      <td className="tabular">
                        <strong>{s.participant_code}</strong>
                        {s.account_status === "PENDING_CONSENT" && (
                          <span className="text-caption" style={{ display: "block" }}>
                            consentimiento de acudiente pendiente
                          </span>
                        )}
                      </td>
                      <td>{s.current_task_title ?? (s.active_session_id ? "Sin actividad abierta" : "Sin sesión activa")}</td>
                      <td>
                        {s.operational_state ? (
                          <Badge tone="info" title="Interpretación operativa del sistema; el estudiante solo ve la etiqueta neutral">
                            {s.state_label} · {s.operational_state}
                          </Badge>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="tabular">{s.system_helps_in_session}</td>
                      <td className="tabular">{s.help_requests_in_session}</td>
                      <td className="tabular">{s.teacher_interventions_in_session}</td>
                      <td className="text-caption">{s.last_event_at ? `${new Date(s.last_event_at).toLocaleTimeString("es-CO")} · ${s.last_event_type ?? ""}` : "—"}</td>
                      <td>
                        {s.suggest_teacher && (
                          <Badge tone="teacher" icon={<HandHelping size={12} aria-hidden />}>
                            Sugerencia de acompañamiento
                          </Badge>
                        )}{" "}
                        {s.active_session_id && <Link to={`/teacher/sessions/${s.active_session_id}`}>Observar</Link>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
      </div>
    </>
  );
}

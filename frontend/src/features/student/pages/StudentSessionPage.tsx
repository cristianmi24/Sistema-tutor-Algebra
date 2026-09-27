import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle, CircleDot } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { Alert, Badge, Button, Card, PageHeader, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { TASK_TYPE_LABEL, studentApi, studentQueryKeys } from "../api";

const STATUS_ICON = { PENDING: Circle, OPEN: CircleDot, COMPLETED: CheckCircle2, ABANDONED: Circle } as const;
const STATUS_LABEL = { PENDING: "Pendiente", OPEN: "En curso", COMPLETED: "Terminada", ABANDONED: "Dejada" } as const;

export function StudentSessionPage() {
  const { sessionId = "" } = useParams();
  const queryClient = useQueryClient();
  const session = useQuery({ queryKey: studentQueryKeys.session(sessionId), queryFn: () => studentApi.session(sessionId) });
  const end = useMutation({
    mutationFn: () => studentApi.endSession(sessionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });

  if (session.isPending) return <Skeleton height="8rem" />;
  if (session.isError) return <Alert tone="error">{errorMessage(session.error)}</Alert>;
  const data = session.data;
  const allDone = data.tasks.every((t) => t.status === "COMPLETED" || t.status === "ABANDONED");

  return (
    <>
      <PageHeader
        eyebrow="Sesión de trabajo"
        title="Tus actividades"
        description="Trabaja en el orden que prefieras. Puedes volver a una actividad cuando quieras."
        actions={
          data.status === "ACTIVE" ? (
            <Button variant="secondary" loading={end.isPending} onClick={() => {
                end.mutate();
              }}
            >
              {allDone ? "Cerrar sesión de trabajo" : "Terminar por hoy"}
            </Button>
          ) : (
            <Badge tone="neutral">Sesión {data.status === "COMPLETED" ? "terminada" : "cerrada"}</Badge>
          )
        }
      />
      {end.isError && <Alert tone="error">{errorMessage(end.error)}</Alert>}
      <Card>
        <ul className="session-card__tasks">
          {data.tasks.map((st) => {
            const Icon = STATUS_ICON[st.status];
            return (
              <li key={st.id} className="session-card__task">
                <span className="ds-inline-actions">
                  <Icon size={18} aria-hidden style={{ color: st.status === "COMPLETED" ? "var(--color-success)" : "var(--color-muted)" }} />
                  <span>
                    <strong>{st.task.title}</strong>
                    <span className="text-caption" style={{ display: "block" }}>
                      {TASK_TYPE_LABEL[st.task.task_type]} · {STATUS_LABEL[st.status]}
                    </span>
                  </span>
                </span>
                <Link to={`/student/sessions/${data.id}/tasks/${st.task.id}`} className="ds-button ds-button--secondary ds-button--sm">
                  {st.status === "COMPLETED" ? "Revisar" : st.status === "OPEN" ? "Continuar" : "Empezar"}
                </Link>
              </li>
            );
          })}
        </ul>
      </Card>
    </>
  );
}

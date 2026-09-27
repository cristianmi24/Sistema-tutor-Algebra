import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpenCheck, Play } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { Alert, Badge, Button, Card, EmptyState, PageHeader, Skeleton } from "@/design-system/components";
import { ConsentStatusBanner } from "@/features/auth/components/ConsentStatusBanner";
import { errorMessage } from "@/lib/api";

import { studentApi, studentQueryKeys } from "../api";

export function StudentDashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sessions = useQuery({ queryKey: studentQueryKeys.sessions, queryFn: studentApi.sessions });
  const start = useMutation({
    mutationFn: () => studentApi.startSession(),
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: studentQueryKeys.sessions });
      void navigate(`/student/sessions/${session.id}`);
    },
  });
  const active = sessions.data?.find((s) => s.status === "ACTIVE");
  const past = sessions.data?.filter((s) => s.status !== "ACTIVE") ?? [];

  return (
    <>
      <PageHeader
        eyebrow="Estudiante"
        title="Tu espacio de trabajo"
        description="Aquí verás tus sesiones y actividades de patrones y generalización."
        actions={
          !active && (
            <Button leadingIcon={<Play size={16} aria-hidden />} loading={start.isPending} onClick={() => {
                start.mutate();
              }}
            >
              Iniciar sesión de trabajo
            </Button>
          )
        }
      />
      <div className="ds-stack">
        <ConsentStatusBanner />
        {start.isError && <Alert tone="error">{errorMessage(start.error)}</Alert>}
        {sessions.isPending && <Skeleton height="6rem" />}
        {sessions.isError && <Alert tone="error">{errorMessage(sessions.error)}</Alert>}
        {active && (
          <Card title="Sesión en curso" description={`Iniciada ${new Date(active.started_at).toLocaleString("es-CO")}`} actions={<Badge tone="success">Activa</Badge>} interactive>
            <p>
              {active.completed_count} de {active.task_count} actividades terminadas.
            </p>
            <Link to={`/student/sessions/${active.id}`} className="ds-button ds-button--primary ds-button--md" style={{ marginTop: "var(--space-3)" }}>
              Continuar
            </Link>
          </Card>
        )}
        {sessions.data && !active && past.length === 0 && (
          <Card>
            <EmptyState icon={<BookOpenCheck size={26} />} title="Aún no tienes sesiones" description="Inicia una sesión de trabajo para ver tus actividades." />
          </Card>
        )}
        {past.length > 0 && (
          <Card title="Sesiones anteriores">
            <ul className="session-card__tasks">
              {past.map((s) => (
                <li key={s.id} className="session-card__task">
                  <span>
                    {new Date(s.started_at).toLocaleDateString("es-CO")} · {s.completed_count}/{s.task_count} actividades · {s.help_count} pistas
                  </span>
                  <Link to={`/student/sessions/${s.id}`}>Revisar</Link>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </>
  );
}

import { useQuery } from "@tanstack/react-query";

import { Alert, Card, PageHeader, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { studentApi, studentQueryKeys } from "../api";

/** Progreso permitido al estudiante: actividad realizada, nunca etiquetas de estado ni "aciertos". */
export function StudentProgressPage() {
  const sessions = useQuery({ queryKey: studentQueryKeys.sessions, queryFn: studentApi.sessions });
  if (sessions.isPending) return <Skeleton height="6rem" />;
  if (sessions.isError) return <Alert tone="error">{errorMessage(sessions.error)}</Alert>;
  const total = sessions.data.reduce((acc, s) => acc + s.completed_count, 0);
  const helps = sessions.data.reduce((acc, s) => acc + s.help_count, 0);
  return (
    <>
      <PageHeader eyebrow="Estudiante" title="Mi progreso" description="Lo que has trabajado hasta ahora." />
      <div className="ds-grid">
        <Card title="Sesiones">
          <span className="ds-kpi__value">{sessions.data.length}</span>
        </Card>
        <Card title="Actividades terminadas">
          <span className="ds-kpi__value">{total}</span>
        </Card>
        <Card title="Pistas usadas">
          <span className="ds-kpi__value">{helps}</span>
          <p className="text-caption">Pedir ayuda es parte de aprender.</p>
        </Card>
      </div>
    </>
  );
}

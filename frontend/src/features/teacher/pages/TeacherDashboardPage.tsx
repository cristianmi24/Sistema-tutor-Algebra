import { Users } from "lucide-react";

import { Alert, Card, EmptyState, PageHeader } from "@/design-system/components";

export function TeacherDashboardPage() {
  return (
    <>
      <PageHeader eyebrow="Docente" title="Acompañamiento" description="Observa sesiones, revisa producciones e interviene cuando aporte." />
      <div className="ds-stack">
        <Alert tone="teacher" title="Tus intervenciones se registran por separado">
          Las intervenciones del docente nunca se mezclan con las del sistema: tienen su propio registro, color e icono.
        </Alert>
        <Card title="Grupos">
          <EmptyState icon={<Users size={26} />} title="Sin grupos asignados" description="El dashboard docente se implementa en la Fase 6." />
        </Card>
      </div>
    </>
  );
}

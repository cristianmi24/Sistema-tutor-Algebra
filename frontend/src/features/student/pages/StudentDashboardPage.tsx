import { BookOpenCheck } from "lucide-react";

import { Card, EmptyState, PageHeader } from "@/design-system/components";

export function StudentDashboardPage() {
  return (
    <>
      <PageHeader eyebrow="Estudiante" title="Tu espacio de trabajo" description="Aquí verás tus sesiones y actividades de patrones y generalización." />
      <div className="ds-grid">
        <Card title="Sesiones" description="Actividades asignadas por tu docente.">
          <EmptyState icon={<BookOpenCheck size={26} />} title="Aún no hay sesiones" description="Las sesiones y actividades se habilitan en la Fase 3." />
        </Card>
      </div>
    </>
  );
}

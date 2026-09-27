import { ClipboardList } from "lucide-react";

import { Card, EmptyState, PageHeader } from "@/design-system/components";

export function ResearcherDashboardPage() {
  return (
    <>
      <PageHeader
        eyebrow="Investigación"
        title="Participantes y episodios"
        description="Reconstruye trayectorias y compara episodios. El sistema registra; la interpretación es tuya."
      />
      <Card title="Participantes" description="Códigos anonimizados (STU-001…). Nunca nombres reales.">
        <EmptyState icon={<ClipboardList size={26} />} title="Sin datos aún" description="El módulo de investigación se implementa en la Fase 5." />
      </Card>
    </>
  );
}

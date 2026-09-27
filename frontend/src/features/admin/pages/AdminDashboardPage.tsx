import { ShieldCheck } from "lucide-react";

import { Card, EmptyState, PageHeader } from "@/design-system/components";

export function AdminDashboardPage() {
  return (
    <>
      <PageHeader eyebrow="Administración" title="Gestión del sistema" description="Usuarios, instituciones, catálogos pedagógicos, reglas y auditoría." />
      <Card title="Auditoría">
        <EmptyState icon={<ShieldCheck size={26} />} title="Sin eventos" description="La gestión y auditoría se habilitan desde la Fase 2." />
      </Card>
    </>
  );
}

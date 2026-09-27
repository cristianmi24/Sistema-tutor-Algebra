import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Card, PageHeader, Skeleton } from "@/design-system/components";

import { adminApi, adminQueryKeys } from "../api";

export function AdminDashboardPage() {
  const users = useQuery({ queryKey: adminQueryKeys.users({ page_size: 1 }), queryFn: () => adminApi.users({ page_size: 1 }) });
  const students = useQuery({ queryKey: adminQueryKeys.users({ role: "STUDENT", page_size: 1 }), queryFn: () => adminApi.users({ role: "STUDENT", page_size: 1 }) });
  const audit = useQuery({ queryKey: adminQueryKeys.audit({ page_size: 1 }), queryFn: () => adminApi.audit({ page_size: 1 }) });

  const kpi = (label: string, value: number | undefined, pending: boolean) => (
    <div className="ds-kpi">
      <span className="text-label text-muted">{label}</span>
      {pending ? <Skeleton width="3rem" height="2rem" /> : <span className="ds-kpi__value">{value ?? "—"}</span>}
    </div>
  );

  return (
    <>
      <PageHeader eyebrow="Administración" title="Gestión del sistema" description="Usuarios, instituciones, catálogos pedagógicos, reglas y auditoría." />
      <div className="ds-grid">
        <Card title="Cuentas" actions={<Link to="/admin/users">Gestionar</Link>}>
          {kpi("Usuarios", users.data?.total, users.isPending)}
        </Card>
        <Card title="Estudiantes" actions={<Link to="/admin/users">Ver</Link>}>
          {kpi("Registrados", students.data?.total, students.isPending)}
        </Card>
        <Card title="Auditoría" actions={<Link to="/admin/audit">Revisar</Link>}>
          {kpi("Eventos", audit.data?.total, audit.isPending)}
        </Card>
        <Card title="Catálogo pedagógico" actions={<Link to="/admin/catalog">Abrir</Link>}>
          <p className="text-muted">Actividades, ejemplos trabajados, banco de andamiajes, reglas e inferencia.</p>
        </Card>
      </div>
    </>
  );
}

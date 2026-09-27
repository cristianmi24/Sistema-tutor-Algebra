import {
  BookOpenCheck,
  Building2,
  ClipboardList,
  Database,
  FlaskConical,
  GitCompare,
  Grid3x3,
  Home,
  LogOut,
  MessageSquareText,
  NotebookPen,
  Settings2,
  ShieldCheck,
  Users,
} from "lucide-react";
import type { ComponentType } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { Badge, Button } from "@/design-system/components";
import { useSession } from "@/features/auth/session-store";
import type { Role } from "@/lib/api";
import { config } from "@/lib/config";

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ size?: number; "aria-hidden"?: boolean }>;
  end?: boolean;
}

/** Navegación por rol. Las rutas hijas se implementan en las fases 3–6. */
const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  STUDENT: [
    { to: "/student", label: "Inicio", icon: Home, end: true },
    { to: "/student/sessions", label: "Mis sesiones", icon: BookOpenCheck },
    { to: "/student/progress", label: "Mi progreso", icon: Grid3x3 },
  ],
  TEACHER: [
    { to: "/teacher", label: "Inicio", icon: Home, end: true },
    { to: "/teacher/episodes", label: "Episodios", icon: ClipboardList },
    { to: "/teacher/export", label: "Exportar", icon: Database },
  ],
  RESEARCHER: [
    { to: "/researcher", label: "Participantes", icon: Users, end: true },
    { to: "/researcher/sessions", label: "Sesiones", icon: BookOpenCheck },
    { to: "/researcher/episodes", label: "Episodios", icon: ClipboardList },
    { to: "/researcher/compare", label: "Comparar", icon: GitCompare },
    { to: "/researcher/memos", label: "Memos", icon: NotebookPen },
    { to: "/researcher/interviews", label: "Entrevistas", icon: MessageSquareText },
    { to: "/researcher/export", label: "Exportar", icon: Database },
  ],
  ADMIN: [
    { to: "/admin", label: "Inicio", icon: Home, end: true },
    { to: "/admin/users", label: "Usuarios", icon: Users },
    { to: "/admin/institutions", label: "Instituciones", icon: Building2 },
    { to: "/admin/catalog", label: "Actividades y ayudas", icon: FlaskConical },
    { to: "/admin/rules", label: "Reglas", icon: Settings2 },
    { to: "/admin/audit", label: "Auditoría", icon: ShieldCheck },
  ],
};

const ROLE_LABEL: Record<Role, string> = {
  STUDENT: "Estudiante",
  TEACHER: "Docente",
  RESEARCHER: "Investigador/a",
  ADMIN: "Administración",
};

export function AppShell() {
  const { user, signOut } = useSession();
  const navigate = useNavigate();
  const role: Role = user?.role ?? "STUDENT";
  const items = NAV_BY_ROLE[role];

  const handleSignOut = () => {
    void signOut().then(() => navigate("/login", { replace: true }));
  };

  return (
    <div className="shell">
      <a href="#main" className="skip-link">
        Saltar al contenido
      </a>
      <aside className="shell__sidebar" aria-label="Navegación principal">
        <NavLink to={items[0]?.to ?? "/"} className="shell__brand">
          <span className="shell__brand-mark" aria-hidden="true">
            <Grid3x3 size={20} />
          </span>
          <span>{config.appName}</span>
        </NavLink>
        <nav className="shell__nav">
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end ?? false} className="shell__nav-link">
              <Icon size={18} aria-hidden />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <p className="shell__sidebar-footer">Observar mucho, intervenir poco y adaptar cuando sea necesario.</p>
      </aside>
      <div>
        <header className="shell__topbar">
          <Badge tone="primary">{ROLE_LABEL[role]}</Badge>
          <div className="shell__user">
            <span className="text-label tabular" aria-label="Código de usuario">
              {user?.display_code ?? "—"}
            </span>
            <Button variant="ghost" size="sm" leadingIcon={<LogOut size={16} aria-hidden />} onClick={handleSignOut}>
              Salir
            </Button>
          </div>
        </header>
        <main id="main" className="shell__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

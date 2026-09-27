import { Navigate, Outlet, useLocation } from "react-router-dom";

import { Skeleton } from "@/design-system/components";
import { HOME_BY_ROLE, useSession } from "@/features/auth/session-store";
import type { Role } from "@/lib/api";

/**
 * Guardas de navegación. Solo adaptan la interfaz: la autorización real se verifica
 * SIEMPRE en el backend (RBAC + scope en cada endpoint).
 */
function Restoring() {
  return (
    <div className="centered-page" aria-busy="true">
      <div style={{ width: "min(100%, 360px)", display: "grid", gap: "var(--space-3)" }}>
        <Skeleton height="1.5rem" label="Restaurando sesión" />
        <Skeleton height="1rem" width="70%" />
      </div>
    </div>
  );
}

export function RequireAuth() {
  const { status } = useSession();
  const location = useLocation();
  if (status === "loading") return <Restoring />;
  if (status !== "authenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

export function RequireRole({ roles }: { roles: readonly Role[] }) {
  const { user } = useSession();
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to={HOME_BY_ROLE[user.role]} replace />;
  return <Outlet />;
}

export function RedirectToHome() {
  const { status, user } = useSession();
  if (status === "loading") return <Restoring />;
  if (status === "authenticated" && user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />;
  return <Navigate to="/login" replace />;
}

/** Si ya hay sesión, las páginas de autenticación redirigen al inicio del rol. */
export function AnonymousOnly() {
  const { status, user } = useSession();
  if (status === "authenticated" && user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />;
  return <Outlet />;
}

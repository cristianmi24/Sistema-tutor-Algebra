import { Grid3x3 } from "lucide-react";
import { Link, Outlet } from "react-router-dom";

import { config } from "@/lib/config";

export function AuthLayout() {
  return (
    <div className="auth-layout">
      <aside className="auth-layout__brand">
        <Link to="/login" className="auth-layout__brand-name" style={{ color: "inherit", textDecoration: "none" }}>
          <span className="auth-layout__brand-mark" aria-hidden="true">
            <Grid3x3 size={22} />
          </span>
          {config.appName} · Álgebra
        </Link>
        <p className="auth-layout__claim">Descubre patrones. Construye reglas. Explica tu razonamiento.</p>
        <ul className="auth-layout__principles">
          <li>Autonomía antes que ayuda permanente.</li>
          <li>Razonamiento antes que respuesta aislada.</li>
          <li>Acompañamiento, no alertas.</li>
        </ul>
      </aside>
      <main className="auth-layout__main">
        <div className="auth-layout__panel">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

import { Link } from "react-router-dom";

import { Alert, Button, Card, Field } from "@/design-system/components";

/** Fase 1: estructura visual. La autenticación real (JWT + refresh) llega en la Fase 2. */
export function LoginPage() {
  return (
    <Card title="Iniciar sesión" description="Accede con tu usuario o correo institucional.">
      <form
        className="ds-stack"
        onSubmit={(event) => {
          event.preventDefault();
        }}
        aria-describedby="login-phase-note"
      >
        <Field label="Usuario o correo" name="identifier" autoComplete="username" required />
        <Field label="Contraseña" name="password" type="password" autoComplete="current-password" required />
        <Button type="submit" size="lg" disabled>
          Entrar
        </Button>
        <Alert tone="info" id="login-phase-note" title="Autenticación disponible en la Fase 2">
          Esta pantalla forma parte de la fundación técnica. El inicio de sesión seguro (JWT, refresh tokens, RBAC) se activa en la
          siguiente fase.
        </Alert>
        <p className="text-caption" style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
          <Link to="/forgot-password">¿Olvidaste tu contraseña?</Link>
          <Link to="/register">Crear cuenta de estudiante</Link>
        </p>
      </form>
    </Card>
  );
}

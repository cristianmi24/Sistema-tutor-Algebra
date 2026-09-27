import { Link } from "react-router-dom";

import { Alert, Card } from "@/design-system/components";

export function ForgotPasswordPage() {
  return (
    <Card title="Recuperar contraseña" description="Te enviaremos un enlace temporal; nunca tu contraseña.">
      <div className="ds-stack">
        <Alert tone="info" title="Disponible en la Fase 2">
          La recuperación segura (token temporal hasheado, expiración e invalidación) se implementa en la Fase 2.
        </Alert>
        <Link to="/login">Volver al inicio de sesión</Link>
      </div>
    </Card>
  );
}

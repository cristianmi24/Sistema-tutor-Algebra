import { Link } from "react-router-dom";

import { Alert, Card } from "@/design-system/components";

export function ResetPasswordPage() {
  return (
    <Card title="Restablecer contraseña">
      <div className="ds-stack">
        <Alert tone="info" title="Disponible en la Fase 2">
          El restablecimiento con token temporal se implementa en la Fase 2.
        </Alert>
        <Link to="/login">Volver al inicio de sesión</Link>
      </div>
    </Card>
  );
}

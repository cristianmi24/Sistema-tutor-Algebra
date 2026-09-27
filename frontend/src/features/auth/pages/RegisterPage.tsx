import { Link } from "react-router-dom";

import { Alert, Card } from "@/design-system/components";

export function RegisterPage() {
  return (
    <Card title="Crear cuenta de estudiante" description="Registro con política de privacidad, términos y consentimiento.">
      <div className="ds-stack">
        <Alert tone="info" title="Disponible en la Fase 2">
          El flujo de registro (datos mínimos → política de privacidad → términos → consentimiento → creación de cuenta) se
          implementa en la Fase 2, incluyendo el consentimiento de acudiente cuando el protocolo lo requiera.
        </Alert>
        <Link to="/login">Volver al inicio de sesión</Link>
      </div>
    </Card>
  );
}

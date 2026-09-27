import { Alert } from "@/design-system/components";

import { useSession } from "../session-store";

/** Explica al estudiante, sin etiquetas negativas, qué implica que falte el consentimiento del acudiente. */
export function ConsentStatusBanner() {
  const { user } = useSession();
  if (user?.role !== "STUDENT" || user.status !== "PENDING_CONSENT") return null;
  return (
    <Alert tone="info" title="Puedes trabajar con normalidad">
      Tu institución requiere la autorización de tu acudiente para incluir tu trabajo en la investigación. Mientras se registra, todo lo que hagas
      aquí sirve para tu aprendizaje y lo ve tu docente, pero no entra en el estudio.
    </Alert>
  );
}

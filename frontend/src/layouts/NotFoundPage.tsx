import { Compass } from "lucide-react";
import { Link } from "react-router-dom";

import { Card, EmptyState } from "@/design-system/components";

export function NotFoundPage() {
  return (
    <div className="centered-page">
      <Card style={{ width: "min(100%, 480px)" }}>
        <EmptyState
          icon={<Compass size={28} />}
          title="No encontramos esta página"
          description="La ruta no existe o fue movida."
          action={<Link to="/">Volver al inicio</Link>}
        />
      </Card>
    </div>
  );
}

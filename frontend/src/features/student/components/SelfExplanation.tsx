import { useState } from "react";

import { Button, Textarea } from "@/design-system/components";

export function SelfExplanation({ onSave, saving }: { onSave: (text: string) => void; saving: boolean }) {
  const [text, setText] = useState("");
  const [saved, setSaved] = useState(false);
  return (
    <div className="ds-stack">
      <Textarea
        label="Explicar mi razonamiento"
        hint="¿Cómo pensaste el problema? ¿Qué probaste? No hay respuestas malas aquí."
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setSaved(false);
        }}
        placeholder="Primero observé que…"
      />
      <div className="ds-inline-actions">
        <Button
          variant="secondary"
          disabled={!text.trim()}
          loading={saving}
          onClick={() => {
            onSave(text.trim());
            setSaved(true);
          }}
        >
          Guardar mi explicación
        </Button>
        {saved && <span className="text-caption">Explicación guardada.</span>}
      </div>
    </div>
  );
}

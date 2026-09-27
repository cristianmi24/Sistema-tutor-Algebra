import { Lightbulb, RefreshCw, ThumbsDown, ThumbsUp } from "lucide-react";

import { Alert, Button } from "@/design-system/components";

import type { HelpOffer } from "../api";

export interface HelpPanelProps {
  offer: HelpOffer | null;
  decided: "ACCEPTED" | "REJECTED" | null;
  busy: boolean;
  onRequest: () => void;
  onFeedback: (action: "ACCEPTED" | "REJECTED" | "REFORMULATE") => void;
}

/**
 * Panel de ayuda: el estudiante decide. Puede pedir una pista, aceptarla, rechazarla o pedirla de
 * otra forma. Nunca muestra etiquetas de estado ni la solución.
 */
export function HelpPanel({ offer, decided, busy, onRequest, onFeedback }: HelpPanelProps) {
  if (!offer?.offered) {
    return (
      <div className="help-panel">
        <p className="text-muted">{offer?.message ?? "Si te trabas, puedes pedir una pista. Intenta primero por tu cuenta."}</p>
        <Button variant="secondary" leadingIcon={<Lightbulb size={16} aria-hidden />} onClick={onRequest} loading={busy}>
          Pedir una pista
        </Button>
      </div>
    );
  }
  return (
    <div className="help-panel">
      <Alert tone="info" title="Pista del tutor">
        <p className="help-panel__text">{offer.text}</p>
        {offer.follow_up && <p className="text-caption">{offer.follow_up}</p>}
      </Alert>
      {decided === null ? (
        <div className="ds-inline-actions">
          <Button
            size="sm"
            leadingIcon={<ThumbsUp size={14} aria-hidden />}
            onClick={() => {
              onFeedback("ACCEPTED");
            }}
            loading={busy}
          >
            Me sirve
          </Button>
          <Button
            size="sm"
            variant="secondary"
            leadingIcon={<ThumbsDown size={14} aria-hidden />}
            onClick={() => {
              onFeedback("REJECTED");
            }}
            disabled={busy}
          >
            No, gracias
          </Button>
          {offer.can_reformulate && (
            <Button
              size="sm"
              variant="ghost"
              leadingIcon={<RefreshCw size={14} aria-hidden />}
              onClick={() => {
                onFeedback("REFORMULATE");
              }}
              disabled={busy}
            >
              Dímelo de otra forma
            </Button>
          )}
        </div>
      ) : (
        <div className="ds-inline-actions">
          <span className="text-caption">{decided === "ACCEPTED" ? "Usarás esta pista. Cuando quieras, pide otra." : "Sin problema. Sigue por tu cuenta o pide otra pista distinta."}</span>
          <Button size="sm" variant="secondary" onClick={onRequest} loading={busy}>
            Pedir otra pista
          </Button>
        </div>
      )}
    </div>
  );
}

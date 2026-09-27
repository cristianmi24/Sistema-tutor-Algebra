import { useCallback, useEffect, useRef } from "react";

import { type ClientEventType, type ClientMeta, type Representation, studentApi } from "../api";

/**
 * Registra eventos del cliente (append-only en el servidor) y mide señales locales:
 * tiempo en la tarea, clics y ediciones. Nunca bloquea la interfaz si falla la red.
 */
export function useInteractionLogger(sessionId: string, taskId: string) {
  const startedAt = useRef<number>(Date.now());
  const clicks = useRef(0);
  const edits = useRef(0);

  useEffect(() => {
    startedAt.current = Date.now();
    clicks.current = 0;
    edits.current = 0;
    const onClick = () => {
      clicks.current += 1;
    };
    document.addEventListener("click", onClick);
    return () => {
      document.removeEventListener("click", onClick);
    };
  }, [sessionId, taskId]);

  const meta = useCallback(
    (): ClientMeta => ({ time_on_task_ms: Date.now() - startedAt.current, clicks: clicks.current, edits: edits.current }),
    [],
  );

  const log = useCallback(
    (event_type: ClientEventType, extra: { representation?: Representation; payload?: Record<string, unknown> } = {}) => {
      void studentApi
        .event(sessionId, { event_type, task_id: taskId, client_meta: meta(), ...extra })
        .catch(() => undefined);
    },
    [sessionId, taskId, meta],
  );

  const countEdit = useCallback(() => {
    edits.current += 1;
  }, []);

  return { log, meta, countEdit };
}

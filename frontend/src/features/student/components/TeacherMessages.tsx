import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Alert, Button } from "@/design-system/components";
import { teacherApi, teacherQueryKeys } from "@/features/teacher/api";

/** Mensajes del docente: siempre con tono y rótulo de "docente", distintos de las pistas del sistema. */
export function TeacherMessages({ sessionId, taskId }: { sessionId: string; taskId: string }) {
  const queryClient = useQueryClient();
  const messages = useQuery({ queryKey: teacherQueryKeys.messages(sessionId), queryFn: () => teacherApi.studentMessages(sessionId), refetchInterval: 20_000 });
  const seen = useMutation({
    mutationFn: (id: string) => teacherApi.markSeen(sessionId, id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: teacherQueryKeys.messages(sessionId) }),
  });
  const relevant = (messages.data ?? []).filter((m) => !m.task_id || m.task_id === taskId);
  if (!relevant.length) return null;
  return (
    <div className="ds-stack">
      {relevant.map((m) => (
        <Alert key={m.id} tone="teacher" title="Tu docente te escribe">
          <p className="help-panel__text">{m.content}</p>
          {!m.seen && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => {
                seen.mutate(m.id);
              }}
            >
              Leído
            </Button>
          )}
        </Alert>
      ))}
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { Alert, Badge, Button, Card, PageHeader, Select, Skeleton, Textarea } from "@/design-system/components";
import { researchApi, researchQueryKeys } from "@/features/researcher/api";
import { Timeline } from "@/features/shared/Timeline";
import { studentApi, studentQueryKeys } from "@/features/student/api";
import { errorMessage } from "@/lib/api";

import { INTERVENTION_LABEL, type InterventionType, teacherApi, teacherQueryKeys } from "../api";

export function TeacherSessionPage() {
  const { sessionId = "" } = useParams();
  const queryClient = useQueryClient();
  const session = useQuery({ queryKey: studentQueryKeys.session(sessionId), queryFn: () => studentApi.session(sessionId) });
  const timeline = useQuery({ queryKey: researchQueryKeys.sessionTimeline(sessionId), queryFn: () => researchApi.sessionTimeline(sessionId), refetchInterval: 15_000 });
  const interventions = useQuery({ queryKey: teacherQueryKeys.interventions(sessionId), queryFn: () => teacherApi.interventions(sessionId) });

  const [type, setType] = useState<InterventionType>("QUESTION");
  const [visibility, setVisibility] = useState<"STUDENT" | "RESEARCH_ONLY">("STUDENT");
  const [taskId, setTaskId] = useState("");
  const [content, setContent] = useState("");

  const send = useMutation({
    mutationFn: () =>
      teacherApi.createIntervention({ session_id: sessionId, intervention_type: type, content, visibility, ...(taskId ? { task_id: taskId } : {}) }),
    onSuccess: () => {
      setContent("");
      void queryClient.invalidateQueries({ queryKey: teacherQueryKeys.interventions(sessionId) });
      void queryClient.invalidateQueries({ queryKey: researchQueryKeys.sessionTimeline(sessionId) });
    },
  });

  if (session.isPending) return <Skeleton height="10rem" />;
  if (session.isError) return <Alert tone="error">{errorMessage(session.error)}</Alert>;

  return (
    <>
      <PageHeader
        eyebrow={`Observación · ${session.data.participant_code ?? ""}`}
        title="Sesión de trabajo"
        description={`Iniciada ${new Date(session.data.started_at).toLocaleString("es-CO")} · ${session.data.status}`}
      />
      <div className="activity__two">
        <Card title="Trayectoria" description="Estudiante, sistema tutor y docente se distinguen por color, icono y texto.">
          {timeline.isPending && <Skeleton height="10rem" />}
          {timeline.data && <Timeline steps={timeline.data} />}
        </Card>
        <div className="ds-stack">
          <Card title="Intervenir" description="Tu mensaje llega al estudiante como mensaje del docente. Las observaciones solo quedan para investigación.">
            <form
              className="ds-stack"
              onSubmit={(e) => {
                e.preventDefault();
                if (content.trim()) send.mutate();
              }}
            >
              <Select
                label="Tipo"
                value={type}
                onChange={(e) => {
                  setType(e.target.value as InterventionType);
                }}
              >
                {Object.entries(INTERVENTION_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </Select>
              <Select
                label="Actividad"
                value={taskId}
                onChange={(e) => {
                  setTaskId(e.target.value);
                }}
              >
                <option value="">Toda la sesión</option>
                {session.data.tasks.map((t) => (
                  <option key={t.task.id} value={t.task.id}>
                    {t.task.title}
                  </option>
                ))}
              </Select>
              <Select
                label="Visibilidad"
                value={visibility}
                onChange={(e) => {
                  setVisibility(e.target.value as "STUDENT" | "RESEARCH_ONLY");
                }}
              >
                <option value="STUDENT">Enviar al estudiante</option>
                <option value="RESEARCH_ONLY">Solo anotación (no la ve el estudiante)</option>
              </Select>
              <Textarea
                label="Mensaje"
                rows={3}
                value={content}
                onChange={(e) => {
                  setContent(e.target.value);
                }}
                hint="Prefiere preguntas que ayuden a pensar antes que respuestas."
              />
              {send.isError && <Alert tone="error">{errorMessage(send.error)}</Alert>}
              <Button type="submit" loading={send.isPending} leadingIcon={<Send size={14} aria-hidden />} disabled={session.data.status !== "ACTIVE" && visibility === "STUDENT"}>
                Registrar intervención
              </Button>
            </form>
          </Card>
          <Card title="Intervenciones del docente">
            {interventions.data?.length === 0 && <p className="text-muted">Aún no hay intervenciones.</p>}
            <div className="ds-stack">
              {interventions.data?.map((i) => (
                <Alert key={i.id} tone="teacher" title={`${INTERVENTION_LABEL[i.intervention_type as InterventionType]} · ${new Date(i.created_at).toLocaleTimeString("es-CO")}`}>
                  <p>{i.content}</p>
                  <p className="text-caption">
                    {i.visibility === "STUDENT" ? (i.student_seen_at ? "Vista por el estudiante" : "Aún no vista") : "Solo anotación"}{" "}
                    <Badge tone="teacher">{i.teacher_code}</Badge>
                  </p>
                </Alert>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

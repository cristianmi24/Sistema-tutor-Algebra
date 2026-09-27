import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Alert, Badge, Button, Card, PageHeader, Skeleton } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { type HelpOffer, REPRESENTATION_LABEL, type Representation, TASK_TYPE_LABEL, studentApi, studentQueryKeys } from "../api";
import { ExamplePanel } from "../components/ExamplePanel";
import { HelpPanel } from "../components/HelpPanel";
import { PatternView } from "../components/PatternView";
import { QuestionBlock, type ResponseDraft } from "../components/ResolutionSpace";
import { SelfExplanation } from "../components/SelfExplanation";
import { TeacherMessages } from "../components/TeacherMessages";
import { useInteractionLogger } from "../hooks/useInteractionLogger";

/**
 * Pantalla de actividad (C.29). El estudiante entiende de inmediato: qué hacer, dónde responder,
 * cómo pedir ayuda, cómo cambiar de representación y cómo explicar su razonamiento.
 */
export function ActivityPage() {
  const { sessionId = "", taskId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const session = useQuery({ queryKey: studentQueryKeys.session(sessionId), queryFn: () => studentApi.session(sessionId), enabled: Boolean(sessionId) });
  const responses = useQuery({
    queryKey: studentQueryKeys.responses(sessionId, taskId),
    queryFn: () => studentApi.responses(sessionId, taskId),
    enabled: Boolean(sessionId && taskId),
  });
  const { log, meta, countEdit } = useInteractionLogger(sessionId, taskId);

  const [offer, setOffer] = useState<HelpOffer | null>(null);
  const [decided, setDecided] = useState<"ACCEPTED" | "REJECTED" | null>(null);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [stateLabel, setStateLabel] = useState<string | null>(null);
  const [activeQuestion, setActiveQuestion] = useState<string | null>(null);
  const openedLogged = useRef<string | null>(null);

  const sessionTask = session.data?.tasks.find((t) => t.task.id === taskId);
  const task = sessionTask?.task;

  useEffect(() => {
    if (task && openedLogged.current !== task.id) {
      openedLogged.current = task.id;
      log("TASK_OPENED");
    }
  }, [task, log]);

  const submit = useMutation({
    mutationFn: ({ questionId, draft }: { questionId: string; draft: ResponseDraft }) =>
      studentApi.submit(sessionId, { task_id: taskId, question_id: questionId, representation: draft.representation, content: draft.content, client_meta: meta() }),
    onSuccess: (result) => {
      void queryClient.invalidateQueries({ queryKey: studentQueryKeys.responses(sessionId, taskId) });
      setStateLabel(result.state_label);
      setLastMessage("Tu respuesta quedó registrada. Puedes seguir, revisarla o pedir una pista.");
      if (result.help?.offered) {
        setOffer(result.help);
        setDecided(null);
      }
    },
  });

  const help = useMutation({
    mutationFn: () => studentApi.requestHelp(sessionId, taskId, activeQuestion ?? undefined, meta()),
    onSuccess: (result) => {
      setOffer(result);
      setDecided(null);
    },
  });

  const feedback = useMutation({
    mutationFn: (action: "ACCEPTED" | "REJECTED" | "REFORMULATE") => {
      if (!offer?.scaffold_event_id) throw new Error("No hay una pista activa.");
      return studentApi.feedback(sessionId, offer.scaffold_event_id, action).then((r) => ({ action, r }));
    },
    onSuccess: ({ action, r }) => {
      if (action === "REFORMULATE" && "offered" in r) setOffer(r);
      else setDecided(action === "ACCEPTED" ? "ACCEPTED" : "REJECTED");
    },
  });

  const explanation = useMutation({
    mutationFn: (text: string) => studentApi.event(sessionId, { event_type: "SELF_EXPLANATION", task_id: taskId, payload: { text }, client_meta: meta() }),
  });

  const complete = useMutation({
    mutationFn: () => studentApi.event(sessionId, { event_type: "TASK_COMPLETED", task_id: taskId, client_meta: meta() }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: studentQueryKeys.session(sessionId) });
      void navigate(`/student/sessions/${sessionId}`);
    },
  });

  if (session.isPending || responses.isPending) {
    return (
      <div className="ds-stack">
        <Skeleton height="2rem" width="40%" />
        <Skeleton height="10rem" />
      </div>
    );
  }
  if (session.isError) return <Alert tone="error">{errorMessage(session.error)}</Alert>;
  if (!task || !sessionTask) return <Alert tone="warning">Esta actividad no pertenece a la sesión.</Alert>;

  const attemptsByQuestion = (responses.data ?? []).reduce<Record<string, number>>((acc, r) => {
    acc[r.question_id] = (acc[r.question_id] ?? 0) + 1;
    return acc;
  }, {});
  const readOnly = session.data.status !== "ACTIVE";

  return (
    <div className="activity">
      <PageHeader
        eyebrow={`Actividad · ${TASK_TYPE_LABEL[task.task_type]}`}
        title={task.title}
        actions={
          <div className="ds-inline-actions">
            {stateLabel && <Badge tone="secondary">{stateLabel}</Badge>}
            <Link to={`/student/sessions/${sessionId}`} className="ds-button ds-button--ghost ds-button--sm">
              <ArrowLeft size={14} aria-hidden /> Volver a la sesión
            </Link>
          </div>
        }
      />

      <TeacherMessages sessionId={sessionId} taskId={taskId} />

      <Card title="Tarea">
        <p className="activity__prompt">{task.statement.prompt}</p>
        <div style={{ marginTop: "var(--space-4)" }}>
          <PatternView pattern={task.statement.pattern} />
        </div>
      </Card>

      <Card title="Espacio de resolución" description="Registra lo que piensas. Puedes responder varias veces y cambiar de representación.">
        {readOnly && <Alert tone="info">La sesión terminó: puedes revisar, pero no registrar nuevas respuestas.</Alert>}
        <div className="ds-stack">
          {task.statement.questions.map((q) => (
            <div
              key={q.id}
              onFocus={() => {
                setActiveQuestion(q.id);
              }}
            >
              <QuestionBlock
                question={q}
                pattern={task.statement.pattern}
                attempts={attemptsByQuestion[q.id] ?? 0}
                submitting={submit.isPending && submit.variables?.questionId === q.id}
                onSubmit={(draft) => {
                  if (!readOnly) submit.mutate({ questionId: q.id, draft });
                }}
                onRepresentationChange={(representation: Representation) => {
                  log("REPRESENTATION_CHANGED", { representation, payload: { question_id: q.id, to: REPRESENTATION_LABEL[representation] } });
                }}
                onEdit={countEdit}
              />
            </div>
          ))}
          {lastMessage && (
            <Alert tone="success" title="Registrado">
              {lastMessage}
            </Alert>
          )}
          {submit.isError && <Alert tone="error">{errorMessage(submit.error)}</Alert>}
        </div>
      </Card>

      <div className="activity__two">
        <Card title="Ejemplo" description="Ejemplos con un patrón distinto para que compares estrategias.">
          <ExamplePanel
            taskId={task.id}
            onOpen={(example) => {
              log("EXAMPLE_OPENED", { payload: { example_id: example.id, example_type: example.example_type } });
            }}
          />
        </Card>
        <Card title="Ayuda" description="Tú decides cuándo pedirla y si te sirve.">
          <HelpPanel
            offer={offer}
            decided={decided}
            busy={help.isPending || feedback.isPending}
            onRequest={() => {
              if (!readOnly) help.mutate();
            }}
            onFeedback={(action) => {
              feedback.mutate(action);
            }}
          />
          {(help.isError || feedback.isError) && <Alert tone="error">{errorMessage(help.error ?? feedback.error)}</Alert>}
        </Card>
      </div>

      <Card>
        <SelfExplanation
          saving={explanation.isPending}
          onSave={(text) => {
            explanation.mutate(text);
          }}
        />
      </Card>

      {!readOnly && sessionTask.status !== "COMPLETED" && (
        <div className="ds-inline-actions" style={{ justifyContent: "flex-end" }}>
          <Button
            variant="secondary"
            leadingIcon={<CheckCircle2 size={16} aria-hidden />}
            loading={complete.isPending}
            onClick={() => {
              complete.mutate();
            }}
          >
            Terminé esta actividad
          </Button>
        </div>
      )}
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";

import { Alert, Button, Card, Field, PageHeader, Select, Skeleton, Textarea } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { type InterviewIn, researchApi, researchQueryKeys } from "../api";

export function InterviewsPage() {
  const queryClient = useQueryClient();
  const interviews = useQuery({ queryKey: researchQueryKeys.interviews, queryFn: researchApi.interviews });
  const episodes = useQuery({ queryKey: researchQueryKeys.episodes({}), queryFn: () => researchApi.episodes() });
  const [draft, setDraft] = useState<InterviewIn>({
    title: "",
    interviewee_kind: "STUDENT",
    participant_code: "",
    conducted_at: new Date().toISOString().slice(0, 16),
    notes: "",
    responses: [{ question: "", answer: "" }],
  });
  const create = useMutation({
    mutationFn: () =>
      researchApi.createInterview({
        ...draft,
        conducted_at: new Date(draft.conducted_at).toISOString(),
        responses: draft.responses.filter((r) => r.question.trim()),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: researchQueryKeys.interviews });
      setDraft((d) => ({ ...d, title: "", notes: "", responses: [{ question: "", answer: "" }] }));
    },
  });

  return (
    <>
      <PageHeader eyebrow="Investigación" title="Entrevistas" description="Asociadas a estudiante, docente, sesión, tarea o episodio." />
      <div className="activity__two">
        <Card title="Registradas">
          {interviews.isPending && <Skeleton height="6rem" />}
          {interviews.isError && <Alert tone="error">{errorMessage(interviews.error)}</Alert>}
          {interviews.data?.length === 0 && <p className="text-muted">Sin entrevistas.</p>}
          <div className="ds-stack">
            {interviews.data?.map((iv) => (
              <details key={iv.id} className="question">
                <summary>
                  <strong>{iv.title}</strong> · {iv.participant_code ?? iv.teacher_code} · {new Date(iv.conducted_at).toLocaleDateString("es-CO")}
                </summary>
                {iv.notes && <p>{iv.notes}</p>}
                <ol className="example-steps">
                  {iv.responses.map((r) => (
                    <li key={r.id}>
                      <strong>{r.question}</strong>
                      <p>{r.answer ?? "—"}</p>
                      {r.observations && <p className="text-caption">{r.observations}</p>}
                    </li>
                  ))}
                </ol>
              </details>
            ))}
          </div>
        </Card>
        <Card title="Nueva entrevista">
          <form
            className="ds-stack"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate();
            }}
          >
            <Field
              label="Título"
              value={draft.title}
              onChange={(e) => {
                setDraft({ ...draft, title: e.target.value });
              }}
              required
            />
            <Select
              label="Persona entrevistada"
              value={draft.interviewee_kind}
              onChange={(e) => {
                setDraft({ ...draft, interviewee_kind: e.target.value as "STUDENT" | "TEACHER" });
              }}
            >
              <option value="STUDENT">Estudiante</option>
              <option value="TEACHER">Docente</option>
            </Select>
            {draft.interviewee_kind === "STUDENT" ? (
              <Field
                label="Código de participante"
                placeholder="STU-001"
                value={draft.participant_code ?? ""}
                onChange={(e) => {
                  setDraft({ ...draft, participant_code: e.target.value });
                }}
              />
            ) : (
              <Field
                label="Código de docente"
                placeholder="TEA-001"
                value={draft.teacher_code ?? ""}
                onChange={(e) => {
                  setDraft({ ...draft, teacher_code: e.target.value });
                }}
              />
            )}
            <Select
              label="Episodio relacionado (opcional)"
              value={draft.episode_id ?? ""}
              onChange={(e) => {
                const rest = { ...draft };
                delete rest.episode_id;
                setDraft(e.target.value ? { ...rest, episode_id: e.target.value } : rest);
              }}
            >
              <option value="">Ninguno</option>
              {episodes.data?.map((ep) => (
                <option key={ep.id} value={ep.id}>
                  {ep.participant_code} · {ep.task_code} · {new Date(ep.created_at).toLocaleDateString("es-CO")}
                </option>
              ))}
            </Select>
            <Field
              label="Fecha y hora"
              type="datetime-local"
              value={draft.conducted_at}
              onChange={(e) => {
                setDraft({ ...draft, conducted_at: e.target.value });
              }}
            />
            <Textarea
              label="Notas"
              rows={2}
              value={draft.notes ?? ""}
              onChange={(e) => {
                setDraft({ ...draft, notes: e.target.value });
              }}
            />
            {draft.responses.map((r, i) => (
              <div key={i} className="question">
                <Field
                  label={`Pregunta ${i + 1}`}
                  value={r.question}
                  onChange={(e) => {
                    const responses = [...draft.responses];
                    responses[i] = { ...r, question: e.target.value };
                    setDraft({ ...draft, responses });
                  }}
                />
                <Textarea
                  label="Respuesta"
                  rows={2}
                  value={r.answer ?? ""}
                  onChange={(e) => {
                    const responses = [...draft.responses];
                    responses[i] = { ...r, answer: e.target.value };
                    setDraft({ ...draft, responses });
                  }}
                />
              </div>
            ))}
            <Button
              variant="ghost"
              leadingIcon={<Plus size={14} aria-hidden />}
              onClick={() => {
                setDraft({ ...draft, responses: [...draft.responses, { question: "", answer: "" }] });
              }}
            >
              Añadir pregunta
            </Button>
            {create.isError && <Alert tone="error">{errorMessage(create.error)}</Alert>}
            {create.isSuccess && <Alert tone="success">Entrevista registrada.</Alert>}
            <Button type="submit" loading={create.isPending}>
              Registrar entrevista
            </Button>
          </form>
        </Card>
      </div>
    </>
  );
}

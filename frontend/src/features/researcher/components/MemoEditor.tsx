import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Alert, Button, Field, Textarea } from "@/design-system/components";
import { errorMessage } from "@/lib/api";

import { type Memo, type MemoIn, researchApi } from "../api";

const FIELDS: { key: keyof MemoIn; label: string; hint: string }[] = [
  { key: "observation", label: "Observación", hint: "Qué ocurrió, descrito lo más cerca posible del registro." },
  { key: "interpretation", label: "Interpretación", hint: "Tu lectura provisional." },
  { key: "emerging_question", label: "Pregunta emergente", hint: "¿Qué nueva pregunta abre este episodio?" },
  { key: "contradiction", label: "Contradicción", hint: "Tensiones con otros episodios o con tu interpretación previa." },
  { key: "negative_case", label: "Caso negativo", hint: "Episodios donde no ocurre lo mismo." },
  { key: "possible_category", label: "Posible categoría (del investigador)", hint: "Separada de las clasificaciones automáticas del sistema." },
  { key: "theoretical_sampling_need", label: "Necesidad de muestreo teórico", hint: "Qué casos o datos buscar después." },
];

export function MemoEditor({ episodeId, participantCode, memo, onSaved }: { episodeId?: string; participantCode?: string | null; memo?: Memo; onSaved?: () => void }) {
  const queryClient = useQueryClient();
  const [values, setValues] = useState<MemoIn>(() => ({
    title: memo?.title ?? "",
    episode_id: memo?.episode_id ?? episodeId ?? null,
    participant_code: memo?.participant_code ?? participantCode ?? null,
    observation: memo?.observation ?? "",
    interpretation: memo?.interpretation ?? "",
    emerging_question: memo?.emerging_question ?? "",
    contradiction: memo?.contradiction ?? "",
    negative_case: memo?.negative_case ?? "",
    possible_category: memo?.possible_category ?? "",
    theoretical_sampling_need: memo?.theoretical_sampling_need ?? "",
    tags: memo?.tags ?? [],
  }));
  const [tagText, setTagText] = useState((memo?.tags ?? []).join(", "));

  const save = useMutation({
    mutationFn: () => {
      const payload: MemoIn = { ...values, tags: tagText.split(",").map((t) => t.trim()).filter(Boolean) };
      return memo ? researchApi.updateMemo(memo.id, payload) : researchApi.createMemo(payload);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["research"] });
      if (!memo) {
        setValues((v) => ({ ...v, title: "", observation: "", interpretation: "", emerging_question: "", contradiction: "", negative_case: "", possible_category: "", theoretical_sampling_need: "" }));
        setTagText("");
      }
      onSaved?.();
    },
  });

  return (
    <form
      className="ds-stack"
      onSubmit={(e) => {
        e.preventDefault();
        if (values.title.trim().length >= 2) save.mutate();
      }}
    >
      <Field
        label="Título del memo"
        value={values.title}
        onChange={(e) => {
          setValues({ ...values, title: e.target.value });
        }}
        required
      />
      {FIELDS.map((f) => (
        <Textarea
          key={f.key}
          label={f.label}
          hint={f.hint}
          rows={3}
          value={(values[f.key] as string | undefined) ?? ""}
          onChange={(e) => {
            setValues({ ...values, [f.key]: e.target.value });
          }}
        />
      ))}
      <Field
        label="Etiquetas (separadas por coma)"
        value={tagText}
        onChange={(e) => {
          setTagText(e.target.value);
        }}
      />
      {save.isError && <Alert tone="error">{errorMessage(save.error)}</Alert>}
      {save.isSuccess && <Alert tone="success">Memo guardado.</Alert>}
      <Button type="submit" loading={save.isPending}>
        {memo ? "Guardar cambios" : "Guardar memo"}
      </Button>
    </form>
  );
}

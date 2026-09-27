import { useState } from "react";

import { Button, Field, Textarea } from "@/design-system/components";

import { REPRESENTATION_LABEL, type Pattern, type Question, type Representation } from "../api";

export interface ResponseDraft {
  representation: Representation;
  content: Record<string, unknown>;
}

function defaultRepresentation(question: Question): Representation {
  return question.representations?.[0] ?? (question.kind === "explain" || question.kind === "justify" || question.kind === "compare" || question.kind === "describe" ? "VERBAL" : "NUMERIC");
}

function TableInput({ positions, value, onChange }: { positions: number[]; value: Record<string, string>; onChange: (v: Record<string, string>) => void }) {
  return (
    <table className="table-editor" aria-label="Completa la tabla">
      <thead>
        <tr>
          <th scope="col">Número de figura</th>
          {positions.map((p) => (
            <th key={p} scope="col">
              {p}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">Cantidad</th>
          {positions.map((p) => (
            <td key={p}>
              <input
                className="ds-input"
                inputMode="numeric"
                aria-label={`Cantidad para la figura ${p}`}
                value={value[String(p)] ?? ""}
                onChange={(e) => {
                  onChange({ ...value, [String(p)]: e.target.value });
                }}
              />
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}

function GraphInput({ pattern, positions, value, onChange }: { pattern: Pattern; positions: number[]; value: Record<string, string>; onChange: (v: Record<string, string>) => void }) {
  const xMax = pattern.x_max ?? Math.max(...positions, 6) + 1;
  const yMax = pattern.y_max ?? 30;
  const W = 420;
  const H = 260;
  const pad = 32;
  const sx = (x: number) => pad + (x / xMax) * (W - 2 * pad);
  const sy = (y: number) => H - pad - (y / yMax) * (H - 2 * pad);
  const points = positions.map((p) => ({ x: p, y: Number(value[String(p)]) })).filter((pt) => Number.isFinite(pt.y) && value[String(pt.x)] !== "" && value[String(pt.x)] !== undefined);
  return (
    <div className="graph-editor">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Plano con los puntos marcados">
        <line x1={pad} y1={H - pad} x2={W - pad} y2={H - pad} stroke="var(--color-muted)" />
        <line x1={pad} y1={pad} x2={pad} y2={H - pad} stroke="var(--color-muted)" />
        {Array.from({ length: xMax }).map((_, i) => (
          <text key={`x${i}`} x={sx(i + 1)} y={H - pad + 16} fontSize={10} textAnchor="middle" fill="var(--color-muted)">
            {i + 1}
          </text>
        ))}
        {Array.from({ length: 6 }).map((_, i) => {
          const y = Math.round(((i + 1) * yMax) / 6);
          return (
            <text key={`y${i}`} x={pad - 6} y={sy(y) + 3} fontSize={10} textAnchor="end" fill="var(--color-muted)">
              {y}
            </text>
          );
        })}
        <text x={W - pad} y={H - 6} fontSize={11} textAnchor="end" fill="var(--color-text)">
          {pattern.x_label ?? "n"}
        </text>
        <text x={pad} y={pad - 12} fontSize={11} fill="var(--color-text)">
          {pattern.y_label ?? "cantidad"}
        </text>
        {points.map((pt) => (
          <circle key={pt.x} cx={sx(pt.x)} cy={sy(Math.min(pt.y, yMax))} r={6} fill="var(--color-secondary)" />
        ))}
      </svg>
      <div className="graph-editor__points">
        {positions.map((p) => (
          <Field
            key={p}
            label={`${pattern.x_label ?? "n"} = ${p}`}
            inputMode="numeric"
            value={value[String(p)] ?? ""}
            onChange={(e) => {
              onChange({ ...value, [String(p)]: e.target.value });
            }}
            style={{ width: 88 }}
          />
        ))}
      </div>
    </div>
  );
}

export interface QuestionBlockProps {
  question: Question;
  pattern: Pattern;
  attempts: number;
  submitting: boolean;
  onSubmit: (draft: ResponseDraft) => void;
  onRepresentationChange: (representation: Representation) => void;
  onEdit: () => void;
}

/** Bloque de una pregunta: pestañas de representación + entrada + envío. Sin corrección inmediata. */
export function QuestionBlock({ question, pattern, attempts, submitting, onSubmit, onRepresentationChange, onEdit }: QuestionBlockProps) {
  const options = question.representations ?? [defaultRepresentation(question)];
  const [representation, setRepresentation] = useState<Representation>(options[0] ?? "NUMERIC");
  const [text, setText] = useState("");
  const [value, setValue] = useState("");
  const [expression, setExpression] = useState("");
  const [table, setTable] = useState<Record<string, string>>({});
  const positions = question.positions ?? [1, 2, 3, 4, 5];

  const switchRepresentation = (next: Representation) => {
    if (next === representation) return;
    setRepresentation(next);
    onRepresentationChange(next);
  };

  const submit = () => {
    if (representation === "VERBAL") {
      if (!text.trim()) return;
      onSubmit({ representation, content: { text: text.trim() } });
    } else if (representation === "NUMERIC") {
      if (!value.trim()) return;
      onSubmit({ representation, content: { value: value.trim() } });
    } else if (representation === "SYMBOLIC") {
      if (!expression.trim()) return;
      onSubmit({ representation, content: { expression: expression.trim() } });
    } else if (representation === "TABULAR") {
      const rows = positions.filter((p) => (table[String(p)] ?? "").trim() !== "").map((p) => ({ n: p, value: (table[String(p)] ?? "").trim() }));
      if (!rows.length) return;
      onSubmit({ representation, content: { rows } });
    } else {
      const points = positions.filter((p) => (table[String(p)] ?? "").trim() !== "").map((p) => ({ x: p, y: (table[String(p)] ?? "").trim() }));
      if (!points.length) return;
      onSubmit({ representation, content: { points } });
    }
  };

  return (
    <section className="question" aria-labelledby={`q-${question.id}`}>
      <div className="question__title">
        <h3 id={`q-${question.id}`} style={{ fontSize: "var(--font-size-body-lg)" }}>
          {question.text}
        </h3>
        <span className="question__status">{attempts === 0 ? "Sin responder" : `${attempts} respuesta${attempts > 1 ? "s" : ""} registrada${attempts > 1 ? "s" : ""}`}</span>
      </div>
      {options.length > 1 && (
        <div className="repr-tabs" role="tablist" aria-label="Representación">
          {options.map((r) => (
            <button key={r} type="button" role="tab" aria-selected={representation === r} className="repr-tab" onClick={() => {
                switchRepresentation(r);
              }}
            >
              {REPRESENTATION_LABEL[r]}
            </button>
          ))}
        </div>
      )}
      {representation === "VERBAL" && (
        <Textarea
          label="Tu explicación"
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            onEdit();
          }}
          placeholder="Escribe con tus palabras…"
        />
      )}
      {representation === "NUMERIC" && (
        <Field
          label="Tu respuesta"
          inputMode="numeric"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            onEdit();
          }}
          style={{ maxWidth: 200 }}
        />
      )}
      {representation === "SYMBOLIC" && (
        <Field
          label="Tu expresión (usa n para el número de la figura)"
          placeholder="por ejemplo: 4n - 1"
          value={expression}
          onChange={(e) => {
            setExpression(e.target.value);
            onEdit();
          }}
          style={{ maxWidth: 320 }}
        />
      )}
      {representation === "TABULAR" && (
        <TableInput
          positions={positions}
          value={table}
          onChange={(v) => {
            setTable(v);
            onEdit();
          }}
        />
      )}
      {representation === "GRAPHIC" && (
        <GraphInput
          pattern={pattern}
          positions={positions}
          value={table}
          onChange={(v) => {
            setTable(v);
            onEdit();
          }}
        />
      )}
      <div className="ds-inline-actions">
        <Button onClick={submit} loading={submitting}>
          {attempts === 0 ? "Registrar respuesta" : "Registrar otra respuesta"}
        </Button>
      </div>
    </section>
  );
}

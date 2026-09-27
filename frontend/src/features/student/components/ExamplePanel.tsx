import { useQuery } from "@tanstack/react-query";
import { BookOpen, Eye } from "lucide-react";
import { useState } from "react";

import { Badge, Skeleton } from "@/design-system/components";

import { type WorkedExample, studentApi, studentQueryKeys } from "../api";

const TYPE_LABEL: Record<WorkedExample["example_type"], string> = {
  FULL: "Resuelto",
  PARTIAL: "Parcial",
  HIDDEN_STEPS: "Pasos ocultos",
  SELF_EXPLANATION: "Autoexplicación",
  STRATEGY_COMPARISON: "Dos estrategias",
  INTENTIONAL_ERROR: "Encuentra el error",
  TRANSFER: "Transferencia",
};

interface Step {
  text: string;
  hidden?: boolean;
  prompt?: string;
}

function asSteps(raw: unknown): Step[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((s) => (typeof s === "string" ? { text: s } : (s as Step)));
}

function ExampleBody({ example }: { example: WorkedExample }) {
  const content = example.content;
  const [revealed, setRevealed] = useState<Set<number>>(new Set());
  const steps = asSteps(content.steps);
  const strategies = Array.isArray(content.strategies) ? (content.strategies as { name: string; steps: string[]; reaches?: string }[]) : [];
  return (
    <div className="ds-stack" style={{ marginTop: "var(--space-3)" }}>
      {typeof content.situation === "string" && <p>{content.situation}</p>}
      {steps.length > 0 && (
        <ol className="example-steps">
          {steps.map((step, i) => (
            <li key={i}>
              {step.hidden && !revealed.has(i) ? (
                <>
                  {step.prompt && <p className="text-muted">{step.prompt}</p>}
                  <button
                    type="button"
                    className="example-hidden"
                    onClick={() => {
                      setRevealed((prev) => new Set(prev).add(i));
                    }}
                  >
                    <Eye size={14} aria-hidden /> Revelar paso
                  </button>
                </>
              ) : (
                <>
                  <span>{step.text}</span>
                  {step.prompt && !step.hidden && <p className="text-caption">{step.prompt}</p>}
                </>
              )}
            </li>
          ))}
        </ol>
      )}
      {strategies.length > 0 && (
        <div className="strategy-grid">
          {strategies.map((s) => (
            <div key={s.name} className="question">
              <strong>{s.name}</strong>
              <ol className="example-steps">
                {s.steps.map((st, i) => (
                  <li key={i}>{st}</li>
                ))}
              </ol>
              {s.reaches && <p className="text-caption">{s.reaches}</p>}
            </div>
          ))}
        </div>
      )}
      {typeof content.your_turn === "string" && <p className="text-body-lg">{content.your_turn}</p>}
      {typeof content.prompt === "string" && <p className="text-body-lg">{content.prompt}</p>}
    </div>
  );
}

export function ExamplePanel({ taskId, onOpen }: { taskId: string; onOpen: (example: WorkedExample) => void }) {
  const examples = useQuery({ queryKey: studentQueryKeys.examples(taskId), queryFn: () => studentApi.workedExamples(taskId) });
  const [open, setOpen] = useState<string | null>(null);

  if (examples.isPending) return <Skeleton height="4rem" label="Cargando ejemplos" />;
  if (!examples.data?.length) return <p className="text-muted">Esta actividad no tiene ejemplos. Puedes pedir una pista.</p>;

  return (
    <div className="example-list">
      {examples.data.map((example) => {
        const expanded = open === example.id;
        return (
          <div key={example.id}>
            <button
              type="button"
              className="example-item"
              aria-expanded={expanded}
              style={{ width: "100%" }}
              onClick={() => {
                const next = expanded ? null : example.id;
                setOpen(next);
                if (next) onOpen(example);
              }}
            >
              <span className="ds-inline-actions">
                <BookOpen size={16} aria-hidden />
                <strong>{example.title}</strong>
                <Badge tone="secondary">{TYPE_LABEL[example.example_type]}</Badge>
              </span>
            </button>
            {expanded && <ExampleBody example={example} />}
          </div>
        );
      })}
    </div>
  );
}

import { Cpu, UserRound, UserSquare2 } from "lucide-react";

import { Badge } from "@/design-system/components";
import { asText } from "@/lib/text";

import type { TimelineStep } from "@/features/researcher/api";

const ACTOR = {
  STUDENT: { label: "Estudiante", tone: "neutral", Icon: UserSquare2 },
  SYSTEM: { label: "Sistema tutor", tone: "info", Icon: Cpu },
  TEACHER: { label: "Docente", tone: "teacher", Icon: UserRound },
} as const;

function describeContent(step: TimelineStep): string | null {
  const c = step.content;
  if (!c) return null;
  if (typeof c.text === "string") return `“${c.text}”`;
  if (c.value !== undefined) return `valor: ${asText(c.value)}`;
  if (typeof c.expression === "string") return `expresión: ${c.expression}`;
  if (Array.isArray(c.rows)) return `tabla: ${(c.rows as { n: unknown; value: unknown }[]).map((r) => `${asText(r.n)}→${asText(r.value)}`).join(", ")}`;
  if (Array.isArray(c.points)) return `puntos: ${(c.points as { x: unknown; y: unknown }[]).map((p) => `(${asText(p.x)}, ${asText(p.y)})`).join(" ")}`;
  if (typeof c.error_pattern === "string") return `patrón de error observado: ${c.error_pattern}`;
  return null;
}

/**
 * Línea de tiempo de interacciones. El sistema (azul, chip) y el docente (violeta, persona) se
 * distinguen por color, icono y texto. Las interpretaciones del sistema se rotulan como operativas.
 */
export function Timeline({ steps, showInterpretation = true }: { steps: TimelineStep[]; showInterpretation?: boolean }) {
  if (!steps.length) return <p className="text-muted">Sin eventos.</p>;
  return (
    <ol className="timeline">
      {steps.map((step) => {
        const actor = ACTOR[step.actor];
        const content = describeContent(step);
        const interpretation = step.system_interpretation;
        const evaluation = step.evaluation;
        return (
          <li key={step.sequence} className={`timeline__item timeline__item--${step.actor.toLowerCase()}`}>
            <div className="timeline__marker" aria-hidden="true">
              <actor.Icon size={14} />
            </div>
            <div className="timeline__body">
              <div className="ds-inline-actions">
                <span className="text-caption tabular">
                  #{step.sequence} · {new Date(step.timestamp).toLocaleTimeString("es-CO")}
                </span>
                <Badge tone="primary">{step.phase}</Badge>
                <Badge tone={actor.tone} icon={<actor.Icon size={12} aria-hidden />}>
                  {actor.label}
                </Badge>
                <span className="text-caption">{step.event_type}</span>
                {step.representation && <Badge tone="secondary">{step.representation}</Badge>}
              </div>
              {content && <p>{content}</p>}
              {step.help_text && (
                <p>
                  <strong>Ayuda (nivel {step.help_level ?? "—"}, {step.help_type ?? "—"}):</strong> {step.help_text}
                </p>
              )}
              {step.teacher_intervention && (
                <p>
                  <strong>Docente ({asText(step.teacher_intervention.type)}):</strong> {asText(step.teacher_intervention.content)}
                </p>
              )}
              {evaluation && (evaluation.correct !== undefined || evaluation.observed_dimensions !== undefined) && (
                <p className="text-caption">
                  Registro del evaluador de dominio:{" "}
                  {evaluation.correct === true ? "coincide con la regla" : evaluation.correct === false ? `no coincide (${asText(evaluation.error_pattern)})` : "no calificado"}
                  {Array.isArray(evaluation.observed_dimensions) && evaluation.observed_dimensions.length > 0 && ` · dimensiones observadas: ${(evaluation.observed_dimensions as string[]).join(", ")}`}
                </p>
              )}
              {showInterpretation && interpretation && (
                <details className="timeline__details">
                  <summary className="text-caption">Interpretación operativa del sistema (no es una categoría teórica)</summary>
                  <p className="text-caption">
                    {asText(interpretation.previous_state)} → {asText(interpretation.current_state)} · regla {asText(interpretation.rule_fired)} · nivel{" "}
                    {asText(interpretation.help_level)} · fading {asText(interpretation.fading_action)}
                  </p>
                </details>
              )}
              {showInterpretation && step.ai_interpretation && Array.isArray(step.ai_interpretation.dimensions) && (
                <details className="timeline__details">
                  <summary className="text-caption">Interpretación asistida por IA (validada; no es una categoría teórica)</summary>
                  <p className="text-caption">
                    {(step.ai_interpretation.dimensions as string[]).join(", ") || "sin dimensiones"} · confianza {asText(step.ai_interpretation.confidence)}
                  </p>
                </details>
              )}
              {step.ai_interpretation?.reformulation_source === "AI_VALIDATED" && <p className="text-caption">Reformulación generada por IA y validada.</p>}
              {showInterpretation && step.scaffold_decision && (
                <details className="timeline__details">
                  <summary className="text-caption">Por qué intervino el sistema</summary>
                  <p className="text-caption">{asText(step.scaffold_decision.reason)}</p>
                </details>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

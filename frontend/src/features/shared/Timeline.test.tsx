import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { TimelineStep } from "@/features/researcher/api";

import { Timeline } from "./Timeline";

const base = { timestamp: "2026-09-27T10:00:00Z", representation: null, content: null, help_level: null, help_type: null, help_text: null, evaluation: null, teacher_intervention: null, client_meta: {} };

const steps: TimelineStep[] = [
  { ...base, sequence: 1, phase: "RESPUESTA", event_type: "STUDENT_RESPONSE", actor: "STUDENT", content: { value: 41 }, evaluation: { correct: false, error_pattern: "OFF_BY_STEP" } },
  {
    ...base,
    sequence: 2,
    phase: "AYUDA",
    event_type: "HELP_OFFERED",
    actor: "SYSTEM",
    help_level: 1,
    help_type: "FOCUSING",
    help_text: "Fíjate en cómo cambia.",
    scaffold_decision: { reason: "Regla R-DIFFICULTY-MICRO" },
    system_interpretation: { previous_state: "NORMAL", current_state: "DIFFICULTY", rule_fired: "R-DIFFICULTY-MICRO", help_level: 1, fading_action: "INCREASE" },
  },
  { ...base, sequence: 3, phase: "INTERVENCIÓN DOCENTE", event_type: "TEACHER_INTERVENTION", actor: "TEACHER", teacher_intervention: { type: "QUESTION", content: "¿Qué observas?" } },
];

describe("Timeline", () => {
  it("separates student, system and teacher and labels system interpretation as operational", () => {
    render(<Timeline steps={steps} />);
    expect(screen.getByText("Estudiante")).toBeInTheDocument();
    expect(screen.getByText("Sistema tutor")).toBeInTheDocument();
    expect(screen.getByText("Docente")).toBeInTheDocument();
    expect(screen.getByText(/no coincide \(OFF_BY_STEP\)/)).toBeInTheDocument();
    expect(screen.getByText("Interpretación operativa del sistema (no es una categoría teórica)")).toBeInTheDocument();
    expect(screen.getByText("Por qué intervino el sistema")).toBeInTheDocument();
    expect(screen.getByText(/¿Qué observas\?/)).toBeInTheDocument();
    const items = document.querySelectorAll(".timeline__item");
    expect(items[1]).toHaveClass("timeline__item--system");
    expect(items[2]).toHaveClass("timeline__item--teacher");
  });

  it("can hide system interpretations", () => {
    render(<Timeline steps={steps} showInterpretation={false} />);
    expect(screen.queryByText(/Interpretación operativa/)).not.toBeInTheDocument();
  });
});

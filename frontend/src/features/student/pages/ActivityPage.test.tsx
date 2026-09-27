import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { mockFetch, renderWithProviders, studentSession } from "@/test/utils";

import { ActivityPage } from "./ActivityPage";

const task = {
  id: "t1",
  code: "B-FIG-01",
  task_type: "FIGURAL_PATTERN",
  title: "Mesas y sillas",
  skill: "FUNCTIONAL_RELATION",
  difficulty: 2,
  grade_min: "7",
  grade_max: "9",
  statement: {
    prompt: "Observa las figuras.",
    pattern: { kind: "figural", shape: "tables_chairs", expression: "3*n+2", shown_figures: [1, 2, 3] },
    questions: [
      { id: "q2", kind: "predict", text: "¿Cuántas personas caben con 4 mesas?", position: 4, representations: ["NUMERIC", "TABULAR"] },
      { id: "q4", kind: "generalize", text: "Escribe una regla para n mesas.", representations: ["SYMBOLIC", "VERBAL"] },
    ],
  },
  related_task_id: null,
  order_index: 20,
};

const session = {
  id: "s1",
  student_id: "st1",
  participant_code: "STU-001",
  started_at: "2026-09-27T10:00:00Z",
  ended_at: null,
  status: "ACTIVE",
  context: {},
  tasks: [{ id: "st-1", task, order_index: 0, status: "OPEN", opened_at: null, completed_at: null }],
};

const offer = {
  scaffold_event_id: "se1",
  offered: true,
  level: 1,
  scaffold_type: "FOCUSING",
  text: "Fíjate en cómo cambia la cantidad de la figura 2 a la 3.",
  follow_up: null,
  can_reformulate: true,
  message: "Aquí tienes una pista.",
};

function renderActivity() {
  return renderWithProviders(
    <Routes>
      <Route path="/student/sessions/:sessionId/tasks/:taskId" element={<ActivityPage />} />
    </Routes>,
    { route: "/student/sessions/s1/tasks/t1", session: studentSession() },
  );
}

describe("ActivityPage", () => {
  it("shows task, questions, representation tabs and logs TASK_OPENED", async () => {
    const { calls } = mockFetch([
      { path: "/sessions/s1", body: session },
      { path: /\/sessions\/s1\/responses\?task_id=t1$/, body: [] },
      { path: "/tasks/t1/worked-examples", body: [] },
      { method: "POST", path: "/sessions/s1/events", status: 201, body: { ...eventStub, event_type: "TASK_OPENED" } },
    ]);
    renderActivity();
    expect(await screen.findByRole("heading", { name: "Mesas y sillas" })).toBeInTheDocument();
    expect(screen.getByText("¿Cuántas personas caben con 4 mesas?")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Tabla" })).toBeInTheDocument();
    expect(screen.getByLabelText("Explicar mi razonamiento")).toBeInTheDocument();
    await waitFor(() => {
      const opened = calls.find((c) => c.url.endsWith("/sessions/s1/events"));
      expect((opened?.json() as { event_type: string }).event_type).toBe("TASK_OPENED");
    });
  });

  it("registers a response without showing correctness and lets the student ask, reject and re-ask help", async () => {
    const { calls } = mockFetch([
      { path: "/sessions/s1", body: session },
      { path: /\/sessions\/s1\/responses\?task_id=t1$/, body: [] },
      { path: "/tasks/t1/worked-examples", body: [] },
      { method: "POST", path: "/sessions/s1/events", status: 201, body: eventStub },
      {
        method: "POST",
        path: "/sessions/s1/responses",
        status: 201,
        body: {
          response: { id: "r1", task_id: "t1", question_id: "q2", attempt_number: 1, representation: "NUMERIC", content: { value: "20" }, is_edit_of: null, submitted_at: "2026-09-27T10:01:00Z", evaluation: null },
          help: null,
          state_label: "En marcha",
        },
      },
      { method: "POST", path: "/sessions/s1/help", body: offer },
      { method: "POST", path: "/sessions/s1/scaffold-events/se1/feedback", body: { ...scaffoldEventStub, rejected: true, result: "REJECTED" } },
    ]);
    renderActivity();
    await screen.findByRole("heading", { name: "Mesas y sillas" });

    const [answerInput] = screen.getAllByLabelText("Tu respuesta");
    const [registerButton] = screen.getAllByRole("button", { name: "Registrar respuesta" });
    expect(answerInput).toBeDefined();
    expect(registerButton).toBeDefined();
    if (!answerInput || !registerButton) throw new Error("faltan controles");
    await userEvent.type(answerInput, "20");
    await userEvent.click(registerButton);
    expect(await screen.findByText("Tu respuesta quedó registrada. Puedes seguir, revisarla o pedir una pista.")).toBeInTheDocument();
    expect(screen.queryByText(/incorrect/i)).not.toBeInTheDocument();
    expect(screen.getByText("En marcha")).toBeInTheDocument();
    const submitted = calls.find((c) => c.url.endsWith("/sessions/s1/responses") && c.init?.method === "POST")?.json() as { content: { value: string }; client_meta: { clicks: number } };
    expect(submitted.content.value).toBe("20");
    expect(submitted.client_meta.clicks).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: "Pedir una pista" }));
    expect(await screen.findByText(offer.text)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dímelo de otra forma" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "No, gracias" }));
    expect(await screen.findByText(/Sin problema/)).toBeInTheDocument();
    const feedbackCall = calls.find((c) => c.url.includes("/scaffold-events/se1/feedback"));
    expect((feedbackCall?.json() as { action: string }).action).toBe("REJECTED");
    expect(screen.getByRole("button", { name: "Pedir otra pista" })).toBeInTheDocument();
  });
});

const eventStub = {
  id: "e1",
  session_id: "s1",
  student_id: "st1",
  task_id: "t1",
  timestamp: "2026-09-27T10:00:01Z",
  sequence: 2,
  event_type: "TASK_OPENED",
  student_action: "TASK_OPENED",
  student_response: null,
  representation: null,
  help_requested: false,
  help_level: null,
  help_type: null,
  help_content: null,
  help_accepted: null,
  help_rejected: null,
  scaffold_event_id: null,
  ai_interpretation: null,
  teacher_intervention_id: null,
  next_student_action: null,
  client_meta: {},
};

const scaffoldEventStub = {
  id: "se1",
  session_id: "s1",
  student_id: "st1",
  task_id: "t1",
  interaction_id: null,
  scaffold_id: "sc1",
  scaffold_code: "FOC-CHANGE-01",
  scaffold_type: "FOCUSING",
  decision: {},
  previous_help_level: 0,
  current_help_level: 1,
  reason_for_change: null,
  source: "STATIC",
  delivered_text: offer.text,
  accepted: null,
  rejected: null,
  reformulations: 0,
  result: "PENDING",
  subsequent_strategy: null,
  created_at: "2026-09-27T10:02:00Z",
  resolved_at: null,
};

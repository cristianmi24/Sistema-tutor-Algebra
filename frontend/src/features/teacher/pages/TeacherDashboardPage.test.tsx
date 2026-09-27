import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mockFetch, renderWithProviders, studentSession } from "@/test/utils";

import { TeacherDashboardPage } from "./TeacherDashboardPage";

describe("TeacherDashboardPage", () => {
  it("shows group students with operational state separated from the neutral label and a support suggestion", async () => {
    mockFetch([
      {
        path: "/teacher/groups",
        body: [
          {
            institution_id: "i",
            grade: "8",
            group_code: "A",
            students: [
              {
                student_id: "s1",
                participant_code: "STU-001",
                grade: "8",
                group_code: "A",
                account_status: "ACTIVE",
                active_session_id: "ses1",
                current_task_code: "B-FIG-01",
                current_task_title: "Mesas y sillas",
                last_event_at: "2026-09-27T10:00:00Z",
                last_event_type: "HELP_OFFERED",
                system_helps_in_session: 3,
                help_requests_in_session: 1,
                teacher_interventions_in_session: 0,
                state_label: "Buscando otro camino",
                operational_state: "STAGNATION",
                suggest_teacher: true,
              },
            ],
          },
        ],
      },
    ]);
    renderWithProviders(<TeacherDashboardPage />, { session: studentSession({ role: "TEACHER", display_code: "TEA-001" }) });
    expect(await screen.findByText("Grupo 8.º A")).toBeInTheDocument();
    expect(screen.getByText("Buscando otro camino · STAGNATION")).toBeInTheDocument();
    expect(screen.getByText("Sugerencia de acompañamiento")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Observar" })).toHaveAttribute("href", "/teacher/sessions/ses1");
  });
});

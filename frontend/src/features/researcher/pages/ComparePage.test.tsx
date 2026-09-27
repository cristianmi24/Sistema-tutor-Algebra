import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { mockFetch, renderWithProviders, studentSession } from "@/test/utils";

import { ComparePage } from "./ComparePage";

const ep = (id: string, code: string) => ({
  id,
  student_id: "s",
  participant_code: code,
  session_id: "ss",
  task_id: "t",
  task_code: "B-FIG-01",
  task_title: "Mesas y sillas",
  trigger: "HELP_REQUEST",
  status: "CLOSED",
  close_reason: "RESOLVED",
  summary: {},
  created_at: "2026-09-27T10:00:00Z",
  closed_at: null,
  interaction_count: 5,
});

describe("ComparePage", () => {
  it("shows both episodes side by side with the no-conclusion note", async () => {
    mockFetch([
      { path: /\/research\/episodes$/, body: [ep("a1", "STU-001"), ep("b1", "STU-002")] },
      {
        path: /\/research\/episodes\/compare\?a=a1&b=b1$/,
        body: {
          a: ep("a1", "STU-001"),
          b: ep("b1", "STU-002"),
          dimensions: { representación: { a: ["NUMERIC", "TABULAR"], b: ["NUMERIC"] }, cierre: { a: "RESOLVED", b: "TASK_ABANDONED" } },
          note: "Comparación descriptiva de registros. El sistema no produce conclusiones ni categorías teóricas.",
        },
      },
    ]);
    const researcher = studentSession({ role: "RESEARCHER", display_code: "RES-001" });
    renderWithProviders(
      <Routes>
        <Route path="/researcher/compare" element={<ComparePage />} />
      </Routes>,
      { route: "/researcher/compare?a=a1&b=b1", session: researcher },
    );
    expect(await screen.findByText(/no produce conclusiones/)).toBeInTheDocument();
    expect(screen.getByText("NUMERIC → TABULAR")).toBeInTheDocument();
    expect(screen.getByText("TASK_ABANDONED")).toBeInTheDocument();
  });
});

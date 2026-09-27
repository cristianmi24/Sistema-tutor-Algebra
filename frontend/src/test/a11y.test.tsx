import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { Alert, Button, Checkbox, Field, Select, Textarea } from "@/design-system/components";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { HelpPanel } from "@/features/student/components/HelpPanel";
import { Timeline } from "@/features/shared/Timeline";

import { axeViolations } from "./a11y";
import { mockFetch, renderWithProviders } from "./utils";

describe("accesibilidad (axe-core)", () => {
  it("componentes de formulario sin violaciones", async () => {
    const { container } = renderWithProviders(
      <form>
        <Field label="Correo" error="Obligatorio" hint="Institucional" />
        <Select label="Grado">
          <option>7</option>
        </Select>
        <Textarea label="Explicación" />
        <Checkbox label="Acepto" />
        <Button>Enviar</Button>
        <Alert tone="teacher" title="Mensaje del docente">
          Hola
        </Alert>
      </form>,
    );
    expect(await axeViolations(container)).toEqual([]);
  });

  it("página de inicio de sesión sin violaciones", async () => {
    mockFetch([]);
    const { container } = renderWithProviders(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
      </Routes>,
      { route: "/login" },
    );
    await screen.findByRole("heading", { name: "Iniciar sesión" });
    expect(await axeViolations(container)).toEqual([]);
  });

  it("panel de ayuda y línea de tiempo sin violaciones", async () => {
    const { container } = renderWithProviders(
      <main>
        <HelpPanel
          offer={{ scaffold_event_id: "s", offered: true, level: 1, scaffold_type: "FOCUSING", text: "Fíjate en el cambio.", can_reformulate: true, message: "" }}
          decided={null}
          busy={false}
          onRequest={() => undefined}
          onFeedback={() => undefined}
        />
        <Timeline
          steps={[
            {
              sequence: 1,
              timestamp: "2026-09-27T10:00:00Z",
              phase: "AYUDA",
              event_type: "HELP_OFFERED",
              actor: "SYSTEM",
              representation: null,
              content: null,
              help_level: 1,
              help_type: "FOCUSING",
              help_text: "Fíjate en el cambio.",
              evaluation: null,
              teacher_intervention: null,
              client_meta: {},
            },
          ]}
        />
      </main>,
    );
    expect(await axeViolations(container)).toEqual([]);
  });
});

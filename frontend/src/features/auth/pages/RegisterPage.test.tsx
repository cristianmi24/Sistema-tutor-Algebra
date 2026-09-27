import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { mockFetch, renderWithProviders } from "@/test/utils";

import { RegisterPage } from "./RegisterPage";

const legal = [
  { kind: "PRIVACY_POLICY", version: "2026.1", locale: "es-CO", title: "Política", body_markdown: "# Política\n\n- Recogemos poco.", published_at: null },
  { kind: "TERMS", version: "2026.1", locale: "es-CO", title: "Términos", body_markdown: "# Términos\n\n1. Respeto.", published_at: null },
];

describe("RegisterPage", () => {
  it("walks through data → privacy → terms → consent and sends the consent versions", async () => {
    const { calls } = mockFetch([
      { path: "/legal/institutions", body: [{ code: "DEMO", name: "Institución Demo", required_consent_parties: ["STUDENT", "GUARDIAN"] }] },
      { path: "/legal/documents", body: legal },
      { method: "POST", path: "/auth/register", status: 201, body: { user_id: "u", participant_code: "STU-007", status: "PENDING_CONSENT", research_status: "PENDING" } },
    ]);
    renderWithProviders(<RegisterPage />, { route: "/register" });

    await userEvent.type(await screen.findByLabelText("Usuario o correo institucional"), "patron.7");
    await userEvent.type(screen.getByLabelText("Contraseña"), "Figuras-Crecen-2026");
    await userEvent.selectOptions(await screen.findByLabelText("Institución"), "DEMO");
    await userEvent.selectOptions(screen.getByLabelText("Grado"), "8");
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }));

    expect(await screen.findByText("Recogemos poco.")).toBeInTheDocument();
    const continuePrivacy = screen.getByRole("button", { name: "Continuar" });
    expect(continuePrivacy).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(continuePrivacy);

    expect(await screen.findByText("Respeto.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }));

    expect(await screen.findByText("Tu institución requiere autorización de tu acudiente")).toBeInTheDocument();
    const create = screen.getByRole("button", { name: "Crear mi cuenta" });
    expect(create).toBeDisabled();
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(create);

    expect(await screen.findByText("¡Cuenta creada!")).toBeInTheDocument();
    expect(screen.getByText("STU-007")).toBeInTheDocument();
    const registerCall = calls.find((c) => c.url.endsWith("/auth/register"));
    const body = registerCall?.json() as { consents: { party: string; privacy_policy_version: string }[]; grade: string };
    expect(body.grade).toBe("8");
    expect(body.consents).toEqual([{ party: "STUDENT", privacy_policy_version: "2026.1", terms_version: "2026.1", status: "ACCEPTED" }]);
  });
});

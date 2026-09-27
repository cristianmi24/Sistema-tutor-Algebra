import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { mockFetch, renderWithProviders } from "@/test/utils";

import { LoginPage } from "./LoginPage";

function renderLogin() {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/teacher" element={<h1>Docente home</h1>} />
    </Routes>,
    { route: "/login" },
  );
}

describe("LoginPage", () => {
  it("validates required fields before calling the API", async () => {
    const { fetchMock } = mockFetch([]);
    renderLogin();
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("Escribe tu usuario o correo.")).toBeInTheDocument();
    expect(screen.getByText("Escribe tu contraseña.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("signs in and redirects to the role home", async () => {
    const { calls } = mockFetch([
      {
        method: "POST",
        path: "/auth/login",
        body: {
          access_token: "jwt",
          token_type: "bearer",
          expires_in: 900,
          user: { id: "t1", role: "TEACHER", status: "ACTIVE", display_code: "TEA-001", institution_id: "i1" },
        },
      },
    ]);
    renderLogin();
    await userEvent.type(screen.getByLabelText("Usuario o correo"), "docente@demo.edu");
    await userEvent.type(screen.getByLabelText("Contraseña"), "Clave-Segura-2026");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("heading", { name: "Docente home" })).toBeInTheDocument();
    const body = calls[0]?.json() as Record<string, string>;
    expect(body).toEqual({ identifier: "docente@demo.edu", password: "Clave-Segura-2026" });
    expect(calls[0]?.init?.credentials).toBe("include");
  });

  it("shows the backend error message on failure", async () => {
    mockFetch([
      {
        method: "POST",
        path: "/auth/login",
        status: 401,
        body: { error: { code: "INVALID_CREDENTIALS", message: "Credenciales inválidas.", request_id: "r", details: null } },
      },
    ]);
    renderLogin();
    await userEvent.type(screen.getByLabelText("Usuario o correo"), "alguien");
    await userEvent.type(screen.getByLabelText("Contraseña"), "mala");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    await waitFor(() => {
      expect(screen.getByText("Credenciales inválidas.")).toBeInTheDocument();
    });
  });
});

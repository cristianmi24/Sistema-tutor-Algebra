import { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { RouterProvider } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { SessionProvider, type SessionState } from "@/features/auth/session-store";

import { AppProviders } from "./providers";
import { createTestRouter } from "./router";

function renderAt(path: string, session?: SessionState) {
  const router = createTestRouter([path]);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const tree = session ? (
    <SessionProvider initialState={session}>
      <RouterProvider router={router} />
    </SessionProvider>
  ) : (
    <RouterProvider router={router} />
  );
  render(<AppProviders queryClient={queryClient}>{tree}</AppProviders>);
  return router;
}

const studentSession: SessionState = {
  status: "authenticated",
  accessToken: "t",
  user: { id: "u1", role: "STUDENT", displayCode: "STU-001" },
};

describe("router & guards", () => {
  it("redirects anonymous users from protected routes to /login", async () => {
    const router = renderAt("/student");
    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it("shows the student dashboard to an authenticated student", async () => {
    renderAt("/student", studentSession);
    expect(await screen.findByRole("heading", { name: "Tu espacio de trabajo" })).toBeInTheDocument();
    expect(screen.getByText("STU-001")).toBeInTheDocument();
  });

  it("redirects a student trying to open the researcher area to their own home", async () => {
    const router = renderAt("/researcher", studentSession);
    expect(await screen.findByRole("heading", { name: "Tu espacio de trabajo" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/student");
  });

  it("renders a not-found page for unknown routes", async () => {
    renderAt("/no-existe");
    expect(await screen.findByRole("heading", { name: "No encontramos esta página" })).toBeInTheDocument();
  });
});

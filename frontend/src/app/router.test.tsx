import { QueryClient } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";

import type { SessionState } from "@/features/auth/session-store";
import { mockFetch, studentSession } from "@/test/utils";

import { AppProviders } from "./providers";
import { createTestRouter } from "./router";

function renderAt(path: string, session: SessionState) {
  const router = createTestRouter([path]);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <AppProviders queryClient={queryClient} session={session}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return router;
}

const anonymous: SessionState = { status: "anonymous", user: null, accessToken: null };

beforeEach(() => {
  mockFetch([]);
});

describe("router & guards", () => {
  it("redirects anonymous users from protected routes to /login", async () => {
    const router = renderAt("/student", anonymous);
    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/login");
  });

  it("shows the student dashboard to an authenticated student", async () => {
    renderAt("/student", studentSession());
    expect(await screen.findByRole("heading", { name: "Tu espacio de trabajo" })).toBeInTheDocument();
    expect(screen.getByText("STU-001")).toBeInTheDocument();
  });

  it("explains pending guardian consent to the student without negative labels", async () => {
    renderAt("/student", studentSession({ status: "PENDING_CONSENT", research_status: "PENDING" }));
    expect(await screen.findByText("Puedes trabajar con normalidad")).toBeInTheDocument();
  });

  it("redirects a student trying to open the researcher area to their own home", async () => {
    const router = renderAt("/researcher", studentSession());
    expect(await screen.findByRole("heading", { name: "Tu espacio de trabajo" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/student");
  });

  it("sends authenticated users away from the login page", async () => {
    const router = renderAt("/login", studentSession());
    expect(await screen.findByRole("heading", { name: "Tu espacio de trabajo" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/student");
  });

  it("renders a not-found page for unknown routes", async () => {
    renderAt("/no-existe", anonymous);
    expect(await screen.findByRole("heading", { name: "No encontramos esta página" })).toBeInTheDocument();
  });
});

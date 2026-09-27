import { QueryClient } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { AppProviders } from "@/app/providers";
import { type SessionState, SessionProvider } from "@/features/auth/session-store";

export const ANON: SessionState = { status: "anonymous", user: null, accessToken: null };

export function studentSession(overrides: Partial<SessionState["user"] & object> = {}): SessionState {
  return {
    status: "authenticated",
    accessToken: "token-student",
    user: {
      id: "u-student",
      role: "STUDENT",
      status: "ACTIVE",
      display_code: "STU-001",
      institution_id: "inst-1",
      grade: "8",
      group_code: "A",
      research_status: "ELIGIBLE",
      ...overrides,
    },
  };
}

export function renderWithProviders(ui: ReactNode, { session = ANON, route = "/" }: { session?: SessionState; route?: string } = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <AppProviders queryClient={queryClient} session={session}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </AppProviders>,
  );
}

export interface Route {
  method?: string;
  path: string | RegExp;
  status?: number;
  body: unknown;
}

/** Mock de fetch por rutas: devuelve el primer body cuya ruta coincida con la URL. */
export function mockFetch(routes: Route[]) {
  const calls: { url: string; init: RequestInit | undefined; json: () => unknown }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    calls.push({ url, init, json: () => (typeof init?.body === "string" ? (JSON.parse(init.body) as unknown) : undefined) });
    const method = (init?.method ?? "GET").toUpperCase();
    const route = routes.find((r) => (r.method ?? "GET").toUpperCase() === method && (typeof r.path === "string" ? url.endsWith(r.path) : r.path.test(url)));
    if (!route) {
      return new Response(JSON.stringify({ error: { code: "NOT_FOUND", message: `Sin mock para ${method} ${url}`, request_id: null, details: null } }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    }
    const status = route.status ?? 200;
    if (status === 204) return new Response(null, { status });
    return new Response(JSON.stringify(route.body), { status, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, calls };
}

export { SessionProvider };

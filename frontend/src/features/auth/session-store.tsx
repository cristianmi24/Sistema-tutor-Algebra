import { type ReactNode, createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { type Role, setAccessTokenProvider } from "@/lib/api";

/**
 * Sesión de autenticación en memoria (Fase 1: estructura; Fase 2: login real).
 * El access token NUNCA se guarda en localStorage; el refresh token vive en una cookie HttpOnly.
 */
export interface SessionUser {
  id: string;
  role: Role;
  /** Código visible (STU-001, TEA-001, RES-001) — nunca el nombre real en módulos de investigación. */
  displayCode: string;
}

export interface SessionState {
  status: "anonymous" | "authenticated";
  user: SessionUser | null;
  accessToken: string | null;
}

interface SessionContextValue extends SessionState {
  signIn: (user: SessionUser, accessToken: string) => void;
  signOut: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

const ANONYMOUS: SessionState = { status: "anonymous", user: null, accessToken: null };

export function SessionProvider({ children, initialState = ANONYMOUS }: { children: ReactNode; initialState?: SessionState }) {
  const [state, setState] = useState<SessionState>(initialState);

  useEffect(() => {
    setAccessTokenProvider(() => state.accessToken);
    return () => {
      setAccessTokenProvider(() => null);
    };
  }, [state.accessToken]);

  const signIn = useCallback((user: SessionUser, accessToken: string) => {
    setState({ status: "authenticated", user, accessToken });
  }, []);

  const signOut = useCallback(() => {
    setState(ANONYMOUS);
  }, []);

  const value = useMemo<SessionContextValue>(() => ({ ...state, signIn, signOut }), [state, signIn, signOut]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession debe usarse dentro de <SessionProvider>");
  return ctx;
}

/** Ruta de inicio por rol. */
export const HOME_BY_ROLE: Record<Role, string> = {
  STUDENT: "/student",
  TEACHER: "/teacher",
  RESEARCHER: "/researcher",
  ADMIN: "/admin",
};

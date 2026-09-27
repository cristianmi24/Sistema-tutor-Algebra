import { type ReactNode, createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { type Role, setAccessTokenProvider, setUnauthorizedHandler } from "@/lib/api";

import { type UserSummary, authApi } from "./api";

/**
 * Sesión de autenticación en memoria. El access token NUNCA se guarda en localStorage; el refresh
 * token vive en una cookie HttpOnly que solo el backend lee. Al cargar la app se intenta renovar la
 * sesión con esa cookie.
 */
export interface SessionState {
  status: "loading" | "anonymous" | "authenticated";
  user: UserSummary | null;
  accessToken: string | null;
}

interface SessionContextValue extends SessionState {
  signIn: (user: UserSummary, accessToken: string) => void;
  signOut: () => Promise<void>;
  updateUser: (user: UserSummary) => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

const ANONYMOUS: SessionState = { status: "anonymous", user: null, accessToken: null };

export interface SessionProviderProps {
  children: ReactNode;
  initialState?: SessionState;
  /** Intentar restaurar la sesión con la cookie de refresh al montar (por defecto sí). */
  restoreOnMount?: boolean;
}

export function SessionProvider({ children, initialState, restoreOnMount = true }: SessionProviderProps) {
  const [state, setState] = useState<SessionState>(
    () => initialState ?? (restoreOnMount ? { status: "loading", user: null, accessToken: null } : ANONYMOUS),
  );
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    setAccessTokenProvider(() => stateRef.current.accessToken);
    return () => {
      setAccessTokenProvider(() => null);
    };
  }, []);

  const tryRefresh = useCallback(async (): Promise<boolean> => {
    try {
      const data = await authApi.refresh();
      setState({ status: "authenticated", user: data.user, accessToken: data.access_token });
      stateRef.current = { status: "authenticated", user: data.user, accessToken: data.access_token };
      return true;
    } catch {
      setState(ANONYMOUS);
      stateRef.current = ANONYMOUS;
      return false;
    }
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(tryRefresh);
    return () => {
      setUnauthorizedHandler(null);
    };
  }, [tryRefresh]);

  useEffect(() => {
    if (initialState === undefined && restoreOnMount) {
      void tryRefresh();
    }
  }, [initialState, restoreOnMount, tryRefresh]);

  const signIn = useCallback((user: UserSummary, accessToken: string) => {
    setState({ status: "authenticated", user, accessToken });
  }, []);

  const updateUser = useCallback((user: UserSummary) => {
    setState((prev) => ({ ...prev, user }));
  }, []);

  const signOut = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // aunque falle la red, se limpia la sesión local
    } finally {
      setState(ANONYMOUS);
    }
  }, []);

  const value = useMemo<SessionContextValue>(() => ({ ...state, signIn, signOut, updateUser }), [state, signIn, signOut, updateUser]);
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

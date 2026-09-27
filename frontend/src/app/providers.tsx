import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";

import { type SessionState, SessionProvider } from "@/features/auth/session-store";
import { ApiError } from "@/lib/api";

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (failureCount, error) => {
          // No reintentar errores de cliente (401/403/404/422): son definitivos.
          if (error instanceof ApiError && error.status < 500) return false;
          return failureCount < 2;
        },
      },
    },
  });
}

export function AppProviders({ children, queryClient, session }: { children: ReactNode; queryClient?: QueryClient; session?: SessionState }) {
  const [client] = useState(() => queryClient ?? createQueryClient());
  return (
    <QueryClientProvider client={client}>
      <SessionProvider {...(session ? { initialState: session } : {})}>{children}</SessionProvider>
    </QueryClientProvider>
  );
}

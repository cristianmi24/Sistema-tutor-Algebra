# STI-GA · Frontend (React + TypeScript)

## Scripts

```bash
npm ci
npm run dev          # http://localhost:5173 (proxy /api → http://localhost:8000)
npm run typecheck    # tsc --noEmit (strict)
npm run lint         # eslint (typescript-eslint strict + react-hooks)
npm run test         # vitest + testing-library (jsdom)
npm run build        # tsc + vite build → dist/
npm run check        # todo lo anterior
```

Variables públicas en `.env.example` (`VITE_*` se incluye en el bundle: nunca secretos).

## Estructura

```text
src/
  main.tsx                    # entrada; carga fuente Lexend autoalojada y estilos
  app/                        # App, providers (TanStack Query, sesión), router, guardas por rol
  design-system/              # tokens.css (tipografía, paleta, espaciado), base.css, componentes base
  layouts/                    # AppShell (sidebar + topbar por rol), AuthLayout, NotFoundPage
  features/
    auth/                     # session-store (token en memoria) y páginas (Fase 2: lógica real)
    student|teacher|researcher|admin/   # dashboards (placeholders de Fase 1)
    status/                   # /status: salud de API y BD
  lib/
    config.ts                 # variables VITE_* validadas con Zod
    api/                      # cliente HTTP tipado (ApiError), esquemas Zod, queryKeys
  test/setup.ts               # jest-dom + cleanup
```

## Sistema de diseño

- Tipografía única **Lexend** (variable, autoalojada con `@fontsource-variable/lexend`).
- Tokens semánticos: `--color-primary`, `--color-secondary`, `success`, `warning`, `error`, `info`, `teacher`, `background`, `surface`, `text`, `muted`, `border`.
- Regla: ningún estado se comunica solo por color (icono + texto). `info` = sistema; `teacher` = docente.
- Modo oscuro por `prefers-color-scheme` o `data-theme`.

# 12 — Fase 1 (Fundación): qué se construyó y cómo se verificó

## 1. Entregables

### Monorepo
- `README.md`, `Makefile`, `docker-compose.yml` (PostgreSQL 16 local), `db/init/01-app-role.sql` (rol `sti_app` de mínimo privilegio), `.gitignore` (excluye `.env`, `.venv`, `node_modules`, `dist`).

### Backend (`backend/`)
| Componente | Archivo | Notas |
|-----------|---------|-------|
| Configuración tipada | `app/core/config.py` | `pydantic-settings`; listas CSV; exige driver `psycopg`; **rechaza configuración insegura en producción** (DEBUG, secreto por defecto, CORS http, LLM sin clave) |
| Logging estructurado | `app/core/logging.py` | structlog con `request_id` en cada línea; JSON en producción |
| Errores uniformes | `app/core/errors.py` | Sobre `{"error": {code, message, request_id, details}}`; nunca trazas al cliente |
| Middleware | `app/core/middleware.py` | `X-Request-ID`, cabeceras de seguridad (`nosniff`, `DENY`, `Referrer-Policy`, `Permissions-Policy`, `no-store`, HSTS en prod), CORS restrictivo, log de acceso con duración |
| Base de datos | `app/core/database.py` | SQLAlchemy 2 async + psycopg 3; `Base` con convención de nombres y `TIMESTAMPTZ`; esquemas `identity/learning/research/ops`; soporte de pooler en modo transacción |
| Vocabularios | `app/modules/common/enums.py` | Roles, estados (+ etiquetas neutrales visibles al estudiante), niveles 0–5, tipos de tarea A–G, ejemplos trabajados, representaciones, andamiajes, 18 eventos de trazabilidad, acciones de auditoría |
| Modelos `identity` | `app/modules/identity/models.py` | `institutions`, `users`, `students` (`participant_code`), `teachers`, `researchers`, `teacher_group_assignments`, `legal_documents`, `consents`, `refresh_tokens`, `password_reset_tokens` |
| Modelos `ops` | `app/modules/ops/models.py` | `audit_logs` (append-only, sin FK al actor), `system_settings` |
| Migración | `alembic/versions/0001_identity_and_ops_foundation.py` | Crea los 4 esquemas y 13 tablas con `CHECK`, FK, índices y unicidad de correo insensible a mayúsculas |
| API | `app/api/v1/health.py`, `meta.py` | `GET /api/v1/health`, `/health/ready`, `/meta` |
| Pruebas | `tests/` | 15 pruebas: configuración, cabeceras, CORS, sobre de error, metadatos, readiness con y sin BD, migración upgrade→downgrade→upgrade + **detección de deriva modelo↔migración** + `CHECK` + unicidad de correo |

### Frontend (`frontend/`)
| Componente | Archivo | Notas |
|-----------|---------|-------|
| Tooling | `package.json`, `tsconfig.json` (strict + `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes`), `vite.config.ts` (proxy `/api`), `eslint.config.js` (typescript-eslint strict type-checked) | |
| Design system | `src/design-system/tokens.css`, `base.css`, `components/` | Tipografía única **Lexend** autoalojada; tokens Primary/Secondary/Success/Warning/Error/Info/**Teacher**/Background/Surface/Text/Muted/Border; modo oscuro; foco visible; `prefers-reduced-motion` |
| Componentes | `Button`, `Card`, `Badge`, `Alert`, `Field`, `PageHeader`, `EmptyState`, `Skeleton` | Accesibles; `Alert` distingue **sistema** (`info`) de **docente** (`teacher`) con icono, color y texto oculto para lectores de pantalla |
| Layouts | `AppShell` (sidebar por rol + topbar con código de usuario), `AuthLayout`, `NotFoundPage` | Responsive: sidebar → barra inferior en < 900 px |
| Routing | `src/app/router.tsx`, `guards.tsx` | `/login`, `/register`, `/forgot-password`, `/reset-password`, `/status`, `/student/*`, `/teacher/*`, `/researcher/*`, `/admin/*`; `RequireAuth`, `RequireRole`, redirección por rol |
| Estado | `providers.tsx`, `features/auth/session-store.tsx` | TanStack Query (sin reintentos en 4xx); sesión en memoria (token nunca en `localStorage`) |
| API | `src/lib/api/` | Cliente tipado con Zod, `ApiError` normalizado, `credentials: include`, proveedor de token |
| Página de estado | `/status` | Consulta `/health` y `/health/ready` y muestra badges con icono + texto |
| Pruebas | 12 pruebas Vitest + Testing Library | Botón, Alert (sistema vs. docente), cliente API (éxito, sobre de error, fallback, bearer, esquema inválido), rutas y guardas (anónimo → login; estudiante en `/researcher` → `/student`; 404) |

## 2. Resultados de verificación (ejecutados en esta fase)

```text
backend:  ruff check .            → All checks passed
          ruff format --check .   → OK
          mypy (strict)           → Success: no issues found in 21 source files
          pytest                  → 15 passed (contra PostgreSQL 16)
          alembic upgrade head / downgrade base / upgrade head → OK
          alembic check           → No new upgrade operations detected (sin deriva)
frontend: tsc --noEmit            → OK
          eslint .                → 0 errores
          vitest run              → 12 passed (3 archivos)
          vite build              → OK (index.js 460 kB / 143 kB gzip; fuentes woff2 autoalojadas)
smoke:    GET /api/v1/health        → 200 {"status":"ok",...} + X-Request-ID + cabeceras de seguridad
          GET /api/v1/health/ready  → 200 {"status":"ready","database":"ok"}
          GET /api/v1/meta          → 200 (vocabularios; etiquetas neutrales de estado)
          GET /api/v1/nope          → 404 {"error":{"code":"NOT_FOUND",...}}
          OpenAPI                   → /api/v1/openapi.json con las 3 rutas
```

## 3. Checklist del Paso 8

| Pregunta | Respuesta |
|----------|-----------|
| ¿Funciona? | Sí: API, migración y frontend construidos y probados |
| ¿Es segura? | Cabeceras, CORS restrictivo, sobre de error sin fugas, secretos solo en entorno, validación de producción, rol de BD de mínimo privilegio, token nunca en `localStorage`, CSP en `index.html` |
| ¿Es mantenible? | Módulos pequeños, tipado estricto (mypy strict, TS strict), lint, tests, docs por módulo |
| ¿Preserva la trazabilidad? | `request_id` extremo a extremo; `audit_logs` append-only listo; vocabulario de 18 eventos definido |
| ¿Mantiene al estudiante como agente? | Aún no hay actividades; el vocabulario de estados ya impone etiquetas neutrales y niveles 0–5 |
| ¿Es coherente con la investigación? | `participant_code`; separación de esquemas PII / investigación; `Alert` diferencia sistema/docente |
| ¿La adaptación es explicable? | Estructura `ScaffoldDecision` definida (docs/05); implementación en Fase 4 |
| ¿Puede ampliarse? | Nuevos módulos se registran en `app/models.py` y `api/v1/__init__.py`; nuevas rutas en `router.tsx` |

## 4. Checklist de seguridad C.44 (estado en Fase 1)

```text
¿Hay secretos en el frontend?                   No (solo VITE_API_BASE_URL, VITE_APP_NAME)
¿Se almacenan contraseñas de forma segura?      Columna password_hash lista; Argon2id en Fase 2
¿Se verifica autorización en backend?           Dependencias RBAC en Fase 2 (guardas UI ya presentes)
¿Los JWT expiran?                               Configurado (15 min); emisión en Fase 2
¿Los refresh tokens pueden revocarse?           Tabla refresh_tokens con familia/rotación/revocación lista
¿Hay protección contra abuso?                   slowapi instalado y RATE_LIMIT_AUTH configurado; se aplica en Fase 2
¿Se validan entradas?                           Pydantic en backend; Zod en frontend
¿Se registran acciones administrativas?         Tabla ops.audit_logs lista; AuditService en Fase 2
¿Se separan datos personales de investigación?  Sí: esquemas identity vs learning/research
¿Se limita el acceso por rol?                   Fase 2 (backend); guardas UI listas
¿Se protege la información de menores?          Tablas consents/legal_documents y consent_policy por institución listas
¿Se puede auditar quién accedió a qué?          request_id + audit_logs listos
```

## 5. Pendientes conscientes y decisiones

> Actualización: todos estos puntos se resolvieron en las Fases 2–8 (ver `13-fases-2-8-verificacion.md`); la inmutabilidad de tablas se aplicó con disparadores de base de datos en lugar de `GRANT`.

- Las páginas de autenticación son estructura visual (botón deshabilitado con aviso explícito) hasta la Fase 2.
- `learning`/`research` existen como esquemas vacíos: sus tablas llegan con las Fases 3–5 en migraciones propias.
- `GRANT` de solo `INSERT/SELECT` sobre tablas append-only se añadirá en una migración de endurecimiento al desplegar (requiere el rol `sti_app` distinto del propietario).
- El bundle del frontend se dividirá por rutas (`React.lazy`) cuando existan pantallas reales.

## 6. Siguiente fase

**Fase 2 — Autenticación y consentimiento**: Argon2id, JWT + refresh rotativo en cookie HttpOnly, `require_roles`, recuperación de contraseña, rate limiting, `AuditService`, documentos legales versionados y flujo de registro con consentimiento multi-parte. Ver `09-plan-de-desarrollo.md`.

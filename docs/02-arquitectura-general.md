# 02 — Arquitectura general y módulos

## 1. Vista general

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                               NAVEGADOR                                      │
│  React 19 + TypeScript (Vite)                                                │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌────────┐   Design System (tokens)│
│  │ Student  │ │ Teacher  │ │ Researcher │ │ Admin  │   Router · Query · Forms │
│  └────┬─────┘ └────┬─────┘ └─────┬──────┘ └───┬────┘                         │
└───────┼────────────┼─────────────┼────────────┼──────────────────────────────┘
        │  HTTPS / JSON (JWT Bearer)             │
┌───────▼────────────▼─────────────▼────────────▼──────────────────────────────┐
│                          FASTAPI  (/api/v1)                                  │
│  ┌──────────────── Capa API (routers + schemas Pydantic) ─────────────────┐  │
│  │ auth │ users │ tasks │ sessions │ interactions │ scaffolding │ research│  │
│  └────────────┬───────────────────────────────────────┬────────────────────┘  │
│  ┌────────────▼──── Capa de servicios (casos de uso) ─▼───────────────────┐   │
│  │ AuthService · ConsentService · SessionService · InteractionService     │   │
│  │ EpisodeService · ExportService · AuditService                          │   │
│  └────────────┬─────────────────────────────┬─────────────────────────────┘   │
│  ┌────────────▼──── MOTOR ADAPTATIVO (Python puro, sin I/O) ──────────────┐   │
│  │ EvidenceExtractor → StudentStateEngine → BayesianInferenceEngine       │   │
│  │        → TutorDecisionEngine (reglas) → ScaffoldingEngine (banco)      │   │
│  │        → InterventionMemory → FadingPolicy                             │   │
│  └────────────┬─────────────────────────────┬─────────────────────────────┘   │
│  ┌────────────▼──── IA OPCIONAL ────────────▼─────────────────────────────┐   │
│  │ LLMProvider (abstracto) → Validador pedagógico → seguridad → dominio   │   │
│  │ LLM_ENABLED=false ⇒ ruta completa sin IA                               │   │
│  └────────────┬───────────────────────────────────────────────────────────┘   │
│  ┌────────────▼──── Infraestructura ──────────────────────────────────────┐   │
│  │ SQLAlchemy 2 async (psycopg 3) · Alembic · Settings · Logging · Seguridad│  │
│  └────────────┬───────────────────────────────────────────────────────────┘   │
└───────────────┼──────────────────────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────────────────────┐
│                     POSTGRESQL 16  (Supabase / local)                        │
│  schema identity  │ schema learning        │ schema research │ schema ops    │
│  users, students, │ sessions, tasks,       │ episodes, memos,│ audit_logs    │
│  teachers, ...    │ interactions, states,  │ interviews      │               │
│  consents, tokens │ scaffolds, rules, ai_* │                 │               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 2. Estilo arquitectónico

- **Monolito modular** (un backend FastAPI, un frontend React). Los módulos se comunican por servicios Python, no por red. Justificación: equipo pequeño, necesidad de trazabilidad transaccional (evento + estado + decisión en una sola transacción), y evitar complejidad prematura.
- **Motor adaptativo puro**: sin acceso a BD ni red. Recibe evidencias y configuración, devuelve una `ScaffoldDecision` explicable. Esto lo hace testeable de forma determinista y auditable.
- **Eventos append-only**: `learning.interactions` nunca se actualiza; cualquier corrección es un nuevo evento.
- **Separación identidad / investigación** por esquemas de PostgreSQL y por módulos de código.

## 3. Módulos del backend (`backend/app`)

| Módulo | Responsabilidad | Fase |
|--------|-----------------|------|
| `core/config` | Settings tipados desde variables de entorno | 1 |
| `core/database` | Engine async, sesión, `Base` declarativa, esquemas | 1 |
| `core/logging` | Logging estructurado con `request_id` | 1 |
| `core/security` | Hash Argon2id, JWT, dependencias de autorización | 2 |
| `core/errors` | Excepciones de dominio → respuestas HTTP uniformes | 1 |
| `api/v1/health` | Salud de la aplicación y de la BD | 1 |
| `api/v1/auth` | login, register, refresh, logout, forgot/reset password | 2 |
| `modules/identity` | Users, Students, Teachers, Researchers, Institutions, Consents (modelos) | 1 (modelos) / 2 (servicios) |
| `modules/ops` | AuditLog (modelo) y AuditService | 1 (modelo) / 2 (servicio) |
| `modules/learning` | Sessions, Tasks, WorkedExamples, Responses, Interactions, Evidence, State | 3–4 |
| `modules/tutor` | Engines adaptativos, reglas, banco de andamiajes, memoria, fading | 4 |
| `modules/research` | Episodes, Memos, Interviews, Export | 5 |
| `modules/teacher` | Intervenciones y observaciones docentes | 6 |
| `modules/ai` | Proveedor LLM abstracto, validadores, trazabilidad | 7 |

## 4. Módulos del frontend (`frontend/src`)

| Módulo | Responsabilidad |
|--------|-----------------|
| `design-system/` | Tokens CSS (color, tipografía, espaciado, radios, sombras), componentes base (Button, Card, Badge, Input, Alert, PageHeader, EmptyState) |
| `app/` | Providers (Query, Router), rutas, guardas por rol |
| `layouts/` | `AppShell` (sidebar + topbar), `AuthLayout` |
| `features/auth` | Páginas login/registro/recuperación (Fase 2), store de sesión |
| `features/student` | Dashboard, actividad, representaciones, ejemplos, ayuda (Fase 3) |
| `features/teacher` | Dashboard docente (Fase 6) |
| `features/researcher` | Participantes, sesiones, episodios, timeline, comparación, memos (Fase 5) |
| `features/admin` | Gestión de catálogos y usuarios |
| `lib/api` | Cliente HTTP tipado, manejo de errores, refresh transparente |
| `lib/config` | Variables `VITE_*` validadas con Zod |

## 5. Flujo de una interacción (Fase 4 en adelante)

```text
Estudiante responde ──► POST /interactions (evento STUDENT_RESPONSE)
        │
        ▼
InteractionService: persiste evento (append-only) en la misma transacción que:
        │
        ├─► EvidenceExtractor: ventana de 3–5 eventos → InteractionEvidence
        ├─► StudentStateEngine: estado previo + evidencias → candidatos
        ├─► BayesianInferenceEngine: P(estado | evidencias) (auxiliar)
        ├─► TutorDecisionEngine: reglas legibles → estado actual + nivel
        ├─► ScaffoldingEngine: banco + memoria → andamiaje concreto (o Nivel 0)
        ├─► FadingPolicy: mantener / reducir / aumentar → ScaffoldEvent
        └─► Persistir StudentState + StudentStateHistory + ScaffoldDecision
        │
        ▼
Respuesta al frontend: { evento, estado_visible_para_estudiante (neutral), ayuda opcional }
        │
        ▼
Estudiante acepta / rechaza / reformula ──► nuevos eventos ──► InterventionMemory
        │
        ▼
EpisodeService agrupa la trayectoria en un Episode reconstruible por el investigador
```

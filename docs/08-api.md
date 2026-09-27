# 08 — API REST (`/api/v1`)

Documentación viva en `/docs` (Swagger UI) y `/redoc` generadas por FastAPI. Todas las respuestas de error siguen:

```json
{ "error": { "code": "FORBIDDEN", "message": "No tienes permiso para este recurso.", "request_id": "…", "details": null } }
```

Códigos: `VALIDATION_ERROR` (422), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409), `RATE_LIMITED` (429), `INTERNAL_ERROR` (500).

Autenticación: `Authorization: Bearer <access>`; refresh vía cookie HttpOnly. Paginación: `?page=1&page_size=25` → `{ items, page, page_size, total }`.

## Fase 1 (implementado)
| Método | Ruta | Rol | Descripción |
|--------|------|-----|-------------|
| GET | `/api/v1/health` | público | Estado de la app (`status`, `version`, `environment`) |
| GET | `/api/v1/health/ready` | público | Comprueba conexión a BD |
| GET | `/api/v1/meta` | público | Metadatos no sensibles (roles, estados, tipos de tarea, versión de política) |

## Fase 2 — Auth
| Método | Ruta | Rol | Payload → Respuesta |
|--------|------|-----|---------------------|
| POST | `/auth/register` | público (rate limit) | `{email/username, password, institution_code, grade, group_code, birth_year, consents:[{party, privacy_policy_version, terms_version}]}` → `{user_id, status}` |
| POST | `/auth/login` | público (rate limit) | `{identifier, password}` → `{access_token, token_type, expires_in, user:{id, role, display_code}}` + cookie refresh |
| POST | `/auth/refresh` | cookie | → nuevo access + rota cookie |
| POST | `/auth/logout` | autenticado | revoca familia → 204 |
| POST | `/auth/forgot-password` | público (rate limit) | `{email}` → 202 siempre |
| POST | `/auth/reset-password` | público (rate limit) | `{token, new_password}` → 204 |
| GET | `/auth/me` | autenticado | perfil mínimo según rol |
| GET | `/legal/documents?kind=PRIVACY_POLICY` | público | texto vigente y versión |
| POST | `/consents` | autenticado / acudiente | registrar consentimiento adicional |

## Fase 3 — Estudiante
| Método | Ruta | Rol |
|--------|------|-----|
| GET | `/tasks`, `/tasks/{id}` | STUDENT (asignadas), TEACHER, RESEARCHER, ADMIN |
| GET | `/worked-examples?task_id=` | STUDENT, TEACHER, RESEARCHER, ADMIN |
| POST | `/sessions` / PATCH `/sessions/{id}` (end) | STUDENT |
| GET | `/sessions`, `/sessions/{id}` | propio / scope |
| POST | `/sessions/{id}/responses` | STUDENT → evalúa, registra evento, devuelve decisión (Fase 4) |
| POST | `/interactions` | STUDENT (eventos de cliente: EXAMPLE_OPENED, REPRESENTATION_CHANGED, SELF_EXPLANATION, HELP_*) |
| GET | `/interactions?session_id=` | scope |

## Fase 4 — Motor adaptativo
| Método | Ruta | Rol |
|--------|------|-----|
| GET | `/student-state/{student_id}` | TEACHER (scope), RESEARCHER, ADMIN |
| GET | `/student-state/{student_id}/history` | idem |
| GET | `/evidence?session_id=` | idem |
| POST | `/scaffolding/decision` | interno / ADMIN (simulación con evidencias dadas → `ScaffoldDecision`) |
| GET | `/scaffolding/events?session_id=` | scope |
| POST | `/scaffolding/events/{id}/feedback` | STUDENT (`accepted`/`rejected`/`reformulate`) |
| GET/POST/PUT | `/scaffolds`, `/tutor-rules`, `/bayesian-config` | ADMIN (lectura RESEARCHER) |

## Fase 5 — Investigación
`/episodes`, `/episodes/{id}`, `/episodes/{id}/timeline`, `/episodes/compare?a=&b=`, `/research/memos`, `/research/interviews`, `/research/interviews/{id}/responses`, `/export?format=csv|json|jsonl|xlsx|pdf&scope=…` (RESEARCHER; auditado).

## Fase 6 — Docente
`/teacher/groups`, `/teacher/sessions`, `/teacher/interventions` (POST/GET), `/teacher/observations`.

## Fase 7 — IA
`/ai/interactions?session_id=` (RESEARCHER, ADMIN), `/ai/config` (ADMIN).

## Administración y auditoría
`/users`, `/students`, `/teachers`, `/researchers`, `/institutions`, `/admin/settings`, `/audit?actor=&action=&from=&to=` (ADMIN).

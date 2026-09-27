# 08 — API REST (`/api/v1`)

Documentación viva en `/docs` (Swagger UI), `/redoc` y `/api/v1/openapi.json` (desactivadas en producción). Esta tabla refleja las rutas implementadas.

**Errores** — sobre uniforme:

```json
{ "error": { "code": "FORBIDDEN", "message": "No tienes permiso para este recurso.", "request_id": "…", "details": null } }
```

Códigos: `VALIDATION_ERROR` 422 · `UNAUTHORIZED` 401 · `INVALID_CREDENTIALS` 401 · `FORBIDDEN` 403 · `NOT_FOUND` 404 (también fuera de alcance, para no revelar existencia) · `CONFLICT` 409 · `ACCOUNT_LOCKED` 423 · `PAYLOAD_TOO_LARGE` 413 · `RATE_LIMITED` 429 · `SERVICE_UNAVAILABLE` 503 · `INTERNAL_ERROR` 500.

**Autenticación** — `Authorization: Bearer <access>` (15 min). El refresh viaja solo en la cookie HttpOnly `sti_refresh` (`Path=/api/v1/auth`, `SameSite=Strict`).

Roles: **S** estudiante · **T** docente · **R** investigador · **A** administración · **pub** público. «Alcance»: estudiante = propio; docente = sus grupos; investigador = participantes con consentimiento efectivo de su institución.

## Salud y metadatos
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/health`, `/health/ready` | pub | Estado de la app y de la BD |
| GET | `/meta` | pub | Vocabularios, etiquetas neutrales de estado, versiones legales, IA activa |
| GET | `/legal/documents`, `/legal/institutions` | pub | Política/términos vigentes; instituciones y partes de consentimiento requeridas |

## Autenticación y consentimiento
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/auth/register` | pub (rate limit) | Registro de estudiante con consentimiento versionado → `participant_code`, `research_status` |
| POST | `/auth/login` | pub (rate limit) | Access token + cookie de refresh; bloqueo progresivo |
| POST | `/auth/refresh` | cookie (rate limit) | Rotación; reuso ⇒ revocación de la familia |
| POST | `/auth/logout` | S T R A | Revoca la familia y borra la cookie |
| POST | `/auth/forgot-password` | pub (rate limit) | Siempre 202 (anti-enumeración) |
| POST | `/auth/reset-password` | pub (rate limit) | Token hasheado, un solo uso, revoca sesiones |
| POST | `/auth/change-password` | S T R A | Revoca sesiones |
| GET | `/auth/me` | S T R A | Perfil mínimo |
| GET | `/consents/me` · POST `/consents` · POST `/consents/revoke/{party}` | S T R A | Consentimientos (estudiante: propio o acudiente; personal: su institución) |

## Estudiante: actividades, sesiones, eventos y ayuda
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/tasks`, `/tasks/{id}`, `/tasks/{id}/worked-examples` | S T R A | Actividades (sin solución) y ejemplos trabajados |
| POST | `/sessions` | S | Inicia sesión (una activa a la vez) |
| GET | `/sessions`, `/sessions/{id}` | S T R A (alcance) | Sesiones con resumen |
| PATCH | `/sessions/{id}/end` | S | Termina la sesión |
| POST | `/sessions/{id}/events` | S | Eventos del cliente: TASK_OPENED, EXAMPLE_OPENED, REPRESENTATION_CHANGED, SELF_EXPLANATION, TASK_COMPLETED, TASK_ABANDONED |
| POST | `/sessions/{id}/responses` | S | Registra respuesta → decisión del tutor (ayuda opcional) + etiqueta neutral; sin corrección inmediata |
| GET | `/sessions/{id}/responses`, `/sessions/{id}/interactions` | alcance | Evaluación e interpretaciones solo para personal |
| POST | `/sessions/{id}/help` | S | Solicitud explícita de ayuda |
| POST | `/sessions/{id}/scaffold-events/{eid}/feedback` | S | `ACCEPTED`, `REJECTED` o `REFORMULATE` |
| GET | `/sessions/{id}/scaffold-events` | T R A | Decisiones del tutor (`ScaffoldDecision`) |
| GET · POST | `/sessions/{id}/teacher-messages` · `/{mid}/seen` | S | Mensajes del docente para el estudiante |

## Motor adaptativo
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/student-state/{student_id}`, `/…/history` | T R A (alcance) | Perfil dinámico e historial |
| GET | `/evidence?session_id=` | T R A (alcance) | Evidencias extraídas por evento |
| POST | `/scaffolding/decision` | R A | Simulación del motor con evidencias dadas |
| GET · POST · PUT | `/tutor-rules` | R lee · A edita | Reglas pedagógicas (auditado, versionado) |
| GET · POST | `/bayesian-config`, `/bayesian-config/default` | R lee · A crea versión | Configuración bayesiana |
| GET · POST · PUT | `/catalog/tasks`, `/catalog/scaffolds`, POST `/catalog/worked-examples` | R lee · A edita | Catálogo pedagógico (incluye soluciones: nunca para estudiantes) |

## Investigación
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/research/participants` | T R A (alcance) | Participantes pseudonimizados |
| GET · POST | `/research/episodes` | T R A · R A crea manual | Episodios (automáticos o por rango) |
| GET | `/research/episodes/{id}`, `/…/timeline` | T R A | Detalle con contexto, timeline y memos |
| GET | `/research/episodes/compare?a=&b=` | T R A | Comparación descriptiva A vs. B |
| GET | `/research/sessions/{id}/timeline` | T R A | Timeline completo de una sesión |
| GET · POST · PUT · DELETE | `/research/memos` | R (propios) · A lee | Memos analíticos |
| GET · POST | `/research/interviews`, POST `/…/{id}/responses` | R (propias) · A lee | Entrevistas |
| GET | `/research/export?dataset=&format=` | R A; T (sesiones, interacciones, episodios) | CSV, JSON, JSONL, XLSX, PDF; auditado |

## Docente
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/teacher/groups` | T | Grupos con estado de cada estudiante y sugerencia de acompañamiento |
| POST | `/teacher/interventions` | T (alcance) | Intervención docente (evento TEACHER_INTERVENTION propio) o anotación |
| GET | `/teacher/interventions` | T R A (alcance) | Intervenciones |

## IA opcional
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET | `/ai/config` | A | Configuración sin secretos y garantías |
| GET | `/ai/interactions` | R A (alcance) | Cada llamada, su validación y si fue aprobada |

## Administración
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| GET · POST | `/admin/users` | A | Lista (acceso a PII auditado) y creación de personal |
| PATCH | `/admin/users/{id}/status` | A | Deshabilitar / reactivar (revoca sesiones) |
| POST | `/admin/users/{id}/anonymize` | A | Supresión de identidad; conserva datos pseudonimizados |
| GET · POST · PUT | `/admin/institutions` | A | Política de consentimiento y retención |
| GET | `/admin/audit` | A | Auditoría filtrable |

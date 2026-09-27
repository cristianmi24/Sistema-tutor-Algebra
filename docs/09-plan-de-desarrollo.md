# 09 — Plan de desarrollo por fases

Cada fase termina con la verificación (Paso 8): ¿Funciona? ¿Es segura? ¿Es mantenible? ¿Preserva la trazabilidad? ¿Mantiene al estudiante como agente? ¿Es coherente con la investigación? ¿La adaptación es explicable? ¿Puede ampliarse? No se avanza sin corregir.

| Fase | Entregables | Verificación |
|------|-------------|--------------|
| **0 Arquitectura** ✅ | Docs 00–11 | Revisión de coherencia requisitos ↔ arquitectura ↔ datos |
| **1 Fundación** ✅ | Monorepo `backend/` + `frontend/`; FastAPI con settings, logging, errores, health; SQLAlchemy async + Alembic con esquemas `identity/learning/research/ops` y migración 0001 (identidad + auditoría); React + TS estricto, design system, tipografía, layouts, routing por rol, cliente API; tests backend y frontend; `docker-compose` Postgres local; `.env.example` | `pytest` verde contra PostgreSQL; `alembic upgrade head` y `downgrade`; `npm run typecheck`, `lint`, `test`, `build` verdes |
| **2 Autenticación** | Argon2id, JWT access, refresh rotativo en cookie, logout, RBAC `require_roles`, recuperación de contraseña, rate limiting, auditoría, flujo de registro con consentimiento y documentos legales versionados; páginas login/registro/recuperación | Casos 11 y 12 de C.43; tests de autorización por rol; checklist C.44 |
| **3 Módulo estudiante** | Tasks A–G, worked examples (7 tipos), sesiones, respuestas, representaciones, eventos `interactions` append-only, pantalla de actividad, solicitud/aceptación/rechazo de ayuda (sin motor aún: ayuda del banco por nivel fijo) | Reconstrucción de una sesión completa desde eventos |
| **4 Motor adaptativo** | `EvidenceExtractor`, `StudentStateEngine`, `BayesianInferenceEngine`, `TutorDecisionEngine` (DSL de reglas), `ScaffoldingEngine`, `InterventionMemory`, `FadingPolicy`, `ScaffoldDecision`, persistencia de estado/historial | Casos 1–8 y 11 de C.43 como tests deterministas; explicación completa por decisión |
| **5 Investigación** | Episodios automáticos + manuales, timeline, comparación A/B, memos Charmaz, entrevistas, dashboard investigador, exportación CSV/JSON/JSONL/XLSX/PDF pseudonimizada y auditada | Ningún nombre real en respuestas del módulo; exportación auditada |
| **6 Docente** | Dashboard docente, observación de sesiones, intervención (`TEACHER_INTERVENTION`), anotaciones; separación visual sistema/docente | Caso 9 de C.43 |
| **7 IA opcional** | `LLMProvider` abstracto, `NullProvider`, proveedor real configurable, validadores pedagógico/seguridad/dominio, `ai_interactions`, fallback | Caso 10 de C.43; piloto con criterio de adopción |
| **8 Seguridad y pruebas** | Suite completa: unitarias, integración, API, auth/authz, motor, inferencia, frontend, accesibilidad, regresión; revisión de seguridad; hardening de despliegue | Cobertura de casos C.43 completa; checklist C.44 sin pendientes |

## Convenciones de trabajo

- Ramas por fase; commits pequeños; migraciones Alembic una por cambio de esquema, siempre con `downgrade`.
- Backend: `ruff` (lint+format), `mypy --strict` en módulos del motor, `pytest`.
- Frontend: `tsc --noEmit` (strict), `eslint`, `vitest`, `vite build`.
- Cada módulo importante lleva `README.md` con propósito, entradas, salidas, dependencias, reglas, decisiones y pruebas.

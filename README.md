# STI-GA · Sistema Tutor Inteligente para la Generalización Algebraica

Plataforma web de **investigación educativa** con un **Sistema Tutor Inteligente adaptativo** para estudiantes de 7.º, 8.º y 9.º (12–15 años). Dominio inicial: generalización algebraica (patrones, relaciones recursivas y funcionales, representaciones, justificación y transferencia).

> **OBSERVAR MUCHO, INTERVENIR POCO Y ADAPTAR CUANDO SEA NECESARIO.**
>
> Registrar lo que ocurre sin convertir automáticamente los registros en conclusiones teóricas.

## Estado

| Fase | Estado |
|------|--------|
| 0 · Arquitectura | ✅ [`docs/`](docs/README.md) |
| 1 · Fundación técnica | ✅ [verificación](docs/12-fase-1-verificacion.md) |
| 2 · Autenticación, RBAC y consentimiento | ✅ |
| 3 · Módulo estudiante | ✅ |
| 4 · Motor adaptativo (evidencias, Bayes, reglas, andamiaje, fading) | ✅ |
| 5 · Investigación (episodios, timeline, memos, entrevistas, exportación) | ✅ |
| 6 · Docente | ✅ |
| 7 · IA opcional validada | ✅ |
| 8 · Seguridad y pruebas | ✅ [verificación fases 2–8](docs/13-fases-2-8-verificacion.md) |

## Estructura

```text
docs/        Fase 0: requisitos, arquitectura, seguridad, datos, motor adaptativo, IA, UX, API, plan, riesgos, ADR
backend/     FastAPI · SQLAlchemy 2 async · Alembic · Pydantic · pytest
frontend/    React 19 · TypeScript estricto · Vite · React Router · TanStack Query · Vitest
db/init/     Inicialización de PostgreSQL local (rol de aplicación)
```

## Puesta en marcha rápida

```bash
# 1) Base de datos local (o usa Supabase: ver backend/README.md)
docker compose up -d postgres

# 2) Backend
cd backend && cp .env.example .env
uv venv && uv pip install -e ".[dev]"
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli seed-demo                   # cuentas y catálogo de demostración
.venv/bin/uvicorn app.main:app --reload --port 8000     # http://localhost:8000/docs

# 3) Frontend (otra terminal)
cd frontend && cp .env.example .env
npm ci && npm run dev                                   # http://localhost:5173  (estado: /status)
```

Cuentas de demostración (contraseña `Demo-STI-GA-2026!`): `admin@demo.edu`, `docente@demo.edu`, `investigadora@demo.edu`, `estudiante1..3`.

## Verificaciones

```bash
make check
# backend:  ruff · mypy · pytest (con PostgreSQL: migración upgrade/downgrade + deriva de modelos)
# frontend: tsc --noEmit · eslint · vitest (incluye accesibilidad) · vite build · secretos en el bundle
# e2e:      npm run e2e  (Chromium local; ver docs/13)
```

## Principios no negociables

- El tutor **nunca** resuelve la tarea si aún es posible ayudar a razonar; nivel 0 por defecto; ninguna señal aislada dispara intervención.
- Estados del estudiante = interpretaciones operativas; **nunca** etiquetas negativas visibles.
- Intervención del **sistema** e intervención del **docente** se registran y muestran por separado.
- El LLM es opcional, va detrás de validadores y **no** controla la pedagogía.
- Datos personales (`identity`) separados de datos de investigación (`learning`, `research`); investigadores solo ven códigos (`STU-001`).
- Toda autorización se verifica en el backend; el frontend solo adapta la interfaz.

## Licencia

MIT — ver [LICENSE](LICENSE).

# STI-GA · Backend (FastAPI)

API del Sistema Tutor Inteligente para la Generalización Algebraica. Ver la arquitectura en [`../docs`](../docs/README.md).

## Requisitos
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recomendado) o `pip`
- PostgreSQL 16 (local vía `docker compose` en la raíz, o Supabase)

## Puesta en marcha

```bash
cd backend
cp .env.example .env            # ajusta DATABASE_URL y JWT_SECRET_KEY
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

alembic upgrade head            # crea esquemas identity/learning/research/ops y tablas de la Fase 1
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- Salud: `GET /api/v1/health`, `GET /api/v1/health/ready`
- Vocabularios: `GET /api/v1/meta`

## Supabase

1. Crea un proyecto y copia la cadena de conexión **con el driver `psycopg`**: `postgresql+psycopg://…`.
2. Usa el pooler (puerto 6543) en `DATABASE_URL` con `DATABASE_USES_TRANSACTION_POOLER=true`.
3. Usa la conexión directa/sesión (puerto 5432) en `ALEMBIC_DATABASE_URL` para las migraciones.
4. Ejecuta `alembic upgrade head`.

## Calidad

```bash
ruff check . && ruff format --check .
mypy
pytest                            # usa TEST_DATABASE_URL (o DATABASE_URL); omite pruebas de BD si no hay conexión
```

## Estructura

```text
app/
  main.py                 # create_app(): middleware, rate limiting, errores, routers, política del tutor, IA
  cli.py                  # seed-demo · retention
  core/                   # config, database, logging, errors, middleware, security, auth (RBAC), cookies, ratelimit
  api/v1/                 # health, meta, auth, legal, consents, admin, tasks, sessions, catalog, tutor, research, teacher, ai
  modules/
    common/enums.py       # vocabularios cerrados
    identity/             # PII: modelos, servicios de auth/consentimiento, privacidad (anonimización, retención), correo
    learning/             # tareas, sesiones, eventos append-only, evaluador de dominio, alcance por rol
    tutor/                # motor puro: evidence, bayes, rules, scaffolding, decision + orquestador y configuración
    research/             # episodios, timeline, comparación, memos, entrevistas, exportación
    teacher/              # panorama de grupos e intervenciones
    ai/                   # proveedores LLM, validadores, servicio con respaldo
    ops/                  # auditoría
  seed/                   # documentos legales, catálogo pedagógico, reglas y Bayes, datos demo
alembic/versions/         # 0001–0006
tests/                    # 100 pruebas (PostgreSQL)
```

## IA opcional

```bash
uv pip install -e ".[ai]"
# .env: LLM_ENABLED=true, LLM_PROVIDER=anthropic, LLM_API_KEY=..., LLM_MODEL=claude-opus-5
```

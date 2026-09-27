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
  main.py               # create_app(), lifespan, routers
  core/                 # config, database, logging, errors, middleware, deps
  api/v1/               # routers: health, meta (Fase 1)
  modules/
    common/enums.py     # vocabularios cerrados (roles, estados, eventos, tipos de tarea…)
    identity/models.py  # esquema identity (PII): instituciones, usuarios, perfiles, consentimientos, tokens
    ops/models.py       # esquema ops: audit_logs (append-only), system_settings
  models.py             # registro de modelos para Alembic
alembic/                # migraciones (env async con creación de esquemas)
tests/                  # pytest (+ PostgreSQL opcional)
```

# Atajos de desarrollo. Requiere: uv, node >= 20.19, docker (opcional).
.PHONY: seed retention e2e help db-up db-down backend-install backend-dev backend-test backend-lint migrate frontend-install frontend-dev frontend-check check

help:
	@echo "db-up / db-down        PostgreSQL local (docker compose)"
	@echo "backend-install        Crea .venv e instala dependencias"
	@echo "migrate                alembic upgrade head"
	@echo "backend-dev            uvicorn con recarga en :8000"
	@echo "backend-test           pytest"
	@echo "backend-lint           ruff + mypy"
	@echo "frontend-install       npm ci"
	@echo "frontend-dev           vite en :5173"
	@echo "frontend-check         typecheck + lint + test + build"
	@echo "check                  todas las verificaciones"

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

backend-install:
	cd backend && uv venv && uv pip install -e ".[dev]"

migrate:
	cd backend && .venv/bin/alembic upgrade head

backend-dev:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

backend-test:
	cd backend && .venv/bin/pytest

backend-lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy

frontend-install:
	cd frontend && npm ci

frontend-dev:
	cd frontend && npm run dev

frontend-check:
	cd frontend && npm run check

check: backend-lint backend-test frontend-check

seed:
	cd backend && .venv/bin/python -m app.cli seed-demo

retention:
	cd backend && .venv/bin/python -m app.cli retention --dry-run

e2e:
	cd frontend && npm run e2e

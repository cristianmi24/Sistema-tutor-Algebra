# 11 — Registro de decisiones de arquitectura (ADR)

| ADR | Decisión | Alternativas | Justificación |
|-----|----------|--------------|---------------|
| 001 | Monolito modular FastAPI + React | Microservicios; NestJS adicional | Un equipo pequeño; trazabilidad transaccional; el prompt descarta NestJS sin necesidad concreta |
| 002 | Autenticación propia (JWT + Argon2id) en FastAPI en lugar de Supabase Auth | Supabase Auth / GoTrue | Necesidad de RBAC fino, scope por grupo, consentimiento multi-parte para menores, auditoría propia y rate limiting específico; Supabase se usa como PostgreSQL administrado |
| 003 | Esquemas PostgreSQL `identity / learning / research / ops` | Una sola `public`; bases separadas | Separación real de PII y datos de investigación con integridad referencial y una única migración |
| 004 | SQLAlchemy 2 async con driver `psycopg` 3 | asyncpg; SQLModel | psycopg 3 funciona en modo directo y con el pooler de Supabase; SQLAlchemy 2 tipado con `Mapped[]`; SQLModel añade una capa que dificulta relaciones y esquemas |
| 005 | Alembic para migraciones | Supabase CLI migrations | Migraciones versionadas con `downgrade`, ejecutables en CI y contra cualquier PostgreSQL |
| 006 | Enums como `VARCHAR + CHECK` | `ENUM` nativo | Evolución sin `ALTER TYPE`; misma validación fuerte en Pydantic |
| 007 | Eventos append-only en `learning.interactions` | Tablas mutables | Trazabilidad e investigación exigen historia íntegra |
| 008 | Motor adaptativo como funciones puras | Servicios con acceso a BD | Determinismo, tests, explicabilidad |
| 009 | Naive Bayes discreto configurable | Redes bayesianas dinámicas; BKT; ML | Explicable, sin entrenamiento, suficiente como auxiliar de reglas; extensible más adelante |
| 010 | Reglas en DSL JSON versionado en BD | Reglas hardcodeadas | Legibles por expertos; auditables; cambiables sin despliegue |
| 011 | Access token en memoria + refresh en cookie HttpOnly | Ambos en `localStorage` | Mitiga XSS; rotación con detección de reuso |
| 012 | Tipografía Lexend autoalojada | Google Fonts CDN; Inter | Legibilidad para adolescentes; sin peticiones a terceros (privacidad de menores) |
| 013 | Vite + React Router 7 + TanStack Query + RHF + Zod | Next.js | SPA sin SSR: la app es privada y autenticada; simplicidad de despliegue estático |
| 014 | LLM opcional detrás de validadores, `NullProvider` por defecto | LLM como tutor | El prompt exige que el LLM no controle la pedagogía; funcionamiento sin IA garantizado |
| 015 | `uv` para gestión de dependencias Python | pip + requirements; poetry | Rápido, lockfile reproducible, compatible con `pyproject.toml` estándar |

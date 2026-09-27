# 00 — Resumen ejecutivo

## Qué se construye

**STI-GA** (Sistema Tutor Inteligente para la Generalización Algebraica) es una plataforma web de investigación educativa para estudiantes de 7.º, 8.º y 9.º (12–15 años). Integra un **Sistema Tutor Inteligente adaptativo** cuyo dominio inicial es la **generalización algebraica** (patrones numéricos y figurales, relaciones recursivas y funcionales, representaciones tabular/gráfica/simbólica, justificación y transferencia).

La plataforma cumple dos funciones simultáneas e inseparables:

1. **Dispositivo pedagógico.** Observa la interacción del estudiante, construye un perfil dinámico (`StudentCognitiveInteractionState`), estima su estado con múltiples evidencias apoyadas en **inferencia bayesiana explícita y configurable**, aplica **reglas pedagógicas legibles**, selecciona el **andamiaje mínimo necesario** de un banco revisado por expertos y **retira la ayuda progresivamente** (fading) cuando hay evidencia de recuperación o autonomía.
2. **Instrumento de investigación cualitativa.** Registra cada interacción como evento trazable, reconstruye **episodios** (dificultad → ayuda → reacción → resultado), separa con nitidez la intervención del sistema de la del docente, y ofrece al investigador herramientas de **memos, entrevistas, comparación de episodios y exportación**, sin imponer categorías teóricas (Teoría Fundamentada Constructivista, Charmaz).

## Qué NO es

- No es un chatbot genérico ni un resolutor automático de tareas.
- No es un sistema de alertas ni de castigo por tiempo o error.
- No usa deep learning, redes neuronales ni entrenamiento sobre datasets históricos.
- El LLM es **opcional**, está detrás de validadores y **nunca controla la decisión pedagógica**.
- No interpreta automáticamente "menos ayuda" como aprendizaje ni "respuesta correcta" como comprensión.

## Principios rectores

```text
OBSERVAR MUCHO, INTERVENIR POCO Y ADAPTAR CUANDO SEA NECESARIO.

AUTONOMÍA        > AYUDA PERMANENTE
APRENDIZAJE      > CORRECCIÓN INMEDIATA
ACOMPAÑAMIENTO   > ALERTAS
ADAPTACIÓN       > CASTIGO
RAZONAMIENTO     > RESPUESTA AISLADA
```

Ciclo del tutor: **OBSERVAR → INTERPRETAR → DECIDIR → ADAPTAR → RECORDAR → RETIRAR AYUDA CUANDO SEA APROPIADO.**

## Unidad de análisis

```text
ESTUDIANTE ↕ TAREA ↕ EJEMPLO ↕ ANDAMIAJE ↕ SISTEMA TUTOR / IA ↕ DOCENTE
```

Cada evento, episodio, memo y entrevista debe poder situarse en esta cadena.

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | React 19 + TypeScript estricto, Vite, React Router, TanStack Query, React Hook Form + Zod |
| Backend | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 (async, driver psycopg 3), Alembic |
| Base de datos | PostgreSQL 16 (Supabase como infraestructura administrada; PostgreSQL local para desarrollo) |
| Autenticación | JWT (access + refresh con rotación y revocación), Argon2id, RBAC verificado en backend |
| Motor adaptativo | Python puro: `StudentStateEngine`, `BayesianInferenceEngine`, `TutorDecisionEngine`, `ScaffoldingEngine` |
| IA opcional | Capa de abstracción de proveedor + cadena de validadores (pedagógico, seguridad, dominio) + fallback sin LLM |

## Roles

`STUDENT`, `TEACHER`, `RESEARCHER`, `ADMIN`. Todo permiso se verifica en FastAPI; el frontend solo adapta la interfaz.

## Estado del proyecto

- **Fase 0 (Arquitectura):** documentada en esta carpeta.
- **Fase 1 (Fundación):** implementada (ver `12-fase-1-verificacion.md`).
- Fases 2 → 8: planificadas en `09-plan-de-desarrollo.md`.

# Documentación — Sistema Tutor Inteligente de Generalización Algebraica (STI-GA)

Esta carpeta contiene la **Fase 0 (Arquitectura)** del proyecto y se actualiza en cada fase.

| # | Documento | Contenido |
|---|-----------|-----------|
| 00 | [Resumen ejecutivo](00-resumen-ejecutivo.md) | Qué se construye, para quién y bajo qué principios |
| 01 | [Requisitos](01-requisitos.md) | Requisitos funcionales, no funcionales, roles, entidades, eventos, restricciones, riesgos |
| 02 | [Arquitectura general y módulos](02-arquitectura-general.md) | Diagrama general, capas, módulos y responsabilidades |
| 03 | [Seguridad y privacidad](03-seguridad-y-privacidad.md) | JWT, refresh tokens, RBAC, Argon2id, recuperación, consentimiento, auditoría, protección de datos |
| 04 | [Modelo de datos](04-modelo-de-datos.md) | Esquemas PostgreSQL, tablas, relaciones, índices, separación identidad/investigación |
| 05 | [Arquitectura adaptativa](05-arquitectura-adaptativa.md) | Evidencias, estados, inferencia bayesiana, reglas, matriz pedagógica, fading, memoria |
| 06 | [Arquitectura de IA opcional](06-arquitectura-ia.md) | Qué puede y qué no puede hacer el LLM; validadores; fallback |
| 07 | [Frontend y sistema de diseño](07-frontend-y-diseno-visual.md) | Pantallas, navegación, tipografía, paleta, componentes, responsive |
| 08 | [API REST](08-api.md) | Endpoints, métodos, payloads, permisos, errores |
| 09 | [Plan de desarrollo](09-plan-de-desarrollo.md) | Fases 0 → 8, criterios de verificación por fase |
| 10 | [Riesgos](10-riesgos.md) | Técnicos, pedagógicos, metodológicos, seguridad, privacidad, IA |
| 11 | [Decisiones de arquitectura (ADR)](11-decisiones-adr.md) | Registro de decisiones tecnológicas y su justificación |
| 12 | [Fase 1 — Verificación](12-fase-1-verificacion.md) | Qué se construyó en la Fase 1, cómo ejecutarlo y cómo se verificó |
| 13 | [Fases 2–8 — Verificación](13-fases-2-8-verificacion.md) | Entregables por fase, casos C.43 ↔ pruebas, checklist C.44, hallazgos de la prueba de extremo a extremo |

Principio rector de todo el sistema:

> **OBSERVAR MUCHO, INTERVENIR POCO Y ADAPTAR CUANDO SEA NECESARIO.**

Principio investigativo:

> **Registrar lo que ocurre sin convertir automáticamente los registros en conclusiones teóricas.**

# 10 — Riesgos y mitigaciones

## Técnicos
| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Acoplamiento del motor a la BD dificulta pruebas | Alto | Motor puro sin I/O; servicios lo orquestan |
| Crecimiento de `interactions` degrada consultas | Medio | Índices `(session_id, sequence)`, `(student_id, timestamp)`; particionado por mes si > 10M filas |
| Supabase pooler (transaction mode) y prepared statements | Medio | psycopg 3 con `prepare_threshold=None` cuando `DATABASE_URL` apunta al pooler; migraciones por conexión directa |
| Deriva entre esquemas Zod y Pydantic | Medio | Generar tipos TS desde OpenAPI en Fase 2+ |
| Dependencias de frontend con cambios mayores frecuentes | Bajo | Versiones fijadas; `npm ci`; CI |

## Pedagógicos
| Riesgo | Mitigación |
|--------|------------|
| El tutor interviene demasiado y sustituye el razonamiento | Nivel 0 por defecto; histéresis; regla "una sola variable nunca dispara"; límite de intervenciones por tarea |
| Ayudas que revelan la solución | Banco revisado; validador de dominio; nunca fórmula final |
| Etiquetas negativas visibles | Mapa de estados → etiquetas neutrales; revisión UX |
| Fading interpretado como logro | Fading = evento observable; ninguna métrica de "aprendizaje" automática |
| Reglas opacas para expertos | DSL JSON legible + nombre y descripción; vista de reglas en admin |

## Metodológicos (investigación)
| Riesgo | Mitigación |
|--------|------------|
| El sistema impone categorías (viola Charmaz) | Estados = interpretaciones operativas, marcadas como tales; memos con categorías del investigador separadas; sin conclusiones automáticas en comparación |
| Pérdida de contexto de un episodio | Eventos append-only con `sequence`; episodios referencian eventos, no copias |
| Mezcla de intervención IA/docente | Tablas y colores distintos; `source` explícito; tests |
| Sesgo hacia la respuesta correcta | Registrar estrategia, representación, explicación y cambios; no solo `correct` |

## Seguridad
| Riesgo | Mitigación |
|--------|------------|
| Robo de tokens | Access corto en memoria; refresh HttpOnly rotativo con detección de reuso |
| Escalada por confiar en frontend | RBAC + scope en cada endpoint; tests de autorización |
| Fuerza bruta | Rate limiting, bloqueo progresivo, Argon2id |
| Secretos filtrados | `.env` ignorado; solo `VITE_*` público; revisión en CI |

## Privacidad
| Riesgo | Mitigación |
|--------|------------|
| PII en módulos de investigación | Esquemas separados; vistas pseudonimizadas; auditoría de lectura de PII |
| Consentimiento inválido en menores | Consentimiento multi-parte; modo `PENDING_CONSENT`; textos claros; versionado |
| Retención indefinida | `retention_days` por institución + job de anonimización |
| Exportaciones sin control | Exportación pseudonimizada, por rol, auditada |

## IA
| Riesgo | Mitigación |
|--------|------------|
| El LLM toma decisiones pedagógicas | Arquitectura: LLM después del motor, solo propuestas |
| Alucinación matemática | Validador de dominio determinista |
| Inyección de prompt desde respuestas del estudiante | Sin herramientas; salida solo texto/JSON validado; nunca ejecutada |
| Dependencia del proveedor | `NullProvider` y fallback; la plataforma es completa sin IA |
| Fuga de PII al proveedor | Solo `participant_code` y contenido de tarea |

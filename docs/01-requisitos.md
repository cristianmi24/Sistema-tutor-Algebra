# 01 — Mapa de requisitos

## 1. Requisitos funcionales (RF)

### RF-A Autenticación, cuentas y consentimiento
| ID | Requisito |
|----|-----------|
| RF-A1 | Login con correo/usuario + contraseña; emisión de access token y refresh token |
| RF-A2 | Refresh con rotación y revocación; logout revoca la familia de tokens |
| RF-A3 | Registro de estudiantes con flujo: datos mínimos → política de privacidad → términos → consentimiento → registro del consentimiento → creación de cuenta |
| RF-A4 | Consentimiento de menores extensible a acudiente e institución/investigador (multi-parte) |
| RF-A5 | Recuperación segura de contraseña con token temporal hasheado, expiración e invalidación |
| RF-A6 | RBAC: STUDENT, TEACHER, RESEARCHER, ADMIN; verificación en backend en cada endpoint |
| RF-A7 | Gestión de usuarios, instituciones, grupos y roles (ADMIN) |
| RF-A8 | Códigos anonimizados de participante (`STU-001`) usados en todo módulo de investigación |

### RF-B Módulo estudiante
| ID | Requisito |
|----|-----------|
| RF-B1 | Dashboard con sesiones/actividades disponibles y progreso permitido |
| RF-B2 | Banco de actividades configurable: tipos A–G (numérico, figural, tabla, gráfico, simbólico, justificación, transferencia) |
| RF-B3 | Espacio de resolución con múltiples representaciones (verbal, tabular, gráfica, simbólica) y cambio explícito de representación |
| RF-B4 | Ejemplos trabajados: resuelto, parcial, pasos ocultos, autoexplicación, comparación de estrategias, error intencional, transferencia |
| RF-B5 | Solicitud de ayuda explícita; aceptación/rechazo de ayuda; reformulación |
| RF-B6 | Campo "Explicar mi razonamiento" (autoexplicación) |
| RF-B7 | Edición de respuestas con registro del cambio |
| RF-B8 | Nunca mostrar etiquetas negativas de estado al estudiante |

### RF-C Motor adaptativo (STI)
| ID | Requisito |
|----|-----------|
| RF-C1 | Perfil dinámico `StudentCognitiveInteractionState` con historial |
| RF-C2 | Extracción de evidencias multiseñal con ventana configurable (3–5 eventos) |
| RF-C3 | Estados: NORMAL, EXPLORACIÓN, DIFICULTAD, INCERTIDUMBRE, IMPULSIVIDAD, ESTANCAMIENTO, RECUPERACIÓN, AUTONOMÍA |
| RF-C4 | Inferencia bayesiana explícita, configurable y documentada (priors, CPTs) — auxiliar, no decisora |
| RF-C5 | Motor de reglas pedagógicas legibles (SI…ENTONCES) versionadas en BD |
| RF-C6 | Niveles de intervención 0–5; mínima intervención necesaria |
| RF-C7 | Banco de andamiajes prediseñados y revisados; sin generación libre |
| RF-C8 | Fading registrado como evento (`previous_help_level`, `current_help_level`, `reason_for_change`, `student_response`, `result`) |
| RF-C9 | Memoria de intervenciones: no repetir idénticamente una ayuda rechazada o ineficaz |
| RF-C10 | Cada decisión explicable: qué observó, qué evidencia, qué estado, qué regla, por qué, qué intervención, qué pasó después |

### RF-D Trazabilidad e investigación
| ID | Requisito |
|----|-----------|
| RF-D1 | Cada interacción genera un evento inmutable con el esquema mínimo definido (C.19) |
| RF-D2 | Reconstrucción de sesiones y episodios completos |
| RF-D3 | Timeline de episodio y comparación Episodio A vs. B sin conclusión automática |
| RF-D4 | Research memos con campos Charmaz (observation, interpretation, emerging_question, contradiction, negative_case, possible_category, theoretical_sampling_need) |
| RF-D5 | Entrevistas asociadas a student/teacher/session/task/episode |
| RF-D6 | Exportación CSV, JSON, JSONL, Excel, PDF con permisos y pseudonimización |
| RF-D7 | Categorías del investigador separadas de las clasificaciones automáticas |

### RF-E Módulo docente
| ID | Requisito |
|----|-----------|
| RF-E1 | Dashboard: estudiantes, grupos, sesiones, actividades, producciones, intervenciones, episodios |
| RF-E2 | Intervención docente (pregunta, comentario, observación) registrada como `TEACHER_INTERVENTION`, nunca mezclada con la del sistema |
| RF-E3 | Observaciones/anotaciones docentes |

### RF-F IA opcional
| ID | Requisito |
|----|-----------|
| RF-F1 | Capa de abstracción de proveedor LLM, activable por configuración, con fallback total sin LLM |
| RF-F2 | Toda salida pasa por validador pedagógico → seguridad → dominio; nada no validado llega al estudiante |
| RF-F3 | Registro de cada interacción IA (`ai_interactions`) con prompt, salida, validación y decisión |

### RF-G Administración y auditoría
| ID | Requisito |
|----|-----------|
| RF-G1 | Gestión de actividades, ejemplos, andamiajes, reglas, configuraciones |
| RF-G2 | Auditoría de acciones sensibles (`audit_logs`): quién, qué, cuándo, sobre qué |

## 2. Requisitos no funcionales (RNF)

| ID | Categoría | Requisito |
|----|-----------|-----------|
| RNF-1 | Seguridad | Argon2id; JWT con expiración corta (15 min) y refresh rotativo (7–30 días); rate limiting en `/auth/*`; CORS restrictivo; cabeceras de seguridad; secretos solo en entorno |
| RNF-2 | Privacidad | Separación física de esquemas `identity` vs `learning`/`research`; pseudonimización; retención configurable; minimización |
| RNF-3 | Explicabilidad | Toda decisión del tutor persiste su justificación estructurada (`ScaffoldDecision`) |
| RNF-4 | Trazabilidad | Eventos inmutables (append-only), ordenados, con `session_id`, `student_id`, `task_id`, `timestamp` |
| RNF-5 | Mantenibilidad | Módulos pequeños, tipado estricto (TS `strict`, mypy), Pydantic, tests por módulo |
| RNF-6 | Extensibilidad | Nuevos tipos de actividad, andamiajes, reglas y estados sin cambiar el núcleo |
| RNF-7 | Disponibilidad sin IA | El sistema funciona completamente con `LLM_ENABLED=false` |
| RNF-8 | Accesibilidad | Contraste AA, estados no comunicados solo por color, navegación por teclado, textos legibles |
| RNF-9 | Rendimiento | Respuesta de decisión del tutor < 300 ms sin LLM; paginación en listados |
| RNF-10 | Observabilidad | Logging estructurado con `request_id`; logs de seguridad |
| RNF-11 | Portabilidad | PostgreSQL local o Supabase con la misma migración |

## 3. Roles

Ver `03-seguridad-y-privacidad.md` §RBAC para la matriz de permisos.

## 4. Entidades principales

`Institution`, `User`, `Student`, `Teacher`, `Researcher`, `Consent`, `Group`, `LearningSession`, `Task`, `WorkedExample`, `StudentResponse`, `Representation`, `Interaction`, `InteractionEvidence`, `StudentState`, `StudentStateHistory`, `Scaffold`, `ScaffoldEvent`, `TutorRule`, `AIInteraction`, `TeacherIntervention`, `Episode`, `ResearchMemo`, `Interview`, `InterviewResponse`, `RefreshToken`, `PasswordResetToken`, `AuditLog`. Detalle en `04-modelo-de-datos.md`.

## 5. Eventos mínimos

```text
SESSION_STARTED, TASK_OPENED, EXAMPLE_OPENED, STUDENT_RESPONSE, STUDENT_EDITED_RESPONSE,
HELP_REQUESTED, HELP_OFFERED, HELP_ACCEPTED, HELP_REJECTED, HELP_REFORMULATED,
STUDENT_REATTEMPT, REPRESENTATION_CHANGED, SELF_EXPLANATION, ERROR_DETECTED,
TEACHER_INTERVENTION, TASK_COMPLETED, TASK_ABANDONED, SESSION_ENDED
```

## 6. Restricciones

- Sin NestJS ni segundo backend.
- Sin deep learning; inferencia bayesiana explícita solamente.
- El LLM nunca decide la intervención ni genera ayudas fuera del banco sin validación.
- Nunca resolver la tarea automáticamente si aún es posible ayudar a razonar.
- Nunca intervenir por una única señal (p. ej., solo tiempo).
- Nombres reales nunca aparecen en módulos de investigación.

## 7. Riesgos identificados

Ver `10-riesgos.md`.

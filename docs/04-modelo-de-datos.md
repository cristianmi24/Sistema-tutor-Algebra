# 04 — Modelo de datos

## 1. Organización por esquemas PostgreSQL

| Esquema | Propósito | Contiene PII |
|---------|-----------|--------------|
| `identity` | Cuentas, personas, instituciones, consentimiento, tokens | **Sí** |
| `learning` | Sesiones, tareas, ejemplos, respuestas, interacciones, estados, andamiajes, reglas, IA, intervenciones docentes | No (solo `student_id` UUID y `participant_code`) |
| `research` | Episodios, memos, entrevistas | No |
| `ops` | Auditoría y configuración del sistema | Mínimo (user_id actor) |

Regla: **ninguna tabla de `learning` o `research` referencia `identity.users`**. Referencian `identity.students.id` (UUID opaco) o `identity.teachers.id`. El acceso del investigador pasa por vistas que solo exponen `participant_code`.

Convenciones: PK `id UUID DEFAULT gen_random_uuid()`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at` donde aplique, enums como `VARCHAR` + `CHECK` (facilita migraciones), JSONB para payloads flexibles con validación en Pydantic.

## 2. Esquema `identity` (Fase 1: modelos + migración)

```text
institutions
  id, code (UQ), name, country, city, consent_policy JSONB, retention_days INT, is_active, created_at, updated_at

users
  id, institution_id FK→institutions (NULL para ADMIN global), email (UQ, citext/lower), username (UQ, NULL),
  password_hash, role CHECK IN (STUDENT, TEACHER, RESEARCHER, ADMIN), status CHECK IN (ACTIVE, PENDING_CONSENT, LOCKED, DISABLED),
  failed_login_attempts INT, locked_until, last_login_at, password_changed_at, created_at, updated_at
  IDX (institution_id, role)

students
  id, user_id FK→users (UQ), institution_id FK, participant_code (UQ por institución: STU-001), grade CHECK IN (7,8,9),
  group_code, birth_year INT (NULL), created_at, updated_at
  IDX (institution_id, grade, group_code)

teachers
  id, user_id FK→users (UQ), institution_id FK, display_code (TEA-001), created_at

researchers
  id, user_id FK→users (UQ), institution_id FK (NULL), display_code (RES-001), created_at

teacher_group_assignments
  id, teacher_id FK, institution_id FK, grade, group_code, created_at  UQ(teacher_id, institution_id, grade, group_code)

consents
  id, user_id FK→users, consent_party CHECK IN (STUDENT, GUARDIAN, INSTITUTION, RESEARCHER),
  privacy_policy_version, terms_version, consent_status CHECK IN (ACCEPTED, DECLINED, REVOKED, PENDING),
  accepted_at, revoked_at, evidence JSONB (method, ip_truncated, user_agent, guardian_reference), created_at
  IDX (user_id, consent_party)

legal_documents
  id, kind CHECK IN (PRIVACY_POLICY, TERMS), version, locale, title, body_markdown, published_at, is_current
  UQ (kind, version, locale)

refresh_tokens
  id, user_id FK, family_id UUID, token_hash (UQ), issued_at, expires_at, revoked_at, revoked_reason, rotated_to FK→refresh_tokens (NULL), user_agent, ip_truncated
  IDX (user_id), IDX (family_id)

password_reset_tokens
  id, user_id FK, token_hash (UQ), expires_at, used_at, requested_ip_truncated, created_at
```

## 3. Esquema `learning` (Fases 3–4)

```text
tasks
  id, code (UQ), task_type CHECK IN (NUMERIC_PATTERN, FIGURAL_PATTERN, TABLE, GRAPH, SYMBOLIC, JUSTIFICATION, TRANSFER),
  title, statement JSONB (patrón, figuras, tabla, preguntas), difficulty INT 1–5, skill (p.ej. RECURSIVE_RELATION, FUNCTIONAL_RELATION),
  related_task_id FK→tasks (para TRANSFER), grade_min, grade_max, version, is_active, created_by (admin user_id, sin FK cruzada), created_at

worked_examples
  id, task_id FK, example_type CHECK IN (FULL, PARTIAL, HIDDEN_STEPS, SELF_EXPLANATION, STRATEGY_COMPARISON, INTENTIONAL_ERROR, TRANSFER),
  content JSONB (pasos, prompts, estrategias), order_index, is_active, created_at

learning_sessions
  id, student_id FK→identity.students, institution_id, started_at, ended_at, status CHECK IN (ACTIVE, COMPLETED, ABANDONED),
  context JSONB (dispositivo, grupo), created_at   IDX (student_id, started_at)

session_tasks
  id, session_id FK, task_id FK, opened_at, completed_at, status, order_index   UQ (session_id, task_id)

student_responses
  id, session_id FK, task_id FK, student_id FK, attempt_number INT, representation CHECK IN (VERBAL, NUMERIC, TABULAR, GRAPHIC, SYMBOLIC),
  content JSONB, is_edit_of FK→student_responses, evaluation JSONB (correct?, error_pattern, rubric) NULL, submitted_at
  IDX (session_id, task_id, submitted_at)

representations
  id, response_id FK, representation, payload JSONB, created_at    -- una respuesta puede tener varias vistas

interactions   (APPEND-ONLY — el evento de trazabilidad C.19)
  id, session_id FK, student_id FK, task_id FK (NULL), timestamp, sequence BIGINT (por sesión),
  event_type CHECK IN (SESSION_STARTED, TASK_OPENED, EXAMPLE_OPENED, STUDENT_RESPONSE, STUDENT_EDITED_RESPONSE, HELP_REQUESTED, HELP_OFFERED,
                       HELP_ACCEPTED, HELP_REJECTED, HELP_REFORMULATED, STUDENT_REATTEMPT, REPRESENTATION_CHANGED, SELF_EXPLANATION,
                       ERROR_DETECTED, TEACHER_INTERVENTION, TASK_COMPLETED, TASK_ABANDONED, SESSION_ENDED),
  student_action, student_response JSONB, representation, help_requested BOOL, help_level INT, help_type, help_content,
  help_accepted BOOL NULL, help_rejected BOOL NULL, ai_interpretation JSONB NULL, teacher_intervention_id FK NULL,
  next_student_action (rellenado por el siguiente evento), client_meta JSONB (clics, tiempo en pantalla)
  IDX (session_id, sequence), IDX (student_id, timestamp), IDX (event_type)

interaction_evidence
  id, interaction_id FK, student_id FK, window_size INT, evidence JSONB
     {response_time_ms, recent_accuracy, attempt_count, repetition_count, click_pattern, error_pattern, answer_changes, help_requests, prior_help_result}
  IDX (student_id, created_at)

student_state   (perfil dinámico vigente: StudentCognitiveInteractionState)
  id, student_id FK (UQ), session_id FK, current_skill, current_difficulty, recent_accuracy NUMERIC, average_response_time_ms,
  click_pattern, attempt_count, repetition_count, error_pattern, confidence NUMERIC,
  current_state CHECK IN (NORMAL, EXPLORATION, DIFFICULTY, UNCERTAINTY, IMPULSIVITY, STAGNATION, RECOVERY, AUTONOMY),
  previous_state, last_intervention_id FK→scaffold_events, intervention_result, posterior JSONB (P(estado|evidencias)), updated_at

student_state_history
  id, student_id FK, session_id FK, interaction_id FK, previous_state, evidence_snapshot JSONB, posterior JSONB, inferred_state,
  rule_fired, current_state, created_at    IDX (student_id, created_at)

scaffolds   (BANCO DE ANDAMIAJES, revisado por expertos)
  id, code (UQ), scaffold_type CHECK IN (FOCUSING, GUIDING_QUESTION, HINT, SELF_EXPLANATION, REPRESENTATION_CHANGE, TASK_DIVISION,
                                       RECOVERY, METACOGNITIVE, STRATEGY_COMPARISON, ERROR_REFLECTION),
  level INT 1–5, applicable_task_types TEXT[], applicable_skills TEXT[], content JSONB (texto, variantes), language, version, is_active, reviewed_by, reviewed_at

scaffold_events   (decisiones + fading + memoria de intervención)
  id, session_id FK, student_id FK, task_id FK, interaction_id FK (evento que disparó), scaffold_id FK (NULL si nivel 0),
  decision JSONB (ScaffoldDecision: needDetected, evidence[], candidateSupports[], selectedSupport, explicitnessLevel, confidence, reason, validationStatus),
  previous_help_level INT, current_help_level INT, reason_for_change, source CHECK IN (SYSTEM, AI_VALIDATED),
  accepted BOOL NULL, rejected BOOL NULL, student_response JSONB NULL, result CHECK IN (IMPROVED, PERSISTED, REJECTED, ABANDONED, UNKNOWN),
  subsequent_strategy, created_at, resolved_at    IDX (student_id, created_at), IDX (scaffold_id)

tutor_rules
  id, code (UQ), name, description, priority INT, conditions JSONB (DSL legible), actions JSONB, version, is_active, created_at, updated_at

bayesian_config
  id, name (UQ), version, priors JSONB, likelihoods JSONB (CPTs por evidencia discretizada), thresholds JSONB, is_active, created_at

ai_interactions
  id, session_id FK, student_id FK, interaction_id FK, provider, model, purpose CHECK IN (INTERPRET_OPEN_ANSWER, ADAPT_LANGUAGE, FORMULATE_QUESTION, ANALYZE_EXPLANATION, DETECT_CONTRADICTION),
  prompt_hash, prompt JSONB, raw_output TEXT, validation JSONB (pedagogical, safety, domain, approved BOOL, reasons[]), latency_ms, created_at

teacher_interventions   (SIEMPRE separado del sistema)
  id, teacher_id FK→identity.teachers, student_id FK, session_id FK, task_id FK NULL, interaction_id FK NULL,
  intervention_type CHECK IN (QUESTION, COMMENT, OBSERVATION, REDIRECTION, ENCOURAGEMENT), content TEXT, visibility CHECK IN (STUDENT, RESEARCH_ONLY), created_at
```

## 4. Esquema `research` (Fase 5)

```text
episodes
  id, student_id FK, session_id FK, task_id FK, started_interaction_id FK, ended_interaction_id FK NULL,
  trigger CHECK IN (DIFFICULTY, HELP_REQUEST, STAGNATION, TEACHER, MANUAL), summary JSONB (auto: conteos, niveles, estados — NO categorías),
  status CHECK IN (OPEN, CLOSED), created_at, closed_at    IDX (student_id, created_at)

episode_interactions
  episode_id FK, interaction_id FK, order_index    PK (episode_id, interaction_id)

research_memos
  id, researcher_id FK→identity.researchers, episode_id FK NULL, student_id FK NULL, session_id FK NULL, task_id FK NULL,
  observation TEXT, interpretation TEXT, emerging_question TEXT, contradiction TEXT, negative_case TEXT,
  possible_category TEXT, theoretical_sampling_need TEXT, tags TEXT[], created_at, updated_at

interviews
  id, researcher_id FK, interviewee_kind CHECK IN (STUDENT, TEACHER), student_id FK NULL, teacher_id FK NULL,
  session_id FK NULL, task_id FK NULL, episode_id FK NULL, conducted_at, notes TEXT, created_at

interview_responses
  id, interview_id FK, order_index, question TEXT, answer TEXT, related_episode_id FK NULL, observations TEXT, memo_id FK NULL, created_at
```

## 5. Esquema `ops`

```text
audit_logs   (APPEND-ONLY)
  id, occurred_at, actor_user_id UUID NULL (sin FK para conservar tras borrado), actor_role, action (LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT,
  TOKEN_REFRESHED, TOKEN_REUSE_DETECTED, PASSWORD_RESET_REQUESTED, PASSWORD_RESET, USER_CREATED, USER_UPDATED, ROLE_CHANGED, CONSENT_RECORDED,
  CONSENT_REVOKED, EXPORT_GENERATED, PII_ACCESSED, RULE_UPDATED, SCAFFOLD_UPDATED, ...),
  resource_type, resource_id, outcome CHECK IN (SUCCESS, FAILURE, DENIED), request_id, ip_truncated, user_agent, details JSONB
  IDX (occurred_at), IDX (actor_user_id, occurred_at), IDX (action)

system_settings
  key (PK), value JSONB, description, updated_by, updated_at
```

## 6. Relaciones clave (ER simplificado)

```text
institutions 1──* users 1──1 students ──* learning_sessions ──* interactions ──1 interaction_evidence
                     │  1──1 teachers ──* teacher_interventions          │
                     │  1──1 researchers ──* research_memos, interviews  ├──* scaffold_events ──1 scaffolds
                     └──* consents, refresh_tokens, password_reset_tokens └──* student_state_history
students 1──1 student_state
tasks 1──* worked_examples ; tasks 1──* session_tasks ; tasks *──1 tasks (related_task_id)
episodes *──* interactions (episode_interactions)
```

## 7. Políticas de acceso a datos

- La aplicación se conecta con un rol de BD propio (`sti_app`) con permisos DML sobre los cuatro esquemas; no usa el rol `postgres`.
- `learning.interactions`, `learning.student_state_history`, `ops.audit_logs`: la app solo tiene `INSERT` y `SELECT` (sin `UPDATE`/`DELETE`) — se aplica por `GRANT` en la migración de producción.
- Vista `research.v_participants` = `students` sin `user_id`, expone `participant_code`, `grade`, `group_code`, `institution_code`.
- Supabase: RLS no se usa para la app (acceso vía API con RBAC); si se habilita acceso directo desde Supabase Studio, activar RLS con políticas "deny all" para roles anónimos.

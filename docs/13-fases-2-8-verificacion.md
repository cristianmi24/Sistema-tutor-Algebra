# 13 — Fases 2 a 8: qué se construyó y cómo se verificó

## 1. Resumen por fase

| Fase | Backend | Frontend | Migración |
|------|---------|----------|-----------|
| **2 · Autenticación** | Argon2id y política de contraseñas; JWT de acceso 15 min; refresh opaco rotativo en cookie HttpOnly con detección de reuso; `require_roles` + alcance; bloqueo progresivo; recuperación con token hasheado y respuesta anti-enumeración; registro con consentimiento versionado; estado de participación `PENDING/ELIGIBLE/EXCLUDED` según la política de la institución; auditoría; rate limiting | Login, registro en 5 pasos (datos → privacidad → términos → consentimiento → cuenta), recuperación, restauración de sesión, renovación transparente ante 401, administración de usuarios, instituciones y auditoría | 0002 |
| **3 · Estudiante** | Tareas A–G, 7 tipos de ejemplos trabajados, banco de 14 andamiajes; sesiones; eventos append-only con secuencia por sesión; evaluador de dominio con parser seguro y patrones de error observables; respuestas verbales observadas, no calificadas; ayuda solicitada, aceptada, rechazada o reformulada con memoria | Pantalla de actividad C.29: patrón numérico y figural en SVG, espacio de resolución con pestañas de representación (número, tabla, gráfico, expresión, palabras), ejemplos con pasos ocultos y estrategias, panel de ayuda, autoexplicación | 0003 |
| **4 · Motor adaptativo** | `extract_evidence` (multiseñal, ventana 5), `infer` (naive Bayes discreto configurable), `evaluate_rules` (DSL legible con histéresis), `select_scaffold` (mínima explicitud + memoria), `ScaffoldDecision` explicable, perfil dinámico con historial, fading como evento, pausa tras intervención docente, tope de intervenciones y sugerencia de acompañamiento | Reglas SI/ENTONCES legibles, tablas bayesianas, catálogo | 0004 |
| **5 · Investigación** | Episodios automáticos y manuales, timeline por fases con actor explícito, comparación A/B sin conclusiones, memos Charmaz, entrevistas, participantes pseudonimizados, exportación CSV/JSON/JSONL/XLSX/PDF auditada | Participantes, sesiones con trayectoria, episodios, detalle con memos, comparación, entrevistas, exportación | 0005 |
| **6 · Docente** | Panorama de grupos, intervención separada (evento `TEACHER_INTERVENTION` propio), anotaciones solo para investigación, mensajes con marca de lectura | Panel por grupos, observación de sesión e intervención, mensajes del docente en la actividad del estudiante | — |
| **7 · IA opcional** | Proveedor abstracto (nulo, Anthropic, simulado), validadores pedagógico/seguridad/dominio, respaldo al banco, límite por sesión, trazabilidad `ai_interactions` | Trazas de IA y configuración; interpretación validada en el timeline | (tabla en 0004) |
| **8 · Seguridad y pruebas** | Disparadores append-only en BD, límite de tamaño de peticiones, auditoría de acceso a PII, anonimización y retención, secuencia atómica ante concurrencia, pruebas de seguridad | Pruebas de accesibilidad (axe-core), contraste AA de tokens, verificación de secretos en el bundle, carga diferida por rol, prueba de extremo a extremo en Chromium, CI | 0006 |

## 2. Casos de prueba C.43 ↔ pruebas automatizadas

| Caso | Escenario | Prueba |
|------|-----------|--------|
| 1 | Buen desempeño → no intervención | `test_tutor_engine.py::test_case_1_…`, `test_tutor_integration.py::test_adaptive_cycle_…` |
| 2 | Error aislado → observar | `test_case_2_isolated_error_is_observed_not_corrected` + integración |
| 3 | Errores persistentes → microayuda (con confirmación) | `test_case_3_persistent_errors_need_confirmation_then_microhelp` |
| 4 | Persistencia → orientación | `test_case_4_persistence_after_microhelp_escalates_to_orientation` |
| 5 | Estancamiento → cambio de representación | `test_case_5_…`, `test_stagnation_changes_representation_…` |
| 6 | Mejora → reducción de ayuda (fading registrado) | `test_case_6_…` + integración (evento de fading 1 → 0) |
| 7 | Autonomía → retirada de apoyo | `test_case_7_autonomy_withdraws_support` |
| 8 | Ayuda rechazada → no repetir | `test_case_8_…`, `test_help_request_accept_reject_and_reformulate` |
| 9 | Intervención docente → registro separado y pausa | `test_case_9_…`, `test_teacher.py::test_teacher_intervention_is_separate_…` |
| 10 | LLM produce ayuda inválida → bloquear | `test_ai.py::test_case_10_invalid_llm_output_is_blocked_and_bank_is_used` |
| 11 | Usuario sin permisos → rechazar | `test_auth.py::test_role_based_access_…`, `test_security.py::test_students_cannot_reach_each_others_data`, pruebas de alcance |
| 12 | Token expirado → renovar o reautenticar | `test_auth.py::test_expired_or_tampered_tokens_…`, `client.test.ts` (renovación ante 401) |
| extra | Solo tiempo largo no dispara ayuda | `test_case_11_slow_time_alone_never_triggers_help` |

## 3. Resultados de verificación

```text
backend   ruff · ruff format · mypy --strict (76 archivos)       OK
          alembic upgrade head · downgrade · check                OK (6 migraciones, sin deriva)
          pytest                                                  100 passed (PostgreSQL 16)
frontend  tsc --noEmit · eslint (type-checked strict)             OK
          vitest (incluye axe-core y contraste AA)                31 passed
          vite build + comprobación de secretos en el bundle      OK (chunk principal 66 kB)
e2e       e2e/smoke.mjs en Chromium real, dos ejecuciones         OK, 0 errores 500, 0 errores de JS
```

Flujo de extremo a extremo verificado: el estudiante inicia sesión y una sesión de trabajo, abre la actividad figural, recibe aviso ante respuesta vacía, registra respuestas sin corrección inmediata, recibe una pista (ofrecida por el tutor o solicitada), la rechaza, cambia a tabla y guarda su explicación; el docente observa la trayectoria e interviene; el estudiante ve el mensaje del docente distinto de las pistas; el investigador ve participantes sin nombres de usuario, abre un episodio con la interpretación del sistema rotulada y escribe un memo; la administración ve reglas legibles y auditoría.

### Hallazgos corregidos gracias a la verificación

- **Condición de carrera** en la secuencia de eventos: dos eventos simultáneos de la misma sesión obtenían el mismo número (error 500). Se reemplazó por un incremento atómico `UPDATE … RETURNING`; prueba `test_concurrent_events_get_unique_sequences` (falla sin la corrección).
- **Respuesta vacía ignorada en silencio**: ahora el formulario avisa «Escribe tu respuesta antes de registrarla».
- **CSP**: `frame-ancestors` no aplica en `<meta>`; debe enviarse como cabecera HTTP (el backend ya envía `X-Frame-Options: DENY`; el servidor estático debe añadir `Content-Security-Policy: frame-ancestors 'none'`).
- **Contraste**: dos pares de color no alcanzaban 4.5:1 (secundario claro y fondo primario oscuro); se ajustaron.
- **Límite de intentos** leía la configuración global en vez de la de la aplicación en ejecución; corregido y probado (429 al sexto intento con 5/min).

## 4. Checklist de seguridad C.44 (estado final)

| Pregunta | Estado | Evidencia |
|----------|--------|-----------|
| ¿Hay secretos en el frontend? | No | `npm run check:bundle`; solo `VITE_API_BASE_URL`, `VITE_APP_NAME` |
| ¿Contraseñas seguras? | Argon2id con rehash | `core/security.py`, pruebas de registro y login |
| ¿Autorización en backend? | Rol + alcance en cada ruta; 404 fuera de alcance | `test_security.py`, `test_student_flow.py::test_scope_…` |
| ¿Los JWT expiran? | 15 min; `iss`, `aud`, `exp`, firma verificados; `alg: none` rechazado | `test_unsigned_and_malformed_tokens_are_rejected` |
| ¿Refresh revocable? | Rotación, reuso ⇒ familia revocada, logout, cambio/restablecimiento de contraseña, deshabilitar, anonimizar | `test_refresh_rotates_and_detects_reuse` |
| ¿Protección contra abuso? | Rate limiting, bloqueo progresivo, límite de 1 MB, límite de llamadas a IA | `test_login_rate_limit`, `test_oversized_payload_is_rejected` |
| ¿Se validan entradas? | Pydantic `extra="forbid"`, parser de expresiones sin `eval`, Zod | `test_evaluation.py`, `test_register_requires_…` |
| ¿Acciones administrativas registradas? | Sí, incluidas reglas, catálogo, exportaciones y acceso a PII | `ops.audit_logs` |
| ¿PII separada de investigación? | Esquemas `identity` vs `learning`/`research`; exportaciones con código | `test_export_formats_are_pseudonymized_and_audited` |
| ¿Acceso limitado por rol? | Matriz RBAC + alcance | pruebas por rol |
| ¿Protección de menores? | Consentimiento multiparte, `PENDING_CONSENT`, exclusión de investigación, minimización, anonimización y retención | `test_guardian_consent_makes_student_eligible`, `test_retention_…` |
| ¿Auditable quién accedió a qué? | `request_id` extremo a extremo; auditoría append-only garantizada por la BD | `test_trace_tables_are_append_only_in_the_database` |

## 5. Cómo ejecutar todo

```bash
docker compose up -d postgres
cd backend && cp .env.example .env && uv venv && uv pip install -e ".[dev]"
.venv/bin/alembic upgrade head && .venv/bin/python -m app.cli seed-demo
.venv/bin/uvicorn app.main:app --port 8000
# otra terminal
cd frontend && npm ci && npm run build && npx vite preview --port 4173
# pruebas de extremo a extremo (Chromium instalado localmente)
E2E_BASE_URL=http://localhost:4173 CHROMIUM_PATH=/ruta/a/chrome npm run e2e
```

Cuentas de demostración (contraseña `Demo-STI-GA-2026!` o `SEED_DEMO_PASSWORD`): `admin@demo.edu`, `docente@demo.edu`, `investigadora@demo.edu`, `estudiante1`, `estudiante2`, `estudiante3`.

Retención: `python -m app.cli retention --dry-run` y luego sin `--dry-run` (programable con cron).

## 6. Límites conocidos

- El correo real (SMTP) no está implementado: el enlace de recuperación se registra en logs (`EMAIL_BACKEND=console`). Añadir un `EmailSender` SMTP es un cambio aislado en `identity/email.py`.
- La autorización del acudiente se registra como referencia declarada (formato institucional); la verificación de identidad del acudiente depende del protocolo de cada institución.
- Los parámetros bayesianos y las reglas son una propuesta inicial del equipo técnico: deben revisarse con el equipo pedagógico antes del trabajo de campo.
- El proveedor de Anthropic se probó con un cliente simulado; una prueba con clave real requiere `LLM_PROVIDER=anthropic` y `LLM_API_KEY`.
- La prueba de extremo a extremo no corre en CI (necesita Chromium); corre localmente con `npm run e2e`.

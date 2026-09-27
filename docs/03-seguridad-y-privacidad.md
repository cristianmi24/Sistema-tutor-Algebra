# 03 — Arquitectura de seguridad y privacidad

## 1. Autenticación

### 1.1 Contraseñas
- Hash con **Argon2id** (`argon2-cffi`), parámetros iniciales: `time_cost=3`, `memory_cost=64 MiB`, `parallelism=2`, salt aleatorio por contraseña. Parámetros configurables y rehash automático cuando cambian.
- Política mínima: 10 caracteres, verificación contra lista de contraseñas comprometidas comunes (local). Sin límites máximos arbitrarios (hasta 128).
- Nunca se registran contraseñas en logs ni se devuelven en respuestas.

### 1.2 Tokens
| Token | Formato | Vida | Almacenamiento | Contenido |
|-------|---------|------|----------------|-----------|
| Access | JWT firmado (HS256 con secreto ≥ 32 bytes; migrable a RS256/EdDSA) | 15 min | Memoria del frontend (nunca `localStorage`) | `sub` (user_id), `role`, `sid` (sesión de auth), `jti`, `exp`, `iat`, `iss`, `aud` |
| Refresh | Cadena aleatoria opaca 256 bits | 14 días (configurable) | Cookie `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth` | Solo hash SHA-256 en `identity.refresh_tokens` |

- **Rotación**: cada refresh emite un nuevo refresh token y marca el anterior como `rotated_to`. Reuso de un token ya rotado ⇒ **revocación de toda la familia** (detección de robo).
- **Revocación**: logout revoca la familia; cambio de contraseña revoca todas las familias del usuario; ADMIN puede revocar.
- Claims verificados siempre: firma, `exp`, `iss`, `aud`, `nbf`.

### 1.3 Recuperación de contraseña
```text
POST /auth/forgot-password (email)
   → respuesta idéntica exista o no el correo (anti-enumeración)
   → si existe: token aleatorio 256 bits, se guarda SHA-256 + expiración 30 min
   → correo con enlace (nunca la contraseña)
POST /auth/reset-password (token, new_password)
   → verificar hash, expiración, no usado
   → actualizar hash Argon2id, marcar token usado, revocar refresh tokens
   → auditar PASSWORD_RESET
```
Habilitable por rol mediante configuración (`PASSWORD_RESET_ROLES`).

### 1.4 Protección contra abuso
- Rate limiting (slowapi) en `/auth/login`, `/auth/register`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/refresh` (por IP y por identificador).
- Bloqueo progresivo de cuenta tras N intentos fallidos (registro en `audit_logs`).
- Respuestas de error homogéneas ("credenciales inválidas") para evitar enumeración.
- Tiempo constante en comparación de hashes.

## 2. Autorización (RBAC)

Toda ruta declara sus roles permitidos con una dependencia `require_roles(...)`. El frontend nunca es fuente de verdad.

| Recurso | STUDENT | TEACHER | RESEARCHER | ADMIN |
|---------|---------|---------|------------|-------|
| Propias sesiones/actividades | CRUD propio | R (grupos asignados) | R (pseudonimizado) | R |
| Ayuda / andamiaje | solicitar, aceptar, rechazar | R | R | R + configurar |
| Intervención docente | recibir | crear (grupos asignados) | R | R |
| Episodios | — | R (grupos asignados) | R + comparar | R |
| Memos / entrevistas | — | — | CRUD propio | R |
| Exportación | — | limitada a grupos | pseudonimizada | completa |
| Datos personales (nombre, correo) | propio | mínimo de grupos | **nunca** | gestión |
| Usuarios, instituciones, catálogos, reglas | — | — | — | CRUD |
| Auditoría | — | — | — | R |

Reglas transversales:
- Alcance (**scope**) además del rol: un docente solo ve grupos asignados; un estudiante solo sus datos.
- El módulo de investigación consume una vista que **excluye** columnas de identidad y expone `participant_code`.

## 3. Consentimiento y menores

```text
REGISTRO → DATOS MÍNIMOS → POLÍTICA DE PRIVACIDAD → TÉRMINOS → CONSENTIMIENTO
        → REGISTRO DEL CONSENTIMIENTO (versión, fecha, tipo, parte) → CUENTA
```

- Tabla `identity.consents` registra `privacy_policy_version`, `terms_version`, `accepted_at`, `consent_status`, `consent_party` (`STUDENT`, `GUARDIAN`, `INSTITUTION`, `RESEARCHER`), `evidence` (método, IP truncada, user agent) y `revoked_at`.
- El **estado efectivo** de participación en investigación se calcula por protocolo: p. ej., `STUDENT + GUARDIAN` requeridos para menores. Configurable por institución (`consent_policy`).
- Un clic del estudiante **no** se asume como consentimiento legal suficiente. Sin consentimiento efectivo, la cuenta puede existir en modo `PENDING_CONSENT`: puede iniciar sesión y ver la información, pero sus interacciones **no** entran a la vista de investigación.
- Textos de política y términos versionados en BD y mostrados en la interfaz con lenguaje claro para adolescentes: qué se recoge, para qué, cuánto tiempo, quién accede, derechos, cómo solicitar eliminación.
- Este diseño es técnico; el protocolo legal concreto (Colombia: Ley 1581 de 2012 y decretos reglamentarios; comité de ética institucional) lo define la institución. No se presenta como asesoría jurídica.

## 4. Protección de datos

| Principio | Implementación |
|-----------|----------------|
| Minimización | Estudiante: correo institucional o usuario, grado, grupo, año de nacimiento (no fecha completa). Sin dirección, teléfono, documento. |
| Separación | Esquema `identity` (PII) separado de `learning`/`research` (pseudonimizado por `participant_code` + `student_id` UUID). Las tablas de investigación no tienen FK a `users`, sólo a `students.id` (UUID sin significado). |
| Pseudonimización | `participant_code` (`STU-001`) generado por institución; los módulos de investigación no consultan `identity.users`. |
| Retención | `retention_policy` por institución; job de anonimización irreversible (borra `identity`, conserva `learning` con código). |
| Acceso | RBAC + scope; investigador nunca ve PII. |
| Auditoría | `ops.audit_logs` append-only: actor, acción, recurso, resultado, IP truncada, `request_id`. |
| Secretos | Solo variables de entorno; `.env` ignorado por git; sin secretos en frontend (`VITE_*` es público). |
| Transporte | HTTPS obligatorio en producción; HSTS; cookies `Secure`. |

## 5. Seguridad de la aplicación web

- CORS: lista explícita de orígenes (`CORS_ORIGINS`), credenciales permitidas solo para esos orígenes.
- Cabeceras: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, `Content-Security-Policy` en frontend.
- Validación estricta de payloads con Pydantic (`extra="forbid"` en entradas).
- Manejo de errores: nunca stack traces al cliente; `request_id` para correlación.
- Paginación y límites de tamaño en listados y exportaciones.
- Dependencias fijadas y auditadas (`uv lock`, `npm audit`).
- Sin SQL manual con interpolación; SQLAlchemy parametrizado.

## 6. Checklist por fase (C.44)

```text
[ ] ¿Hay secretos en el frontend?                    → No: solo VITE_API_BASE_URL y flags públicos
[ ] ¿Se almacenan contraseñas de forma segura?       → Argon2id
[ ] ¿Se verifica autorización en backend?            → require_roles + scope en cada endpoint
[ ] ¿Los JWT expiran?                                → 15 min
[ ] ¿Los refresh tokens pueden revocarse?            → Sí, por familia y por usuario
[ ] ¿Hay protección contra abuso?                    → Rate limiting + bloqueo progresivo
[ ] ¿Se validan entradas?                            → Pydantic extra=forbid, Zod en frontend
[ ] ¿Se registran acciones administrativas?          → ops.audit_logs
[ ] ¿Se separan datos personales de investigación?   → Esquemas identity vs learning/research
[ ] ¿Se limita el acceso por rol?                    → Matriz RBAC
[ ] ¿Se protege la información de menores?           → Consentimiento multi-parte, minimización
[ ] ¿Se puede auditar quién accedió a qué?           → audit_logs incluye lecturas sensibles (export, PII)
```

## 7. Modelo de amenazas (resumen)

| Amenaza | Mitigación |
|---------|------------|
| Robo de access token (XSS) | Vida corta; CSP; sin `localStorage`; sanitización de contenido |
| Robo de refresh token | Cookie HttpOnly + rotación + detección de reuso ⇒ revocación de familia |
| Fuerza bruta / credential stuffing | Rate limiting, bloqueo progresivo, Argon2id |
| Enumeración de usuarios | Respuestas y tiempos homogéneos |
| Escalada de privilegios | RBAC en backend, scope por grupo/institución, tests de autorización |
| Fuga de PII a investigación | Esquemas separados, vistas pseudonimizadas, auditoría de lecturas |
| Inyección de prompt hacia el LLM | LLM sin autoridad pedagógica; validadores; salidas nunca ejecutadas |
| Manipulación de eventos | Tablas append-only, sin UPDATE/DELETE desde la app |
| Exposición de secretos | `.env` ignorado, revisión de CI, rotación de claves |

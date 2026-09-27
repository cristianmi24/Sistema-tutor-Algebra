# 05 — Arquitectura adaptativa (Sistema Tutor Inteligente)

## 1. Ciclo

```text
OBSERVAR → INTERPRETAR → DECIDIR → ADAPTAR → RECORDAR → RETIRAR AYUDA CUANDO SEA APROPIADO
```

```text
INTERACCIONES (eventos append-only)
      ↓  EvidenceExtractor (ventana 3–5 eventos, configurable)
EVIDENCIAS (InteractionEvidence)
      ↓  BayesianInferenceEngine (priors + CPTs configurables)
ESTIMACIÓN PROBABILÍSTICA  P(estado | evidencias)
      ↓  StudentStateEngine (estado previo + posterior + histéresis)
PERFIL DINÁMICO (StudentCognitiveInteractionState)
      ↓  TutorDecisionEngine (reglas legibles SI…ENTONCES, prioridad, versión)
DECISIÓN (estado actual, nivel de intervención, razón)
      ↓  ScaffoldingEngine (banco + InterventionMemory + FadingPolicy)
ANDAMIAJE concreto o NIVEL 0
      ↓
RESPUESTA DEL ESTUDIANTE → RESULTADO → MEMORIA → FADING / MANTENER / AUMENTAR
```

Todo el motor vive en `backend/app/modules/tutor/` como funciones puras: reciben datos ya cargados y devuelven estructuras Pydantic. Nunca acceden a BD ni red. Esto garantiza determinismo, tests unitarios y auditabilidad.

## 2. Evidencias (multiseñal)

| Evidencia | Fuente | Discretización (para Bayes) |
|-----------|--------|-----------------------------|
| `response_time_ms` (relativo a la mediana de la tarea) | timestamps de eventos | `FAST` (< 0.4×), `TYPICAL`, `SLOW` (> 2×) |
| `recent_accuracy` (ventana) | `evaluation.correct` | `LOW` (< 0.34), `MID`, `HIGH` (> 0.66) |
| `attempt_count` (misma tarea) | `STUDENT_RESPONSE`, `STUDENT_REATTEMPT` | `1`, `2–3`, `4+` |
| `repetition_count` (misma respuesta repetida) | comparación de contenido | `0`, `1`, `2+` |
| `click_pattern` | `client_meta` | `CALM`, `ERRATIC` (clics/min > umbral), `IDLE` |
| `error_pattern` | evaluador de dominio | `NONE`, `VARIED`, `PERSISTENT` (mismo patrón ≥ 2) |
| `answer_changes` | `STUDENT_EDITED_RESPONSE` | `0`, `1–2`, `3+` |
| `help_requests` (ventana) | `HELP_REQUESTED` | `0`, `1`, `2+` |
| `prior_help_result` | `scaffold_events.result` | `NONE`, `IMPROVED`, `PERSISTED`, `REJECTED` |
| `representation_switches` | `REPRESENTATION_CHANGED` | `0`, `1`, `2+` |
| `difficulty` | tarea | `1–5` |

**Regla de oro:** ninguna evidencia aislada determina un estado. El tiempo por sí solo nunca dispara intervención.

## 3. Estados

Interpretaciones operativas del sistema (no categorías teóricas; nunca mostradas al estudiante con etiquetas negativas):

| Estado | Lectura operativa | Etiqueta visible al estudiante |
|--------|-------------------|--------------------------------|
| `NORMAL` | Trabajo estable sin señales fuertes | "En marcha" |
| `EXPLORATION` | Cambia representaciones, prueba, sin errores persistentes | "Explorando" |
| `DIFFICULTY` | Errores recientes crecientes con intentos genuinos | "Pensando" |
| `UNCERTAINTY` | Muchos cambios de respuesta, tiempos largos, sin patrón de error fijo | "Revisando" |
| `IMPULSIVITY` | Respuestas muy rápidas, clics erráticos, errores variados | "Rápido" |
| `STAGNATION` | Mismo error persistente, repeticiones, sin progreso tras ayuda | "Buscando otro camino" |
| `RECOVERY` | Mejora tras intervención, errores bajan, sigue sin pedir ayuda | "Avanzando" |
| `AUTONOMY` | Buen desempeño estable sin ayuda | "Con autonomía" |

Transiciones con **histéresis**: un estado requiere evidencia en ≥ 2 eventos consecutivos de la ventana para cambiar, salvo `IMPULSIVITY` que puede detectarse en 3 eventos rápidos seguidos.

## 4. Inferencia bayesiana (auxiliar)

Modelo **naive Bayes discreto** por estado, con priors y verosimilitudes en `learning.bayesian_config` (versionado):

```text
P(S | e1..en) ∝ P(S) · Π P(ei | S)
```

- `S ∈ {DIFFICULTY, UNCERTAINTY, IMPULSIVITY, STAGNATION, AUTONOMY}` + variable derivada `NEED_SUPPORT`.
- Priors iniciales: uniformes ajustados por dificultad de la tarea (documentados en `bayesian_config.priors`).
- Verosimilitudes iniciales definidas por el equipo pedagógico (tabla por evidencia discretizada), con suavizado de Laplace para evitar ceros.
- El posterior alimenta el perfil (`student_state.posterior`) y **solo** actúa como condición dentro de las reglas (p. ej., `P(STAGNATION) > 0.6`). Nunca decide por sí mismo.
- No hay aprendizaje de parámetros, no hay entrenamiento, no hay redes neuronales. Los parámetros cambian por decisión humana y quedan versionados.

## 5. Reglas pedagógicas (DSL legible)

Las reglas viven en `learning.tutor_rules` con un DSL JSON legible por desarrolladores y expertos:

```json
{
  "code": "R-STAGNATION-REPR",
  "name": "Estancamiento → cambio de representación",
  "priority": 40,
  "when": {
    "all": [
      {"evidence": "error_pattern", "is": "PERSISTENT"},
      {"evidence": "attempt_count", "gte": 3},
      {"trend": "recent_errors", "is": "INCREASING"},
      {"posterior": "STAGNATION", "gt": 0.6}
    ]
  },
  "then": {"state": "STAGNATION", "intervention": "REPRESENTATION_CHANGE", "level": 4}
}
```

```json
{
  "code": "R-RECOVERY-FADE",
  "name": "Mejora tras intervención → reducir apoyo",
  "priority": 30,
  "when": {"all": [
      {"evidence": "prior_help_result", "is": "IMPROVED"},
      {"trend": "recent_errors", "is": "DECREASING"},
      {"evidence": "help_requests", "eq": 0}
  ]},
  "then": {"state": "RECOVERY", "fading": "REDUCE"}
}
```

```json
{
  "code": "R-AUTONOMY-ZERO",
  "name": "Buen desempeño estable sin ayuda → autonomía",
  "priority": 20,
  "when": {"all": [
      {"evidence": "recent_accuracy", "is": "HIGH"},
      {"evidence": "answer_changes", "lte": 1},
      {"evidence": "help_requests", "eq": 0},
      {"stable_for_events": 4}
  ]},
  "then": {"state": "AUTONOMY", "level": 0}
}
```

Evaluación: se ordenan por `priority` descendente; la primera regla cuyas condiciones se cumplen fija estado y acción; las demás quedan registradas como "candidatas" en la decisión para auditoría. Regla por defecto: `NORMAL`, nivel 0.

## 6. Niveles de intervención y banco de andamiajes

| Nivel | Nombre | Tipos de andamiaje del banco |
|-------|--------|------------------------------|
| 0 | No intervención | — (observar) |
| 1 | Microayuda | `FOCUSING` ("Mira cómo cambia la cantidad entre la figura 2 y la 3"), `METACOGNITIVE` ("¿Qué sabes ya y qué te falta?") |
| 2 | Orientación | `GUIDING_QUESTION` ("¿Cómo podrías relacionar el número de la figura con la cantidad total?"), `SELF_EXPLANATION` |
| 3 | Andamiaje / división | `TASK_DIVISION` (subtareas), `HINT` (pista parcial), `ERROR_REFLECTION` |
| 4 | Cambio de representación | `REPRESENTATION_CHANGE` (de figural a tabla, de tabla a gráfico), `STRATEGY_COMPARISON` |
| 5 | Recuperación | `RECOVERY` (ejemplo trabajado parcial + reconstrucción), nunca la respuesta final |

Selección: mínimo nivel que la regla permite; dentro del nivel, `ScaffoldingEngine` filtra por `task_type`/`skill`, excluye andamiajes rechazados o ineficaces recientemente (memoria), y prefiere tipos no usados en el episodio actual.

## 7. Matriz pedagógica

| Evidencia (combinada) | Estado posible | Intervención | Fading |
|-----------------------|----------------|--------------|--------|
| Precisión alta, tiempos típicos, sin ayuda, estable ≥ 4 eventos | AUTONOMY | Nivel 0 | Retirar apoyo; registrar `REDUCE` con razón |
| Cambios de representación, sin error persistente, precisión media | EXPLORATION | Nivel 0 (observar) | Mantener |
| 1 error aislado, sin repetición | NORMAL | Nivel 0 (esperar siguiente evento) | Mantener |
| Errores crecientes, 2–3 intentos, patrón variado | DIFFICULTY | Nivel 1 microayuda (FOCUSING) | Mantener |
| DIFFICULTY persiste tras microayuda, mismo patrón | DIFFICULTY (alta) | Nivel 2 orientación (GUIDING_QUESTION) | Aumentar 1 |
| 3+ cambios de respuesta, tiempos largos, sin patrón fijo, P(UNCERTAINTY) alta | UNCERTAINTY | Nivel 2 SELF_EXPLANATION / METACOGNITIVE | Mantener |
| Tiempos muy rápidos ×3, clics erráticos, errores variados | IMPULSIVITY | Nivel 1 METACOGNITIVE ("antes de responder, describe el patrón") | Mantener |
| Error persistente ≥ 3 intentos, repeticiones, P(STAGNATION) > 0.6, ayuda previa PERSISTED | STAGNATION | Nivel 4 REPRESENTATION_CHANGE (o Nivel 3 TASK_DIVISION si aún no se usó) | Aumentar |
| Estancamiento tras Nivel 4 sin mejora | STAGNATION (crítico) | Nivel 5 RECOVERY (ejemplo parcial) | Aumentar; abrir posibilidad de intervención docente |
| Mejora tras ayuda, errores bajan, no pide ayuda | RECOVERY | Nivel bajado en 1 | `REDUCE` |
| Ayuda rechazada | (se conserva) | Alternativa de distinto tipo o Nivel 0 si el estudiante progresa | Mantener; nunca repetir idéntica |
| Intervención docente registrada | (se conserva) | Sistema pausa intervenciones N eventos | Mantener |

## 8. Fading

Cada cambio de nivel produce un `scaffold_event` con:

```text
previous_help_level, current_help_level, reason_for_change (regla + evidencias), student_response, result
```

Política inicial: reducir un nivel por vez; volver a subir solo con evidencia nueva (no por tiempo). **Nunca** se infiere que `menos ayuda = aprendizaje`: el fading es un evento observable para el investigador, no un indicador de logro.

## 9. Memoria de intervenciones

`InterventionMemory` consulta `scaffold_events` del estudiante (ventana por sesión y por tarea):

- Ayuda `REJECTED` ⇒ ese `scaffold_id` queda excluido para la tarea; se prefiere otro `scaffold_type`.
- Ayuda `PERSISTED` dos veces ⇒ subir nivel o cambiar tipo.
- Ayuda `IMPROVED` ⇒ candidata a fading.
- Límite de intervenciones por tarea (configurable, p. ej. 4) ⇒ sugerir intervención docente en el dashboard, sin bloquear al estudiante.

## 10. Explicabilidad: `ScaffoldDecision`

```python
class ScaffoldDecision(BaseModel):
    need_detected: str                 # p.ej. "STAGNATION"
    evidence: list[str]                # ["error_pattern=PERSISTENT", "attempt_count=4", "P(STAGNATION)=0.71"]
    candidate_supports: list[str]      # códigos de andamiajes candidatos
    selected_support: str | None       # código elegido o None (nivel 0)
    explicitness_level: int            # 0–5
    confidence: float                  # 0–1, del posterior o de la regla
    reason: str                        # texto legible: regla + por qué este andamiaje
    validation_status: Literal["NOT_REQUIRED", "APPROVED", "REJECTED"]  # validación IA si aplicó
    rule_code: str | None
    previous_help_level: int
    fading_action: Literal["KEEP", "REDUCE", "INCREASE"]
```

Responde a: ¿qué observó? (`evidence`), ¿qué estado estimó? (`need_detected`, `confidence`), ¿qué regla activó? (`rule_code`), ¿por qué intervino? (`reason`), ¿qué intervención? (`selected_support`, `explicitness_level`), ¿qué ocurrió después? (`scaffold_events.result`), ¿qué hará ahora? (`fading_action`).

## 11. Casos de prueba del motor (C.43)

| Caso | Escenario | Esperado |
|------|-----------|----------|
| 1 | 5 respuestas correctas, sin ayuda | NORMAL→AUTONOMY, nivel 0 |
| 2 | 1 error aislado tras aciertos | NORMAL, nivel 0 (observar) |
| 3 | 2 errores seguidos, patrón variado | DIFFICULTY, nivel 1 |
| 4 | Persiste tras microayuda | DIFFICULTY, nivel 2 |
| 5 | Mismo error ×3, P(STAGNATION) alta | STAGNATION, nivel 4 REPRESENTATION_CHANGE |
| 6 | Mejora tras ayuda | RECOVERY, `REDUCE` |
| 7 | Estable y correcto ×4 | AUTONOMY, nivel 0 |
| 8 | Ayuda rechazada | siguiente ayuda de tipo distinto; misma nunca |
| 9 | TEACHER_INTERVENTION | evento separado; el sistema pausa |
| 10 | LLM devuelve la fórmula final | validador de dominio la bloquea; fallback al banco |
| 11 | Tiempo largo sin otras señales | nivel 0 (no intervenir por una sola variable) |

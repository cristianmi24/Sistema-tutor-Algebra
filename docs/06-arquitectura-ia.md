# 06 — Arquitectura de IA opcional (LLM)

## 1. Principio

El LLM es una **capa auxiliar, opcional y subordinada**. La plataforma funciona completamente con `LLM_ENABLED=false` (Fases 1–6 no lo usan). El LLM **nunca** controla el comportamiento pedagógico.

```text
ESTUDIANTE → INTERFAZ → MOTOR DE INTERACCIÓN → ANÁLISIS → MOTOR PEDAGÓGICO → BANCO DE ANDAMIAJES
                                                                                   ↓
                                                                    LLM OPCIONAL → VALIDADOR → INTERVENCIÓN
```

## 2. Qué PUEDE hacer

| Propósito (`ai_interactions.purpose`) | Descripción | Salida esperada |
|---------------------------------------|-------------|-----------------|
| `INTERPRET_OPEN_ANSWER` | Clasificar una explicación verbal del estudiante según dimensiones observables (¿menciona relación recursiva? ¿funcional? ¿coordina cantidades?) | JSON con etiquetas de un vocabulario cerrado + confianza |
| `ADAPT_LANGUAGE` | Reformular un andamiaje **del banco** al vocabulario del estudiante sin alterar su intención pedagógica | Texto corto; se compara semánticamente con el original |
| `FORMULATE_QUESTION` | Proponer una pregunta orientadora a partir de una **plantilla** del banco | Texto corto que debe terminar en `?` y no contener la solución |
| `ANALYZE_EXPLANATION` | Señalar si la autoexplicación es consistente con la respuesta dada | JSON `{consistent: bool, notes[]}` |
| `DETECT_CONTRADICTION` | Detectar contradicción entre regla verbal y tabla/expresión | JSON |

Toda salida es una **propuesta**. La decisión (intervenir, nivel, tipo) ya fue tomada por el motor de reglas.

## 3. Qué NO puede hacer

- Decidir si intervenir, cuándo o con qué nivel.
- Generar ayudas fuera de las plantillas del banco.
- Entregar la respuesta, la fórmula o la generalización final.
- Evaluar como "correcto/incorrecto" de forma vinculante (la evaluación de dominio es determinista).
- Etiquetar al estudiante ("tiene dificultad", "es impulsivo") ni producir categorías teóricas.
- Acceder a datos de identidad (recibe solo `participant_code` y contenido de la tarea).
- Ejecutar acciones (sin herramientas/funciones).

## 4. Cadena de validación

```text
LLM ──► Validador pedagógico ──► Validador de seguridad ──► Validador de dominio ──► APROBAR / RECHAZAR
```

| Validador | Verifica | Rechaza si |
|-----------|----------|-----------|
| Pedagógico | Intención del andamiaje preservada; nivel de explicitud no aumentado; formato de pregunta cuando aplica | La reformulación contiene pasos de solución no presentes en el original; cambia de tipo |
| Seguridad | Sin contenido inapropiado; sin PII; longitud; idioma; sin instrucciones al usuario ajenas a la tarea | Cualquier hallazgo |
| Dominio | No contiene la expresión objetivo ni valores de la generalización (`3n+2`, término n-ésimo pedido); coherencia matemática con la tarea | Contiene la solución o un enunciado matemáticamente falso |

Si cualquier validador rechaza ⇒ se usa el andamiaje original del banco (**fallback**) y se registra `validation.approved=false` con razones. Nunca se muestra una salida no validada.

## 5. Trazabilidad

Cada llamada crea un registro en `learning.ai_interactions`: proveedor, modelo, propósito, prompt (con hash), salida cruda, resultado de cada validador, latencia, y el `interaction_id` que la motivó. El investigador puede ver qué propuso la IA, qué se aprobó y qué recibió el estudiante (`scaffold_events.source = AI_VALIDATED`).

## 6. Capa de abstracción

```python
class LLMProvider(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

# Implementaciones: NullProvider (por defecto), AnthropicProvider, OpenAICompatibleProvider (configurable)
```

Configuración: `LLM_ENABLED`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY` (solo backend), `LLM_TIMEOUT_MS`, `LLM_MAX_CALLS_PER_SESSION`. Sin clave o con proveedor `null` la plataforma opera sin IA sin cambios funcionales.

## 7. Criterio de adopción (Fase 7)

Se integra solo si un piloto demuestra utilidad verificable: p. ej., la interpretación de respuestas abiertas coincide con codificación humana en ≥ 80 % de una muestra, y la reformulación de lenguaje no altera la intención en la revisión de expertos. Si no, permanece desactivado.

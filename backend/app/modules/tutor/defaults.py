"""Configuración pedagógica por defecto: reglas legibles y parámetros bayesianos.

Se siembra en ``learning.tutor_rules`` y ``learning.bayesian_config`` (versionada) y sirve como
respaldo si la base de datos no tiene configuración activa. Cambiarla es una decisión humana.
"""

from __future__ import annotations

from typing import Any

# Prioridad: mayor = se evalúa primero. La primera regla que se cumple decide.
DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "code": "R-TEACHER-PAUSE",
        "name": "Intervención docente reciente → el sistema pausa",
        "description": "Tras una intervención del docente, el sistema no interviene durante algunos eventos: la voz del docente prevalece y no se mezcla con la del tutor.",
        "priority": 100,
        "when": {
            "all": [
                {"evidence": "teacher_intervened_recently", "is": True},
                {"evidence": "help_requested_now", "is": False},
            ]
        },
        "then": {"state": "NORMAL", "level": 0, "fading": "KEEP"},
    },
    {
        "code": "R-HELP-REQUESTED",
        "name": "El estudiante pide ayuda → orientación mínima",
        "description": "La solicitud explícita se atiende siempre con la menor ayuda útil; el nivel sube solo si ya hubo ayudas que no funcionaron.",
        "priority": 90,
        "when": {
            "all": [
                {"evidence": "help_requested_now", "is": True},
                {"evidence": "prior_help_result", "in": ["NONE", "IMPROVED", "UNKNOWN", "REJECTED"]},
            ]
        },
        "then": {"state": "DIFFICULTY", "intervention": "GUIDING_QUESTION", "level": 2, "fading": "KEEP"},
    },
    {
        "code": "R-HELP-REQUESTED-AGAIN",
        "name": "Pide ayuda y la anterior no funcionó → subir un nivel",
        "priority": 89,
        "when": {
            "all": [
                {"evidence": "help_requested_now", "is": True},
                {"evidence": "prior_help_result", "in": ["PERSISTED", "PENDING"]},
            ]
        },
        "then": {"state": "DIFFICULTY", "intervention": "HINT", "level": 3, "fading": "INCREASE"},
    },
    {
        "code": "R-STAGNATION-RECOVERY",
        "name": "Estancamiento tras cambio de representación → recuperación",
        "description": "Mismo error persistente, muchos intentos y ayudas de nivel 4 sin mejora: se ofrece reconstruir desde un ejemplo parcial, nunca la respuesta.",
        "priority": 60,
        "when": {
            "all": [
                {"evidence": "error_pattern", "is": "PERSISTENT"},
                {"evidence": "attempt_count", "gte": 5},
                {"evidence": "interventions_in_task", "gte": 3},
                {"evidence": "prior_help_result", "is": "PERSISTED"},
                {"posterior": "STAGNATION", "gt": 0.5},
            ]
        },
        "then": {"state": "STAGNATION", "intervention": "RECOVERY", "level": 5, "fading": "INCREASE"},
    },
    {
        "code": "R-STAGNATION-REPR",
        "name": "Estancamiento → cambio de representación",
        "description": "Si el mismo patrón de error persiste tras al menos dos ayudas de menor nivel que no funcionaron, los intentos aumentan y la probabilidad de estancamiento es alta, se propone mirar el problema con otra representación.",
        "priority": 50,
        "when": {
            "all": [
                {"evidence": "error_pattern", "is": "PERSISTENT"},
                {"evidence": "attempt_count", "gte": 4},
                {"evidence": "interventions_in_task", "gte": 2},
                {"evidence": "prior_help_result", "in": ["PERSISTED", "REJECTED"]},
                {"evidence": "recent_errors_trend", "in": ["INCREASING", "STABLE"]},
                {"posterior": "STAGNATION", "gt": 0.45},
            ]
        },
        "then": {"state": "STAGNATION", "intervention": "REPRESENTATION_CHANGE", "level": 4, "fading": "INCREASE"},
    },
    {
        "code": "R-DIFFICULTY-ORIENT",
        "name": "Dificultad persiste tras microayuda → orientación",
        "priority": 45,
        "when": {
            "all": [
                {"evidence": "accuracy_band", "is": "LOW"},
                {"evidence": "attempt_count", "gte": 3},
                {"evidence": "prior_help_result", "in": ["PERSISTED", "PENDING"]},
                {"evidence": "interventions_in_task", "gte": 1},
            ]
        },
        "then": {"state": "DIFFICULTY", "intervention": "GUIDING_QUESTION", "level": 2, "fading": "INCREASE"},
    },
    {
        "code": "R-IMPULSIVITY-META",
        "name": "Respuestas muy rápidas con errores variados → apoyo metacognitivo",
        "description": "Tres respuestas seguidas muy rápidas con errores de distinto tipo (o clics erráticos): se invita a describir el patrón antes de responder.",
        "priority": 42,
        "when": {
            "all": [
                {"evidence": "fast_streak", "gte": 3},
                {"evidence": "accuracy_band", "in": ["LOW", "MID"]},
                {
                    "any": [
                        {"evidence": "error_pattern", "is": "VARIED"},
                        {"evidence": "click_pattern", "is": "ERRATIC"},
                    ]
                },
            ]
        },
        "then": {"state": "IMPULSIVITY", "intervention": "METACOGNITIVE", "level": 1, "fading": "KEEP"},
    },
    {
        "code": "R-UNCERTAINTY-SELFEXPL",
        "name": "Muchos cambios de respuesta y tiempos largos → autoexplicación",
        "priority": 40,
        "when": {
            "all": [
                {"evidence": "answer_changes", "gte": 3},
                {"evidence": "response_time_band", "in": ["SLOW", "TYPICAL"]},
                {"evidence": "error_pattern", "in": ["NONE", "VARIED"]},
                {"posterior": "UNCERTAINTY", "gt": 0.35},
            ]
        },
        "then": {"state": "UNCERTAINTY", "intervention": "SELF_EXPLANATION", "level": 2, "fading": "KEEP"},
    },
    {
        "code": "R-DIFFICULTY-MICRO",
        "name": "Errores recientes crecientes con intentos genuinos → microayuda",
        "description": "Requiere al menos dos respuestas incorrectas y confirmación en dos evaluaciones: un error aislado nunca dispara ayuda.",
        "priority": 35,
        "min_consecutive": 2,
        "when": {
            "all": [
                {"evidence": "accuracy_band", "is": "LOW"},
                {"evidence": "attempt_count", "gte": 2},
                {"evidence": "responses_in_window", "gte": 2},
                {"evidence": "interventions_in_task", "eq": 0},
                {"need_support": {"gt": 0.5}},
            ]
        },
        "then": {"state": "DIFFICULTY", "intervention": "FOCUSING", "level": 1, "fading": "INCREASE"},
    },
    {
        "code": "R-RECOVERY-FADE",
        "name": "Mejora tras intervención → reducir apoyo",
        "description": "Si mejora después de una ayuda, los errores disminuyen y no pide ayuda, el sistema retira un nivel de apoyo. El fading es un evento observable, no una prueba de aprendizaje.",
        "priority": 30,
        "when": {
            "all": [
                {"evidence": "prior_help_result", "is": "IMPROVED"},
                {"evidence": "recent_errors_trend", "in": ["DECREASING", "STABLE"]},
                {"evidence": "help_requested_now", "is": False},
                {"evidence": "stable_correct_streak", "gte": 1},
            ]
        },
        "then": {"state": "RECOVERY", "level": 0, "fading": "REDUCE"},
    },
    {
        "code": "R-AUTONOMY-ZERO",
        "name": "Buen desempeño estable sin ayuda → autonomía",
        "priority": 20,
        "when": {
            "all": [
                {"evidence": "accuracy_band", "is": "HIGH"},
                {"evidence": "stable_correct_streak", "gte": 3},
                {"evidence": "answer_changes", "lte": 1},
                {"evidence": "help_requests", "eq": 0},
            ]
        },
        "then": {"state": "AUTONOMY", "level": 0, "fading": "REDUCE"},
    },
    {
        "code": "R-EXPLORATION",
        "name": "Cambia de representación sin errores persistentes → exploración",
        "priority": 10,
        "when": {
            "all": [
                {"evidence": "representation_switches", "gte": 1},
                {"evidence": "error_pattern", "in": ["NONE", "VARIED"]},
            ]
        },
        "then": {"state": "EXPLORATION", "level": 0, "fading": "KEEP"},
    },
]

# Verosimilitudes P(valor | estado) definidas por el equipo pedagógico. Cada fila suma 1.
# Diseño: los valores de "ausencia" (0 cambios, 0 ayudas, sin repetición, ritmo típico) son poco
# discriminativos; la evidencia fuerte proviene de precisión, patrón de error, intentos, ritmo rápido,
# muchos cambios de respuesta, repeticiones y el resultado de la ayuda anterior.
DEFAULT_BAYES_CONFIG: dict[str, Any] = {
    "name": "default",
    "version": 1,
    "smoothing": 0.05,
    "priors": {
        "NORMAL": 0.30,
        "DIFFICULTY": 0.18,
        "UNCERTAINTY": 0.12,
        "IMPULSIVITY": 0.10,
        "STAGNATION": 0.15,
        "AUTONOMY": 0.15,
    },
    "likelihoods": {
        "accuracy_band": {
            "NORMAL": {"LOW": 0.15, "MID": 0.50, "HIGH": 0.35},
            "DIFFICULTY": {"LOW": 0.65, "MID": 0.30, "HIGH": 0.05},
            "UNCERTAINTY": {"LOW": 0.45, "MID": 0.40, "HIGH": 0.15},
            "IMPULSIVITY": {"LOW": 0.55, "MID": 0.35, "HIGH": 0.10},
            "STAGNATION": {"LOW": 0.80, "MID": 0.17, "HIGH": 0.03},
            "AUTONOMY": {"LOW": 0.03, "MID": 0.17, "HIGH": 0.80},
        },
        "error_pattern": {
            "NORMAL": {"NONE": 0.60, "VARIED": 0.30, "PERSISTENT": 0.10},
            "DIFFICULTY": {"NONE": 0.10, "VARIED": 0.55, "PERSISTENT": 0.35},
            "UNCERTAINTY": {"NONE": 0.25, "VARIED": 0.60, "PERSISTENT": 0.15},
            "IMPULSIVITY": {"NONE": 0.15, "VARIED": 0.70, "PERSISTENT": 0.15},
            "STAGNATION": {"NONE": 0.03, "VARIED": 0.17, "PERSISTENT": 0.80},
            "AUTONOMY": {"NONE": 0.90, "VARIED": 0.09, "PERSISTENT": 0.01},
        },
        "attempt_band": {
            "NORMAL": {"1": 0.45, "2-3": 0.40, "4+": 0.15},
            "DIFFICULTY": {"1": 0.20, "2-3": 0.50, "4+": 0.30},
            "UNCERTAINTY": {"1": 0.25, "2-3": 0.45, "4+": 0.30},
            "IMPULSIVITY": {"1": 0.20, "2-3": 0.40, "4+": 0.40},
            "STAGNATION": {"1": 0.05, "2-3": 0.30, "4+": 0.65},
            "AUTONOMY": {"1": 0.50, "2-3": 0.35, "4+": 0.15},
        },
        "repetition_band": {
            "NORMAL": {"0": 0.75, "1": 0.20, "2+": 0.05},
            "DIFFICULTY": {"0": 0.65, "1": 0.25, "2+": 0.10},
            "UNCERTAINTY": {"0": 0.65, "1": 0.25, "2+": 0.10},
            "IMPULSIVITY": {"0": 0.60, "1": 0.25, "2+": 0.15},
            "STAGNATION": {"0": 0.35, "1": 0.35, "2+": 0.30},
            "AUTONOMY": {"0": 0.80, "1": 0.17, "2+": 0.03},
        },
        "response_time_band": {
            "NORMAL": {"FAST": 0.25, "TYPICAL": 0.55, "SLOW": 0.20},
            "DIFFICULTY": {"FAST": 0.10, "TYPICAL": 0.45, "SLOW": 0.45},
            "UNCERTAINTY": {"FAST": 0.10, "TYPICAL": 0.35, "SLOW": 0.55},
            "IMPULSIVITY": {"FAST": 0.80, "TYPICAL": 0.15, "SLOW": 0.05},
            "STAGNATION": {"FAST": 0.15, "TYPICAL": 0.40, "SLOW": 0.45},
            "AUTONOMY": {"FAST": 0.30, "TYPICAL": 0.55, "SLOW": 0.15},
        },
        "answer_changes_band": {
            "NORMAL": {"0": 0.55, "1-2": 0.35, "3+": 0.10},
            "DIFFICULTY": {"0": 0.45, "1-2": 0.40, "3+": 0.15},
            "UNCERTAINTY": {"0": 0.10, "1-2": 0.35, "3+": 0.55},
            "IMPULSIVITY": {"0": 0.55, "1-2": 0.35, "3+": 0.10},
            "STAGNATION": {"0": 0.45, "1-2": 0.40, "3+": 0.15},
            "AUTONOMY": {"0": 0.60, "1-2": 0.35, "3+": 0.05},
        },
        "click_pattern": {
            "NORMAL": {"CALM": 0.70, "ERRATIC": 0.15, "IDLE": 0.15},
            "DIFFICULTY": {"CALM": 0.60, "ERRATIC": 0.20, "IDLE": 0.20},
            "UNCERTAINTY": {"CALM": 0.55, "ERRATIC": 0.25, "IDLE": 0.20},
            "IMPULSIVITY": {"CALM": 0.20, "ERRATIC": 0.75, "IDLE": 0.05},
            "STAGNATION": {"CALM": 0.55, "ERRATIC": 0.15, "IDLE": 0.30},
            "AUTONOMY": {"CALM": 0.75, "ERRATIC": 0.15, "IDLE": 0.10},
        },
        "help_requests_band": {
            "NORMAL": {"0": 0.65, "1": 0.30, "2+": 0.05},
            "DIFFICULTY": {"0": 0.45, "1": 0.35, "2+": 0.20},
            "UNCERTAINTY": {"0": 0.45, "1": 0.35, "2+": 0.20},
            "IMPULSIVITY": {"0": 0.65, "1": 0.25, "2+": 0.10},
            "STAGNATION": {"0": 0.35, "1": 0.35, "2+": 0.30},
            "AUTONOMY": {"0": 0.80, "1": 0.18, "2+": 0.02},
        },
        "prior_help_result": {
            "NORMAL": {"NONE": 0.55, "IMPROVED": 0.25, "PERSISTED": 0.07, "REJECTED": 0.08, "PENDING": 0.05},
            "DIFFICULTY": {"NONE": 0.40, "IMPROVED": 0.15, "PERSISTED": 0.25, "REJECTED": 0.10, "PENDING": 0.10},
            "UNCERTAINTY": {"NONE": 0.45, "IMPROVED": 0.15, "PERSISTED": 0.18, "REJECTED": 0.12, "PENDING": 0.10},
            "IMPULSIVITY": {"NONE": 0.50, "IMPROVED": 0.10, "PERSISTED": 0.15, "REJECTED": 0.20, "PENDING": 0.05},
            "STAGNATION": {"NONE": 0.25, "IMPROVED": 0.05, "PERSISTED": 0.50, "REJECTED": 0.10, "PENDING": 0.10},
            "AUTONOMY": {"NONE": 0.50, "IMPROVED": 0.40, "PERSISTED": 0.03, "REJECTED": 0.05, "PENDING": 0.02},
        },
        "recent_errors_trend": {
            "NORMAL": {"INCREASING": 0.20, "DECREASING": 0.30, "STABLE": 0.50},
            "DIFFICULTY": {"INCREASING": 0.50, "DECREASING": 0.15, "STABLE": 0.35},
            "UNCERTAINTY": {"INCREASING": 0.35, "DECREASING": 0.25, "STABLE": 0.40},
            "IMPULSIVITY": {"INCREASING": 0.40, "DECREASING": 0.20, "STABLE": 0.40},
            "STAGNATION": {"INCREASING": 0.40, "DECREASING": 0.05, "STABLE": 0.55},
            "AUTONOMY": {"INCREASING": 0.10, "DECREASING": 0.40, "STABLE": 0.50},
        },
    },
    "thresholds": {"need_support_alert": 0.6},
}

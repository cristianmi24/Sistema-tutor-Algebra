"""OBSERVAR: extracción de evidencias multiseñal a partir de los eventos recientes de una tarea."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any, Literal

TimeBand = Literal["FAST", "TYPICAL", "SLOW", "UNKNOWN"]
Band3 = Literal["LOW", "MID", "HIGH", "UNKNOWN"]
Trend = Literal["INCREASING", "DECREASING", "STABLE", "UNKNOWN"]
ErrorPatternBand = Literal["NONE", "VARIED", "PERSISTENT"]
ClickPattern = Literal["CALM", "ERRATIC", "IDLE", "UNKNOWN"]

RESPONSE_EVENTS = {"STUDENT_RESPONSE", "STUDENT_REATTEMPT", "STUDENT_EDITED_RESPONSE"}


@dataclass(slots=True)
class EventRecord:
    """Proyección mínima de un evento de interacción (independiente del ORM)."""

    sequence: int
    event_type: str
    timestamp: datetime
    task_id: str | None = None
    question_id: str | None = None
    correct: bool | None = None
    error_pattern: str | None = None
    representation: str | None = None
    content_key: str | None = None  # hash del contenido para detectar repeticiones
    client_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ScaffoldRecord:
    """Memoria de una ayuda previa en la tarea."""

    code: str | None
    scaffold_type: str | None
    level: int
    result: str  # PENDING, IMPROVED, PERSISTED, REJECTED, ABANDONED, UNKNOWN
    rejected: bool
    accepted: bool | None
    created_sequence: int | None = None


@dataclass(slots=True)
class Evidence:
    window_size: int
    events_in_window: int
    responses_in_window: int
    response_time_ms: int | None
    response_time_band: TimeBand
    fast_streak: int
    recent_accuracy: float | None
    accuracy_band: Band3
    attempt_count: int
    repetition_count: int
    click_pattern: ClickPattern
    error_pattern: ErrorPatternBand
    last_error_pattern: str | None
    answer_changes: int
    help_requests: int
    help_requested_now: bool
    prior_help_result: str  # NONE | IMPROVED | PERSISTED | REJECTED | PENDING
    interventions_in_task: int
    representation_switches: int
    recent_errors_trend: Trend
    stable_correct_streak: int
    teacher_intervened_recently: bool
    last_event_type: str | None
    difficulty: int

    def as_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def as_strings(self) -> list[str]:
        keys = (
            "response_time_band",
            "recent_accuracy",
            "attempt_count",
            "repetition_count",
            "click_pattern",
            "error_pattern",
            "answer_changes",
            "help_requests",
            "prior_help_result",
            "representation_switches",
            "recent_errors_trend",
            "stable_correct_streak",
        )
        return [f"{k}={getattr(self, k)}" for k in keys]

    def discretized(self) -> dict[str, str]:
        """Valores discretos para la inferencia bayesiana."""
        return {
            "response_time_band": self.response_time_band,
            "accuracy_band": self.accuracy_band,
            "attempt_band": "1" if self.attempt_count <= 1 else "2-3" if self.attempt_count <= 3 else "4+",
            "repetition_band": "0" if self.repetition_count == 0 else "1" if self.repetition_count == 1 else "2+",
            "click_pattern": self.click_pattern,
            "error_pattern": self.error_pattern,
            "answer_changes_band": "0" if self.answer_changes == 0 else "1-2" if self.answer_changes <= 2 else "3+",
            "help_requests_band": "0" if self.help_requests == 0 else "1" if self.help_requests == 1 else "2+",
            "prior_help_result": self.prior_help_result,
            "representation_switches_band": "0"
            if self.representation_switches == 0
            else "1"
            if self.representation_switches == 1
            else "2+",
            "recent_errors_trend": self.recent_errors_trend,
        }


def _time_band(ms: int | None, expected_ms: int) -> TimeBand:
    if ms is None or expected_ms <= 0:
        return "UNKNOWN"
    ratio = ms / expected_ms
    if ratio < 0.4:
        return "FAST"
    if ratio > 2.0:
        return "SLOW"
    return "TYPICAL"


def _accuracy_band(value: float | None) -> Band3:
    if value is None:
        return "UNKNOWN"
    if value < 0.34:
        return "LOW"
    if value > 0.66:
        return "HIGH"
    return "MID"


def _click_pattern(meta: dict[str, Any]) -> ClickPattern:
    clicks = meta.get("clicks")
    time_ms = meta.get("time_on_task_ms")
    if not isinstance(clicks, int | float) or not isinstance(time_ms, int | float) or time_ms <= 0:
        return "UNKNOWN"
    per_minute = clicks / (time_ms / 60000)
    if per_minute > 40:
        return "ERRATIC"
    if per_minute < 1 and time_ms > 120000:
        return "IDLE"
    return "CALM"


def _trend(responses: list[EventRecord]) -> Trend:
    """Compara los errores de las dos respuestas más recientes con los de las dos anteriores."""
    evaluated = [r for r in responses if r.correct is not None]
    if len(evaluated) < 2:
        return "UNKNOWN"
    recent = evaluated[-2:]
    earlier = evaluated[-4:-2] or evaluated[:-2][-1:]
    if not earlier:
        return "UNKNOWN"
    recent_rate = sum(1 for r in recent if r.correct is False) / len(recent)
    earlier_rate = sum(1 for r in earlier if r.correct is False) / len(earlier)
    if recent_rate > earlier_rate + 1e-9:
        return "INCREASING"
    if recent_rate < earlier_rate - 1e-9:
        return "DECREASING"
    return "STABLE"


def _error_pattern_band(responses: list[EventRecord]) -> tuple[ErrorPatternBand, str | None]:
    errors = [r.error_pattern for r in responses if r.correct is False and r.error_pattern]
    if not errors:
        return "NONE", None
    last = errors[-1]
    if len(errors) >= 2 and errors[-1] == errors[-2]:
        return "PERSISTENT", last
    return "VARIED", last


def extract_evidence(
    events: list[EventRecord],
    *,
    task_id: str,
    scaffolds: list[ScaffoldRecord],
    window_size: int = 5,
    expected_time_ms: int = 90000,
    teacher_pause_events: int = 3,
    difficulty: int = 2,
    help_requested_now: bool = False,
) -> Evidence:
    """Construye la evidencia de la tarea usando la ventana de los últimos ``window_size`` eventos de respuesta.

    Nunca una sola variable decide: todas las señales se devuelven juntas para las reglas y Bayes.
    """
    task_events = sorted((e for e in events if e.task_id == task_id), key=lambda e: e.sequence)
    responses_all = [e for e in task_events if e.event_type in RESPONSE_EVENTS]
    window = responses_all[-window_size:]
    recent_events = task_events[-(window_size * 3) :]

    last_response = window[-1] if window else None
    meta = last_response.client_meta if last_response else {}
    time_ms = meta.get("time_on_task_ms")
    response_time_ms = int(time_ms) if isinstance(time_ms, int | float) else None

    fast_streak = 0
    for r in reversed(window):
        t = r.client_meta.get("time_on_task_ms")
        if isinstance(t, int | float) and _time_band(int(t), expected_time_ms) == "FAST":
            fast_streak += 1
        else:
            break

    evaluated = [r for r in window if r.correct is not None]
    accuracy = (sum(1 for r in evaluated if r.correct) / len(evaluated)) if evaluated else None

    keys = [r.content_key for r in window if r.content_key]
    repetition_count = len(keys) - len(set(keys))

    error_band, last_error = _error_pattern_band(window)
    answer_changes = sum(1 for e in recent_events if e.event_type == "STUDENT_EDITED_RESPONSE")
    help_requests = sum(1 for e in recent_events if e.event_type == "HELP_REQUESTED") + (1 if help_requested_now else 0)
    representation_switches = sum(1 for e in recent_events if e.event_type == "REPRESENTATION_CHANGED")

    stable = 0
    for r in reversed(window):
        if r.correct is True:
            stable += 1
        else:
            break
    if help_requests:
        stable = (
            min(stable, 0) if any(e.event_type == "HELP_REQUESTED" for e in recent_events[-len(window) :]) else stable
        )

    last_scaffold = None
    for s in sorted(scaffolds, key=lambda s: s.created_sequence or 0):
        last_scaffold = s
    prior_help_result = (
        "NONE" if last_scaffold is None else ("REJECTED" if last_scaffold.rejected else last_scaffold.result)
    )
    interventions_in_task = sum(1 for s in scaffolds if s.level > 0 and s.code is not None)

    teacher_recent = any(e.event_type == "TEACHER_INTERVENTION" for e in task_events[-teacher_pause_events:])

    return Evidence(
        window_size=window_size,
        events_in_window=len(recent_events),
        responses_in_window=len(window),
        response_time_ms=response_time_ms,
        response_time_band=_time_band(response_time_ms, expected_time_ms),
        fast_streak=fast_streak,
        recent_accuracy=round(accuracy, 3) if accuracy is not None else None,
        accuracy_band=_accuracy_band(accuracy),
        attempt_count=len(responses_all),
        repetition_count=repetition_count,
        click_pattern=_click_pattern(meta),
        error_pattern=error_band,
        last_error_pattern=last_error,
        answer_changes=answer_changes,
        help_requests=help_requests,
        help_requested_now=help_requested_now,
        prior_help_result=prior_help_result,
        interventions_in_task=interventions_in_task,
        representation_switches=representation_switches,
        recent_errors_trend=_trend(window),
        stable_correct_streak=stable,
        teacher_intervened_recently=teacher_recent,
        last_event_type=task_events[-1].event_type if task_events else None,
        difficulty=difficulty,
    )

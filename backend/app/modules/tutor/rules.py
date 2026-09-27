"""DECIDIR: motor de reglas pedagógicas legibles (DSL JSON).

Regla::

    {"code": "R-STAGNATION-REPR", "name": "...", "priority": 40, "min_consecutive": 1,
     "when": {"all": [{"evidence": "error_pattern", "is": "PERSISTENT"},
                      {"evidence": "attempt_count", "gte": 3},
                      {"posterior": "STAGNATION", "gt": 0.5}]},
     "then": {"state": "STAGNATION", "intervention": "REPRESENTATION_CHANGE", "level": 4, "fading": "INCREASE"}}

Condiciones: ``evidence`` (campo de Evidence) con ``is``/``in``/``eq``/``ne``/``gt``/``gte``/``lt``/``lte``;
``posterior`` (estado) con comparadores numéricos; ``previous_state`` con ``is``/``in``; combinadores
``all``/``any``/``not``. Se evalúan por prioridad descendente; la primera que se cumple decide.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.modules.tutor.bayes import Posterior
from app.modules.tutor.evidence import Evidence

Fading = str  # KEEP | REDUCE | INCREASE


@dataclass(slots=True)
class Rule:
    code: str
    name: str
    priority: int
    when: dict[str, Any]
    then: dict[str, Any]
    min_consecutive: int = 1
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        return cls(
            code=str(data["code"]),
            name=str(data.get("name", data["code"])),
            priority=int(data.get("priority", 0)),
            when=dict(data.get("when", {})),
            then=dict(data.get("then", {})),
            min_consecutive=int(data.get("min_consecutive", 1)),
            description=str(data.get("description", "")),
        )


@dataclass(slots=True)
class RuleContext:
    evidence: Evidence
    posterior: Posterior
    previous_state: str
    candidate_state: str | None
    candidate_count: int


@dataclass(slots=True)
class RuleResult:
    state: str
    level: int
    intervention: str | None
    fading: Fading
    rule_code: str | None
    rule_name: str | None
    matched_codes: list[str] = field(default_factory=list)
    confirmed: bool = True
    candidate_state: str | None = None
    candidate_count: int = 0
    explanation: str = ""


_NUMERIC_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "gt": lambda a, b: bool(a > b),
    "gte": lambda a, b: bool(a >= b),
    "lt": lambda a, b: bool(a < b),
    "lte": lambda a, b: bool(a <= b),
    "eq": lambda a, b: bool(a == b),
    "ne": lambda a, b: bool(a != b),
}


def _compare(actual: Any, condition: dict[str, Any]) -> bool:
    if "is" in condition:
        return bool(actual == condition["is"])
    if "in" in condition:
        return actual in list(condition["in"])
    for op, fn in _NUMERIC_OPS.items():
        if op in condition:
            if actual is None:
                return False
            try:
                return bool(fn(actual, condition[op]))
            except TypeError:
                return False
    return False


def evaluate_condition(condition: dict[str, Any], ctx: RuleContext) -> bool:
    if "all" in condition:
        return all(evaluate_condition(c, ctx) for c in condition["all"])
    if "any" in condition:
        return any(evaluate_condition(c, ctx) for c in condition["any"])
    if "not" in condition:
        return not evaluate_condition(condition["not"], ctx)
    if "evidence" in condition:
        name = str(condition["evidence"])
        actual = getattr(ctx.evidence, name, None)
        return _compare(actual, condition)
    if "posterior" in condition:
        return _compare(ctx.posterior.get(str(condition["posterior"])), condition)
    if "need_support" in condition:
        spec = condition["need_support"]
        return _compare(ctx.posterior.need_support, spec if isinstance(spec, dict) else {"gte": spec})
    if "previous_state" in condition:
        spec = condition["previous_state"]
        return _compare(ctx.previous_state, spec if isinstance(spec, dict) else {"is": spec})
    return False


def evaluate_rules(rules: list[Rule], ctx: RuleContext) -> RuleResult:
    """Devuelve la decisión de la primera regla (mayor prioridad) cuyas condiciones se cumplen.

    Histéresis: una regla con ``min_consecutive > 1`` solo cambia el estado tras cumplirse en esa
    cantidad de evaluaciones consecutivas; mientras tanto el estado previo se mantiene y no se interviene.
    """
    ordered = sorted(rules, key=lambda r: r.priority, reverse=True)
    matched = [r for r in ordered if evaluate_condition(r.when, ctx)]
    if not matched:
        return RuleResult(
            state=ctx.previous_state if ctx.previous_state in {"NORMAL", "EXPLORATION", "AUTONOMY"} else "NORMAL",
            level=0,
            intervention=None,
            fading="KEEP",
            rule_code=None,
            rule_name=None,
            matched_codes=[],
            candidate_state=None,
            candidate_count=0,
            explanation="Ninguna regla se cumplió: se observa sin intervenir (nivel 0).",
        )
    winner = matched[0]
    then = winner.then
    state = str(then.get("state", ctx.previous_state))
    level = int(then.get("level", 0))
    intervention = then.get("intervention")
    fading = str(then.get("fading", "KEEP"))

    candidate_state = state
    candidate_count = ctx.candidate_count + 1 if ctx.candidate_state == state else 1
    confirmed = candidate_count >= max(1, winner.min_consecutive) or state == ctx.previous_state
    if not confirmed:
        return RuleResult(
            state=ctx.previous_state,
            level=0,
            intervention=None,
            fading="KEEP",
            rule_code=winner.code,
            rule_name=winner.name,
            matched_codes=[r.code for r in matched],
            confirmed=False,
            candidate_state=candidate_state,
            candidate_count=candidate_count,
            explanation=(
                f"La regla {winner.code} sugiere {state}, pero requiere {winner.min_consecutive} evaluaciones "
                f"consecutivas ({candidate_count}/{winner.min_consecutive}); "
                f"se mantiene {ctx.previous_state} y se observa."
            ),
        )
    return RuleResult(
        state=state,
        level=level,
        intervention=str(intervention) if intervention else None,
        fading=fading,
        rule_code=winner.code,
        rule_name=winner.name,
        matched_codes=[r.code for r in matched],
        confirmed=True,
        candidate_state=candidate_state,
        candidate_count=candidate_count,
        explanation=f"Regla {winner.code} ({winner.name}): estado {state}, nivel {level}"
        + (f", intervención {intervention}" if intervention else ", sin intervención")
        + f", fading {fading}.",
    )

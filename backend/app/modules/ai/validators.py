"""Validadores de salidas del LLM: pedagógico → seguridad → dominio. Cualquier rechazo bloquea la salida."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from app.modules.learning.evaluation import (
    ExpressionError,
    evaluate_expression,
    expression_values,
    normalize_expression,
)

# Vocabulario cerrado de dimensiones observables (igual al del evaluador determinista + extras).
OBSERVABLE_DIMENSIONS: tuple[str, ...] = (
    "RECURSIVE_LANGUAGE",
    "FUNCTIONAL_LANGUAGE",
    "MENTIONS_POSITION",
    "GENERAL_CLAIM",
    "EXAMPLE_ONLY",
    "REFERS_TO_STRUCTURE",
    "USES_SYMBOLS",
    "COMPARES_STRATEGIES",
    "EXPRESSES_DOUBT",
    "CHECKS_WITH_CASE",
)

_URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"\b\d{7,}\b")
_INJECTION = re.compile(
    r"\b(ignora|olvida|ignore|disregard)\b.{0,40}\b(instrucciones|reglas|instructions|rules)\b", re.IGNORECASE
)
_BLOCKED_WORDS = {"idiota", "estúpido", "estupido", "tonto", "burro", "inútil", "inutil"}
_ANSWER_PHRASES = re.compile(
    r"\b(la (respuesta|fórmula|formula|regla) (es|sería|seria)|el resultado es|la solución es|la solucion es)\b",
    re.IGNORECASE,
)
_EXPR_CANDIDATE = re.compile(
    r"[0-9]*\s*[·*x×]?\s*\(?\s*[nx]\s*\)?\s*(?:[+\-−]\s*\d+)?|\d+\s*\(\s*[nx]\s*[+\-−]\s*\d+\s*\)", re.IGNORECASE
)
_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")


@dataclass(slots=True)
class ValidationResult:
    approved: bool
    pedagogical: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)
    domain: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "pedagogical": self.pedagogical,
            "safety": self.safety,
            "domain": self.domain,
            "reasons": self.reasons,
        }


def safety_check(text: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    lowered = text.lower()
    if _URL.search(text):
        reasons.append("contiene enlaces")
    if _EMAIL.search(text):
        reasons.append("contiene un correo electrónico")
    if _PHONE.search(text):
        reasons.append("contiene un número que parece dato personal")
    if _INJECTION.search(text):
        reasons.append("contiene instrucciones ajenas a la tarea")
    if any(word in lowered.split() for word in _BLOCKED_WORDS):
        reasons.append("lenguaje inapropiado")
    return not reasons, reasons


def _mentions_rule(text: str, rule: str) -> bool:
    """¿El texto contiene una expresión equivalente a la regla de la tarea?"""
    expected = expression_values(rule)
    for match in _EXPR_CANDIDATE.finditer(text):
        candidate = match.group(0).strip()
        if "n" not in candidate.lower() and "x" not in candidate.lower():
            continue
        try:
            if expression_values(normalize_expression(candidate)) == expected:
                return True
        except (ExpressionError, ZeroDivisionError):
            continue
    return False


def domain_check_hint(
    text: str, *, rule: str | None, protected_positions: list[int], original: str
) -> tuple[bool, list[str]]:
    """Una ayuda nunca revela la regla ni los valores que la tarea pide; no introduce números nuevos."""
    reasons: list[str] = []
    if _ANSWER_PHRASES.search(text):
        reasons.append("anuncia la respuesta o la fórmula")
    if rule:
        if _mentions_rule(text, rule):
            reasons.append("contiene la expresión general de la tarea")
        protected = set()
        for position in protected_positions:
            try:
                protected.add(evaluate_expression(rule, position))
            except ExpressionError:
                continue
        original_numbers = {Fraction(n.replace(",", ".")) for n in _NUMBER.findall(original)}
        for raw in _NUMBER.findall(text):
            value = Fraction(raw.replace(",", "."))
            if value in protected and value not in original_numbers:
                reasons.append(f"revela un valor pedido por la tarea ({raw})")
    new_numbers = {n for n in _NUMBER.findall(text)} - set(_NUMBER.findall(original))
    if new_numbers:
        reasons.append(f"introduce números que no estaban en la ayuda original ({', '.join(sorted(new_numbers))})")
    return not reasons, reasons


def pedagogical_check_hint(text: str, *, original: str, scaffold_type: str | None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    stripped = text.strip()
    if len(stripped) < 10:
        reasons.append("demasiado corta")
    if len(stripped) > max(240, int(len(original) * 1.8)):
        reasons.append("más extensa que la ayuda original (aumenta la explicitud)")
    if original.strip().endswith("?") and "?" not in stripped:
        reasons.append("la ayuda original es una pregunta y la reformulación no")
    if (
        scaffold_type in {"GUIDING_QUESTION", "METACOGNITIVE", "SELF_EXPLANATION"}
        and "?" not in stripped
        and not stripped.endswith(".")
    ):
        reasons.append("no mantiene la forma de invitación a pensar")
    if re.search(r"\b(correcto|incorrecto|mal|bien hecho|te equivocaste)\b", stripped, re.IGNORECASE):
        reasons.append("evalúa al estudiante (no es una ayuda para pensar)")
    return not reasons, reasons


def validate_hint(
    data: dict[str, Any] | None,
    *,
    original: str,
    scaffold_type: str | None,
    rule: str | None,
    protected_positions: list[int],
) -> tuple[str | None, ValidationResult]:
    text = str((data or {}).get("text", "")).strip()
    if not text:
        return None, ValidationResult(approved=False, reasons=["salida vacía o sin el campo 'text'"])
    ped_ok, ped = pedagogical_check_hint(text, original=original, scaffold_type=scaffold_type)
    safe_ok, safe = safety_check(text)
    dom_ok, dom = domain_check_hint(text, rule=rule, protected_positions=protected_positions, original=original)
    result = ValidationResult(
        approved=ped_ok and safe_ok and dom_ok,
        pedagogical={"approved": ped_ok, "reasons": ped},
        safety={"approved": safe_ok, "reasons": safe},
        domain={"approved": dom_ok, "reasons": dom},
        reasons=[*ped, *safe, *dom],
    )
    return (text if result.approved else None), result


def validate_interpretation(data: dict[str, Any] | None) -> tuple[dict[str, Any] | None, ValidationResult]:
    """La interpretación solo puede usar el vocabulario cerrado y una confianza en [0, 1]."""
    if not data:
        return None, ValidationResult(approved=False, reasons=["salida vacía"])
    dims = data.get("dimensions")
    confidence = data.get("confidence")
    reasons: list[str] = []
    if not isinstance(dims, list) or not all(isinstance(d, str) for d in dims):
        reasons.append("'dimensions' debe ser una lista de etiquetas")
        dims = []
    unknown = [d for d in dims if d not in OBSERVABLE_DIMENSIONS]
    if unknown:
        reasons.append(f"etiquetas fuera del vocabulario cerrado: {unknown}")
    if not isinstance(confidence, int | float) or not 0 <= float(confidence) <= 1:
        reasons.append("'confidence' debe estar entre 0 y 1")
    note = str(data.get("note", ""))[:280]
    safe_ok, safe = safety_check(note)
    reasons.extend(safe)
    approved = not reasons
    result = ValidationResult(
        approved=approved,
        pedagogical={"approved": True, "reasons": []},
        safety={"approved": safe_ok, "reasons": safe},
        domain={"approved": not unknown and isinstance(dims, list), "reasons": [r for r in reasons if r not in safe]},
        reasons=reasons,
    )
    if not approved:
        return None, result
    return {
        "label": "interpretación automática asistida por IA (validada; no es una categoría teórica)",
        "dimensions": sorted(set(dims)),
        "confidence": round(float(confidence), 3),  # type: ignore[arg-type]
        "note": note or None,
    }, result

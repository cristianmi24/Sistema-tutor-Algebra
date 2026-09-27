"""Evaluación determinista de dominio (generalización algebraica).

* Expresiones algebraicas en ``n`` evaluadas con un parser seguro (sin ``eval``).
* Corrección por comparación con la regla de la tarea en varios valores de ``n``.
* **Patrones de error** observables (no categorías teóricas): OFF_BY_STEP, SHIFTED_INDEX,
  WRONG_CONSTANT, WRONG_RATE, MISSING_CONSTANT, OTHER.
* Respuestas verbales: no se califican; se etiquetan *dimensiones observables* del lenguaje
  (RECURSIVE_LANGUAGE, FUNCTIONAL_LANGUAGE, MENTIONS_POSITION, GENERAL_CLAIM, EXAMPLE_ONLY).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

SAMPLE_POSITIONS: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 8, 10, 12, 20)
MAX_EXPONENT = 6


class ExpressionError(ValueError):
    """Expresión no válida o no permitida."""


_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_ALLOWED_UNARY = (ast.UAdd, ast.USub)


def normalize_expression(raw: str) -> str:
    """Normaliza la escritura escolar: ``3n+2``, ``3·n``, ``n^2``, ``2(n+1)``, ``x`` como variable."""
    expr = raw.strip().lower()
    expr = expr.replace("·", "*").replace("×", "*").replace("−", "-").replace("÷", "/").replace("^", "**")
    expr = re.sub(r"\s+", "", expr)
    expr = re.sub(r"[a-z]+", lambda m: "n" if m.group(0) in {"n", "x", "f", "k"} else m.group(0), expr)
    # multiplicación implícita: 3n, 3(n+1), n(n+1), (n+1)(n+2), 2n**2
    expr = re.sub(r"(\d)(n|\()", r"\1*\2", expr)
    expr = re.sub(r"(n|\))(n|\()", r"\1*\2", expr)
    expr = re.sub(r"(\))(\d)", r"\1*\2", expr)
    if len(expr) > 120:
        raise ExpressionError("La expresión es demasiado larga.")
    if not re.fullmatch(r"[0-9n+\-*/().]+", expr):
        raise ExpressionError("La expresión contiene símbolos no permitidos.")
    return expr


def _check_node(node: ast.AST) -> None:
    if isinstance(node, ast.Expression):
        _check_node(node.body)
    elif isinstance(node, ast.BinOp):
        if not isinstance(node.op, _ALLOWED_BINOPS):
            raise ExpressionError("Operación no permitida.")
        if isinstance(node.op, ast.Pow):
            if not (isinstance(node.right, ast.Constant) and isinstance(node.right.value, int)):
                raise ExpressionError("El exponente debe ser un número entero.")
            if abs(node.right.value) > MAX_EXPONENT:
                raise ExpressionError("Exponente demasiado grande.")
        _check_node(node.left)
        _check_node(node.right)
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _ALLOWED_UNARY):
            raise ExpressionError("Operación no permitida.")
        _check_node(node.operand)
    elif isinstance(node, ast.Constant):
        if not isinstance(node.value, int | float):
            raise ExpressionError("Constante no permitida.")
    elif isinstance(node, ast.Name):
        if node.id != "n":
            raise ExpressionError("Solo se permite la variable n.")
    else:
        raise ExpressionError("Estructura no permitida.")


def compile_expression(raw: str) -> ast.Expression:
    normalized = normalize_expression(raw)
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise ExpressionError("No pudimos leer la expresión.") from exc
    _check_node(tree)
    return tree


def _eval(node: ast.AST, n: Fraction) -> Fraction:
    if isinstance(node, ast.Expression):
        return _eval(node.body, n)
    if isinstance(node, ast.Constant):
        return Fraction(str(node.value))
    if isinstance(node, ast.Name):
        return n
    if isinstance(node, ast.UnaryOp):
        value = _eval(node.operand, n)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        left = _eval(node.left, n)
        right = _eval(node.right, n)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise ExpressionError("División por cero.")
            return left / right
        if isinstance(node.op, ast.Pow):
            return left ** int(right)
    raise ExpressionError("Estructura no permitida.")


def evaluate_expression(raw: str, n: int) -> Fraction:
    return _eval(compile_expression(raw), Fraction(n))


def expression_values(raw: str, positions: tuple[int, ...] = SAMPLE_POSITIONS) -> list[Fraction]:
    tree = compile_expression(raw)
    return [_eval(tree, Fraction(p)) for p in positions]


# --------------------------------------------------------------------------- resultado


@dataclass(slots=True)
class Evaluation:
    correct: bool | None
    error_pattern: str | None = None
    observed_dimensions: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "correct": self.correct,
            "error_pattern": self.error_pattern,
            "observed_dimensions": self.observed_dimensions,
            "detail": self.detail,
        }


def _step(rule: str) -> Fraction:
    return evaluate_expression(rule, 2) - evaluate_expression(rule, 1)


def _classify_numeric(rule: str, position: int, value: Fraction) -> str:
    expected = evaluate_expression(rule, position)
    if value == expected:
        return "NONE"
    step = _step(rule)
    if step != 0 and value in (expected + step, expected - step):
        return "OFF_BY_STEP"
    if position > 1 and value == evaluate_expression(rule, position - 1):
        return "SHIFTED_INDEX"
    if value == evaluate_expression(rule, position + 1):
        return "SHIFTED_INDEX"
    constant = evaluate_expression(rule, 0)
    if constant != 0 and value == expected - constant:
        return "MISSING_CONSTANT"
    return "OTHER"


def evaluate_numeric(rule: str, position: int, value: float | int | str) -> Evaluation:
    try:
        numeric = Fraction(str(value).strip().replace(",", "."))
    except (ValueError, ZeroDivisionError):
        return Evaluation(correct=False, error_pattern="NOT_A_NUMBER")
    pattern = _classify_numeric(rule, position, numeric)
    expected = evaluate_expression(rule, position)
    return Evaluation(
        correct=pattern == "NONE",
        error_pattern=None if pattern == "NONE" else pattern,
        detail={"position": position, "expected": str(expected), "given": str(numeric)},
    )


def _classify_symbolic(rule: str, given: str) -> tuple[str, list[str]]:
    expected = expression_values(rule)
    values = expression_values(given)
    diffs = [g - e for g, e in zip(values, expected, strict=True)]
    if all(d == 0 for d in diffs):
        return "NONE", []
    # En reglas lineales, un desplazamiento de índice coincide con un desfase constante de ±paso:
    # se prioriza la lectura "índice desplazado" porque es la más informativa pedagógicamente.
    shifted_plus = [evaluate_expression(rule, p + 1) for p in SAMPLE_POSITIONS]
    shifted_minus = [evaluate_expression(rule, p - 1) for p in SAMPLE_POSITIONS]
    if values in (shifted_plus, shifted_minus):
        return "SHIFTED_INDEX", []
    if len(set(diffs)) == 1:
        constant = evaluate_expression(rule, 0)
        return ("MISSING_CONSTANT" if diffs[0] == -constant and constant != 0 else "WRONG_CONSTANT"), [str(diffs[0])]
    second = [diffs[i + 1] - diffs[i] for i in range(3)]  # posiciones 1..4 consecutivas
    if len(set(second)) == 1:
        return "WRONG_RATE", [str(second[0])]
    return "OTHER", []


def evaluate_symbolic(rule: str, given: str) -> Evaluation:
    try:
        pattern, notes = _classify_symbolic(rule, given)
    except ExpressionError as exc:
        return Evaluation(correct=False, error_pattern="UNPARSEABLE_EXPRESSION", detail={"message": str(exc)})
    return Evaluation(
        correct=pattern == "NONE",
        error_pattern=None if pattern == "NONE" else pattern,
        detail={"normalized": normalize_expression(given), "notes": notes},
    )


def evaluate_table(rule: str, rows: list[dict[str, Any]], required_positions: list[int] | None = None) -> Evaluation:
    checked: dict[str, Any] = {}
    patterns: list[str] = []
    for row in rows:
        try:
            n = int(row["n"])
            value = Fraction(str(row["value"]).strip().replace(",", "."))
        except (KeyError, ValueError, TypeError, ZeroDivisionError):
            patterns.append("NOT_A_NUMBER")
            continue
        pattern = _classify_numeric(rule, n, value)
        checked[str(n)] = {"given": str(value), "expected": str(evaluate_expression(rule, n)), "pattern": pattern}
        if pattern != "NONE":
            patterns.append(pattern)
    missing = [p for p in (required_positions or []) if str(p) not in checked]
    correct = not patterns and not missing
    dominant = max(set(patterns), key=patterns.count) if patterns else None
    return Evaluation(
        correct=correct,
        error_pattern=None if correct else (dominant or "INCOMPLETE"),
        detail={"rows": checked, "missing_positions": missing},
    )


def evaluate_points(rule: str, points: list[dict[str, Any]]) -> Evaluation:
    rows = [{"n": p.get("x"), "value": p.get("y")} for p in points]
    result = evaluate_table(rule, rows)
    result.detail["kind"] = "points"
    return result


_RECURSIVE = re.compile(
    r"\b(se (le )?(suma|agrega|añade|aumenta)|cada vez|de uno en uno|el anterior|la anterior|siguiente"
    r"|más que|sumando|le sumo)\b"
)
_FUNCTIONAL = re.compile(
    r"\b(multiplic\w*|por el número|veces|el doble|el triple|según la figura|depende del número"
    r"|número de la figura|posición)\b"
)
_POSITION = re.compile(
    r"\b(figura|posición|término|lugar|número)\s*(n|\d+)\b|\bn\b|número de (la|el) (figura|posición|término|mesa)"
)
_GENERAL = re.compile(r"\b(siempre|cualquier|todas?|para todo|en general|regla|fórmula|sin importar)\b")
_EXAMPLE_ONLY = re.compile(r"\b(por ejemplo|en la figura \d+|en el \d+)\b")


def observe_verbal(text: str) -> Evaluation:
    """No califica; registra dimensiones observables del lenguaje para el análisis humano posterior."""
    lowered = text.lower()
    dims: list[str] = []
    if _RECURSIVE.search(lowered):
        dims.append("RECURSIVE_LANGUAGE")
    if _FUNCTIONAL.search(lowered):
        dims.append("FUNCTIONAL_LANGUAGE")
    if _POSITION.search(lowered):
        dims.append("MENTIONS_POSITION")
    if _GENERAL.search(lowered):
        dims.append("GENERAL_CLAIM")
    if _EXAMPLE_ONLY.search(lowered) and "GENERAL_CLAIM" not in dims:
        dims.append("EXAMPLE_ONLY")
    return Evaluation(correct=None, observed_dimensions=dims, detail={"length": len(text.split())})


def evaluate_response(
    *, rule: str | None, question: dict[str, Any], representation: str, content: dict[str, Any]
) -> Evaluation:
    """Punto de entrada: evalúa según el tipo de pregunta y la representación usada."""
    kind = question.get("kind")
    if kind in {"explain", "justify", "compare", "describe"} or representation == "VERBAL":
        return observe_verbal(str(content.get("text", "")))
    if rule is None:
        return Evaluation(correct=None)
    if representation == "SYMBOLIC":
        return evaluate_symbolic(rule, str(content.get("expression", "")))
    if representation == "TABULAR":
        rows = content.get("rows")
        positions = question.get("positions")
        return evaluate_table(
            rule, rows if isinstance(rows, list) else [], positions if isinstance(positions, list) else None
        )
    if representation == "GRAPHIC":
        points = content.get("points")
        return evaluate_points(rule, points if isinstance(points, list) else [])
    position = question.get("position")
    if kind in {"predict", "transfer_predict"} and isinstance(position, int):
        value = content.get("value", "")
        return evaluate_numeric(rule, position, value if isinstance(value, int | float | str) else "")
    return Evaluation(correct=None)

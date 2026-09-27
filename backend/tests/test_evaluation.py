"""Evaluador de dominio: parser seguro, corrección y patrones de error observables."""

from __future__ import annotations

from fractions import Fraction

import pytest
from app.modules.learning.evaluation import (
    ExpressionError,
    evaluate_expression,
    evaluate_numeric,
    evaluate_response,
    evaluate_symbolic,
    evaluate_table,
    normalize_expression,
    observe_verbal,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("3n+2", "3*n+2"),
        ("3·n + 2", "3*n+2"),
        ("n^2", "n**2"),
        ("2(n+1)", "2*(n+1)"),
        ("(n+1)(n+2)", "(n+1)*(n+2)"),
        ("3x+2", "3*n+2"),
    ],
)
def test_normalize_school_notation(raw: str, expected: str) -> None:
    assert normalize_expression(raw) == expected


@pytest.mark.parametrize("raw", ["__import__('os')", "n**99", "m+1", "3n+", "open(1)", "n" * 130])
def test_unsafe_or_invalid_expressions_are_rejected(raw: str) -> None:
    with pytest.raises(ExpressionError):
        evaluate_expression(raw, 3)


def test_expression_values_are_exact() -> None:
    assert evaluate_expression("3n+2", 10) == Fraction(32)
    assert evaluate_expression("n/2 + 1", 3) == Fraction(5, 2)


def test_numeric_prediction_patterns() -> None:
    assert evaluate_numeric("3*n+2", 5, 17).correct is True
    assert evaluate_numeric("3*n+2", 5, 20).error_pattern == "OFF_BY_STEP"
    assert evaluate_numeric("3*n+2", 5, 14).error_pattern in {"OFF_BY_STEP", "SHIFTED_INDEX"}
    assert evaluate_numeric("3*n+2", 5, 15).error_pattern == "MISSING_CONSTANT"
    assert evaluate_numeric("3*n+2", 5, 99).error_pattern == "OTHER"
    assert evaluate_numeric("3*n+2", 5, "diecisiete").error_pattern == "NOT_A_NUMBER"


def test_symbolic_equivalence_and_patterns() -> None:
    assert evaluate_symbolic("3*n+2", "2 + 3n").correct is True
    assert evaluate_symbolic("3*n+2", "3(n+1) - 1").correct is True
    assert evaluate_symbolic("3*n+2", "3n").error_pattern == "MISSING_CONSTANT"
    assert evaluate_symbolic("3*n+2", "3n+7").error_pattern == "WRONG_CONSTANT"
    assert evaluate_symbolic("3*n+2", "4n+2").error_pattern == "WRONG_RATE"
    assert evaluate_symbolic("3*n+2", "3(n+1)+2").error_pattern == "SHIFTED_INDEX"
    assert evaluate_symbolic("3*n+2", "n^2").error_pattern == "OTHER"
    assert evaluate_symbolic("3*n+2", "3n+").error_pattern == "UNPARSEABLE_EXPRESSION"


def test_table_evaluation_reports_missing_and_dominant_pattern() -> None:
    ok = evaluate_table("3*n+2", [{"n": 4, "value": 14}, {"n": 10, "value": 32}], [4, 10])
    assert ok.correct is True
    partial = evaluate_table("3*n+2", [{"n": 4, "value": 14}], [4, 10])
    assert partial.correct is False and partial.error_pattern == "INCOMPLETE"
    wrong = evaluate_table("3*n+2", [{"n": 4, "value": 12}, {"n": 10, "value": 30}], [4, 10])
    assert wrong.error_pattern == "MISSING_CONSTANT"


def test_verbal_answers_are_observed_not_graded() -> None:
    recursive = observe_verbal("Cada vez se le suma 3 al anterior")
    assert recursive.correct is None
    assert "RECURSIVE_LANGUAGE" in recursive.observed_dimensions
    functional = observe_verbal("Multiplico el número de la figura por 3 y sumo 2, siempre funciona")
    assert {"FUNCTIONAL_LANGUAGE", "MENTIONS_POSITION", "GENERAL_CLAIM"} <= set(functional.observed_dimensions)
    example_only = observe_verbal("Por ejemplo en la figura 2 hay 8")
    assert "EXAMPLE_ONLY" in example_only.observed_dimensions


def test_evaluate_response_dispatches_by_kind_and_representation() -> None:
    q_predict = {"id": "q1", "kind": "predict", "position": 5}
    assert (
        evaluate_response(rule="3*n+2", question=q_predict, representation="NUMERIC", content={"value": 17}).correct
        is True
    )
    q_gen = {"id": "q4", "kind": "generalize"}
    assert (
        evaluate_response(
            rule="3*n+2", question=q_gen, representation="SYMBOLIC", content={"expression": "3n+2"}
        ).correct
        is True
    )
    q_explain = {"id": "q2", "kind": "explain"}
    assert (
        evaluate_response(
            rule="3*n+2", question=q_explain, representation="VERBAL", content={"text": "se suma 3"}
        ).correct
        is None
    )
    q_points = {"id": "q1", "kind": "table", "positions": [1, 2]}
    graphic = evaluate_response(
        rule="3*n+2",
        question=q_points,
        representation="GRAPHIC",
        content={"points": [{"x": 1, "y": 5}, {"x": 2, "y": 8}]},
    )
    assert graphic.correct is True

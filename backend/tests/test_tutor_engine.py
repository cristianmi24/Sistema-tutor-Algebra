"""Motor adaptativo (funciones puras): casos C.43 1–8 y 11, Bayes, DSL de reglas y selección con memoria."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.modules.tutor.bayes import BayesConfig, infer
from app.modules.tutor.defaults import DEFAULT_BAYES_CONFIG, DEFAULT_RULES
from app.modules.tutor.evidence import EventRecord, ScaffoldRecord, extract_evidence
from app.modules.tutor.rules import Rule, RuleContext, evaluate_rules
from app.modules.tutor.scaffolding import ScaffoldCandidate, fading_action, select_scaffold

TASK = "task-1"
RULES = [Rule.from_dict(r) for r in DEFAULT_RULES]
BAYES = BayesConfig.from_dict(DEFAULT_BAYES_CONFIG)
BANK = [
    ScaffoldCandidate("FOC-CHANGE-01", "FOCUSING", 1, ["FIGURAL_PATTERN"], [], {"text": "..."}),
    ScaffoldCandidate("META-PAUSE-01", "METACOGNITIVE", 1, [], [], {"text": "..."}),
    ScaffoldCandidate("GUIDE-RELATE-01", "GUIDING_QUESTION", 2, ["FIGURAL_PATTERN"], [], {"text": "..."}),
    ScaffoldCandidate("SELF-EXPL-01", "SELF_EXPLANATION", 2, [], [], {"text": "..."}),
    ScaffoldCandidate("HINT-STRUCT-01", "HINT", 3, ["FIGURAL_PATTERN"], [], {"text": "..."}),
    ScaffoldCandidate("REPR-TABLE-01", "REPRESENTATION_CHANGE", 4, ["FIGURAL_PATTERN"], [], {"text": "..."}),
    ScaffoldCandidate("RECOV-EXAMPLE-01", "RECOVERY", 5, [], [], {"text": "..."}),
]


def responses(specs: list[tuple[bool | None, str | None, int]], *, extra: list[str] | None = None) -> list[EventRecord]:
    """Construye eventos de respuesta: (correcta, patrón de error, tiempo ms)."""
    base = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
    events: list[EventRecord] = []
    seq = 1
    for i, (correct, pattern, ms) in enumerate(specs):
        events.append(
            EventRecord(
                sequence=seq,
                event_type="STUDENT_RESPONSE" if i == 0 else "STUDENT_REATTEMPT",
                timestamp=base + timedelta(seconds=seq),
                task_id=TASK,
                correct=correct,
                error_pattern=pattern,
                content_key=f"c{i}" if correct or pattern != "OFF_BY_STEP" else "same",
                client_meta={"time_on_task_ms": ms, "clicks": 4},
            )
        )
        seq += 1
    for kind in extra or []:
        events.append(EventRecord(sequence=seq, event_type=kind, timestamp=base + timedelta(seconds=seq), task_id=TASK))
        seq += 1
    return events


def decide(
    events: list[EventRecord],
    *,
    scaffolds: list[ScaffoldRecord] | None = None,
    previous_state: str = "NORMAL",
    candidate: tuple[str | None, int] = (None, 0),
    help_now: bool = False,
):
    evidence = extract_evidence(
        events,
        task_id=TASK,
        scaffolds=scaffolds or [],
        window_size=5,
        expected_time_ms=90000,
        help_requested_now=help_now,
    )
    posterior = infer(BAYES, evidence.discretized())
    result = evaluate_rules(
        RULES,
        RuleContext(
            evidence=evidence,
            posterior=posterior,
            previous_state=previous_state,
            candidate_state=candidate[0],
            candidate_count=candidate[1],
        ),
    )
    return evidence, posterior, result


# --------------------------------------------------------------------------- casos C.43


def test_case_1_good_performance_no_intervention_then_autonomy() -> None:
    evidence, posterior, result = decide(responses([(True, None, 60000)] * 5))
    assert evidence.stable_correct_streak == 5 and evidence.accuracy_band == "HIGH"
    assert posterior.most_likely == "AUTONOMY"
    assert result.state == "AUTONOMY" and result.level == 0 and result.rule_code == "R-AUTONOMY-ZERO"


def test_case_2_isolated_error_is_observed_not_corrected() -> None:
    evidence, _, result = decide(responses([(True, None, 60000), (True, None, 60000), (False, "OFF_BY_STEP", 70000)]))
    assert evidence.error_pattern == "VARIED"
    assert result.level == 0
    assert result.state in {"NORMAL", "AUTONOMY"}


def test_case_3_persistent_errors_need_confirmation_then_microhelp() -> None:
    events = responses([(False, "OTHER", 80000), (False, "WRONG_RATE", 85000)])
    _, _, first = decide(events)
    # Primera evaluación: la regla se cumple pero exige confirmación (min_consecutive=2) → observar.
    assert first.rule_code == "R-DIFFICULTY-MICRO" and first.confirmed is False and first.level == 0
    assert first.candidate_state == "DIFFICULTY" and first.candidate_count == 1
    _, _, second = decide(events, candidate=("DIFFICULTY", 1))
    assert second.confirmed and second.state == "DIFFICULTY" and second.level == 1 and second.intervention == "FOCUSING"


def test_case_4_persistence_after_microhelp_escalates_to_orientation() -> None:
    memory = [ScaffoldRecord("FOC-CHANGE-01", "FOCUSING", 1, "PERSISTED", False, True, created_sequence=2)]
    _, _, result = decide(
        responses([(False, "OTHER", 80000), (False, "WRONG_RATE", 85000), (False, "MISSING_CONSTANT", 90000)]),
        scaffolds=memory,
        previous_state="DIFFICULTY",
    )
    assert result.state == "DIFFICULTY" and result.level == 2 and result.intervention == "GUIDING_QUESTION"
    assert result.rule_code == "R-DIFFICULTY-ORIENT"


def test_case_5_stagnation_triggers_representation_change() -> None:
    same = [(False, "OFF_BY_STEP", 100000)] * 4
    memory = [
        ScaffoldRecord("FOC-CHANGE-01", "FOCUSING", 1, "PERSISTED", False, True, 2),
        ScaffoldRecord("GUIDE-RELATE-01", "GUIDING_QUESTION", 2, "PERSISTED", False, True, 3),
    ]
    evidence, posterior, result = decide(responses(same), previous_state="DIFFICULTY", scaffolds=memory)
    assert evidence.error_pattern == "PERSISTENT" and evidence.repetition_count >= 2
    assert posterior.get("STAGNATION") > 0.45
    assert result.state == "STAGNATION" and result.level == 4 and result.intervention == "REPRESENTATION_CHANGE"


def test_case_6_improvement_after_help_reduces_support() -> None:
    memory = [ScaffoldRecord("FOC-CHANGE-01", "FOCUSING", 1, "IMPROVED", False, True, 2)]
    _, _, result = decide(
        responses([(False, "OTHER", 80000), (True, None, 70000), (True, None, 60000)]),
        scaffolds=memory,
        previous_state="DIFFICULTY",
    )
    assert result.state == "RECOVERY" and result.level == 0 and result.fading == "REDUCE"
    assert fading_action(1, 0, result.fading) == "REDUCE"


def test_case_7_autonomy_withdraws_support() -> None:
    _, _, result = decide(responses([(True, None, 50000)] * 4), previous_state="RECOVERY")
    assert result.state == "AUTONOMY" and result.level == 0


def test_case_8_rejected_help_is_never_repeated() -> None:
    memory = [ScaffoldRecord("GUIDE-RELATE-01", "GUIDING_QUESTION", 2, "REJECTED", True, False, 2)]
    selection = select_scaffold(
        BANK,
        task_type="FIGURAL_PATTERN",
        skill="FUNCTIONAL_RELATION",
        level=2,
        intervention="GUIDING_QUESTION",
        memory=memory,
    )
    assert selection.selected is not None
    assert selection.selected.code != "GUIDE-RELATE-01"
    assert "GUIDE-RELATE-01" in selection.excluded
    twice = [
        ScaffoldRecord("HINT-STRUCT-01", "HINT", 3, "PERSISTED", False, True, 2),
        ScaffoldRecord("HINT-STRUCT-01", "HINT", 3, "PERSISTED", False, True, 4),
    ]
    again = select_scaffold(BANK, task_type="FIGURAL_PATTERN", skill="x", level=3, intervention="HINT", memory=twice)
    assert again.selected is not None and again.selected.code != "HINT-STRUCT-01"


def test_case_9_teacher_intervention_pauses_the_system() -> None:
    events = responses([(False, "OFF_BY_STEP", 90000)] * 4, extra=["TEACHER_INTERVENTION"])
    evidence, _, result = decide(events, previous_state="DIFFICULTY")
    assert evidence.teacher_intervened_recently is True
    assert result.rule_code == "R-TEACHER-PAUSE" and result.level == 0


def test_case_11_slow_time_alone_never_triggers_help() -> None:
    evidence, _, result = decide(responses([(True, None, 400000), (None, None, 500000)]))
    assert evidence.response_time_band == "SLOW"
    assert result.level == 0


def test_help_requested_gets_minimal_orientation_and_escalates_only_if_previous_failed() -> None:
    _, _, first = decide(responses([(False, "OTHER", 70000)]), help_now=True)
    assert first.rule_code == "R-HELP-REQUESTED" and first.level == 2
    memory = [ScaffoldRecord("GUIDE-RELATE-01", "GUIDING_QUESTION", 2, "PERSISTED", False, True, 2)]
    _, _, second = decide(
        responses([(False, "OTHER", 70000), (False, "OTHER", 70000)]),
        scaffolds=memory,
        help_now=True,
        previous_state="DIFFICULTY",
    )
    assert second.rule_code == "R-HELP-REQUESTED-AGAIN" and second.level == 3


def test_impulsivity_requires_fast_streak_and_varied_errors() -> None:
    evidence, _, result = decide(
        responses([(False, "OTHER", 5000), (False, "WRONG_RATE", 6000), (False, "MISSING_CONSTANT", 4000)])
    )
    assert evidence.fast_streak == 3 and evidence.error_pattern == "VARIED"
    assert result.state == "IMPULSIVITY" and result.level == 1 and result.intervention == "METACOGNITIVE"


# --------------------------------------------------------------------------- Bayes y DSL


def test_bayes_posterior_is_normalized_and_configurable() -> None:
    posterior = infer(
        BAYES, {"accuracy_band": "LOW", "error_pattern": "PERSISTENT", "attempt_band": "4+", "repetition_band": "2+"}
    )
    assert abs(sum(posterior.probabilities.values()) - 1.0) < 1e-9
    assert posterior.most_likely == "STAGNATION"
    assert posterior.need_support > 0.7
    unknown = infer(BAYES, {"accuracy_band": "UNKNOWN"})
    assert unknown.probabilities["NORMAL"] == max(unknown.probabilities.values())
    custom = BayesConfig.from_dict({"priors": {"NORMAL": 0.1, "AUTONOMY": 0.9}, "likelihoods": {}})
    assert infer(custom, {}).most_likely == "AUTONOMY"


def test_rule_dsl_operators() -> None:
    evidence, posterior, _ = decide(responses([(False, "OTHER", 80000)] * 2))
    ctx = RuleContext(
        evidence=evidence, posterior=posterior, previous_state="NORMAL", candidate_state=None, candidate_count=0
    )
    rule = Rule.from_dict(
        {
            "code": "T",
            "name": "t",
            "priority": 1,
            "when": {
                "all": [
                    {"evidence": "attempt_count", "gte": 2},
                    {"any": [{"evidence": "accuracy_band", "is": "LOW"}, {"evidence": "accuracy_band", "is": "MID"}]},
                    {"not": {"evidence": "help_requested_now", "is": True}},
                    {"previous_state": "NORMAL"},
                    {"posterior": "AUTONOMY", "lt": 0.9},
                ]
            },
            "then": {"state": "DIFFICULTY", "level": 1, "intervention": "FOCUSING"},
        }
    )
    result = evaluate_rules([rule], ctx)
    assert result.rule_code == "T" and result.level == 1
    none = evaluate_rules([], ctx)
    assert none.level == 0 and none.rule_code is None and "sin intervenir" in none.explanation


def test_selection_prefers_lowest_explicitness_and_unused_types() -> None:
    selection = select_scaffold(
        BANK, task_type="FIGURAL_PATTERN", skill="x", level=1, intervention="FOCUSING", memory=[]
    )
    assert selection.selected is not None and selection.selected.code == "FOC-CHANGE-01"
    used = [ScaffoldRecord("FOC-CHANGE-01", "FOCUSING", 1, "PENDING", False, None, 1)]
    second = select_scaffold(
        BANK, task_type="FIGURAL_PATTERN", skill="x", level=1, intervention="FOCUSING", memory=used
    )
    assert second.selected is not None and second.selected.code == "META-PAUSE-01"
    nothing = select_scaffold(BANK, task_type="FIGURAL_PATTERN", skill="x", level=0, intervention=None, memory=[])
    assert nothing.selected is None

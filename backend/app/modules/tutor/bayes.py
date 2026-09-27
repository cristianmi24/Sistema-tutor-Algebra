"""INTERPRETAR: inferencia bayesiana explícita (naive Bayes discreto) como apoyo ante la incertidumbre.

* Sin entrenamiento, sin datasets, sin redes neuronales: priors y verosimilitudes son configuración
  humana versionada (``learning.bayesian_config``).
* El posterior NO decide: solo alimenta condiciones de las reglas pedagógicas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log
from typing import Any

STATES: tuple[str, ...] = ("NORMAL", "DIFFICULTY", "UNCERTAINTY", "IMPULSIVITY", "STAGNATION", "AUTONOMY")
SUPPORT_STATES: frozenset[str] = frozenset({"DIFFICULTY", "UNCERTAINTY", "STAGNATION"})


@dataclass(slots=True)
class BayesConfig:
    name: str
    version: int
    priors: dict[str, float]
    # likelihoods[evidence_name][state][value] = P(value | state)
    likelihoods: dict[str, dict[str, dict[str, float]]]
    smoothing: float = 0.05
    ignore_unknown: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BayesConfig:
        return cls(
            name=str(data.get("name", "default")),
            version=int(data.get("version", 1)),
            priors={k: float(v) for k, v in dict(data.get("priors", {})).items()},
            likelihoods={
                ev: {st: {val: float(p) for val, p in dict(vals).items()} for st, vals in dict(states).items()}
                for ev, states in dict(data.get("likelihoods", {})).items()
            },
            smoothing=float(data.get("smoothing", 0.05)),
            ignore_unknown=bool(data.get("ignore_unknown", True)),
        )


@dataclass(slots=True)
class Posterior:
    probabilities: dict[str, float]
    need_support: float
    most_likely: str
    evidence_used: list[str] = field(default_factory=list)

    def get(self, state: str) -> float:
        return self.probabilities.get(state, 0.0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "probabilities": {k: round(v, 4) for k, v in self.probabilities.items()},
            "need_support": round(self.need_support, 4),
            "most_likely": self.most_likely,
            "evidence_used": self.evidence_used,
        }


def infer(config: BayesConfig, discretized_evidence: dict[str, str]) -> Posterior:
    """P(S | e1..en) ∝ P(S) · Π P(ei | S), con suavizado de Laplace para valores no configurados."""
    states = [s for s in STATES if s in config.priors] or list(STATES)
    log_scores: dict[str, float] = {}
    used: list[str] = []
    for state in states:
        prior = config.priors.get(state, 1.0 / len(states))
        score = log(max(prior, 1e-9))
        for name, value in discretized_evidence.items():
            table = config.likelihoods.get(name)
            if table is None:
                continue
            if value == "UNKNOWN" and config.ignore_unknown:
                continue
            per_state = table.get(state, {})
            n_values = max(len(per_state), 2)
            raw = per_state.get(value)
            total = sum(per_state.values()) if per_state else 0.0
            # Suavizado: (count + α) / (total + α·k), tratando probabilidades como pesos.
            prob = (
                ((raw or 0.0) + config.smoothing) / (total + config.smoothing * n_values)
                if total > 0
                else 1.0 / n_values
            )
            score += log(max(prob, 1e-9))
            if name not in used:
                used.append(name)
        log_scores[state] = score
    max_score = max(log_scores.values())
    weights = {s: exp(v - max_score) for s, v in log_scores.items()}
    norm = sum(weights.values()) or 1.0
    probabilities = {s: w / norm for s, w in weights.items()}
    need_support = sum(p for s, p in probabilities.items() if s in SUPPORT_STATES)
    most_likely = max(probabilities, key=lambda s: probabilities[s])
    return Posterior(
        probabilities=probabilities, need_support=need_support, most_likely=most_likely, evidence_used=used
    )

"""Siembra de reglas pedagógicas y configuración bayesiana por defecto."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tutor.defaults import DEFAULT_BAYES_CONFIG, DEFAULT_RULES
from app.modules.tutor.models import BayesianConfig, TutorRule


async def seed_tutor_config(db: AsyncSession) -> None:
    for spec in DEFAULT_RULES:
        if await db.scalar(select(TutorRule.id).where(TutorRule.code == spec["code"])) is None:
            db.add(
                TutorRule(
                    code=spec["code"],
                    name=spec["name"],
                    description=spec.get("description"),
                    priority=int(spec.get("priority", 0)),
                    min_consecutive=int(spec.get("min_consecutive", 1)),
                    conditions=spec["when"],
                    actions=spec["then"],
                )
            )
    if await db.scalar(select(BayesianConfig.id).where(BayesianConfig.name == DEFAULT_BAYES_CONFIG["name"])) is None:
        db.add(
            BayesianConfig(
                name=DEFAULT_BAYES_CONFIG["name"],
                version=int(DEFAULT_BAYES_CONFIG["version"]),
                priors=DEFAULT_BAYES_CONFIG["priors"],
                likelihoods=DEFAULT_BAYES_CONFIG["likelihoods"],
                thresholds={**DEFAULT_BAYES_CONFIG["thresholds"], "smoothing": DEFAULT_BAYES_CONFIG["smoothing"]},
            )
        )
    await db.flush()

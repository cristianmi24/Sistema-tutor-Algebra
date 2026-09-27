"""Utilidades de línea de comandos.

python -m app.cli seed-demo   # institución DEMO, cuentas de prueba, documentos legales y catálogo
"""

from __future__ import annotations

import asyncio
import os
import sys

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.seed.demo import (
    create_admin,
    create_researcher,
    create_student,
    create_teacher,
    ensure_institution,
)
from app.seed.legal import seed_legal_documents

DEMO_PASSWORD_ENV = "SEED_DEMO_PASSWORD"  # noqa: S105 - nombre de variable, no un secreto


async def seed_demo() -> None:
    settings = get_settings()
    if settings.is_production and not os.environ.get("SEED_ALLOW_PRODUCTION"):
        print("Rechazado: no se siembran datos de demostración en producción.", file=sys.stderr)
        raise SystemExit(2)
    password = os.environ.get(DEMO_PASSWORD_ENV, "Demo-STI-GA-2026!")
    engine = build_engine(settings)
    factory = build_session_factory(engine)
    async with factory() as db:
        await seed_legal_documents(db, settings)
        institution = await ensure_institution(db, code="DEMO", name="Institución Educativa Demo")
        await create_admin(db, email="admin@demo.edu", password=password)
        await create_teacher(
            db,
            email="docente@demo.edu",
            password=password,
            institution=institution,
            groups=[("7", "A"), ("8", "A"), ("9", "A")],
        )
        await create_researcher(db, email="investigadora@demo.edu", password=password, institution=institution)
        for i, grade in enumerate(["7", "8", "9"], start=1):
            await create_student(
                db,
                username=f"estudiante{i}",
                password=password,
                institution=institution,
                grade=grade,
                group_code="A",
            )
        try:
            from app.seed.catalog import seed_catalog

            await seed_catalog(db)
        except ImportError:
            pass
        await db.commit()
    await engine.dispose()
    print("Datos de demostración creados. Cuentas: admin@demo.edu, docente@demo.edu, investigadora@demo.edu,")
    print(f"estudiante1..3 (contraseña: variable {DEMO_PASSWORD_ENV} o la de demostración).")


async def retention(dry_run: bool) -> None:
    from app.modules.identity.privacy import apply_retention

    settings = get_settings()
    engine = build_engine(settings)
    factory = build_session_factory(engine)
    async with factory() as db:
        affected = await apply_retention(db, dry_run=dry_run)
        if dry_run:
            await db.rollback()
        else:
            await db.commit()
    await engine.dispose()
    print(f"{'[simulación] ' if dry_run else ''}Cuentas anonimizadas: {len(affected)}")


def main(argv: list[str]) -> None:
    if len(argv) < 2 or argv[1] not in {"seed-demo", "retention"}:
        print(__doc__)
        raise SystemExit(1)
    if argv[1] == "seed-demo":
        asyncio.run(seed_demo())
    else:
        asyncio.run(retention(dry_run="--dry-run" in argv))


if __name__ == "__main__":
    main(sys.argv)

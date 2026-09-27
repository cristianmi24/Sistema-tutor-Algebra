"""Documentos legales vigentes (política de privacidad y términos) e instituciones públicas."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import DbDep, SettingsDep
from app.core.errors import NotFoundError
from app.modules.common.enums import LegalDocumentKind
from app.modules.identity.models import Institution, LegalDocument
from app.modules.identity.schemas import InstitutionPublic, LegalDocumentOut
from app.modules.identity.service import required_parties

router = APIRouter()


@router.get("/documents", response_model=list[LegalDocumentOut], summary="Documentos legales vigentes")
async def documents(
    db: DbDep,
    settings: SettingsDep,
    kind: LegalDocumentKind | None = Query(default=None),
    locale: str = Query(default="es-CO", max_length=8),
) -> list[LegalDocumentOut]:
    stmt = select(LegalDocument).where(LegalDocument.is_current.is_(True), LegalDocument.locale == locale)
    if kind is not None:
        stmt = stmt.where(LegalDocument.kind == kind.value)
    docs = list((await db.execute(stmt.order_by(LegalDocument.kind))).scalars())
    if kind is not None and not docs:
        raise NotFoundError("No hay una versión vigente publicada de ese documento.")
    return [
        LegalDocumentOut(
            kind=LegalDocumentKind(doc.kind),
            version=doc.version,
            locale=doc.locale,
            title=doc.title,
            body_markdown=doc.body_markdown,
            published_at=doc.published_at,
        )
        for doc in docs
    ]


@router.get(
    "/institutions",
    response_model=list[InstitutionPublic],
    summary="Instituciones activas (registro)",
)
async def institutions(db: DbDep) -> list[InstitutionPublic]:
    rows = (
        await db.execute(select(Institution).where(Institution.is_active.is_(True)).order_by(Institution.name))
    ).scalars()
    return [InstitutionPublic(code=i.code, name=i.name, required_consent_parties=required_parties(i)) for i in rows]

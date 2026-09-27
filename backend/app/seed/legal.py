"""Documentos legales versionados (política de privacidad y términos) en lenguaje claro."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import utcnow
from app.modules.common.enums import LegalDocumentKind
from app.modules.identity.models import LegalDocument

PRIVACY_POLICY_MD = """# Política de privacidad — STI-GA

## ¿Qué información recogemos?
- Un identificador (usuario o correo institucional), tu grado, tu grupo y, si lo indicas, tu año de nacimiento.
- Lo que haces en las actividades: tus respuestas, cuándo pides ayuda, si la aceptas o no, cómo explicas tu razonamiento y qué representaciones usas.
- **No** recogemos dirección, teléfono, documento de identidad ni fotos.

## ¿Para qué se usa?
- Para que el tutor te acompañe mientras trabajas con patrones y reglas.
- Para una investigación educativa sobre cómo las y los estudiantes construyen generalizaciones algebraicas.

## ¿Quién puede ver tus datos?
- Tu docente ve tus producciones para acompañarte.
- Las personas investigadoras ven tu trabajo **solo con un código** (por ejemplo, STU-014), nunca con tu nombre.
- Tus datos personales se guardan separados de los datos de la investigación.

## ¿Cuánto tiempo se conservan?
- Según el protocolo de tu institución (se indica al registrarte). Después, la información personal se elimina y solo quedan datos con código.

## Tus derechos
- Puedes consultar, corregir o pedir la eliminación de tus datos, y retirar tu participación en la investigación cuando quieras, sin ninguna consecuencia en tus clases.
- Pide ayuda a tu docente o escribe al equipo de investigación de tu institución.

## Menores de edad
- Además de tu aceptación, tu institución puede requerir la autorización de tu madre, padre o acudiente. Hasta entonces puedes usar la plataforma, pero tu información no se incluye en la investigación.
"""

TERMS_MD = """# Términos de uso — STI-GA

1. La plataforma es una herramienta de aprendizaje e investigación educativa. Úsala con respeto.
2. Tu cuenta es personal: no compartas tu contraseña.
3. El tutor ofrece ayudas para que pienses; no te dará las respuestas.
4. Tus docentes pueden ver tus producciones y escribirte mensajes dentro de la plataforma.
5. Puedes dejar de participar en la investigación en cualquier momento avisando a tu docente o al equipo de investigación.
6. La institución y el equipo de investigación cuidan tus datos según la política de privacidad.
"""


async def seed_legal_documents(db: AsyncSession, settings: Settings, *, locale: str = "es-CO") -> None:
    """Crea (si no existen) y marca como vigentes las versiones configuradas."""
    specs = [
        (
            LegalDocumentKind.PRIVACY_POLICY,
            settings.privacy_policy_version,
            "Política de privacidad",
            PRIVACY_POLICY_MD,
        ),
        (LegalDocumentKind.TERMS, settings.terms_version, "Términos de uso", TERMS_MD),
    ]
    for kind, version, title, body in specs:
        existing = await db.scalar(
            select(LegalDocument).where(
                LegalDocument.kind == kind.value,
                LegalDocument.version == version,
                LegalDocument.locale == locale,
            )
        )
        await db.execute(
            update(LegalDocument)
            .where(LegalDocument.kind == kind.value, LegalDocument.locale == locale)
            .values(is_current=False)
        )
        if existing is None:
            db.add(
                LegalDocument(
                    kind=kind.value,
                    version=version,
                    locale=locale,
                    title=title,
                    body_markdown=body,
                    published_at=utcnow(),
                    is_current=True,
                )
            )
        else:
            existing.is_current = True
    await db.flush()

"""Registro central de modelos para Alembic y para ``Base.metadata``.

Importar este módulo garantiza que todas las tablas estén registradas en ``Base.metadata``.
Cada fase añade aquí sus módulos de modelos.
"""

from app.core.database import Base
from app.modules.identity import models as identity_models
from app.modules.ops import models as ops_models

__all__ = ["Base", "identity_models", "ops_models"]

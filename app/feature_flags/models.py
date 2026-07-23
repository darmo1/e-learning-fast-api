from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def now_utc():
    return datetime.now(timezone.utc)


class FeatureFlag(SQLModel, table=True):
    """Flag booleano evaluable en FE y BE (estilo LaunchDarkly simplificado).

    `enabled` es el único estado hoy (on/off global, sin targeting por
    usuario) — suficiente para gatear features en desarrollo o simular
    integraciones externas sin credenciales."""

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True, max_length=80)
    description: str = Field(default="", max_length=500)
    enabled: bool = Field(default=False)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class FeatureFlagEditor(SQLModel, table=True):
    """Lista de usuarios (además de admin/super_admin) autorizados a togglear
    flags. La invita un admin; no depende del catálogo de permisos del CRM
    porque un editor de flags no necesariamente tiene rol de staff (puede ser
    cualquier developer del equipo)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    granted_by_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=now_utc)

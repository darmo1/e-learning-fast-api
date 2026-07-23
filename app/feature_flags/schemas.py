from datetime import datetime

from pydantic import EmailStr, Field
from sqlmodel import SQLModel


class FeatureFlagOut(SQLModel):
    key: str
    description: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class FeatureFlagListOut(SQLModel):
    """Respuesta del listado público: incluye el nivel de acceso del caller
    (anónimo o logueado) para que el FE sepa si mostrar los controles de
    edición sin tener que hacer un segundo request."""

    flags: list[FeatureFlagOut]
    can_edit: bool
    can_manage: bool


class FeatureFlagCreate(SQLModel):
    key: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    description: str = Field(default="", max_length=500)
    enabled: bool = False


class FeatureFlagUpdate(SQLModel):
    enabled: bool


class FeatureFlagEditorOut(SQLModel):
    user_id: int
    email: str
    full_name: str | None
    granted_by_email: str
    created_at: datetime


class FeatureFlagEditorCreate(SQLModel):
    email: EmailStr

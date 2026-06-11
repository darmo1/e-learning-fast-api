import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


def now_utc():
    return datetime.now(timezone.utc)


def new_invite_token():
    return uuid.uuid4().hex


class Company(SQLModel, table=True):
    """Empresa habilitada por el admin para acceso corporativo a cursos."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=120)
    is_active: bool = Field(default=True)
    # Cupos: cuántos trabajadores pueden registrarse con el link de invitación
    max_seats: int = Field(default=10, ge=0)
    # Meta: % de los inscritos que deben completar cada curso habilitado
    completion_goal_pct: float = Field(default=80.0, ge=0, le=100)
    # Token del link de invitación; revocable regenerándolo
    invite_token: str = Field(default_factory=new_invite_token, unique=True, index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class CompanyCourse(SQLModel, table=True):
    """Cursos habilitados para una empresa."""

    __table_args__ = (UniqueConstraint("company_id", "course_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    created_at: datetime = Field(default_factory=now_utc)

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


def _generate_code() -> str:
    """Código público no adivinable para verificar el certificado por URL."""
    return uuid.uuid4().hex


class Certificate(SQLModel, table=True):
    """Certificado de finalización: se emite al completar el 100% del curso."""

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_certificate_user_course"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    code: str = Field(default_factory=_generate_code, unique=True, index=True)
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

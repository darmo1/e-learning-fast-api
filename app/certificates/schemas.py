from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CertificateOut(BaseModel):
    id: int
    code: str
    course_id: int
    course_title: str
    issued_at: datetime


class CertificateVerification(BaseModel):
    """Datos públicos del certificado (página de verificación por code)."""

    code: str
    student_name: str
    course_title: str
    course_category: str
    instructor_name: Optional[str] = None
    issued_at: datetime

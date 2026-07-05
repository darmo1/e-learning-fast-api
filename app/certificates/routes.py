from fastapi import APIRouter, Depends, Path

from app.auth.dependencies import get_current_user
from app.certificates import services
from app.certificates.schemas import CertificateOut, CertificateVerification
from app.common.database import SessionDeep
from app.users.models import User

certificates_router = APIRouter(prefix="/certificates", tags=["certificates"])


@certificates_router.post("/{course_id}", response_model=CertificateOut)
async def issue_certificate(
    course_id: int,
    db: SessionDeep,
    current_user: User = Depends(get_current_user),
):
    """Emite (o devuelve, si ya existe) el certificado del curso completado."""
    return services.issue_certificate(db, current_user, course_id)


@certificates_router.get("/mine", response_model=list[CertificateOut])
async def my_certificates(
    db: SessionDeep,
    current_user: User = Depends(get_current_user),
):
    """Certificados del usuario autenticado."""
    return services.my_certificates(db, current_user)


@certificates_router.get("/verify/{code}", response_model=CertificateVerification)
async def verify_certificate(
    db: SessionDeep,
    code: str = Path(min_length=8, max_length=64),
):
    """Verificación pública de un certificado por su código."""
    return services.verify_certificate(db, code)

from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user
from app.common.database import SessionDeep
from app.courses.models import Course
from app.enrollments.schemas import EnrollmentBase, EnrollmentCreate, EnrollmentResponse
from app.enrollments import services

enrollment_router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@enrollment_router.post("/", response_model=EnrollmentResponse)
async def create_enrollment(
    enrollment: EnrollmentBase,
    db: SessionDeep,
    current_user_from_token: dict = Depends(get_current_user),
):
    """Endpoint para inscribir un usuario en un curso gratuito o corporativo.

    Cursos de pago: solo vía webhook de Mercado Pago (pago aprobado) o si la
    empresa del usuario tiene el curso habilitado."""
    course = db.get(Course, enrollment.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if course.price > 0:
        from app.companies.services import user_has_company_access

        if not user_has_company_access(db, current_user_from_token, course.id):
            raise HTTPException(
                status_code=402,
                detail="Este curso requiere pago: usa el checkout",
            )

    user_id = current_user_from_token.id
    enrollemnt_data = EnrollmentCreate(**enrollment.model_dump(), user_id=user_id)
    new_enrollment = services.enroll_user(db, enrollemnt_data)

    if not new_enrollment:
        raise HTTPException(status_code=409, detail="User already enrolled")
    return new_enrollment



@enrollment_router.get("/user")
async def get_enrollments_by_user(
    db: SessionDeep, 
    current_user_from_token: dict = Depends(get_current_user),
):
    """Endpoint para listar cursos inscritos por usuario"""
    user_id = current_user_from_token.id
    enrollments = services.get_enrollments_by_user(db, user_id)
    return enrollments

"""
GET /enrollments/{user_id} → Listar cursos inscritos por usuario.
DELETE /enrollments/{id} → Desinscribir un usuario de un curso.
"""

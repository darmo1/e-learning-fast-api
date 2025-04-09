from sqlmodel import select
from app.enrollments.models import Enrollment
from app.common.database import SessionDeep
from app.enrollments.schemas import EnrollmentCreate
from sqlalchemy.orm import selectinload


def enroll_user(db: SessionDeep, enrollment: EnrollmentCreate):
    # Verificar si el usuario ya está inscrito en el curso
    statement = select(Enrollment).where(
        Enrollment.user_id == enrollment.user_id,
        Enrollment.course_id == enrollment.course_id,
    )

    existing_enrollment = db.exec(statement).first()
    if existing_enrollment:
        return None  # Ya está inscrito

    new_enrollment = Enrollment(**enrollment.model_dump())

    db.add(new_enrollment)
    db.commit()
    db.refresh(new_enrollment)
    return new_enrollment


def get_enrollments_by_user(db: SessionDeep, user_id: int):
    statement = (
        select(Enrollment)
        .where(Enrollment.user_id == user_id)
        .options(selectinload(Enrollment.course))
    )
    enrollments = db.exec(statement).all()

    if not enrollments:
        return []

    results = []
    for enrollment in enrollments:
        # Serializamos el Enrollment
        enrollment_dict = enrollment.model_dump(exclude={"deleted_at"})

        enrollment_created_at = enrollment_dict.pop("created_at", None)
        enrollment_updated_at = enrollment_dict.pop("updated_at", None)


        enrollment_dict["enrollment_created_at"] = enrollment_created_at
        enrollment_dict["enrollment_updated_at"] = enrollment_updated_at


        # Si tiene curso, anidamos solo los campos que queremos
        if enrollment.course:
            enrollment_dict["course"] = enrollment.course.model_dump(exclude={"id", "price"})
        results.append(enrollment_dict)

    return results

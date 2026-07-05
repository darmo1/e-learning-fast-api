from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.certificates.models import Certificate
from app.courses.models import Course
from app.enrollments.models import Enrollment
from app.lessons.models import Lesson, LessonProgress
from app.users.models import User


def _certificate_out(certificate: Certificate, course_title: str) -> dict:
    return {
        "id": certificate.id,
        "code": certificate.code,
        "course_id": certificate.course_id,
        "course_title": course_title,
        "issued_at": certificate.issued_at,
    }


def issue_certificate(db: Session, user: User, course_id: int) -> dict:
    """Emite el certificado si el usuario completó el 100% del curso.

    Idempotente: si ya existe, devuelve el emitido. Requiere inscripción y que
    el curso tenga al menos una lección.
    """
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    existing = db.exec(
        select(Certificate).where(
            Certificate.user_id == user.id,
            Certificate.course_id == course_id,
        )
    ).first()
    if existing:
        return _certificate_out(existing, course.title)

    enrolled = db.exec(
        select(Enrollment).where(
            Enrollment.user_id == user.id,
            Enrollment.course_id == course_id,
        )
    ).first()
    if not enrolled:
        raise HTTPException(
            status_code=403, detail="Debes estar inscrito en el curso"
        )

    total_lessons = db.exec(
        select(func.count()).select_from(Lesson).where(Lesson.course_id == course_id)
    ).one()
    if total_lessons == 0:
        raise HTTPException(
            status_code=400, detail="Este curso aún no tiene lecciones"
        )

    completed = db.exec(
        select(func.count())
        .select_from(LessonProgress)
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .where(
            LessonProgress.user_id == user.id,
            Lesson.course_id == course_id,
        )
    ).one()

    if completed < total_lessons:
        raise HTTPException(
            status_code=409,
            detail=f"Aún no completas el curso ({completed}/{total_lessons} lecciones)",
        )

    certificate = Certificate(user_id=user.id, course_id=course_id)
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return _certificate_out(certificate, course.title)


def my_certificates(db: Session, user: User) -> list[dict]:
    rows = db.exec(
        select(Certificate, Course.title)
        .join(Course, Course.id == Certificate.course_id)
        .where(Certificate.user_id == user.id)
        .order_by(Certificate.issued_at.desc())
    ).all()
    return [_certificate_out(certificate, title) for certificate, title in rows]


def verify_certificate(db: Session, code: str) -> dict:
    """Verificación pública por código (para compartir/validar el certificado)."""
    row = db.exec(
        select(Certificate, Course, User)
        .join(Course, Course.id == Certificate.course_id)
        .join(User, User.id == Certificate.user_id)
        .where(Certificate.code == code)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")

    certificate, course, student = row
    instructor = db.get(User, course.instructor_id)

    return {
        "code": certificate.code,
        "student_name": student.full_name or student.email.split("@")[0],
        "course_title": course.title,
        "course_category": course.category,
        "instructor_name": instructor.full_name if instructor else None,
        "issued_at": certificate.issued_at,
    }

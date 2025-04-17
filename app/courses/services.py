from fastapi import HTTPException
from sqlmodel import Session, select
from app.courses.models import Course
from app.courses.schemas import CourseCreate, CourseResponse
from app.common.database import SessionDeep
from app.enrollments.models import Enrollment
from datetime import datetime, timezone


def create_course(db: SessionDeep, course: dict) -> CourseResponse:
    db_course = Course(**course)

    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


def update_course(
    db: SessionDeep, course_id: int, updates: dict, token_data: dict
) -> Course:
    db_course = db.get(Course, course_id)

    if not db_course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")


    if db_course.instructor_id != token_data.id:
        raise HTTPException(
            status_code=403, detail="No autorizado para editar este curso"
        )

    for key, value in updates.items():
        setattr(db_course, key, value)

    db_course.updated_at = datetime.now(timezone.utc)

    db.add(db_course)
    db.commit()
    db.refresh(db_course)

    return db_course


def get_course(db: SessionDeep, course_id: int) -> CourseResponse:
    course = db.exec(select(Course).where(Course.id == course_id)).first()
    return course


def get_courses(db: SessionDeep, user_id: int):
    subquery = select(Enrollment.course_id).where(Enrollment.user_id == user_id)
    courses = db.exec(select(Course).where(Course.id.notin_(subquery))).all()
    return courses


def get_all_courses(db: SessionDeep) -> list[CourseResponse]:
    """Obtenemos todos los cursos de la base de datos"""
    courses = db.exec(select(Course)).all()


def get_courses_by_instructor(db: SessionDeep, user_id: int):
    courses = db.exec(select(Course).where(Course.instructor_id == user_id)).all()
    return courses


def delete_course(
    db: SessionDeep, course_id: int, token_data: dict
) -> dict:
    db_course = db.get(Course, course_id)

    if not db_course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    if db_course.instructor_id != token_data.id:
        raise HTTPException(status_code=403, detail="No autorizado para eliminar este curso")

    db.delete(db_course)
    db.commit()

    return {"message": "Curso eliminado exitosamente"}
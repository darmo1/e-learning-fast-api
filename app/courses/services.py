from sqlmodel import Session, select
from app.courses.models import Course
from app.courses.schemas import CourseCreate, CourseResponse
from app.common.database import SessionDeep
from app.enrollments.models import Enrollment


def create_course(db: SessionDeep, course: dict) -> CourseResponse:
    # db_course = Course(
    #     title=course.title,
    #     description=course.description,
    #     price=course.price,
    #     is_active=course.is_active
    # )
    db_course = Course(**course)

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

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.auth.dependencies import get_current_user, require_role
from app.auth.permissions import is_admin_user
from app.common.database import SessionDeep
from app.courses.models import Course
from app.enrollments.models import Enrollment
from app.lessons import services
from app.lessons.models import Lesson, LessonProgress
from app.lessons.schemas import LessonCreate, LessonResponse, LessonUpdate
from app.users.models import User, UserRole

lessons_router = APIRouter(prefix="/lessons", tags=["lessons"])


def _check_course_ownership(db: SessionDeep, course_id: int, user: User) -> Course:
    """Verifica que el curso exista y pertenezca al usuario (o sea admin)."""
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    if course.instructor_id != user.id and not is_admin_user(user):
        raise HTTPException(
            status_code=403, detail="No autorizado para gestionar lecciones de este curso"
        )
    return course


@lessons_router.post("/create", response_model=LessonResponse)
def create_lesson(
    lesson: LessonCreate,
    db: SessionDeep,
    current_user: User = Depends(require_role(UserRole.instructor)),
):
    """Endpoint para crear una lección (solo el instructor dueño del curso)"""
    _check_course_ownership(db, lesson.course_id, current_user)
    return services.create_lesson(db, lesson)


@lessons_router.patch("/edit/{lesson_id}", response_model=LessonResponse)
def update_lesson(
    lesson_id: int,
    lesson_update: LessonUpdate,
    db: SessionDeep,
    current_user: User = Depends(require_role(UserRole.instructor)),
):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")

    _check_course_ownership(db, lesson.course_id, current_user)

    # Impedir mover la lección a un curso ajeno
    if lesson_update.course_id is not None and lesson_update.course_id != lesson.course_id:
        _check_course_ownership(db, lesson_update.course_id, current_user)

    return services.update_lesson(db, lesson_id, lesson_update)


@lessons_router.get("/{course_id}")
def get_lessons_by_course_id(
    course_id: int,
    db: SessionDeep,
    current_user: User = Depends(get_current_user),
):
    """Lecciones completas (con video): solo inscritos, el instructor dueño o admin."""
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    is_owner = course.instructor_id == current_user.id
    if not is_owner and not is_admin_user(current_user):
        enrollment = db.exec(
            select(Enrollment).where(
                Enrollment.user_id == current_user.id,
                Enrollment.course_id == course_id,
            )
        ).first()
        if not enrollment:
            raise HTTPException(
                status_code=403, detail="No estás inscrito en este curso"
            )

    return services.get_lessons_by_course_id(db, course_id)


@lessons_router.get("/{course_id}/demo")
def get_demo_lessons_by_course_id(course_id: int, db: SessionDeep):
    return services.get_demo_lessons_by_course_id(db, course_id)


def _require_enrollment(db: SessionDeep, course_id: int, user: User):
    enrollment = db.exec(
        select(Enrollment).where(
            Enrollment.user_id == user.id,
            Enrollment.course_id == course_id,
        )
    ).first()
    if not enrollment and not is_admin_user(user):
        raise HTTPException(status_code=403, detail="No estás inscrito en este curso")


@lessons_router.post("/complete/{lesson_id}")
def complete_lesson(
    lesson_id: int,
    db: SessionDeep,
    current_user: User = Depends(get_current_user),
):
    """Marca una lección como completada por el usuario (idempotente)."""
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")

    _require_enrollment(db, lesson.course_id, current_user)

    existing = db.exec(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    ).first()
    if not existing:
        db.add(LessonProgress(user_id=current_user.id, lesson_id=lesson_id))
        db.commit()

    return {"lesson_id": lesson_id, "completed": True}


@lessons_router.get("/{course_id}/progress")
def get_course_progress(
    course_id: int,
    db: SessionDeep,
    current_user: User = Depends(get_current_user),
):
    """IDs de lecciones completadas por el usuario en el curso."""
    _require_enrollment(db, course_id, current_user)

    lesson_ids = db.exec(select(Lesson.id).where(Lesson.course_id == course_id)).all()
    completed = db.exec(
        select(LessonProgress.lesson_id).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id.in_(lesson_ids),
        )
    ).all()
    return {
        "course_id": course_id,
        "total_lessons": len(lesson_ids),
        "completed_lesson_ids": list(completed),
    }

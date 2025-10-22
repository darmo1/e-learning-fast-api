from fastapi import APIRouter, HTTPException, Depends
from app.common.database import SessionDeep
from app.lessons.schemas import LessonCreate, LessonResponse, LessonUpdate
from app.lessons import services
from app.auth.dependencies import get_current_user

lessons_router = APIRouter(prefix="/lessons", tags=["lessons"])


@lessons_router.post("/create", response_model=LessonResponse)
def create_lesson(
    lesson: LessonCreate, db: SessionDeep, token_data: dict = Depends(get_current_user)
):
    """Endpoint para crear una lección"""

    return services.create_lesson(db, lesson)

@lessons_router.patch("/edit/{lesson_id}", response_model=LessonResponse)
def update_lesson(
    lesson_id: int,
    lesson_update: LessonUpdate,
    db: SessionDeep,
    token_data: dict = Depends(get_current_user)
):
    return services.update_lesson(db, lesson_id, lesson_update)

@lessons_router.get("/{course_id}")
def get_lessons_by_course_id(course_id: str,  db: SessionDeep, token_data:dict = Depends(get_current_user)):
    return services.get_lessons_by_course_id(db, int(course_id))


@lessons_router.get("/{course_id}/demo")
def get_demo_lessons_by_course_id(course_id: str,  db: SessionDeep):
    return services.get_demo_lessons_by_course_id(db, int(course_id))
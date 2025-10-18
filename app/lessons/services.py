from fastapi import HTTPException
from sqlmodel import SQLModel, select
from app.lessons.models import Lesson
from app.lessons.schemas import LessonCreate, LessonResponse, LessonUpdate
from app.common.database import SessionDeep 
from datetime import datetime, timezone


def create_lesson(db: SessionDeep, lesson: LessonCreate) -> LessonResponse:
   
   result = db.exec(
        select(Lesson.position).where(Lesson.course_id == lesson.course_id)
    ).all()

   max_position = max([pos for pos in result if pos is not None], default=0)
   next_position = max_position + 1

   new_lesson = Lesson(**lesson.model_dump(), position=next_position) 
   db.add(new_lesson)
   db.commit()
   db.refresh(new_lesson)
   return new_lesson

async def get_lesson_by_id(db: SessionDeep, lesson_id: int) -> LessonResponse:
    lesson = db.exec(select(Lesson).where(Lesson.id == lesson_id)).first()
    return lesson


def get_lessons_by_course_id(db: SessionDeep, course_id: int):
    lessons = db.exec(select(Lesson).where(Lesson.course_id == course_id)).all()
    return lessons

def get_demo_lessons_by_course_id(db: SessionDeep, course_id: int):
    lessons = db.exec(select(Lesson).where(Lesson.course_id == course_id)).all()

    demo = [lesson for lesson in lessons if lesson.is_free]
    content = [lesson.model_dump(exclude={"video_url"}) for lesson in lessons]
   
    return {
        "demo": demo,
        "content": content,
    }

def update_lesson(db: SessionDeep, lesson_id: int, lesson_update: LessonUpdate) -> LessonResponse:
    lesson = db.get(Lesson, lesson_id)

    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")

    update_data = lesson_update.model_dump(exclude_unset=True)

    if update_data:
        for key, value in update_data.items():
            setattr(lesson, key, value)

        lesson.updated_at = datetime.now(timezone.utc)

        db.add(lesson)
        db.commit()
        db.refresh(lesson)

    return lesson
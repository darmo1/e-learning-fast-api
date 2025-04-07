from sqlmodel import SQLModel, select
from app.lessons.models import Lesson
from app.lessons.schemas import LessonCreate, LessonResponse
from app.common.database import SessionDeep 


def create_lesson(db: SessionDeep, lesson: LessonCreate) -> LessonResponse:
   new_lesson = Lesson(**lesson.model_dump()) 
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
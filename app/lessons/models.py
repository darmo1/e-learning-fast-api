from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime, timezone
from app.courses.models import Course

def now_utc():
    return datetime.now(timezone.utc)

class Lesson(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    video_url: str
    is_free: bool = Field(default=False)
    course_id: int = Field(foreign_key="course.id")
    position: Optional[int] = None ## Nueva columna para la posición de la lección
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

    course: 'Course' = Relationship(back_populates="lessons")
    comments: List['Comment'] = Relationship(back_populates="lesson")




# class Comment(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     text: str
#     lesson_id: int = Field(foreign_key="lesson.id")
#     lesson: 'Lesson' = Relationship(back_populates="comments")
#     user_id: int = Field(foreign_key="user.id")
#     user: 'User' = Relationship()

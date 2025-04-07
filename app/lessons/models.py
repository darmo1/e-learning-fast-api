from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from app.courses.models import Course


class Lesson(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    video_url: str
    is_free: bool = Field(default=False)
    course_id: int = Field(foreign_key="course.id")
    course: 'Course' = Relationship(back_populates="lessons")
    comments: List['Comment'] = Relationship(back_populates="lesson")

# class Comment(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     text: str
#     lesson_id: int = Field(foreign_key="lesson.id")
#     lesson: 'Lesson' = Relationship(back_populates="comments")
#     user_id: int = Field(foreign_key="user.id")
#     user: 'User' = Relationship()

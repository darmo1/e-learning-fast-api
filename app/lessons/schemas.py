from typing import Optional
from sqlmodel import SQLModel
from datetime import datetime

class LessonBase(SQLModel):
    title: str
    video_url: str
    is_free: bool = False
    description: str
    course_id: int

class LessonCreate(LessonBase):
    pass


class LessonUpdate(SQLModel):
    title: Optional[str] = None
    video_url: Optional[str] = None
    is_free: Optional[bool] = None
    course_id: Optional[int] = None
    description: Optional[str] = None

class LessonResponse(LessonBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True



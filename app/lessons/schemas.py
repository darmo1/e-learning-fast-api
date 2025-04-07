from sqlmodel import SQLModel


class LessonBase(SQLModel):
    title: str
    video_url: str
    is_free: bool = False
    course_id: int

class LessonCreate(LessonBase):
    pass

class LessonResponse(LessonBase):
    id: int

    class Config:
        from_attributes = True
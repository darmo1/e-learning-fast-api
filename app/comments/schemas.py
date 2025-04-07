from sqlmodel import SQLModel

class CommentBase(SQLModel):
    text: str
    user_id: int
    lesson_id: int

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    id: int
